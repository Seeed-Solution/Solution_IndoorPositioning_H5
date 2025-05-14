/**
 * Web Bluetooth API Service
 * 
 * Important Considerations:
 * 1. User Interaction: Web Bluetooth scanning MUST be initiated by a user gesture (e.g., a click).
 * 2. Secure Context: Only works in secure contexts (HTTPS or localhost).
 * 3. Browser Support: Check compatibility (Chrome, Edge, Opera on desktop/Android).
 * 4. Permissions: Users will be prompted to grant Bluetooth access.
 * 5. Experimental API: `requestLEScan` is powerful but may still be experimental in some browsers.
 *    Users might need to enable flags like chrome://flags/#enable-experimental-web-platform-features
 */

class WebBluetoothService {
  constructor() {
    this.activeScan = null;
    this.deviceMap = new Map(); // To keep track of devices and their data
    this.onBeaconFoundCallback = null;
    this.scanAbortController = null; // To abort the scan if needed
  }

  _handleAdvertisementReceived = (event) => {
    // This callback is for requestLEScan.
    const { device, rssi, manufacturerData, serviceData, uuids } = event;
    console.log('Advertisement received from:', device.name || device.id, 'RSSI:', rssi, /* ManData, ServiceData, UUIDs omitted for brevity in this snippet */);

    const iBeaconData = this._parseIBeaconData(manufacturerData, rssi, device);

    if (iBeaconData) {
      const beaconOutput = {
        id: device.id,
        name: device.name || iBeaconData.uuid, 
        rssi: rssi,
        ...iBeaconData 
      };
      console.log('Parsed iBeacon:', beaconOutput);
      if (this.onBeaconFoundCallback) {
        this.onBeaconFoundCallback(beaconOutput);
      }
      this.deviceMap.set(device.id, { device, lastSeen: Date.now(), rssi, iBeaconData });
    }
  };

  async scanForIBeacons(onBeaconFoundCallback, scanDuration = 15000) {
    if (!navigator.bluetooth) {
      throw new Error('Web Bluetooth API is not available in this browser. Please ensure you are using a compatible browser (like Chrome, Edge, or Opera) and that the page is served over HTTPS or localhost.');
    }
    if (typeof navigator.bluetooth.requestLEScan !== 'function') {
      throw new Error('The advanced Bluetooth scanning API (requestLEScan) is not available. This is often because an experimental flag is not enabled in your browser. For Chrome/Edge, please navigate to "chrome://flags/#enable-experimental-web-platform-features", enable the flag, and relaunch your browser.');
    }

    console.log('[scanForIBeacons] Ensuring previous scan is stopped before starting new one.');
    await this.stopScan(); // Ensure stopScan completes if it becomes async due to the delay

    this.onBeaconFoundCallback = onBeaconFoundCallback;
    this.deviceMap.clear();
    this.scanAbortController = new AbortController();

    try {
      console.log('Preparing for Web Bluetooth LE Scan with a short delay (500ms)...');
      await new Promise(resolve => setTimeout(resolve, 500)); 

      console.log('[scanForIBeacons] About to call navigator.bluetooth.requestLEScan()');
      this.activeScan = await navigator.bluetooth.requestLEScan({
        acceptAllAdvertisements: true, 
        keepRepeatedDevices: true, 
      });
      // If we reach here, the promise resolved.
      console.log('[scanForIBeacons] navigator.bluetooth.requestLEScan() successful. Scan object acquired.');

      navigator.bluetooth.addEventListener('advertisementreceived', this._handleAdvertisementReceived, { signal: this.scanAbortController.signal });
      console.log('LE Scan started. Listening for advertisements for ' + scanDuration / 1000 + ' seconds.');

      setTimeout(() => {
        if (this.scanAbortController && !this.scanAbortController.signal.aborted) { 
            console.log('Scan duration elapsed. Stopping scan automatically.');
            this.stopScan(); 
        }
      }, scanDuration);
      
      return true; 

    } catch (error) {
      console.error('[scanForIBeacons] Error during scan initiation or requestLEScan call:', error);
      this.activeScan = null; 
      this.onBeaconFoundCallback = null;
      if (this.scanAbortController && !this.scanAbortController.signal.aborted) {
          this.scanAbortController.abort(); 
      }
      this.scanAbortController = null;
      if (error.name === 'NotFoundError' || error.name === 'NotAllowedError') {
        // This error is typical if the user cancels the permission prompt or Bluetooth is off
        throw new Error('Bluetooth scan request failed. User cancelled, permission denied, or Bluetooth disabled.');
      } else if (error.message && error.message.includes("LEScan formal parameter acceptAllAdvertisements is not yet supported")){ 
        throw new Error('requestLEScan with acceptAllAdvertisements is not supported by this browser. Try enabling experimental web platform features.');
      } else {
        // General error re-throw
        throw error;
      }
    }
  }

