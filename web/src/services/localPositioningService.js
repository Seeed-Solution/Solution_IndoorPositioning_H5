// import localBeaconService from './webBluetoothService.js'; // DELETED FILE - This service now manages its own WebSocket connection for local positioning.
import {
  calculateDistance,
  setSignalFactor as setCalcSignalFactor,
  // Import other necessary calculation functions if directly used, e.g., trilateration, leastSquaresPositioning
} from '../utils/positioning/positionCalculator.js';
import {
  init as initPositionManager,
  updatePosition as updatePosManagerPosition,
  getCurrentPosition as getPosManagerCurrentPosition,
  // Import other necessary manager functions
} from '../utils/positioning/positionManager.js';
// KalmanFilter might be used here later, or positionManager handles smoothing
// import KalmanFilter from '../utils/positioning/kalmanFilter.js';

let currentWebUIConfig = null;
let isPositioningActive = false;
let latestPosition = null;
let onPositionUpdateCallback = null; // Callback to notify Vue component of position changes

// Buffer for recent beacon sightings: Map<beaconId, {rssi, distance, x, y, timestamp, ...otherConfiguredBeaconProps}>
// beaconId could be a composite key like `${uuid}-${major}-${minor}`
const latestBeaconSightings = new Map();
const SIGHTING_TIMEOUT_MS = 5000; // Consider a beacon sighting stale after 5 seconds
let positionCalculationInterval = null;
const CALCULATION_INTERVAL_MS = 1500; // Calculate position every 1.5 seconds

let serviceStatusCallbackForPositioning = null;

/**
 * Handles status updates from the LocalBeaconService, specifically for scans initiated by positioning.
 * @param {object} status - The status object (e.g., { type: 'error', message: '...' })
 */
function handlePositioningServiceStatusUpdate(status) {
  console.log('[LocalPositioningService] Status from LocalBeaconService:', status);
  if (status.type === 'error') {
    console.error(`[LocalPositioningService] Error during scan: ${status.message}`);
    // If scan failed to start or a critical error occurred, stop positioning attempts for this session.
    if (isPositioningActive && (status.message.includes('Failed to start scan') || status.message.includes('Bluetooth adapter not ready'))) {
      console.warn('[LocalPositioningService] Scan failed to start via local service. Stopping positioning.');
      // Effectively stop the positioning part, as scan won't run.
      // The localBeaconService itself might try to reconnect if it's a connection issue.
      if (positionCalculationInterval) clearInterval(positionCalculationInterval);
      isPositioningActive = false; // Mark as inactive as scan isn't running
       // Optionally notify UI through a dedicated callback if this service needs to report critical errors upwards
      if (serviceStatusCallbackForPositioning) serviceStatusCallbackForPositioning('error', 'Failed to start beacon scanning for positioning.');
    }
  } else if (status.type === 'info') {
    if (status.message === 'Scanning started.') {
      console.log('[LocalPositioningService] Confirmed: Scan started via local service for positioning.');
      // The isPositioningActive flag is already true if we reached here after a successful startScan call.
      // We could use this point to be absolutely sure.
    } else if (status.message === 'Scanning stopped.') {
      console.log('[LocalPositioningService] Confirmed: Scan stopped via local service for positioning.');
      // isPositioningActive should be false if stopLocalPositioning was called.
    }
  }
  // Also handle 'disconnected' from the main service connection if it affects positioning
  // This might be better handled by a global status listener set in initialize.
}

/**
 * Global status handler for the LocalBeaconService connection itself.
 */
function handleGlobalServiceStatus(status) {
    console.log('[LocalPositioningService] Global LocalBeaconService Status:', status.type, status.message);
    if (status.type === 'disconnected' && isPositioningActive) {
        console.warn('[LocalPositioningService] LocalBeaconService disconnected while positioning was active. Stopping scan and calculation.');
        stopLocalPositioning(); // This will call localBeaconService.stopScan()
        if (serviceStatusCallbackForPositioning) serviceStatusCallbackForPositioning('error', 'Beacon scanning service disconnected.');
    }
    // Could also inform UI if connection is lost and not re-established, affecting ability to start positioning.
}

