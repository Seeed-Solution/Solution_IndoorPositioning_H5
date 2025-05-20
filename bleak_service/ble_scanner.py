import asyncio
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from typing import Callable, List, Optional, Coroutine, Any
import logging

from .models import BeaconData # Assuming models.py is in the same directory

# Configure basic logging
logging.basicConfig(level=logging.INFO) # Reverted to INFO
logger = logging.getLogger(__name__)

APPLE_COMPANY_ID = 0x004C
IBEACON_TYPE = 0x02
IBEACON_EXPECTED_LENGTH = 0x15

class BleScanner:
    def __init__(self,
                 beacon_found_callback: Callable[[BeaconData], Coroutine[Any, Any, None]],
                 notify_callback: Callable[[str, str], Coroutine[Any, Any, None]]):
        self.beacon_found_callback = beacon_found_callback
        self.notify_callback = notify_callback
        self.is_scanning = False
        self._scanner: Optional[BleakScanner] = None
        self._scan_task: Optional[asyncio.Task] = None
        self._current_ignored_macs: List[str] = []

    def _parse_ibeacon_data(self, manufacturer_data: bytes) -> Optional[dict]:
        # logger.debug(f"Attempting to parse iBeacon data: {manufacturer_data.hex()}")
        if not manufacturer_data or len(manufacturer_data) < 2 + 2: # Company ID (2) + Apple Data Header (2)
            # logger.debug("Manufacturer data too short for company ID and Apple header.")
            return None

        try:
            apple_data = manufacturer_data 
            if len(apple_data) < 23: 
                # logger.debug(f"Apple data too short for iBeacon: {len(apple_data)} bytes. Data: {apple_data.hex()}")
                return None

            beacon_type = apple_data[0]
            beacon_data_length = apple_data[1]
            # logger.debug(f"Beacon Type: {beacon_type}, Beacon Data Length: {beacon_data_length}")

            if beacon_type == IBEACON_TYPE and beacon_data_length == IBEACON_EXPECTED_LENGTH:
                uuid_bytes = apple_data[2:18]
                uuid = (
                    uuid_bytes[0:4].hex().upper() + '-' +
                    uuid_bytes[4:6].hex().upper() + '-' +
                    uuid_bytes[6:8].hex().upper() + '-' +
                    uuid_bytes[8:10].hex().upper() + '-' +
                    uuid_bytes[10:16].hex().upper()
                )
                major = int.from_bytes(apple_data[18:20], 'big')
                minor = int.from_bytes(apple_data[20:22], 'big')
                tx_power_calibrated = int.from_bytes(apple_data[22:23], 'big', signed=True)
                
                parsed_result = {
                    "uuid": uuid,
                    "major": major,
                    "minor": minor,
                    "txPowerCalibrated": tx_power_calibrated
                }
                # logger.debug(f"Successfully parsed iBeacon: {parsed_result}")
                return parsed_result
            # else:
                # logger.debug(f"Not an iBeacon: type={beacon_type} (expected {IBEACON_TYPE}), length={beacon_data_length} (expected {IBEACON_EXPECTED_LENGTH})")

        except Exception as e:
            logger.error(f"Error parsing iBeacon data: {e} | Data: {manufacturer_data.hex()}", exc_info=True) # Keep this error log
        return None

    async def _detection_callback(self, device: BLEDevice, advertisement_data: AdvertisementData):
        # logger.info(f"RAW DISCOVERY: Device={device.address}, Name={device.name}, RSSI={advertisement_data.rssi}, MF_Data={advertisement_data.manufacturer_data}") 

        normalized_address = device.address.lower()
        if self._current_ignored_macs and normalized_address in self._current_ignored_macs:
            # logger.debug(f"[Scanner] Ignoring configured beacon by address: {device.address}")
            return

        ibeacon_details = None
        if APPLE_COMPANY_ID in advertisement_data.manufacturer_data:
            # logger.debug(f"Found Apple Manufacturer Data for device {device.address}. Data: {advertisement_data.manufacturer_data[APPLE_COMPANY_ID].hex()}")
            ibeacon_details = self._parse_ibeacon_data(advertisement_data.manufacturer_data[APPLE_COMPANY_ID])

        if not ibeacon_details: 
            return
        
        # logger.info(f"IBEACON PARSED for {device.address}: {ibeacon_details}") 

        beacon = BeaconData(
            id=device.address, 
            address=device.address,
            rssi=advertisement_data.rssi,
            localName=advertisement_data.local_name,
            txPowerAdv=advertisement_data.tx_power, 
            iBeacon=ibeacon_details
        )
        # logger.info(f"SENDING BEACON TO WS: {beacon.model_dump_json()}")
        await self.beacon_found_callback(beacon)

    async def start_scan(self, ignored_macs: Optional[List[str]] = None):
        if self.is_scanning:
            logger.info("Scan is already in progress.")
            await self.notify_callback("info", "Scanning is already in progress.")
            return

        logger.info("Attempting to start BLE scan...")
        self._current_ignored_macs = [mac.lower() for mac in ignored_macs] if ignored_macs else []
        logger.info(f"[Scanner] Starting scan, ignoring MACs: {self._current_ignored_macs}")

        try:
            # Initialize scanner here to ensure it's fresh for each start, 
            # or if Bluetooth adapter state changes.
            self._scanner = BleakScanner(detection_callback=self._detection_callback)
            
            # Start scanning in a separate task
            # Using scanning_mode="active" might be needed on some platforms for more data, but can consume more power.
            # await self._scanner.start() # This would block if not handled in a task
            self._scan_task = asyncio.create_task(self._scanner.start())
            self.is_scanning = True
            logger.info("BLE scanning started.")
            await self.notify_callback("info", "Scanning started.")

        except Exception as e:
            logger.error(f"Error starting scanning: {e}")
            self.is_scanning = False
            self._scanner = None
            await self.notify_callback("error", f"Failed to start scanning: {str(e)}")

    async def stop_scan(self):
        if not self.is_scanning:
            logger.info("Scanning is not active.")
            # await self.notify_callback("info", "Scanning is not active.") # Optional: notify if trying to stop non-active scan
            return

        logger.info("Attempting to stop BLE scan...")
        try:
            if self._scanner:
                await self._scanner.stop()
            if self._scan_task and not self._scan_task.done():
                self._scan_task.cancel()
                try:
                    await self._scan_task
                except asyncio.CancelledError:
                    logger.info("Scan task cancelled.")
            
            self.is_scanning = False
            # self._scanner = None # Clearing the scanner instance. It will be recreated on next start.
            logger.info("BLE scanning stopped.")
            await self.notify_callback("info", "Scanning stopped.")
        except Exception as e:
            logger.error(f"Error stopping scanning: {e}")
            # Even if there's an error, reflect that we attempted to stop.
            self.is_scanning = False 
            await self.notify_callback("error", f"Error stopping scanning: {str(e)}")

    # Optional: Add a cleanup method if needed, e.g., when the application shuts down
    async def cleanup(self):
        if self.is_scanning:
            await self.stop_scan()
        logger.info("BleScanner cleaned up.")

# Example usage (for testing ble_scanner.py directly)
async def main_test():
    async def print_beacon(beacon: BeaconData):
        logger.info(f"CALLBACK - Beacon Found: {beacon.model_dump_json(indent=2)}")

    async def print_notify(type: str, message: str):
        logger.info(f"CALLBACK - Notify: Type={type}, Message='{message}'")

    scanner = BleScanner(print_beacon, print_notify)
    
    logger.info("Starting scan for 15 seconds...")
    await scanner.start_scan()
    await asyncio.sleep(15)
    logger.info("Stopping scan...")
    await scanner.stop_scan()
    logger.info("Scan stopped. Waiting 2 seconds before exiting.")
    await asyncio.sleep(2)
    await scanner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main_test())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.") 