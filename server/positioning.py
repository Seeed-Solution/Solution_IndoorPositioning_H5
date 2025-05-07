# server/positioning.py
import math
from typing import List, Tuple, Optional
import numpy as np
from scipy.optimize import least_squares
import logging # Added for logging

from .models import DetectedBeacon, MiniprogramConfig

log = logging.getLogger(__name__) # Added logger instance

# Basic RSSI to distance calculation
def calculate_distance(rssi: int, tx_power: int, n: float = 2.5) -> float:
    """Estimates distance based on RSSI using the Log-distance path loss model."""
    if rssi == 0:
        return -1.0 # Unable to determine distance
    # Formula: distance = 10^((txPower - RSSI) / (10 * n))
    exponent = (tx_power - rssi) / (10 * n)
    if exponent > 10: # Avoid potential overflow for very weak signals
        return 10000.0 # Return a large distance
    distance = math.pow(10, exponent)
    return distance

# --- NEW: Least Squares Multilateration ---
def multilateration_least_squares(beacons_with_dist: List[Tuple[float, float, float]], initial_guess: Optional[Tuple[float, float]] = None) -> Optional[Tuple[float, float]]:
    """
    Calculates position using least squares optimization based on distances
    to known beacon coordinates.

    Args:
        beacons_with_dist: List of tuples (x, y, distance) for each detected beacon.
        initial_guess: Optional initial guess for the position (x, y). If None, uses the centroid.

    Returns:
        Estimated (x, y) position or None if calculation fails.
    """
    if len(beacons_with_dist) < 3:
        print(f"Multilateration requires at least 3 beacons, got {len(beacons_with_dist)}")
        return None

    beacon_coords = np.array([(b[0], b[1]) for b in beacons_with_dist])
    distances = np.array([b[2] for b in beacons_with_dist])

    def error_func(pos):
        # Calculate the Euclidean distance from the estimated position 'pos' to each beacon
        estimated_distances = np.sqrt(np.sum((beacon_coords - pos)**2, axis=1))
        # Return the difference between measured distances and estimated distances
        return estimated_distances - distances

    if initial_guess is None:
        # Use the centroid of the beacons as an initial guess if none provided
        initial_guess_calc = np.mean(beacon_coords, axis=0)
        # Alternative: Average based on inverse distance squared? (Might be better if distances vary widely)
        # weights = 1.0 / (distances**2)
        # initial_guess_calc = np.average(beacon_coords, axis=0, weights=weights)

    else:
         initial_guess_calc = np.array(initial_guess)

    try:
        result = least_squares(error_func, initial_guess_calc, method='lm') # Levenberg-Marquardt is often good for this

        if result.success:
            return tuple(result.x)
        else:
            print(f"Least squares optimization failed: {result.message}")
            # Try a different initial guess? Maybe centroid even if one was provided?
            # result_centroid = least_squares(error_func, np.mean(beacon_coords, axis=0), method='lm')
            # if result_centroid.success:
            #      print("Optimization succeeded with centroid guess.")
            #      return tuple(result_centroid.x)
            # else:
            #      print(f"Optimization also failed with centroid guess: {result_centroid.message}")
            return None
    except Exception as e:
        print(f"Error during least squares optimization: {e}")
        return None


# REMOVED: Old trilateration function

