const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const { resolve } = require('node:path')

;(async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const base = process.env.GALAXY_URL || 'http://127.0.0.1:8765/'
  const catalog = JSON.parse(readFileSync(resolve(__dirname, '../../web/data/catalog.json')))
  let local = false, delayed = false
  const groups = [['aol', 'Always On Lateral'], ['lane_change', 'Lane Changes'],
    ['torque', 'Steering and Torque'], ['lane', 'Lane Centering']]

  await page.route('**/data/runtime.json', route => route.fulfill({
    json: { schemaVersion: 1, monitor: local ? 'local' : 'sample' },
  }))
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/auth/session') return route.fulfill({
      json: { state: 'configured', authenticated: true, localAccess: true },
    })
    if (path === '/api/device/state') return route.fulfill({ json: { state: 'parked', maxAgeMs: 3000 } })
    if (path.startsWith('/api/settings/pages/')) {
      if (delayed) await new Promise(resolve => setTimeout(resolve, 600))
      const id = path.split('/').at(-1)
      return route.fulfill({ json: { page: id, title: id, view: 'test', parked: true,
        rows: id === 'hub' ? groups.map(([page, label]) => ({ page, label, value: 'Configure ' + label, available: true })) :
          [{ label: 'Test preference', key: 'test', value: 'Off', choices: ['Off', 'On'], action: true, available: true }],
      } })
    }
    return route.fulfill({ status: 503, json: { error: 'Device unavailable. Reconnect to read this tool.' } })
  })

  const paths = [...new Set(['/', '/tools', '/settings', '/developer/connect', '/cameras/events',
    '/cameras/sentry-settings', '/cameras/pip', '/cameras/vasm', '/theme_maker/android_auto',
    '/logs/crashes', '/logs/troubleshoot', '/logs/tmux', '/tuning/plots', '/tuning/flm',
    '/driving/longitudinal-curves', '/appearance', '/driving/conditional', '/driving/curve', '/driving/slc', '/driving/profiles', '/driving/traffic',
    ...groups.map(([page]) => '/driving/' + page), ...catalog.tools.map(tool => tool.path)])]
  for (const width of [360, 1280]) {
    await page.setViewportSize({ width, height: 900 })
    for (const path of paths) {
      await page.goto(base + '#' + path)
      await page.waitForTimeout(250)
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false,
        `${width}px ${path}: no page overflow`)
    }
  }

  local = true
  await page.reload()
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto(base + '#/settings')
  const manage = page.getByRole('button', { name: 'Manage', exact: true }).first()
  await manage.waitFor()
  const widths = await page.locator('.gx-row').evaluateAll(rows => rows.map(row => row.getBoundingClientRect().width))
  assert.ok(widths.every(width => Math.abs(width - widths[0]) < 1), 'settings groups share one width')
  await manage.click()
  await page.waitForTimeout(100)
  assert.equal(await page.locator('.gx-settings-tabs').count(), 0)
  assert.equal(await page.getByRole('heading', { name: 'Toggles', exact: true }).count(), 0)
  await page.getByRole('button', { name: 'Back', exact: true }).click()
  await manage.waitFor()

  delayed = true
  await page.reload()
  const loading = page.getByRole('status').filter({ hasText: 'Reading your device' })
  await loading.waitFor()
  const bounds = await loading.boundingBox()
  assert.ok(Math.abs(bounds.x + bounds.width / 2 - 195) < 1, 'loading card is centered')
  await page.waitForTimeout(750)
  await page.goto(base + '#/android-auto')
  await page.waitForTimeout(300)
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false)
  assert.deepEqual(errors, [], 'preview routes and unavailable Android Auto setup render without exceptions')
  console.log(`Passed ${paths.length} routes at two widths, settings navigation, loading alignment and setup failure.`)
  await browser.close()
})().catch(error => { console.error(error); process.exit(1) })
