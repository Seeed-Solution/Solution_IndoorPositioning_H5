# Beacon Positioning - Web Frontend

This Vue 3 application connects to the backend server via WebSockets to display a live map with tracker positions based on iBeacon signals.

## Setup

1.  **Navigate to Frontend Directory:**
    ```bash
    cd web
    ```
2.  **Install Dependencies:**
    ```bash
    npm install
    ```
    *(If you encounter issues, ensure you have a recent version of Node.js and npm installed.)*

## Running the Development Server

```bash
npm run dev
```

This will start the Vite development server, typically available at `http://localhost:5173` (check the terminal output for the exact address).

The frontend expects the backend server to be running (usually at `http://localhost:8000` by default).

## Usage

1.  **Run Backend:** Make sure the backend server is running.
2.  **Run Frontend:** Start the frontend development server (`npm run dev`).
3.  **Open Frontend:** Access the frontend URL in your browser.
4.  **Upload Configuration:**
    *   Generate the `config.json` file using the companion Weixin Mini Program (Config -> Common Settings -> Export Config to Clipboard).
    *   Save the copied JSON content into a file named `config.json` on your computer.
    *   Use the "Choose File" button in the web UI to select your `config.json` file.
    *   Click "Upload Config".
5.  **View Map:** The map defined in the config file should render, including any configured beacon locations.
6.  **Simulate/Receive Tracker Data:** As the backend receives tracker reports (via its `/api/tracker/report` endpoint), the corresponding trackers should appear and update their positions on the map in real-time. A list of currently tracked devices is also shown below the map.

## Building for Production

```bash
npm run build
```

This command will create a `dist` directory containing the optimized static assets. These assets can then be served by a static file server or integrated into the backend's static file serving (if configured, the FastAPI backend currently looks for `server/web_dist`).

To use the backend's static serving:
1. Run `npm run build` in the `web` directory.
2. Copy the contents of the generated `web/dist` directory into the `server/web_dist` directory.
3. Run the backend server. Accessing the root URL (e.g., `http://localhost:8000`) should now serve the Vue application.
