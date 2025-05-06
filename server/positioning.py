# server/positioning.py
import math
from typing import List, Tuple, Optional
import numpy as np
from scipy.optimize import least_squares

from .models import DetectedBeacon, ConfigData

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
    config: ConfigData,
    last_known_position: Optional[Tuple[float, float]] = None # Added for initial guess
    ) -> Optional[Tuple[float, float]]:
    """
    Main function to calculate position from detected beacons and config.
    Uses least squares multilateration.
    """
    if not config:
        print("Error: Configuration not loaded.")
        return None

    beacons_with_coords_dist = []
    n = config.settings.signalPropagationFactor

    for detected in detected_beacons:
        beacon_info = None
        for cfg_beacon in config.beacons:
            # Compare MAC addresses (case-insensitive recommended)
            if (cfg_beacon.macAddress.lower() == detected.macAddress.lower() and
                cfg_beacon.major == detected.major and # Keep major/minor check if used
                cfg_beacon.minor == detected.minor):
                beacon_info = cfg_beacon
                break

        if beacon_info:
            # Filter out nonsensical RSSI values early? e.g., > 0 or < -100?
            if detected.rssi > 0 or detected.rssi < -120:
                 print(f"Warning: Ignoring beacon {beacon_info.name or detected.macAddress} due to implausible RSSI: {detected.rssi}")
                 continue

            distance = calculate_distance(detected.rssi, beacon_info.txPower, n)
            if distance > 0 and distance < 200: # Use only valid distances within a reasonable range (e.g., < 200m)
                beacons_with_coords_dist.append((beacon_info.x, beacon_info.y, distance))
            else:
                print(f"Warning: Ignoring beacon {beacon_info.name or detected.macAddress} due to invalid calculated distance: {distance} (RSSI: {detected.rssi}, Tx: {beacon_info.txPower})")
        else:
             print(f"Warning: Detected beacon {detected.macAddress}/{detected.major}/{detected.minor} not found in config.")


    if len(beacons_with_coords_dist) < 3:
        print(f"Not enough valid beacon signals ({len(beacons_with_coords_dist)}) for multilateration.")
        return None

    # --- Perform Multilateration ---
    # Use the last known position as an initial guess for the optimization
    estimated_position = multilateration_least_squares(beacons_with_coords_dist, initial_guess=last_known_position)

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