# 定位地图整体改造（`/map` 单页）

依据 `seeed-solutions-hub/docs/specs/positioning-map-overhaul-spec.md`。
分支 `feature/map-overhaul`，从 `feature/ui-kit`（QA-14 + kit tokens 之后）切出。

## 阶段状态

| # | 阶段 | commit | 状态 |
|---|---|---|---|
| 1 | 状态与兼容路由：`/map`、query codec、旧路由 redirect、`lastVisitedPage` 迁移 | `712eedb` | 完成 |
| 2 | 统一页面骨架：紧凑 TrackerList、详情面板、三栏 | `073ac6b` | 完成 |
| 3 | 联动实现：controller、canvas 命中/zoom-pan/tooltip、Leaflet marker registry | `ace6ed8` | 完成 |
| 4 | 轨迹与响应式：共享 trail 开关、三档布局、AppShell off-canvas、溢出修复 | `567d7a8` | 完成 |
| 5 | 测试与发布兼容：Playwright 三视口、nginx 301、文档 | 见 git log | 完成 |

打包页 URL 改动在 `sensecraft-solutions-wt/indoor_positioning_ble_lorawan`，单独一条 commit。

## URL 契约

```
/web/map?layer=indoor|outdoor
        &map=<map-name>
        &tracker=<tracker-id>
        &q=<search>
        &status=all|online|offline|starred
        &group=<group-name>
        &trails=0|1
        &panel=list|detail|closed
```

与缺省相同的参数不写进 URL。非法取值静默回落缺省（`web/src/utils/mapUrlState.js`）。

## 旧路由

| 旧路径 | 新地址 |
|---|---|
| `/tracker`、`/config-tracker` | `/map` |
| `/map-overview` | `/map` |
| `/outdoor-map` | `/map?layer=outdoor` |

两条路都留：生产环境由 `nginx.conf` 的 `location = ... { return 301 ... }` 精确匹配接住
（必须排在 `location /web/` 这条 SPA fallback 之前）；开发环境（Vite）与 SPA 内部导航
由 `web/src/router/index.js` 的 Vue redirect 接住。

## 回滚

旧页面组件全部保留，只是从导航里摘掉、路径加了 `/legacy` 前缀：

- `/legacy/config-tracker` → `TrackerModeConfigView.vue`
- `/legacy/map-overview` → `MapOverview.vue`
- `/legacy/outdoor-map` → `OutdoorMapOverview.vue`

回滚步骤（保留一个发布周期）：

1. 删掉 `nginx.conf` 里的四组 `return 301` 块，重启 nginx；
2. `web/src/router/index.js`：把 `/legacy/*` 三条路径改回原路径，删掉
   `LEGACY_ROUTE_MAP` 展开出来的 redirect 数组；
3. `web/src/App.vue`：`menuItems` 换回 Tracker / Map Dashboard / Outdoor Map / Configuration；
4. `localStorage.lastVisitedPage` 会被 `migrateLastVisitedPage` 写成 `/map?...`，
   回滚后它匹配不到任何路由，落到 `getDefaultRoute` 的兜底分支，不会白屏。

下一个发布周期确认没有外部 launcher / 设备书签再指向旧路径后，才删旧组件。

## 截图

Playwright，三视口 1280×800 / 1024×600 / 390×844，访客登录会话，
`npm run dev`（:5173）+ `uv run python -m server.main`（:8022）：

```bash
cd web && npx playwright test
```

| 文件 | 内容 |
|---|---|
| `map-indoor-{1280,1024,390}.png` | `/map?layer=indoor` |
| `map-outdoor-{1280,1024,390}.png` | `/map?layer=outdoor` |
| `map-detail-{1280,1024,390}.png` | 详情打开态 |

改前基线在 `docs/ui/review/`（`map-dashboard-*`、`outdoor-*`、`tracker-page-*`），
那是审查报告的产物，不要改动。

每个视口都断言 `document.documentElement.scrollWidth === clientWidth`，
且 `.sc-content` 无横向溢出。

## 已知范围外

`/web/config`（`ConfigurationSuiteView.vue`，6800+ 行）在 390 宽下 `.sc-content`
仍有横向溢出（实测 440 > 390）。spec §4 列的四处溢出根因都在地图页，配置页不在
本次范围内，e2e 里只断言它仍能正常打开。