# --- Update calculate_position ---
def calculate_position(
    detected_beacons: List[DetectedBeacon],
    miniprogram_config: MiniprogramConfig, # Changed from ConfigData to MiniprogramConfig
    last_known_position: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, float]]:
    """
    Main function to calculate position from detected beacons and miniprogram_config.
    Uses least squares multilateration.
    """
    if not miniprogram_config or not miniprogram_config.beacons:
        log.error("Miniprogram configuration not loaded or no beacons defined.")
        return None
    if not miniprogram_config.settings:
        log.error("Miniprogram settings (for signalPropagationFactor) not loaded.")
        return None # Or use a default n, but better to ensure it's loaded

    beacons_with_coords_dist = []
    # Get signalPropagationFactor from the MiniprogramConfig settings
    n = miniprogram_config.settings.signalPropagationFactor

    for detected in detected_beacons:
        beacon_info = None
        if detected.macAddress:
            for cfg_beacon in miniprogram_config.beacons: # Use miniprogram_config.beacons
                # The macAddress field in MiniprogramBeaconConfig is populated via AliasChoices
                if cfg_beacon.macAddress and cfg_beacon.macAddress.lower() == detected.macAddress.lower():
                    beacon_info = cfg_beacon
                    break
        else:
            log.warning(f"Detected beacon report without MAC address: {detected}. Cannot match.")
            continue # Skip this detected beacon if it has no MAC

        if beacon_info:
            if not hasattr(beacon_info, 'txPower') or beacon_info.txPower is None:
                log.warning(f"Beacon {beacon_info.name or beacon_info.macAddress} from config is missing txPower. Skipping.")
                continue

            if detected.rssi > 0 or detected.rssi < -120:
                log.warning(f"Ignoring beacon {beacon_info.name or beacon_info.macAddress} due to implausible RSSI: {detected.rssi}")
                continue

            distance = calculate_distance(detected.rssi, beacon_info.txPower, n)
            if distance > 0.1 and distance < 100:
                beacons_with_coords_dist.append((beacon_info.x, beacon_info.y, distance))
                log.info(f"Using beacon: {beacon_info.name or beacon_info.macAddress}, RSSI: {detected.rssi}, Tx: {beacon_info.txPower}, Dist: {distance:.2f}m")
            else:
                log.warning(f"Ignoring beacon {beacon_info.name or beacon_info.macAddress} due to invalid calculated distance: {distance:.2f}m (RSSI: {detected.rssi}, Tx: {beacon_info.txPower})")
        elif detected.macAddress:
            log.warning(f"Detected beacon with MAC {detected.macAddress} not found in miniprogram_config.")

    if len(beacons_with_coords_dist) < 2: 
        log.info(f"Not enough valid beacon signals ({len(beacons_with_coords_dist)}) for multilateration (need at least 2, 3+ recommended).")
        return None
    # For multilateration_least_squares, it internally checks for < 3 beacons.
    # If we allow 2 beacons here, multilateration_least_squares might return None or fail if it strictly needs 3.
    # Let's adjust the check here to be consistent with multilateration_least_squares or adjust that function.
    # For now, multilateration_least_squares itself handles the < 3 case. 
    # We could provide a simpler 2-beacon positioning if len is 2.
    if len(beacons_with_coords_dist) < 3:
        log.info(f"Multilateration requires at least 3 beacons, got {len(beacons_with_coords_dist)}. Skipping position calculation.")
        # Reverting the previous change of allowing 2 beacons for the least_squares function, 
        # as it's more robust with 3. If only 2 are available, it will be handled by the function itself returning None.
        return None

    estimated_position = multilateration_least_squares(beacons_with_coords_dist, initial_guess=last_known_position)

    if estimated_position:
        log.info(f"Multilateration successful. Estimated position: {estimated_position}")
    else:
        log.info("Multilateration failed to estimate a position.")

    return estimated_position

# --- Kalman Filter Implementation ---
class KalmanFilter2D:
    """
    A simple 2D Kalman filter assuming constant velocity.
    State: [x, y, vx, vy]
    Measurement: [x, y]
    """
    def __init__(self, initial_pos: Tuple[float, float],
                 process_variance: float = 1.0,
                 measurement_variance: float = 10.0):
        # State vector [x, y, vx, vy] - Initialize velocity to 0
        self.x = np.array([[initial_pos[0]], [initial_pos[1]], [0.], [0.]])
        # State covariance matrix P - Initial uncertainty
        self.P = np.eye(4) * 100.0 # Large initial uncertainty

        # Measurement matrix H (maps state to measurement space [x, y])
        self.H = np.array([[1., 0., 0., 0.],
                           [0., 1., 0., 0.]])
        # Measurement noise covariance R
        self.R = np.eye(2) * measurement_variance

        # Process noise covariance Q (uncertainty in the motion model)
        # Increase if velocity changes rapidly are expected
        self.Q = np.eye(4) * process_variance

        # State transition matrix F (defined dynamically in predict)
        self.F = np.eye(4)
        # Identity matrix (used multiple times)
        self.I = np.eye(4)

    def predict(self, dt: float):
        """Predict the next state based on the time delta dt."""
        # Update state transition matrix F for time dt
        self.F = np.array([[1., 0., dt, 0.],
                           [0., 1., 0., dt],
                           [0., 0., 1., 0.],
                           [0., 0., 0., 1.]])

        # Predict state: x_k = F * x_{k-1}
        self.x = self.F @ self.x
        # Predict state covariance: P_k = F * P_{k-1} * F^T + Q
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, measurement: Tuple[float, float]):
        """Update the state based on the measurement [x, y]."""
        z = np.array([[measurement[0]], [measurement[1]]])

        # Measurement residual (innovation): y = z - H * x_k
        y = z - self.H @ self.x
        # Residual covariance: S = H * P_k * H^T + R
        S = self.H @ self.P @ self.H.T + self.R
        # Kalman gain: K = P_k * H^T * S^{-1}
        try:
            S_inv = np.linalg.inv(S)
        except np.linalg.LinAlgError:
            print("Warning: Could not invert S matrix in Kalman filter update. Skipping update.")
            # Handle singular matrix: maybe increase R or P? Or just skip?
            return # Skip update this cycle

        K = self.P @ self.H.T @ S_inv

        # Update state estimate: x_k = x_k + K * y
        self.x = self.x + K @ y
        # Update state covariance: P_k = (I - K * H) * P_k
        self.P = (self.I - K @ self.H) @ self.P

    def get_position(self) -> Tuple[float, float]:
        """Return the filtered position (x, y)."""
        return (self.x[0, 0], self.x[1, 0])

    def get_velocity(self) -> Tuple[float, float]:
         """Return the filtered velocity (vx, vy)."""
         return (self.x[2, 0], self.x[3, 0]) 