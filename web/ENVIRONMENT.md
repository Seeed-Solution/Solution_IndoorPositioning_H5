# 环境配置说明

## 开发环境配置

### 本地开发（默认）
```bash
# 使用本地FastAPI服务器
npm run dev
```

### 远程开发
```bash
# 使用远程服务器进行开发
VITE_USE_REMOTE=true npm run dev
```

## 生产环境配置

### 构建生产版本
```bash
# 构建生产版本
npm run build
```

### 部署到生产服务器
生产环境通常不需要代理配置，因为前端和后端会部署在同一个域名下。

## 环境变量说明

- `VITE_USE_REMOTE`: 设置为 `true` 时使用远程服务器，默认为 `false`（本地服务器）
- `NODE_ENV`: 自动设置为 `production` 或 `development`

## 服务器地址配置

### 本地开发
- API: `http://localhost:8022`
- WebSocket: `ws://localhost:8022`

### 远程开发/生产
- API: `http://indoorpositioning-demo.seeed.cc/config-master:8022`
- WebSocket: `wss://indoorpositioning-demo.seeed.cc:8022`

## 快速切换环境

### 切换到本地开发
```bash
npm run dev
```

### 切换到远程开发
```bash
VITE_USE_REMOTE=true npm run dev
```

### 查看当前配置
启动时会显示当前使用的API和WebSocket目标地址。 