# 室内定位前端项目 (Vue.js with Vite)

This directory contains the Vue.js frontend application for the Indoor Positioning System. It is built using Vite.

## API配置说明

此项目现已支持环境变量配置，可以在开发环境和生产环境下使用不同的API基础URL。

### 环境配置

#### 开发环境

1. **本地代理模式**（推荐）
   ```bash
   npm run dev
   # 或者明确设置
   VITE_USE_REMOTE=false npm run dev
   ```
   - 前端通过Vite代理访问后端API
   - API请求：`/api/*` → `http://127.0.0.1:8022/api/*`
   - WebSocket：`/ws/*` → `ws://127.0.0.1:8022/ws/*`

2. **远程直连模式**
   ```bash
   VITE_USE_REMOTE=true npm run dev
   ```
   - 前端直接请求后端服务器
   - API请求：`http://127.0.0.1:8022/api/*`
   - WebSocket：`ws://127.0.0.1:8022/ws/*`

#### 生产环境

```bash
npm run build
```
- 自动使用生产环境配置
- API请求：`https://indoorpositioning-demo.seeed.cc/api/*`
- WebSocket：`wss://indoorpositioning-demo.seeed.cc/ws/*`

### 命令说明

- `npm run dev` - 本地开发（使用代理）
- `npm run dev:local` - 本地开发（使用代理）
- `npm run dev:remote` - 远程开发（直连服务器）
- `npm run build` - 生产构建
- `npm run preview` - 预览生产构建

### API文件结构

```
src/
├── config/
│   └── api.js           # 统一API配置
├── utils/
│   └── httpClient.js    # 统一HTTP客户端
└── services/
    ├── configApiService.js  # 配置API服务
    ├── authService.js       # 认证服务
    └── dashboardService.js  # 仪表板服务
```

### 主要改进

1. **统一API配置** - 所有API调用现在使用统一的配置文件
2. **环境变量支持** - 可通过`VITE_USE_REMOTE`环境变量切换开发模式
3. **生产环境支持** - 打包后可直接访问生产服务器
4. **统一错误处理** - HTTP客户端包含统一的错误处理逻辑
5. **代码一致性** - 所有API调用使用相同的模式

## Project Structure

-   `index.html`: The main HTML entry point for the application.
-   `vite.config.js`: Configuration file for Vite, the build tool.
-   `package.json`: Defines project metadata, dependencies (e.g., `vue`, `vue-router`, `axios`), and npm scripts.
-   `src/`: Contains the main source code for the Vue application.
    -   `main.js` (Implicit): The entry point for the Vue application, where the root Vue instance is created and configured with plugins like Vue Router. (Standard Vite/Vue setup, file might be named `main.ts` if using TypeScript).
    -   `App.vue`: The root Vue component of the application.
    -   `assets/`: Static assets like images, global stylesheets (e.g., `style.css`).
    -   `components/`: Reusable Vue components used across different views (e.g., `MapView.vue`, `BeaconIcon.vue`).
    -   `views/`: Vue components that represent different pages or main sections of the application (e.g., `TrackerModeConfigView.vue`, `LocalModeConfigView.vue`, `MasterConfigView.vue`).
    -   `router/`: Vue Router configuration (`index.js` or `index.ts`), defining application routes and their corresponding view components.
    -   `services/`: Modules for interacting with backend APIs (e.g., `configApiService.js`, `localStorageService.js`) or other external services.
    -   `utils/`: Utility functions and helpers used throughout the application (e.g., `positioning/positionCalculator.js`).
-   `public/`: Static assets that are copied directly to the build output directory (e.g., `favicon.ico`).
-   `node_modules/`: Contains installed npm packages.

## How to Run

The frontend is typically started as part of the main `start.sh` script in the project root. For standalone development:

1.  **Navigate to the web directory:**
    ```bash
    cd /path/to/beacon_posistion_r1000/web
    ```
2.  **Install dependencies (if not already done):**
    ```bash
    npm install
    ```
3.  **Start the Vite development server:**
    ```bash
    npm run dev
    ```
    This command usually includes `--host` to make the server accessible on the local network.
    The frontend will typically be accessible at `http://localhost:5173` (this port is configurable in `vite.config.js` and referenced in the root `start.sh`).

## How to Modify / Develop

1.  **Views & Components**: Create or modify Vue components in `src/views/` (for pages) and `src/components/` (for reusable UI elements). Follow Vue.js single-file component (`.vue`) structure (template, script, style).
2.  **Routing**: Add or update routes in `src/router/index.js` (or equivalent) to link URLs to view components.
3.  **API Interaction**: Use or extend services in `src/services/` (often using `axios` or `fetch`) to communicate with the backend API.
4.  **State Management**: 
    -   For simple cases, use component-level state (Vue's `ref`, `reactive`).
    -   For cross-component state, consider props/events, provide/inject, or a dedicated state management library like Pinia (if integrated).
    -   Local storage interactions are handled by `localStorageService.js`.
5.  **Styling**: 
    -   Global styles can be placed in `src/assets/style.css` (or similar).
    -   Component-specific styles are usually defined within the `<style scoped>` section of `.vue` files.
6.  **Utility Functions**: Place generic helper functions in `src/utils/`.
7.  **Build for Production**:
    ```bash
    npm run build
    ```
    This will create a `dist` directory with optimized static assets for deployment.

## Key Data Structures / Concepts

-   **Master Configuration (`currentFullConfig` in various views)**: This reactive object, often loaded from local storage or the server, holds the map details, beacon list, and settings. Its structure is critical for how maps are rendered and positioning is calculated.
    ```javascript
    // Example structure (often a ref in Vue components)
    {
      map: { name: String, image: String, width: Number, height: Number, origin: Object, ppm: Number, entities: Array },
      beacons: [ { uuid: String, major: Number, minor: Number, x: Number, y: Number, txPower: Number, name: String, deviceId: String } ],
      settings: { signalPropagationFactor: Number, positioningAlgorithm: String, showTrails: Boolean, /* ...other settings */ }
    }
    ```
-   **Tracker Data**: Information about tracked devices, including their ID, position (x, y), timestamp, etc. This data is typically fetched from the server or received via WebSocket and displayed on the map.
-   **Local Device Position**: In `LocalModeConfigView.vue`, this refers to the position calculated based on data from the `local-beacon-service`.
-   **API Service Calls (`configApiService.js`)**: Functions in this service encapsulate HTTP requests to the backend for fetching/updating configurations and data.
-   **WebSocket Communication (`LocalModeConfigView.vue`)**: Handles real-time communication with the `local-beacon-service` for beacon data and status updates.

## Dependencies

-   `vue`: The core Vue.js library.
-   `vue-router`: For client-side routing.
-   `axios`: For making HTTP requests to the backend API.
-   `vite`: The build tool and development server.
-   `@vitejs/plugin-vue`: Vite plugin for Vue.js support. 