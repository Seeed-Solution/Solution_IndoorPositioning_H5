import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const shotDir = path.join(repoRoot, 'docs', 'ui', 'overhaul');
fs.mkdirSync(shotDir, { recursive: true });

const label = (info) => info.project.name.split('-').pop();

// 本地默认管理员（server/config/json/server_runtime_config.json；本地跑用的是
// 哪份配置由 server 决定，换配置时用 E2E_ADMIN_* 覆盖）。
// 齿轮只给非访客看（spec §9.6），所以展示模式这条用例用管理员登录。
const ADMIN_USER = process.env.E2E_ADMIN_USER || 'admin';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'xgg2pvJERKppwHUYU874';

async function adminLogin(page) {
  await page.goto('/web/login');
  await page.locator('#username').fill(ADMIN_USER);
  await page.locator('#password').fill(ADMIN_PASSWORD);
  // 按钮里带一个 FontAwesome 图标, 可访问名里混着私有区字形, 不按名字找
  await page.locator('form.login-form button.login-button').click();
  await page.waitForURL(/\/web\/map/, { timeout: 20_000 });
}

async function expectNoHorizontalOverflow(page) {
  const doc = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(doc.scrollWidth).toBe(doc.clientWidth);
}

// 室内 fit-all 验证用的地图/tracker 数据。名字与外框取自
// server/config/json/dashboard_config.json 的第一张室内图（"10.5 Floor"），
// 换配置时用 E2E_INDOOR_MAP_* 覆盖。
const INDOOR_MAP_NAME = process.env.E2E_INDOOR_MAP_NAME || '10.5 Floor';
const INDOOR_BOUNDS = {
  minX: Number(process.env.E2E_INDOOR_MAP_MIN_X ?? 2.06),
  maxX: Number(process.env.E2E_INDOOR_MAP_MAX_X ?? 35.06),
  minY: Number(process.env.E2E_INDOOR_MAP_MIN_Y ?? 0.86),
  maxY: Number(process.env.E2E_INDOOR_MAP_MAX_Y ?? 33.81),
};

/** 三个分散在外框角落/中心的 tracker：跨度够大, fit-all 没框全就会露馅。 */
function buildMockTrackers() {
  const { minX, maxX, minY, maxY } = INDOOR_BOUNDS;
  const points = [
    { x: minX + (maxX - minX) * 0.1, y: minY + (maxY - minY) * 0.1 },
    { x: minX + (maxX - minX) * 0.5, y: minY + (maxY - minY) * 0.5 },
    { x: minX + (maxX - minX) * 0.9, y: minY + (maxY - minY) * 0.9 },
  ];
  const data = {};
  points.forEach((p, i) => {
    const id = `e2e-fit-tracker-${i}`;
    data[id] = {
      trackerId: id,
      device_name: `E2E Fit ${i}`,
      x: p.x,
      y: p.y,
      map: INDOOR_MAP_NAME,
      type: 'calculation',
      sos: 2,
      used_beacons: [],
      position_history: [],
    };
  });
  return data;
}

/**
 * 用一个假 WebSocket 类顶替 window.WebSocket, 连上就回一条 initial_state
 * 消息（跟 server/main.py 的 /ws 协议一致的最小子集）。不碰后端, 也不用
 * 等真实设备上线——这是 tests-e2e/ 里第一个需要注入 tracker 位置的用例,
 * 仓库里没有现成的 dev 后端注入入口, 所以走页面侧 WS mock。
 */
async function mockTrackerWebSocket(page, trackers) {
  await page.addInitScript((trackersData) => {
    class MockTrackerSocket {
      constructor(url) {
        this.url = url;
        this.readyState = MockTrackerSocket.CONNECTING;
        this.onopen = null;
        this.onmessage = null;
        this.onerror = null;
        this.onclose = null;
        setTimeout(() => {
          this.readyState = MockTrackerSocket.OPEN;
          if (this.onopen) this.onopen({});
          setTimeout(() => {
            if (this.onmessage) {
              this.onmessage({ data: JSON.stringify({ type: 'initial_state', data: trackersData }) });
            }
          }, 30);
        }, 0);
      }
      send() {}
      close() {
        this.readyState = MockTrackerSocket.CLOSED;
        if (this.onclose) this.onclose({});
      }
    }
    MockTrackerSocket.CONNECTING = 0;
    MockTrackerSocket.OPEN = 1;
    MockTrackerSocket.CLOSING = 2;
    MockTrackerSocket.CLOSED = 3;
    window.WebSocket = MockTrackerSocket;
  }, trackers);
}

/**
 * 在 canvas backing 像素里找 tracker 圆点（MapPreview 画 calculation 类型
 * tracker 用的 fillStyle 是 rgba(0,123,255,0.7)）, 按邻近关系聚类, 只保留
 * 像素数够多的簇——文字标签、描边反走样的散点不够格。
 */
function findTrackerClusters(canvasEl) {
  const ctx = canvasEl.getContext('2d');
  const { width, height } = canvasEl;
  if (!width || !height) return [];
  const { data } = ctx.getImageData(0, 0, width, height);
  const step = 2;
  const points = [];
  for (let y = 0; y < height; y += step) {
    for (let x = 0; x < width; x += step) {
      const idx = (y * width + x) * 4;
      const r = data[idx];
      const g = data[idx + 1];
      const b = data[idx + 2];
      const a = data[idx + 3];
      // rgba(0,123,255,0.7) ≈ (0,123,255,178), 留点容差给反走样。
      if (a > 120 && r < 40 && g > 95 && g < 155 && b > 210) {
        points.push({ x, y });
      }
    }
  }
  const used = new Array(points.length).fill(false);
  const clusters = [];
  for (let i = 0; i < points.length; i += 1) {
    if (used[i]) continue;
    const stack = [i];
    used[i] = true;
    const group = [];
    while (stack.length) {
      const cur = stack.pop();
      group.push(points[cur]);
      for (let j = 0; j < points.length; j += 1) {
        if (used[j]) continue;
        const dx = points[cur].x - points[j].x;
        const dy = points[cur].y - points[j].y;
        if (Math.hypot(dx, dy) < 30) {
          used[j] = true;
          stack.push(j);
        }
      }
    }
    if (group.length >= 3) {
      clusters.push({
        x: group.reduce((s, p) => s + p.x, 0) / group.length,
        y: group.reduce((s, p) => s + p.y, 0) / group.length,
        count: group.length,
      });
    }
  }
  return clusters;
}

