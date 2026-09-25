const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')

;(async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/data/runtime.json', route => route.fulfill({ json: { schemaVersion: 1, monitor: 'local' } }))
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname
    const data = path === '/api/auth/session' ? { state: 'configured', authenticated: true, localAccess: true } :
      path === '/api/device/state' ? { state: 'parked', maxAgeMs: 3000 } :
        { page: 'hub', view: 'search', parked: true, rows: [] }
    return route.fulfill({ json: data })
  })
  await page.goto((process.env.GALAXY_URL || 'http://127.0.0.1:8765/') + '#/tools')
  await page.getByRole('heading', { name: 'Tools', exact: true }).waitFor()
  await page.locator('.gx-device-state[aria-label="Parked"]').waitFor()
  for (const width of [320, 360, 390, 480, 600, 767, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    const layout = await page.evaluate(() => {
      const rect = selector => {
        const element = document.querySelector(selector), bounds = element.getBoundingClientRect()
        return { x: bounds.x, right: bounds.right, width: bounds.width, visible: !!element.getClientRects().length }
      }
      return { home: rect('.gx-appbar__home'), search: rect(innerWidth < 768 ? '.gx-search-toggle' : '.gx-searchwrap'),
        state: rect('.gx-device-state'), overflow: document.documentElement.scrollWidth > innerWidth }
    })
    assert.equal(layout.overflow, false, `${width}px: no page overflow`)
    assert.ok(layout.home.right <= layout.search.x, `${width}px: logo and search do not overlap`)
    assert.ok(layout.search.right <= layout.state.x, `${width}px: search and state do not overlap`)
    if (width < 768) {
      assert.ok(layout.state.width <= 24, 'mobile state stays minimal')
      await page.getByRole('button', { name: 'Search toggles', exact: true }).click()
      const search = page.getByRole('combobox', { name: 'Search toggles', exact: true })
      await search.waitFor()
      await search.fill('wheel')
      await search.press('Escape')
      await page.getByRole('button', { name: 'Search toggles', exact: true }).waitFor()
      assert.equal(await page.locator('.gx-appbar__home').isVisible(), true)
    } else {
      assert.equal(await page.locator('.gx-device-state__label').isVisible(), true)
      await page.getByRole('combobox', { name: 'Search toggles', exact: true }).fill('wheel')
      await page.getByRole('combobox', { name: 'Search toggles', exact: true }).press('Escape')
    }
  }
  assert.deepEqual(errors, [])
  await browser.close()
  console.log('Top bar: logo/search/state separation at nine widths, compact accessible state, search open/close and desktop labels passed')
})().catch(error => { console.error(error); process.exit(1) })
