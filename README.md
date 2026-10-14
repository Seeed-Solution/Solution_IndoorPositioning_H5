# Seeed Indoor & Outdoor Positioning System (BLE & LoRaWAN)

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/frontend-Vue%203%20%2B%20Vite-4FC08D.svg)](https://vuejs.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An enterprise-ready indoor and outdoor asset tracking and visualization platform. The system ingests BLE beacon signals and GNSS telemetry from Seeed SenseCAP T1000 trackers and BLE gateways over MQTT/LoRaWAN, performs multilateration with Kalman filter smoothing, supports affine georeferencing between 2D floor plans and WGS84 geographic maps, and renders live positions on an interactive, responsive web dashboard.

---

## 📐 System Architecture

```
                                    +-----------------------------------+
                                    | SenseCAP T1000 Tracker / Gateways |
                                    +-----------------------------------+
                                                      |
                                             (LoRaWAN / MQTT)
                                                      v
                                        +----------------------------+
                                        | MQTT Broker (EMQX/Mosquitto)|
                                        +----------------------------+
                                                      |
                                                      v
+-------------------+      Reverse Proxy        +----------------------------+
|                   | <-----------------------> | Nginx Reverse Proxy        |
|  Web Frontend     |      HTTP / WebSocket     | - Port 5173 (Web/Proxy)    |
|  - Vue 3 + Vite   |                           +----------------------------+
|  - SenseCraft UI  |                                     |
|  - Leaflet Map    |                                     | /api, /ws, /uploads
|  - Canvas 2D Floor|                                     v
|  - Display Mode   |                           +----------------------------+
|                   | <-----------------------> | Backend Server (FastAPI)   |
+-------------------+      WebSocket / REST     | - Multilateration Engine   |
                                                | - Kalman 2D Filter         |
                                                | - Affine Geo-Registration  |
                                                | - Geofence Alert Engine    |
                                                | - SQLite / SQLAlchemy      |
                                                +----------------------------+
```

---

## 🚀 Key Features

1. **Hybrid Indoor & Outdoor Positioning**:
   - **Indoor**: RSSI-based multilateration with 2D Kalman filter smoothing for iBeacon and SenseCAP BLE tags.
   - **Outdoor**: WGS84 GNSS coordinates ingestion from SenseCAP T1000 trackers over LoRaWAN.
   - **Affine Map Registration**: Bilateral coordinate transform (`server/geo/affine.py` & `web/src/utils/affine.js`) aligning indoor metric floor plans with geographic coordinates on Leaflet.
2. **Interactive Web Dashboard & Display Mode**:
   - Modern, high-contrast interface built on **SenseCraft UI Kit** design tokens.
   - **Presentation Mode** (`/map?mode=display`): Fullscreen responsive view with automatic `fit-all` camera framing, screen wake lock (`navigator.wakeLock`), and automatic idle return.
   - Leaflet outdoor view with online map tiles or offline **PMTiles** support (`docs/PMTILES.md`).
3. **Geofencing & Alerts**:
   - Multi-polygon geofences with hysteresis entry/exit detection.
   - Configurable alert rules with WebSocket notifications.
4. **Device & Group Management**:
   - EUI whitelist, grouping, beacon deployment calibration (TxPower, path loss exponent), and data export/import.

---

## 🛠️ Quick Start

### Option 1: Docker Compose (Recommended)

Run the entire system in isolated containers:

```bash
# Clone the repository
git clone git@iteam-gitlab.seeed.cn:saas/solution-indoor-positioning.git
cd solution-indoor-positioning

# Start via docker-compose
docker compose up -d
```

- **Web Dashboard**: `http://localhost:5173`
- **Backend API**: `http://localhost:8022/docs`
- **Default Admin Account**:
  - Username: `admin`
  - Password: `12345678`

To run with local source mounting:
```bash
./run_in_docker.sh
```

---

### Option 2: Local Development Setup

#### Prerequisites
- **Python**: 3.10+ (Python 3.12 recommended, managed via `uv`)
- **Node.js**: 18.x or 20.x LTS
- **uv**: Fast Python package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

#### 1. Backend Server Setup

```bash
cd solution-indoor-positioning

# Install Python dependencies with uv
uv sync

# Run backend development server
uv run uvicorn server.main:app --host 0.0.0.0 --port 8022
```

The backend API documentation will be accessible at `http://127.0.0.1:8022/docs`.

#### 2. Frontend Web Setup

```bash
cd web

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend development server will launch at `http://localhost:5173` with proxy pre-configured to `http://127.0.0.1:8022`.

#### 3. (Optional) Local Beacon Service for Personal Mode

If testing client-side BLE scanning directly from the host machine:

```bash
cd local-beacon-service
npm install
./start_service.sh
```
The local scanning service will listen on `ws://localhost:8081`.

---

## 🧪 Testing & Verification

The project includes automated regression test suites for both backend and frontend components.

### Backend Tests (pytest)
Runs 128 unit and integration tests covering affine transforms, geofence hysteresis, MQTT payload decoding, and map registration:

```bash
uv run pytest server/tests/
```

### Frontend Tests (vitest)
Runs 174 component and logic tests covering coordinate mapping, camera framing, display mode, URL state synchronization, and UI tokens:

```bash
cd web
npm test
```

### Frontend Production Build
```bash
cd web
npm run build
```

---

## ⚙️ Configuration & Ports

| Service | Port | Description |
|---|---|---|
| Web UI / Nginx | `5173` (or `8080` in production) | Frontend app + `/api` and `/ws` reverse proxy |
| FastAPI Backend | `8022` | REST API, WebSocket server, MQTT handler |
| Local Beacon Service | `8081` | Node.js local BLE scanner (personal mode) |

Key configuration files:
- `server/config/server_runtime_config.json`: Server port, MQTT broker credentials, Kalman parameters.
- `server/config/dashboard_config.json`: Floor maps, beacon anchors, and geofence definitions.
- `db/positioning.db`: SQLite database for users, groups, devices, and event history.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.