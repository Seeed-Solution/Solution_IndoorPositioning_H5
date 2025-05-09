// miniprogram/config/ble_scan_config.js
// This file configures the specific iBeacon UUIDs that the Miniprogram will
// attempt to discover when scanning on iOS devices.
//
// How to use:
// 1. Add the UUIDs of the iBeacons you want to scan for into the array below.
// 2. Ensure each UUID is a string and in the standard format (e.g., "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX").
//
// Example:
// iOSScanUUIDs: [
//   '74278BDA-B644-4520-8F0C-720EAF059935', // Default/Example UUID
//   'MY-OTHER-BEACON-UUID-STRING-HERE-01',
//   'AND-ANOTHER-ONE-FOR-SCANNING-02'
// ]

const iOSScanUUIDs = [
  '74278BDA-B644-4520-8F0C-720EAF059935',
  '74278BDA-B644-4520-8F0C-720EAF059936',
  '74278BDA-B644-4520-8F0C-720EAF059937',
  '74278BDA-B644-4520-8F0C-720EAF059938',
  '74278BDA-B644-4520-8F0C-720EAF059939'
  // Add more UUIDs here as needed for your beacons
];

module.exports = {
  iOSScanUUIDs: iOSScanUUIDs
}; 