const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const { readFileSync } = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const web = path.resolve(__dirname, '../../web')
const place = { id: 'coffee', name: 'Coffee Shop', address: '123 Main Street', latitude: 40, longitude: -90 }
const status = { enabled: true, hasKey: true, isMetric: true, status: 'noDestination', revision: '1',
  destination: null, favorites: [], recents: [], location: null, route: [], instruction: null }
;(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) })
  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } })
    const errors = [], actions = [], searches = []
    page.on('pageerror', error => errors.push(error.message))
    await page.route('http://navigation.test/**', async route => {
      const request = route.request(), pathname = new URL(request.url()).pathname
      if (pathname === '/data/runtime.json') return route.fulfill({ json: { schemaVersion: 1, monitor: 'local' } })
      if (pathname === '/api/auth/session') return route.fulfill({ json: { state: 'configured', authenticated: true, localAccess: true } })
      if (pathname === '/api/device/state') return route.fulfill({ json: { state: 'parked', maxAgeMs: 3000 } })
      if (pathname === '/api/navigation/search') {
        const body = request.postDataJSON()
        searches.push(body)
        return route.fulfill({ json: { results: [{ id: 'poi/coffee', name: place.name, description: place.address, searchId: body.searchId }] } })
      }
      if (pathname === '/api/navigation/action') {
        const body = request.postDataJSON()
        actions.push(body)
        if (body.action === 'favoritePlace') status.favorites = [{ ...place, ...(body.label ? { label: body.label } : {}) }]
        if (body.action === 'labelFavorite') status.favorites = [{ ...place, ...(body.label ? { label: body.label } : {}) }]
        status.revision = String(Number(status.revision) + 1)
        return route.fulfill({ json: status })
      }
      if (pathname.startsWith('/api/')) return route.fulfill({ json: status })
      if (pathname === '/' && new URL(request.url()).searchParams.has('shell')) return route.fulfill({ contentType: 'text/html', body:
        `<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/vendor/bootstrap-icons/bootstrap-icons.min.css">
        <link rel="stylesheet" href="/css/galaxy.css"><div id="galaxy-app"></div><script type="module" src="/js/app.js"></script>` })
      if (pathname === '/') return route.fulfill({ contentType: 'text/html', body: `<meta name="viewport" content="width=device-width,initial-scale=1">
        <link rel="stylesheet" href="/vendor/bootstrap-icons/bootstrap-icons.min.css"><link rel="stylesheet" href="/css/galaxy.css"><main class="gx-content"><div id="app"></div></main>
        <script type="module">import {createApp} from '/vendor/vue/vue.esm-browser.js';
        import {NavigationPage} from '/js/navigation.js';
        window.navigation = createApp(NavigationPage,{mode:'local',unauthorized:()=>{}}).mount('#app');</script>` })
      return route.fulfill({ body: readFileSync(path.join(web, pathname)),
        contentType: pathname.endsWith('.js') ? 'text/javascript' : pathname.endsWith('.css') ? 'text/css' : pathname.endsWith('.json') ? 'application/json' : 'application/octet-stream' })
    })
    await page.goto('http://navigation.test/')
    const search = page.getByRole('combobox', { name: 'Search destinations' })
    await search.waitFor()
    assert.equal(await page.getByText('Back to tools', { exact: true }).count(), 0)
    await search.fill('coffee')
    await page.getByRole('button', { name: 'Save Coffee Shop', exact: true }).waitFor()
    const count = searches.length
    await page.getByRole('button', { name: 'Search', exact: true }).click()
    await page.getByRole('list', { name: 'Search results' }).waitFor()
    assert.equal(searches.length, count, 'submitting uses ready suggestions')
    await page.getByRole('button', { name: 'Save Coffee Shop', exact: true }).click()
    const choices = page.getByRole('group', { name: 'Save place as' })
    for (const width of [360, 390, 768, 1280]) {
      await page.setViewportSize({ width, height: 844 })
      for (const name of ['Home', 'Work', 'Other'])
        assert.equal(await choices.getByRole('button', { name, exact: true }).isVisible(), true)
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
      if (width < 400) {
        const field = await search.boundingBox(), button = await page.getByRole('button', { name: 'Search', exact: true }).boundingBox()
        assert(Math.abs(field.y - button.y) < 6, 'search stays in a single row on phones')
        assert((await page.locator('.gx-navigation-map canvas').boundingBox()).height <= 300, 'phone map stays compact')
      }
      await page.screenshot({ path: '/private/tmp/navigation-compact-' + width + '.png', fullPage: true })
    }
    await choices.getByRole('button', { name: 'Home', exact: true }).click()
    await page.waitForFunction(() => window.navigation.data.favorites[0]?.label === 'home')
    assert.equal(actions.at(-1).label, 'home')
    await page.getByRole('button', { name: 'Saved: Coffee Shop', exact: true }).click()
    await choices.getByRole('button', { name: 'Other', exact: true }).click()
    await page.waitForFunction(() => window.navigation.data.favorites[0] && !window.navigation.data.favorites[0].label)
    assert.equal(actions.at(-1).action, 'labelFavorite')
    assert.equal(actions.at(-1).label, null)
    await page.goto('http://navigation.test/?shell=1#/navigation')
    await page.getByRole('combobox', { name: 'Search destinations' }).waitFor()
    assert.equal(await page.locator('.gx-appbar').isVisible(), true)
    assert.equal(await page.getByRole('button', { name: 'Menu', exact: true }).isVisible(), true)
    const header = await page.locator('.gx-appbar').boundingBox(), title = await page.getByRole('heading', { name: 'Navigation', exact: true }).boundingBox()
    assert(title.y >= header.y + header.height, 'Navigation title sits below the shared header')
    await page.setViewportSize({ width: 390, height: 844 })
    await page.screenshot({ path: '/private/tmp/navigation-shell-mobile.png', fullPage: true })
    assert.deepEqual(errors, [])
    console.log('Navigation: 360–1280px layout, inline favorite choices, atomic Home save, Other relabel, and instant suggestion reuse passed')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
