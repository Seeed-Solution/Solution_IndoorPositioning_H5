import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Set

from .models import ClientCommand, WebSocketMessage, BeaconData
from .ble_scanner import BleScanner

app = FastAPI()

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()
scanner: BleScanner = None # Will be initialized when needed

WSS_PORT = 8081 # Matching the old service for now

async def beacon_data_sender(beacon: BeaconData):
    """Sends beacon data to all connected WebSocket clients."""
    message = WebSocketMessage(type="beacon", data=beacon)
    for connection in list(active_connections): # Iterate over a copy
        try:
            await connection.send_json(message.model_dump(exclude_none=True))
        except Exception as e:
            print(f"Error sending to client: {e}")
            # Handle broken connections if necessary, though FastAPI might handle it
            # active_connections.remove(connection) # Or mark for removal

async def notify_clients(message_type: str, text_message: str):
    """Sends an info or error message to all connected WebSocket clients."""
    message = WebSocketMessage(type=message_type, message=text_message)
    for connection in list(active_connections):
        try:
            await connection.send_json(message.model_dump(exclude_none=True))
        except Exception as e:
            print(f"Error sending notification to client: {e}")

@app.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    global scanner
    await websocket.accept()
    active_connections.add(websocket)
    print(f"Client connected. Total clients: {len(active_connections)}")
    try:
        await websocket.send_json(WebSocketMessage(type="info", message="Successfully connected to beacon scanning service.").model_dump())

        if scanner is None:
            # Initialize scanner on first connection or if it was stopped and cleared
            scanner = BleScanner(beacon_found_callback=beacon_data_sender, notify_callback=notify_clients)

        while True:
            try:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)
                print(f"Received message from client: {data}")
                cmd = ClientCommand(**data)

                if cmd.command == "startScan":
                    if scanner:
                        await notify_clients("info", "Scan command received. Starting scan...")
                        # Pass ignored MACs to the scanner
                        await scanner.start_scan(cmd.ignoredMacAddresses)
                    else:
                        await websocket.send_json(WebSocketMessage(type="error", message="Scanner not initialized.").model_dump())

                elif cmd.command == "stopScan":
                    if scanner:
                        await notify_clients("info", "Stop command received. Stopping scan...")
                        await scanner.stop_scan()
                    else:
                        await websocket.send_json(WebSocketMessage(type="error", message="Scanner not initialized or not scanning.").model_dump())
                else:
                    await websocket.send_json(WebSocketMessage(type="error", message="Unknown command.").model_dump())

            except WebSocketDisconnect:
                print("Client disconnected (WebSocketDisconnect)")
                break # Exit loop on disconnect
            except json.JSONDecodeError:
                print("Invalid JSON received from client.")
                await websocket.send_json(WebSocketMessage(type="error", message="Invalid command format. Expected JSON.").model_dump())
            except Exception as e:
                print(f"Error processing client message: {e}")
                await websocket.send_json(WebSocketMessage(type="error", message=f"Server error: {str(e)}").model_dump())
                # Potentially break or handle specific errors

    finally:
        active_connections.remove(websocket)
        print(f"Client disconnected. Total clients: {len(active_connections)}")
        # if not active_connections and scanner: # If no clients are connected, stop scanning
        #     print("No clients connected. Stopping scan.")
        #     await scanner.stop_scan()
            # Optionally, set scanner to None here if you want to re-initialize on next connect
            # scanner = None

@app.on_event("startup")
async def startup_event():
    global scanner
    # Initialize the scanner here if you want it to be always ready, 
    # or initialize it on first WebSocket connection as currently implemented.
    # For now, we initialize on first connection to mimic noble's behavior of not scanning initially.
    print(f"FastAPI application startup. WebSocket will be available at ws://localhost:{WSS_PORT}/")
    # scanner = BleScanner(beacon_data_sender, notify_clients) # Example of initializing here

@app.on_event("shutdown")
async def shutdown_event():
    global scanner
    print("FastAPI application shutting down...")
    if scanner:
        await scanner.stop_scan()
    for ws in list(active_connections):
        try:
            await ws.close(code=1000)
        except Exception:
            pass # Ignore errors during shutdown close
    active_connections.clear()

# To run this app (from the project root directory):
# uvicorn bleak_service.main:app --host 0.0.0.0 --port 8081 --reload 