/**
 * Initializes the local positioning service with the current configuration
 * and sets a callback for position updates.
 * @param {object} webUIConfig - The current WebUIConfig object (map, beacons, settings).
 * @param {function} positionUpdateCb - Callback function (newPosition) => { ... }
 */
export function initialize(webUIConfig, positionUpdateCb, statusCb) {
  currentWebUIConfig = JSON.parse(JSON.stringify(webUIConfig)); // Deep copy
  onPositionUpdateCallback = positionUpdateCb;
  serviceStatusCallbackForPositioning = statusCb; // Callback to inform UI about positioning-specific status/errors
  
  if (currentWebUIConfig && currentWebUIConfig.settings) {
    setCalcSignalFactor(currentWebUIConfig.settings.signalPropagationFactor);
  }
  
  initPositionManager((newPos) => {
    latestPosition = newPos;
    if (onPositionUpdateCallback) {
      onPositionUpdateCallback(latestPosition);
    }
  });

  // Connect to localBeaconService if not already connected by another part of the app.
  // The service itself is a singleton and handles multiple connect calls.
  // Pass a global status handler that can react to disconnections affecting positioning.
  // if (!localBeaconService.isConnected()) { // Temporarily comment out
  //     console.log('[LocalPositioningService] Attempting to connect to LocalBeaconService during initialization.');
  //     localBeaconService.connect(handleGlobalServiceStatus, null); // No dedicated beacon handler here, scan will set its own
  // } else {
  //     console.log('[LocalPositioningService] LocalBeaconService already connected.');
  // }
  console.log('LocalPositioningService initialized.');
}

/**
 * Handles a beacon found event from the WebBluetoothService.
 * @param {object} beaconData - The beacon data from WebBluetoothService (uuid, major, minor, rssi, device, etc.)
 */
function handleBeaconFound(beaconData) {
  if (!isPositioningActive || !currentWebUIConfig || !currentWebUIConfig.beacons) {
    return;
  }

  const configuredBeacons = currentWebUIConfig.beacons;
  // const settings = currentWebUIConfig.settings; // settings.signalPropagationFactor is already set by setCalcSignalFactor

  // beaconData is now the adapted format from localBeaconService
  // { id, name, rssi, uuid, major, minor, txPower, type, deviceId, deviceName }
  if (beaconData.type !== 'ibeacon' || !beaconData.uuid) {
      // console.log('[LocalPositioningService] Received non-iBeacon or iBeacon without UUID, skipping:', beaconData.id);
      return;
  }

  const matchedConfiguredBeacon = configuredBeacons.find(cb => 
    cb.uuid.toLowerCase() === beaconData.uuid.toLowerCase() &&
    cb.major === beaconData.major &&
    cb.minor === beaconData.minor
  );

  if (matchedConfiguredBeacon) {
    // Use beaconData.txPower which is txPowerCalibrated from the iBeacon advertisement
    const distance = calculateDistance(beaconData.rssi, beaconData.txPower);
    
    if (distance !== null && distance > 0) {
      const beaconId = `${beaconData.uuid}-${beaconData.major}-${beaconData.minor}`;
      latestBeaconSightings.set(beaconId, {
        ...matchedConfiguredBeacon,
        rssi: beaconData.rssi,
        distance: distance,
        timestamp: Date.now()
      });
    } 
  } 
}

/**
 * Collects recent beacon sightings and triggers position calculation.
 */
function calculateCurrentPositionFromSightings() {
  if (!isPositioningActive) return;

  const activeSightings = [];
  const now = Date.now();
  for (const [beaconId, sighting] of latestBeaconSightings.entries()) {
    if ((now - sighting.timestamp) < SIGHTING_TIMEOUT_MS) {
      activeSightings.push(sighting);
    } else {
      latestBeaconSightings.delete(beaconId); 
    }
  }

  if (activeSightings.length > 0) {
    // Pass { x, y, distance } for each beacon
    const beaconPositionsForCalc = activeSightings.map(s => ({ x: s.x, y: s.y, distance: s.distance }));
    updatePosManagerPosition(beaconPositionsForCalc, currentWebUIConfig.settings);
  } else {
    // No active beacons, maybe send a null position or last known?
    // updatePosManagerPosition([], currentWebUIConfig.settings); // Clears position if no beacons
  }
}

