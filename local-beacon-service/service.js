const WebSocket = require('ws');
const noble = require('@abandonware/noble');

const WSS_PORT = 8081;

console.log('Attempting to start WebSocket server and initialize Noble...');

// WebSocket Server Setup
const wss = new WebSocket.Server({ port: WSS_PORT });

wss.on('listening', () => {
    console.log(`WebSocket server started on ws://localhost:${WSS_PORT}`);
});

wss.on('connection', (ws) => {
    console.log('Client connected to WebSocket server');

    ws.on('message', (message) => {
        console.log('Received message from client:', message.toString());
        try {
            const parsedMessage = JSON.parse(message.toString());
            handleClientCommand(ws, parsedMessage);
        } catch (error) {
            console.error('Failed to parse message or handle command:', error);
            ws.send(JSON.stringify({ type: 'error', message: 'Invalid command format.' }));
        }
    });

    ws.on('close', () => {
        console.log('Client disconnected');
        // Consider stopping scan if no clients are connected
        // if (wss.clients.size === 0) {
        //     stopScanning();
        // }
    });

    ws.on('error', (error) => {
        console.error('WebSocket error:', error);
    });

    ws.send(JSON.stringify({ type: 'info', message: 'Successfully connected to beacon scanning service.' }));
});

wss.on('error', (error) => {
    console.error('WebSocket server error:', error);
    if (error.code === 'EADDRINUSE') {
        console.error(`Port ${WSS_PORT} is already in use. Please ensure no other application is using this port.`);
    }
});

// Noble (BLE) Setup and Control
let isScanning = false;
let currentIgnoredMacs = []; // Added to store MACs to ignore

noble.on('stateChange', async (state) => {
    console.log('Noble state changed to:', state);
    if (state === 'poweredOn') {
        // Noble is ready, but don't start scanning automatically.
        // Wait for a command from the client.
        console.log('Bluetooth adapter powered on and ready.');
    } else {
        console.log('Bluetooth adapter not powered on. Current state:', state);
        if (isScanning) {
            await stopScanning();
        }
    }
});

noble.on('discover', (peripheral) => {
    // console.log('Discovered peripheral:', peripheral.advertisement.localName, peripheral.address, peripheral.rssi);
    const advertisement = peripheral.advertisement;
    let iBeaconDetails = null;

    // Attempt to parse iBeacon data from manufacturerData
    if (advertisement.manufacturerData && advertisement.manufacturerData.length >= 2) {
        if (advertisement.manufacturerData.length >= 4) { 
            const companyId = advertisement.manufacturerData.readUInt16LE(0);
            if (companyId === 0x004C && advertisement.manufacturerData.length >= 2 + 23) { 
                const appleData = advertisement.manufacturerData.slice(2);
                const beaconType = appleData.readUInt8(0);
                const beaconDataLength = appleData.readUInt8(1);
                if (beaconType === 0x02 && beaconDataLength === 0x15) {
                    const uuidBytes = [];
                    for (let i = 0; i < 16; i++) {
                        uuidBytes.push(appleData.readUInt8(2 + i).toString(16).padStart(2, '0'));
                    }
                    const uuid = [
                        uuidBytes.slice(0, 4).join(''),
                        uuidBytes.slice(4, 6).join(''),
                        uuidBytes.slice(6, 8).join(''),
                        uuidBytes.slice(8, 10).join(''),
                        uuidBytes.slice(10, 16).join('')
                    ].join('-').toUpperCase();
                    const major = appleData.readUInt16BE(18);
                    const minor = appleData.readUInt16BE(20);
                    const txPowerCalibrated = appleData.readInt8(22);
                    iBeaconDetails = {
                        uuid: uuid,
                        major: major,
                        minor: minor,
                        txPowerCalibrated: txPowerCalibrated
                    };
                }
            }
        }
    }

    if (!iBeaconDetails) {
        return; 
    }

    // Check if this beacon's ID (MAC address) is in the ignore list
    if (currentIgnoredMacs && currentIgnoredMacs.includes(peripheral.id)) {
        // console.log(`[Service] Ignoring configured beacon: ${peripheral.id} (MAC: ${peripheral.address})`);
        return; // Skip sending this beacon
    }

    const beaconData = {
        id: peripheral.id, 
        address: peripheral.address, 
        rssi: peripheral.rssi,
        localName: advertisement.localName,
        txPowerAdv: advertisement.txPowerLevel, 
        iBeacon: iBeaconDetails, 
    };

    // Send data to all connected clients
    wss.clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({ type: 'beacon', data: beaconData }));
        }
    });
});

async function startScanning(ignoredMacs = []) {
    if (noble.state !== 'poweredOn') {
        console.warn('Cannot start scanning, Noble not powered on. State:', noble.state);
        wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({ type: 'error', message: 'Bluetooth adapter not ready or powered off.' }));
            }
        });
        return;
    }
    if (isScanning) {
        console.log('Scanning is already in progress.');
        return;
    }
    try {
        currentIgnoredMacs = ignoredMacs; // Set the ignore list
        console.log('[Service] Starting scan, ignoring MACs:', currentIgnoredMacs);

        await noble.startScanningAsync([], true); // Scan for all services, allow duplicates
        isScanning = true;
        console.log('BLE scanning started.');
        wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({ type: 'info', message: 'Scanning started.' }));
            }
        });
    } catch (error) {
        console.error('Error starting scanning:', error);
        isScanning = false;
        wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({ type: 'error', message: 'Failed to start scanning.' }));
            }
        });
    }
}

async function stopScanning() {
    if (!isScanning) {
        console.log('Scanning is not active.');
        return;
    }
    try {
        await noble.stopScanningAsync();
        isScanning = false;
        console.log('BLE scanning stopped.');
        wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({ type: 'info', message: 'Scanning stopped.' }));
            }
        });
    } catch (error) {
        console.error('Error stopping scanning:', error);
        // Notify clients about the error if needed
    }
}

function handleClientCommand(ws, commandObj) {
    console.log('Handling command object:', commandObj);
    const cmd = commandObj.command ? String(commandObj.command) : null;
    const ignoredMacAddresses = commandObj.ignoredMacAddresses || []; // Get ignored list

    console.log('Extracted command string:', cmd);
    console.log('Ignored MAC addresses from command:', ignoredMacAddresses);

    switch (cmd) {
        case 'startScan':
            console.log('Received startScan command');
            startScanning(ignoredMacAddresses); // Pass ignored list to startScanning
            break;
        case 'stopScan':
            console.log('Received stopScan command');
            stopScanning();
            break;
        default:
            console.log('Unknown command string after processing:', cmd);
            ws.send(JSON.stringify({ type: 'error', message: 'Unknown command.' }));
    }
}

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\nGracefully shutting down...');
    if (isScanning) {
        await stopScanning();
    }
    if (noble.state === 'poweredOn') {
       // noble.stopScanning(); // Ensure it's stopped if not using async
    }
    wss.close(() => {
        console.log('WebSocket server closed.');
        process.exit(0);
    });
    // Force exit if not closed within a timeout
    setTimeout(() => process.exit(1), 5000);
});

console.log('Service script loaded. Waiting for Noble state and WebSocket connections.'); 
console.log('Service script loaded. Waiting for Noble state and WebSocket connections.'); 