# UI 截图（接入 sensecraft-ui-kit 前后对照）

分辨率 1280×800，Playwright（chrome-headless-shell 1243）截取，本地 `npm run dev` +
`uv run python -m server.main`（db/app.db 现有数据）环境，admin 登录态。

| 页面 | 路由 | 改前 | 改后 |
|---|---|---|---|
| 登录 | `/web/login` | `login-before.png` | `login-after.png` |
| 室内地图 | `/web/map-overview` | `map-indoor-before.png` | `map-indoor-after.png` |
| 室外地图 | `/web/outdoor-map` | `map-outdoor-before.png` | `map-outdoor-after.png` |
| 配置 | `/web/config` | `config-before.png` | `config-after.png` |

改后基线：`@sensecraft/ui-kit` v0.1.2 的 `dist/tokens.css`（复制到
`web/src/styles/sc-tokens.css`）+ `web/src/components/AppShell.vue`
（侧栏 256 / 顶栏 64 / 面包屑 / 语言切换 / 用户菜单）。

重新截取：

```bash
cd ~/project/solution-indoor-positioning
uv run python -m server.main &          # 后端 :8022
cd web && npm run dev &                 # 前端 :5173
# 然后用 Playwright 访问上表四个路由，viewport 1280×800
```
