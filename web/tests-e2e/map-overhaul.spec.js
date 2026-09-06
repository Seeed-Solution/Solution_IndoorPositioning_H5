import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const shotDir = path.join(repoRoot, 'docs', 'ui', 'overhaul');
fs.mkdirSync(shotDir, { recursive: true });

const label = (info) => info.project.name.split('-').pop();

/** 访客登录：非回归清单里的入口，同时也是截图的会话来源。 */
async function guestLogin(page) {
  await page.goto('/web/login');
  await page.getByRole('button', { name: /访客登录|Guest/i }).click();
  await page.waitForURL(/\/web\/map/, { timeout: 20_000 });
}

/** 整页与内容区都不能有横向溢出。 */
async function expectNoHorizontalOverflow(page) {
  const doc = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(doc.scrollWidth).toBe(doc.clientWidth);

  const content = await page.evaluate(() => {
    const el = document.querySelector('.sc-content');
    if (!el) return null;
    return { scrollWidth: el.scrollWidth, clientWidth: el.clientWidth };
  });
  if (content) {
    expect(content.scrollWidth).toBeLessThanOrEqual(content.clientWidth);
  }
}

async function shoot(page, testInfo, name) {
  const file = path.join(shotDir, `${name}-${label(testInfo)}.png`);
  await page.screenshot({ path: file, fullPage: false });
  return file;
}

test.describe('/map overhaul', () => {
  test.beforeEach(async ({ page }) => {
    await guestLogin(page);
  });

  test('indoor 图层', async ({ page }, testInfo) => {
    await page.goto('/web/map?layer=indoor');
    await page.waitForTimeout(1500);
    await expect(page.locator('.map-workspace')).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await shoot(page, testInfo, 'map-indoor');
  });

  test('outdoor 图层', async ({ page }, testInfo) => {
    await page.goto('/web/map?layer=outdoor');
    await page.waitForTimeout(2500);
    await expect(page.locator('.outdoor-map-view')).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await shoot(page, testInfo, 'map-outdoor');
  });

  test('详情打开态', async ({ page }, testInfo) => {
    await page.goto('/web/map?layer=indoor');
    await page.waitForTimeout(1500);

    // 窄屏先把列表抽屉拉出来, 再把 sheet 从 half 推到 full
    const panelToggle = page.locator('.panel-toggle');
    if (await panelToggle.count()) {
      await panelToggle.click();
      const grip = page.locator('.ws-pane--list .ws-pane__grip');
      if (await grip.count()) await grip.click();
      await page.waitForTimeout(400);
    }

    const firstRow = page.locator('.tracker-compact-item').first();
    if (await firstRow.count()) {
      await firstRow.click();
      await expect(page.locator('.detail-panel__body')).toBeVisible();
      // 选择必须落进 URL
      await expect(page).toHaveURL(/tracker=/);
    }
    await expectNoHorizontalOverflow(page);
    await shoot(page, testInfo, 'map-detail');
  });

  test('旧路由重定向到 /map', async ({ page }) => {
    for (const [from, expected] of [
      ['/web/map-overview', /\/web\/map(\?|$)/],
      ['/web/outdoor-map', /layer=outdoor/],
      ['/web/config-tracker', /\/web\/map(\?|$)/],
    ]) {
      await page.goto(from);
      await page.waitForURL(expected, { timeout: 15_000 });
      expect(page.url()).toMatch(expected);
    }
  });

  test('刷新与后退恢复界面状态', async ({ page }) => {
    await page.goto('/web/map?layer=outdoor&trails=0');
    await page.waitForTimeout(1200);
    await page.reload();
    await page.waitForTimeout(1200);
    expect(page.url()).toContain('layer=outdoor');
    await expect(page.locator('.trails-toggle input')).not.toBeChecked();

    await page.locator('.layer-btn').first().click();
    await page.waitForTimeout(600);
    await page.goBack();
    await page.waitForTimeout(800);
    expect(page.url()).toContain('layer=outdoor');
  });

  test('配准入口与告警设置未回归', async ({ page }) => {
    await page.goto('/web/map?layer=outdoor');
    await page.waitForTimeout(2000);
    // 配准入口只在存在可配准平面图时出现, 这里只断言 outdoor 工具条本身还在
    await expect(page.locator('.outdoor-toolbar')).toBeVisible();
    // 配置页（含 GeofenceEditor / Alarm Settings）仍然打得开。
    // 它的横向溢出是本次 spec §4 范围之外的既有问题, 不在这里断言。
    await page.goto('/web/config');
    await page.waitForTimeout(1500);
    await expect(page.locator('.sc-content')).toBeVisible();
  });
});
