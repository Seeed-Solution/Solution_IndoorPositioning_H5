把 `*.pmtiles` 归档放在这个目录里。docker-compose 以只读方式挂到
`/app/uploads/pmtiles`，前端按 `/uploads/pmtiles/<name>.pmtiles` 访问。

`demo.pmtiles` 未随仓库分发（全球包 ~100 GB，站点 bbox 包也有几十 MB）。
生成命令见 `docs/PMTILES.md`。