  async stopScan() {
    console.log('[stopScan] Attempting to stop scan and clean up...');
    if (this.activeScan) { 
      try {
        this.activeScan.stop();
        console.log('[stopScan] this.activeScan.stop() called.');
      } catch (e) {
        console.error("[stopScan] Error calling this.activeScan.stop():", e);
      }
      this.activeScan = null; 
    }

    if (this.scanAbortController && !this.scanAbortController.signal.aborted) {
        this.scanAbortController.abort(); 
        console.log("[stopScan] Advertisement listener aborted via AbortController.");
    }
    this.scanAbortController = null; 
    this.onBeaconFoundCallback = null; 
    console.log('[stopScan] Cleanup finished.');
  }

  _parseIBeaconData(manufacturerDataMap, rssi, device) {
    if (!manufacturerDataMap) return null;

    // Manufacturer data for Apple is key 0x004C (76 in decimal)
    const appleCompanyId = 0x004C;
    const appleDataView = manufacturerDataMap.get(appleCompanyId);

    if (!appleDataView || appleDataView.byteLength < 23) { 
      // Min length for iBeacon: 2 (type) + 16 (UUID) + 2 (Major) + 2 (Minor) + 1 (TxPower) = 23 bytes
      // Some sources say 25 (prefix + type + length + ...), others say data length is 0x15 (21) + 2 for type+len = 23.
      // Let's stick to byteLength >= 23 for the appleDataView itself.
      return null;
    }

    // iBeacon type is 0x02, data length is 0x15 (21 decimal)
    // These are the first two bytes of the Apple-specific data payload.
    if (appleDataView.getUint8(0) !== 0x02 || appleDataView.getUint8(1) !== 0x15) {
      console.log('Not an iBeacon: Type/Length mismatch. Device ID:', device.id, 'Type:', appleDataView.getUint8(0), 'Length:', appleDataView.getUint8(1));
      return null;
    }

    // Extract UUID (bytes 2-17 of Apple data)
    const uuidBytes = [];
    for (let i = 0; i < 16; i++) {
      uuidBytes.push(appleDataView.getUint8(2 + i).toString(16).padStart(2, '0'));
    }
    const uuid = [
      uuidBytes.slice(0, 4).join(''),
      uuidBytes.slice(4, 6).join(''),
      uuidBytes.slice(6, 8).join(''),
      uuidBytes.slice(8, 10).join(''),
      uuidBytes.slice(10, 16).join('')
    ].join('-').toUpperCase();

    // Extract Major (bytes 18-19 of Apple data)
    const major = appleDataView.getUint16(18, false); // false for big-endian

    // Extract Minor (bytes 20-21 of Apple data)
    const minor = appleDataView.getUint16(20, false); // false for big-endian

    // Extract Tx Power (measured power at 1m, byte 22 of Apple data)
    const txPower = appleDataView.getInt8(22);

    return { uuid, major, minor, txPower, type: 'ibeacon', rssi, deviceId: device.id, deviceName: device.name };
  }

  // Disconnect (not typically used for passive scanning, but good to have if connecting later)
  async disconnectDevice(deviceId) {
    // This function would need to find the device object if we were managing connections.
    // For requestLEScan, there's no persistent connection to a single device unless we initiate it.
    console.warn('disconnectDevice is not directly applicable to passive LE scanning model. Call stopScan() to halt all scanning.');
  }

  // This disconnect method was for a single connected device, which is not the model for requestLEScan.
  // Keeping it commented out as a reference if direct connection is added later.
  /*
  async disconnect() {
    if (this.device && this.device.gatt.connected) {
      console.log('Disconnecting from device...');
      this.device.gatt.disconnect();
    } else {
      console.log('No device connected or already disconnected.');
    }
  }
  */
}

export default new WebBluetoothService(); 