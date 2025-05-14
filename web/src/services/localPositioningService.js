import * as webBluetoothService from './webBluetoothService.js';
import {
  calculateDistance,
  setSignalFactor as setCalcSignalFactor, // Alias to avoid conflict if this module has its own setSignalFactor
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

// Placeholder for 2D Kalman Filter if we decide to implement/use one directly here
// let kfInstance = null;

/**
 * Initializes the local positioning service with the current configuration
 * and sets a callback for position updates.
 * @param {object} webUIConfig - The current WebUIConfig object (map, beacons, settings).
 * @param {function} positionUpdateCb - Callback function (newPosition) => { ... }
 */
export function initialize(webUIConfig, positionUpdateCb) {
  currentWebUIConfig = JSON.parse(JSON.stringify(webUIConfig)); // Deep copy
  onPositionUpdateCallback = positionUpdateCb;
  
  if (currentWebUIConfig && currentWebUIConfig.settings) {
    setCalcSignalFactor(currentWebUIConfig.settings.signalPropagationFactor);
  }
  
  initPositionManager((newPos) => {
    latestPosition = newPos;
    if (onPositionUpdateCallback) {
      onPositionUpdateCallback(latestPosition);
    }
  });
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

  const matchedConfiguredBeacon = configuredBeacons.find(cb => 
    cb.uuid.toLowerCase() === beaconData.uuid.toLowerCase() &&
    cb.major === beaconData.major &&
    cb.minor === beaconData.minor
  );

  if (matchedConfiguredBeacon) {
    const distance = calculateDistance(beaconData.rssi, matchedConfiguredBeacon.txPower);
    
    if (distance !== null && distance > 0) {
      const beaconId = `${beaconData.uuid}-${beaconData.major}-${beaconData.minor}`;
      latestBeaconSightings.set(beaconId, {
        ...matchedConfiguredBeacon, // Includes x, y, txPower, displayName, etc.
        rssi: beaconData.rssi,
        distance: distance,
        timestamp: Date.now() // Timestamp of this sighting
      });
      // console.log(`Sighting updated for ${beaconId}, distance: ${distance}`);
    } else {
      // console.log(`Invalid distance for beacon ${beaconData.uuid}, RSSI: ${beaconData.rssi}, Tx: ${matchedConfiguredBeacon.txPower}`);
    }
  } else {
    // console.log('Scanned beacon not in configured list:', beaconData.uuid);
  }
}

/**
 * Collects recent beacon sightings and triggers position calculation.
 */
function calculateCurrentPositionFromSightings() {
  if (!isPositioningActive || latestBeaconSightings.size === 0) {
    // console.log('Skipping position calculation: not active or no sightings.');
    return;
  }

  const now = Date.now();
  const beaconsForPositioning = [];

  for (const [beaconId, sighting] of latestBeaconSightings.entries()) {
    if (now - sighting.timestamp < SIGHTING_TIMEOUT_MS) {
      beaconsForPositioning.push({
        uuid: sighting.uuid, // Or some unique ID from sighting if needed by manager
        major: sighting.major,
        minor: sighting.minor,
        x: sighting.x,
        y: sighting.y,
        distance: sighting.distance,
        // positionManager might also want txPower, rssi for its own debugging or advanced logic
      });
    } else {
      // Remove stale sighting
      latestBeaconSightings.delete(beaconId);
      // console.log(`Removed stale sighting for ${beaconId}`);
    }
  }

  if (beaconsForPositioning.length > 0) { // positionManager's updatePosition will check if there are enough (e.g. >=3)
    // console.log('Attempting to update position with sightings:', beaconsForPositioning.length, beaconsForPositioning);
    updatePosManagerPosition(beaconsForPositioning); // This will call the onPositionUpdateCallback via initPositionManager
  } else {
    // console.log('No fresh beacon sightings to calculate position.');
    // Optionally, if no beacons are fresh, we could set latestPosition to null or a special state
    // and notify the Vue component. For now, positionManager will handle not updating if no valid calculation.
  }
}

/**
 * Starts the local positioning process.
 */
export async function startLocalPositioning() {
  if (!currentWebUIConfig) {
    console.error('LocalPositioningService: Configuration not set. Call initialize first.');
    return false;
  }
  if (isPositioningActive) {
    console.warn('LocalPositioningService: Already active.');
    return true;
  }

  try {
    // TODO: Add options to scan for specific UUIDs if possible/performant
    // For iBeacons, service UUID is usually 0xFEAA (Eddystone) or vendor specific for iBeacon.
    // The webBluetoothService.scanForIBeacons handles filtering by iBeacon structure.
    await webBluetoothService.scanForIBeacons(handleBeaconFound, currentWebUIConfig.beacons.map(b => b.uuid));
    isPositioningActive = true;
    latestBeaconSightings.clear(); // Clear any old sightings
    if (positionCalculationInterval) clearInterval(positionCalculationInterval);
    positionCalculationInterval = setInterval(calculateCurrentPositionFromSightings, CALCULATION_INTERVAL_MS);
    console.log('LocalPositioningService started.');
    return true;
  } catch (error) {
    console.error('Error starting local positioning scan:', error);
    isPositioningActive = false;
    return false;
  }
}

/**
 * Stops the local positioning process.
 */
export function stopLocalPositioning() {
  if (!isPositioningActive) {
    return;
  }
  webBluetoothService.stopScan();
  if (positionCalculationInterval) {
    clearInterval(positionCalculationInterval);
    positionCalculationInterval = null;
  }
  isPositioningActive = false;
  console.log('LocalPositioningService stopped.');
  // latestBeaconSightings.clear(); // Optionally clear sightings on stop
  // latestPosition = null; // Optionally clear last known position
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