/**
 * Starts the local positioning process.
 */
export async function startLocalPositioning() {
  if (!currentWebUIConfig) {
    console.error('LocalPositioningService: Configuration not set. Call initialize first.');
    if (serviceStatusCallbackForPositioning) serviceStatusCallbackForPositioning('error', 'Configuration not set.');
    return false;
  }
  if (isPositioningActive) {
    console.warn('LocalPositioningService: Already active.');
    return true;
  }

  // if (!localBeaconService.isConnected()) { // Temporarily comment out
  //   console.warn('LocalPositioningService: LocalBeaconService is not connected. Attempting to connect...');
  //   if (serviceStatusCallbackForPositioning) serviceStatusCallbackForPositioning('info', 'Connecting to beacon service...');
  //   localBeaconService.connect(handleGlobalServiceStatus, null);
  //   await new Promise(resolve => setTimeout(resolve, 1000)); 

  //   if (!localBeaconService.isConnected()) {
  //       console.error('LocalPositioningService: Failed to connect to LocalBeaconService. Cannot start positioning.');
  //       if (serviceStatusCallbackForPositioning) serviceStatusCallbackForPositioning('error', 'Failed to connect to beacon scanning service.');
  //       return false;
  //   }
  // }

  try {
    // await localBeaconService.startScan(handleBeaconFound, handlePositioningServiceStatusUpdate); // Temporarily comment out
    console.log('[LocalPositioningService] Skipping localBeaconService.startScan for now.');
    isPositioningActive = true;
    latestBeaconSightings.clear();
    if (positionCalculationInterval) clearInterval(positionCalculationInterval);
    positionCalculationInterval = setInterval(calculateCurrentPositionFromSightings, CALCULATION_INTERVAL_MS);
    console.log('LocalPositioningService: Start scan command sent. Waiting for server confirmation.');
    if (serviceStatusCallbackForPositioning) serviceStatusCallbackForPositioning('info', 'Positioning started. Scanning for beacons...');
    return true;
  } catch (error) {
    console.error('LocalPositioningService: Error sending startScan command to local service:', error);
    isPositioningActive = false;
    if (serviceStatusCallbackForPositioning) serviceStatusCallbackForPositioning('error', `Failed to start beacon scan: ${error.message}`);
    return false;
  }
}

/**
 * Stops the local positioning process.
 */
export function stopLocalPositioning() {
  // if (!isPositioningActive && !localBeaconService.isScanActive()) { // Temporarily comment out
  //   console.log('LocalPositioningService: Not active or scan not running on service.');
  //   return;
  // }
  
  // localBeaconService.stopScan(); // Temporarily comment out
  console.log('[LocalPositioningService] Skipping localBeaconService.stopScan for now.');
  
  if (positionCalculationInterval) {
    clearInterval(positionCalculationInterval);
    positionCalculationInterval = null;
  }
  isPositioningActive = false; // Mark as inactive immediately
  console.log('LocalPositioningService: Stop scan command sent.');
  if (serviceStatusCallbackForPositioning) serviceStatusCallbackForPositioning('info', 'Positioning stopped.');
  // latestBeaconSightings.clear(); // Optionally clear sightings
}

/**
 * Gets the last calculated position.
 * @returns {object | null} The last position object or null.
 */
export function getLatestCalculatedPosition() {
  return latestPosition;
}

/**
 * Updates the configuration used by the service, e.g., if beacons or settings change.
 * @param {object} webUIConfig 
 */
export function updateConfiguration(newWebUIConfig) {
  console.log("LocalPositioningService: Configuration updated.");
  currentWebUIConfig = JSON.parse(JSON.stringify(newWebUIConfig));
  if (currentWebUIConfig && currentWebUIConfig.settings) {
    setCalcSignalFactor(currentWebUIConfig.settings.signalPropagationFactor);
  }
  // Re-initialize position manager or other components if necessary
  // For now, just updating the config and signal factor.
  // If `initPositionManager` clears state, we might not want to call it here unless stopping/starting.
} 