test.describe('/map 展示模式', () => {
  test.beforeEach(async ({ page }) => {
    await adminLogin(page);
  });

  test('全屏铺满、无外壳、齿轮可达', async ({ page }, testInfo) => {
    await page.goto('/web/map?mode=display');
    await page.waitForTimeout(1800);

    const workspace = page.locator('.map-workspace.is-display');
    await expect(workspace).toBeVisible();

    // 1) AppShell 的侧栏与顶栏都不在 DOM 里
    await expect(page.locator('.sc-sider')).toHaveCount(0);
    await expect(page.locator('.sc-header')).toHaveCount(0);
    // 工作台的三栏面板同样不渲染
    await expect(page.locator('.ws-pane--list')).toHaveCount(0);
    await expect(page.locator('.ws-pane--detail')).toHaveCount(0);
    await expect(page.locator('.map-toolbar')).toHaveCount(0);

    // 2) 地图铺满视口
    const viewport = page.viewportSize();
    const box = await workspace.boundingBox();
    expect(box.width).toBeGreaterThanOrEqual(viewport.width - 1);
    expect(Math.abs(box.height - viewport.height)).toBeLessThanOrEqual(2);
    expect(box.x).toBeLessThanOrEqual(1);
    expect(box.y).toBeLessThanOrEqual(1);

    // 3) 信息带在, 齿轮可点且进 /config
    await expect(page.locator('.display-band')).toBeVisible();
    const gear = page.locator('.display-gear');
    await expect(gear).toBeVisible();

    // 4) 三个视口都不能有横向溢出
    await expectNoHorizontalOverflow(page);

    await page.screenshot({
      path: path.join(shotDir, `map-display-${label(testInfo)}.png`),
      fullPage: false,
    });

    await gear.click();
    await page.waitForURL(/\/web\/config/, { timeout: 15_000 });
  });

  test('mode 是 URL 状态: 刷新与后退都还原', async ({ page }) => {
    await page.goto('/web/map?mode=display&layer=outdoor');
    await page.waitForTimeout(1500);
    await page.reload();
    await page.waitForTimeout(1500);
    await expect(page.locator('.map-workspace.is-display')).toBeVisible();
    expect(page.url()).toContain('mode=display');

    // 退出展示模式后 AppShell 回来
    await page.goto('/web/map?layer=outdoor');
    await page.waitForTimeout(1200);
    await expect(page.locator('.sc-sider')).toHaveCount(1);
    // 工作台本身也要渲染出来: 空闲计时器一旦在 App 里抛异常, 外壳还在但内容是空的
    await expect(page.locator('.map-workspace')).toBeVisible();
    await page.goBack();
    await page.waitForTimeout(1200);
    await expect(page.locator('.map-workspace.is-display')).toBeVisible();
  });

  test('有在线 tracker 时 fit-all 把它们全部框进视口, 不贴边', async ({ page }, testInfo) => {
    await mockTrackerWebSocket(page, buildMockTrackers());
    await page.goto(`/web/map?mode=display&map=${encodeURIComponent(INDOOR_MAP_NAME)}`);
    // fit-all 在进入展示模式时立即执行（不等 2s 防抖窗口), 但 WS mock 要等
    // open+message 两个 setTimeout(0) 才把数据灌进去, 留够时间给这一轮和
    // 下一次 trackers 变化触发的重算。
    await page.waitForTimeout(2500);

    const canvas = page.locator('.map-workspace.is-display canvas');
    await expect(canvas).toBeVisible();

    const clusters = await canvas.evaluate(findTrackerClusters);
    // 3 个 tracker 应该都画出来了, 找不到就是数据没灌进去或者根本没画。
    expect(clusters.length).toBeGreaterThanOrEqual(3);

    const backing = await canvas.evaluate((el) => ({ width: el.width, height: el.height }));
    const box = await canvas.boundingBox();
    const viewport = page.viewportSize();
    const padding = 20; // 只挡"贴着视口边缘"这种明显没框好的情况, 不复刻 fit-all 内部的 padding 比例

    // canvas backing 像素 -> 页面/视口像素（canvas 是 max-width:100%, CSS 尺寸
    // 跟 backing 尺寸经常不等, 见 utils/canvasTransform.js 的 cssToCanvasPoint）。
    const toPage = (p) => ({
      x: box.x + (p.x / backing.width) * box.width,
      y: box.y + (p.y / backing.height) * box.height,
    });

    clusters.forEach((cluster) => {
      const p = toPage(cluster);
      expect(p.x).toBeGreaterThanOrEqual(padding);
      expect(p.x).toBeLessThanOrEqual(viewport.width - padding);
      expect(p.y).toBeGreaterThanOrEqual(padding);
      expect(p.y).toBeLessThanOrEqual(viewport.height - padding);
    });

    await page.screenshot({
      path: path.join(shotDir, `map-fit-tracker-${label(testInfo)}.png`),
      fullPage: false,
    });
  });
});
