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
});
