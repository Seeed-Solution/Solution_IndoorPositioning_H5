import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const srcRoot = path.join(webRoot, 'src')

const readText = (rel) => fs.readFileSync(path.join(webRoot, rel), 'utf-8')

function listFiles(dir, ext) {
  const out = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) out.push(...listFiles(full, ext))
    else if (entry.name.endsWith(ext)) out.push(full)
  }
  return out
}

function styleBlocks(vueSource) {
  return [...vueSource.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1])
}

describe('sensecraft-ui-kit token 层', () => {
  it('sc-tokens.css 提供风格指南要求的 token 与四态类', () => {
    const tokens = readText('src/styles/sc-tokens.css')
    for (const name of [
      '--sc-color-primary',
      '--sc-color-success',
      '--sc-color-warning',
      '--sc-color-error',
      '--sc-color-info',
      '--sc-radius-md',
      '--sc-radius-lg',
      '--sc-layout-sider-width',
      '--sc-layout-header-height',
      '--sc-font-sans',
    ]) {
      expect(tokens, `缺少 ${name}`).toContain(name)
    }
    for (const state of ['normal', 'warning', 'danger', 'disabled']) {
      expect(tokens).toContain(`--sc-status-${state}-bg`)
      expect(tokens).toContain(`--sc-status-${state}-fg`)
      expect(tokens).toContain(`.sc-status-badge.sc-status-${state}`)
    }
    // 布局壳尺寸必须与风格指南 §2 一致
    expect(tokens).toMatch(/--sc-layout-sider-width:\s*256px/)
    expect(tokens).toMatch(/--sc-layout-header-height:\s*64px/)
  })

  it('style.css 的旧变量全部指向 --sc-* 而非硬编码色值', () => {
    const css = readText('src/style.css')
    const rootBlock = css.slice(css.indexOf(':root {'), css.indexOf('}', css.indexOf(':root {')))
    const legacyVars = rootBlock
      .split('\n')
      .filter((line) => /^\s*--[a-z-]+:/.test(line))
    expect(legacyVars.length).toBeGreaterThan(10)
    for (const line of legacyVars) {
      if (/box-shadow/.test(line)) continue // 阴影是 rgba 组合，不是单一 token
      expect(line, `未映射到 --sc-*: ${line.trim()}`).toMatch(/var\(--sc-/)
    }
  })

  it('组件 <style> 块里不再残留被替换掉的品牌色/语义色', () => {
    // 这些是接入 kit 之前散落在各组件里的自定义色，全部应改为 --sc-* 变量
    const banned = [
      '#73C74D', '#5EAE3E', // 旧品牌绿
      '#667eea', '#764ba2', '#5a6fd8', '#6a4190', // 紫蓝渐变
      '#11998e', '#38ef7d', // 青绿渐变
      '#dc3545', '#28a745', '#007bff', '#6c757d', // bootstrap 调色板
      '#e9ecef', '#f8f9fa', '#495057',
    ]
    const offenders = []
    for (const file of listFiles(srcRoot, '.vue')) {
      for (const block of styleBlocks(fs.readFileSync(file, 'utf-8'))) {
        for (const color of banned) {
          if (block.toLowerCase().includes(color.toLowerCase())) {
            offenders.push(`${path.relative(webRoot, file)}: ${color}`)
          }
        }
      }
    }
    expect(offenders).toEqual([])
  })

  it('组件 <style> 里不再用主色/语义色渐变做大面积底色', () => {
    // kit 的观感是平面：主色只出现在按钮、数字、下划线等强调处，不做渐变色块。
    // 唯一例外是登录页整页背景（对齐 kit LoginPage 的 135° 渐变）。
    const offenders = []
    for (const file of listFiles(srcRoot, '.vue')) {
      const rel = path.relative(webRoot, file)
      if (rel.endsWith('views/LoginView.vue')) continue
      for (const block of styleBlocks(fs.readFileSync(file, 'utf-8'))) {
        for (const match of block.match(/linear-gradient\([^;]*/g) ?? []) {
          if (/--sc-color-(primary|success|warning|error|info)/.test(match)) {
            offenders.push(`${rel}: ${match.split('\n')[0].slice(0, 80)}`)
          }
        }
      }
    }
    expect(offenders).toEqual([])
  })
})
