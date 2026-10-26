// Run with Playwright installed; GALAXY_BROWSER_CHANNEL and GALAXY_BROWSER_OUTPUT are optional.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const http = require('node:http')
const crypto = require('node:crypto')
const root = path.resolve(__dirname, '../../../..')
const web = path.resolve(__dirname, '../web')
const output = process.env.GALAXY_BROWSER_OUTPUT || fs.mkdtempSync(path.join(require('node:os').tmpdir(), 'galaxy-navigation-'))
fs.mkdirSync(output, { recursive: true })
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')
const inputs = {}
function pin(p) { inputs[path.relative(root, p).split(path.sep).join('/')] = hash(p) }
function walk(p) { for (const d of fs.readdirSync(p, { withFileTypes: true })) { const f = path.join(p, d.name); if (d.isDirectory()) walk(f); else pin(f) } }
walk(web)
pin(__filename)
const link = (page, label) => ({ page, label, value: 'Manage saved preferences', available: true, action: false })
const toggle = (label, confirm = false) => ({ key: label, label, value: 'Off', choices: ['Off', 'On'], available: true, action: true, confirm })
const pages = {
  hub: { title: 'Toggles', rows: [link('lane', 'Lane Centering'), link('aol', 'Always On Lateral'), link('profiles', 'Driving Personalities'), link('slc', 'Speed Limit Controller')] },
  lane: { title: 'Lane Centering', rows: [toggle('Enable Lane Centering'), link('lane/activation', 'Activation Conditions'), link('lane/preferences', 'Driving Preferences')] },
  'lane/activation': { title: 'Activation Conditions', rows: [link('lane/activation/modes', 'Modes'), link('lane/activation/geometry', 'Geometry')] },
  'lane/activation/modes': { title: 'Modes', rows: [toggle('Mode 1'), toggle('Mode 2'), toggle('Mode 3')] },
  'lane/activation/geometry': { title: 'Geometry', rows: [toggle('Geometry example')] },
  'lane/preferences': { title: 'Driving Preferences', rows: [link('lane/preferences/smoothing', 'Smoothing')] },
  'lane/preferences/smoothing': { title: 'Smoothing', rows: [toggle('Smoothing example')] },
  profiles: { title: 'Driving Personalities', rows: [link('relaxed', 'Relaxed')] },
  relaxed: { title: 'Relaxed', rows: [link('relaxed/following', 'Following')] },
  'relaxed/following': { title: 'Following', rows: [toggle('Following example')] },
  slc: { title: 'Speed Limit Controller', rows: [link('slc/timing', 'Timing and confirmation')] },
  'slc/timing': { title: 'Timing and confirmation', rows: [toggle('Timing example')] },
  wheel: { title: 'Wheel Controls', rows: [toggle('Wheel example')] },
  aol: { title: 'Always On Lateral', rows: [toggle('Always On Lateral')] },
}
const infoPages = { pip:'Camera display', sounds:'Sounds & Alerts', display:'Display', lane_change:'Lane Changes',
 conditional:'Conditional Experimental', 'conditional/example':'Conditional example', profiles:'Driving Personalities',
 traffic:'Traffic', aol:'Always On Lateral', torque:'Steering and Torque', lane:'Lane Centering', curve:'Curves',
 slc:'Speed Limit Controller', wheel:'Wheel Controls', data:'Device data', aggressive:'Aggressive', standard:'Standard', relaxed:'Relaxed', sentry:'Motion Monitor', developer:'Developer' }
for(const [id,title] of Object.entries(infoPages)) if(!pages[id]) pages[id]={title,rows:[toggle('Example preference')]}
// Additional fixture-only depth/translation stress, never a proposed driving setting.
const deep = 'lane/activation/modes/example/long/translated'
pages['lane/activation/modes/example'] = { title: 'Example extra level', rows: [link('lane/activation/modes/example/long', 'Long parent label to exercise translated menu text')] }
pages['lane/activation/modes/example/long'] = { title: 'Long parent label to exercise translated menu text', rows: [link(deep, 'A very long translated current page name for narrow displays')] }
pages[deep] = { title: 'A very long translated current page name for narrow displays', rows: [toggle('Example only')] }
fs.writeFileSync(path.join(output, 'api-fixture.json'), JSON.stringify(pages, null, 2))
pin(path.join(output, 'api-fixture.json'))
const requests = [], errors = [], checks = [], served = new Set()
let heldPreview = null, hold = false, failedPage = null, denyPage = null
function json(res, body, status = 200) { res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(body)) }
function pageData(id) { return { ...pages[id], page: id, view: 'fixture-' + id, parked: true, vehicleIdentified: true } }
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1')
  requests.push({ method: req.method, path: url.pathname })
  if (url.pathname === '/data/runtime.json') return json(res, { schemaVersion: 1, monitor: 'local' })
  if (url.pathname === '/api/auth/session') return json(res, { state: 'configured', authenticated: true, localAccess: true })
  if (url.pathname === '/api/device/state') return json(res, { state: 'parked', maxAgeMs: 3000 })
  if (url.pathname.startsWith('/api/settings/pages/')) {
    const id = decodeURIComponent(url.pathname.split('/pages/')[1])
    if (id === denyPage) return json(res, {}, 401)
    if (id === failedPage) return json(res, {}, 503)
    return json(res, pages[id] ? pageData(id) : { error: 'Unknown fixture page' }, pages[id] ? 200 : 404)
  }
  if (url.pathname === '/api/settings/preview') {
    if (hold) { heldPreview = res; return }
    return json(res, { intent: 'fixture-intent', question: 'Save example preference?' })
  }
  if (url.pathname === '/api/settings/confirm') return json(res, { saved: true })
  if (url.pathname.startsWith('/api/')) return json(res, {})
  if (url.pathname === '/component-test') { res.writeHead(200, { 'Content-Type': 'text/html' }); return res.end('<html data-theme="dark"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="css/galaxy.css"><link rel="stylesheet" href="css/settings.css"><main id="test" style="max-width:1100px;margin:16px auto;padding:0 12px"></main></html>') }
  const file = path.resolve(web, '.' + decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname))
  if (!file.startsWith(web + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); return res.end() }
  served.add(file)
  const types = { '.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png' }
  res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' }); res.end(fs.readFileSync(file))
})
const check = (name, condition = true) => { assert.ok(condition, name); checks.push(name) }
async function current(page, text) { await page.locator('.gx-settings-path [aria-current="page"]').filter({ hasText: text }).waitFor(); await page.waitForFunction(() => document.querySelectorAll('.gx-settings-path').length === 1) }
async function pageChrome(page, title) {
  await page.locator('.gx-settings-shell--path > .gx-page-header h2').filter({ hasText: new RegExp('^' + title + '$') }).waitFor()
  check('Current heading: ' + title, await page.locator('.gx-settings-shell--path > .gx-page-header h2').innerText() === title)
  check('All seven categories visible on ' + title, await page.locator('.gx-settings-shell--path > .gx-settings-tabs button').count() === 7)
  check('No in-card search on ' + title, await page.getByRole('button', { name: 'Search within this page' }).count() === 0 && await page.locator('.gx-settings__search').count() === 0)
}
async function manage(page, label) { await page.locator('.gx-row').filter({ hasText: label }).getByRole('button', { name: 'Manage', exact: true }).click() }
async function mount(page, initialPage = 'hub', navigationPath = true) {
  await page.evaluate(async ({ initialPage, navigationPath }) => {
    window.app?.unmount()
    const { route } = await import('./js/route-state.js')
    route.view = {}
    const { createApp } = await import('./vendor/vue/vue.esm-browser.js')
    const { SettingsPage } = await import('./js/settings.js')
    window.expired = 0
    window.app = createApp(SettingsPage, { mode: 'local', unauthorized() { window.expired++ }, initialPage, navigationPath })
    window.vm = app.mount('#test')
  }, { initialPage, navigationPath })
}
;(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const base = `http://127.0.0.1:${server.address().port}/`
  const browser = await chromium.launch({ ...(process.env.GALAXY_BROWSER_CHANNEL ? { channel: process.env.GALAXY_BROWSER_CHANNEL } : {}), headless: true })
  try {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true })
    await context.route('**/*', route => new URL(route.request().url()).hostname === '127.0.0.1' ? route.continue() : route.abort())
    const page = await context.newPage(); page.on('pageerror', e => errors.push(e.message))
    await page.goto(base + '#/settings')
    await pageChrome(page, 'Toggles')
    await manage(page, 'Lane Centering'); await current(page, 'Lane Centering'); await pageChrome(page, 'Lane Centering')
    await manage(page, 'Activation Conditions'); await current(page, 'Activation Conditions'); await pageChrome(page, 'Activation Conditions')
    await manage(page, 'Modes'); await current(page, 'Modes'); await pageChrome(page, 'Modes')
    check('Global search stays available', await page.getByRole('button', {name: 'Search Galaxy', exact:true}).count() > 0)
    assert.deepEqual(await page.locator('.gx-settings-path li').allTextContents(), ['Lateral (Steering)', ...['Lane Centering', 'Activation Conditions', 'Modes'].map(label => String.fromCharCode(8250) + label)])
    check('Actual app integration with category first and no redundant Toggles crumb')
    check('No selected-page dot', await page.locator('.gx-settings-path [aria-current] i, .gx-settings-path [aria-current] svg').count() === 0)
    const postedBefore = requests.filter(r => r.method === 'POST').length
    await page.getByRole('navigation', { name: 'Toggle hierarchy' }).getByRole('button', { name: 'Lane Centering', exact: true }).click(); await current(page, 'Lane Centering')
    check('Direct ancestor jump', await page.locator('.gx-settings-path li').count() === 2)
    await page.goBack(); await current(page, 'Lateral (Steering)')
    check('Browser Back after jump returns to section root')
    await manage(page, 'Lane Centering'); await manage(page, 'Activation Conditions'); await manage(page, 'Modes'); await current(page, 'Modes')
    const geometry = []
    for (const theme of ['dark', 'light']) for (const width of [320, 360, 390, 600, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: width > 900 ? 900 : 844 })
      await page.evaluate(theme => document.documentElement.dataset.theme = theme, theme)
      await page.waitForTimeout(60)
      const result = await page.evaluate(() => {
        const nav = document.querySelector('.gx-settings-path'), bounds = nav.getBoundingClientRect()
        const items = [...nav.querySelectorAll('li')].map(el => el.getBoundingClientRect())
        return { overflow: document.documentElement.scrollWidth > innerWidth || items.some(b => b.right > bounds.right + 1 || b.left < bounds.left - 1),
          rows: new Set(items.map(b => Math.round(b.top))).size, minTouchHeight: Math.min(...[...nav.querySelectorAll('button')].map(b => b.getBoundingClientRect().height)),
          currentLast: nav.querySelector('li:last-child [aria-current="page"]') !== null,
          categoriesFit: [...document.querySelectorAll('.gx-settings-shell--path > .gx-settings-tabs button')].every(el => { const b = el.getBoundingClientRect(); return b.left >= 0 && b.right <= innerWidth + 1 }) }
      })
      check(`${theme} ${width}px fits, wraps and preserves 44px touch targets`, !result.overflow && result.currentLast && result.categoriesFit && result.minTouchHeight >= 44)
      geometry.push({ theme, width, ...result })
      if ([320, 390, 1440].includes(width)) await page.screenshot({ path: path.join(output, `${theme}-${width}.png`), fullPage: true })
    }
    await page.setViewportSize({ width: 844, height: 390 }); await page.waitForTimeout(80)
    await page.locator('.gx-settings-shell--path > .gx-settings-tabs').getByRole('button', { name: 'Wheel Controls', exact:true }).click()
    await current(page, 'Wheel Controls'); await pageChrome(page, 'Wheel Controls')
    check('Category jump from nested page selects destination', await page.locator('.gx-settings-tabs button[aria-pressed="true"]').innerText() === 'Wheel Controls')
    await page.locator('.gx-settings-shell--path > .gx-settings-tabs').getByRole('button', { name: 'Lateral (Steering)', exact:true }).click()
    await current(page, 'Lateral (Steering)'); await pageChrome(page, 'Toggles')
    check('Landscape phone has no horizontal overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    check('Navigation never writes settings', requests.filter(r => r.method === 'POST').length === postedBefore)
    await page.goto(base + 'component-test')
    await mount(page, 'lane/activation/modes'); await current(page, 'Modes')
    await page.getByRole('button', { name: 'Activation Conditions', exact: true }).waitFor()
    check('Direct search entry resolves real ancestor labels')
    await page.getByRole('button', { name: 'Lane Centering', exact: true }).click(); await current(page, 'Lane Centering')
    await page.evaluate(() => vm.navigateBack()); await current(page, 'Lateral (Steering)')
    check('Direct search jump and Back reach root without loop', await page.evaluate(() => vm.navigateBack()) === false)
    await mount(page, 'relaxed/following'); await current(page, 'Following')
    await page.getByRole('button', { name: 'Driving Personalities', exact: true }).waitFor()
    check('Flat personality IDs retain their actual parent')
    await page.getByRole('navigation', { name: 'Toggle hierarchy' }).getByRole('button', { name: 'Longitudinal (Speed & Following)', exact: true }).click(); await current(page, 'Longitudinal (Speed & Following)')
    await page.getByRole('button', { name: 'Lateral (Steering)', exact: true }).click(); await current(page, 'Lateral (Steering)')
    check('Changing sections does not keep stale ancestors', await page.locator('.gx-settings-path').textContent().then(t => !t.includes('Personalities')))
    await mount(page, 'wheel'); await current(page, 'Wheel Controls')
    check('Single-page sections are not duplicated', await page.locator('.gx-settings-path li').count() === 1)
    await mount(page, deep); await current(page, pages[deep].title)
    await page.getByRole('button', { name: pages['lane/activation/modes/example/long'].title, exact: true }).waitFor()
    await page.setViewportSize({ width: 320, height: 700 })
    await page.waitForTimeout(100)
    check('Deep paths and long labels wrap without clipping', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth && [...document.querySelectorAll('.gx-settings-path li')].every(el => el.scrollWidth <= el.clientWidth + 1)))
    await page.screenshot({ path: path.join(output, 'deep-long-320.png'), fullPage: true })
    await page.evaluate(() => document.documentElement.style.fontSize = '200%')
    check('Enlarged text remains within screen', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.evaluate(() => document.documentElement.style.fontSize = '')
    // Every existing description uses the same box below the tree, above controls.
    for(const [id,title] of Object.entries(infoPages)) {
      await mount(page,id); await current(page,title)
      const intro=page.locator('.gx-settings__intro')
      await intro.waitFor()
      const fits=await page.evaluate(()=>{
        const intro=document.querySelector('.gx-settings__intro').getBoundingClientRect()
        const nav=document.querySelector('.gx-settings-path').getBoundingClientRect()
        const row=document.querySelector('.gx-settings__section .gx-row').getBoundingClientRect()
        return intro.top>=nav.bottom && intro.bottom<=row.top && intro.left>=0 && intro.right<=innerWidth &&
          document.querySelectorAll('.gx-settings > .gx-page-description, .gx-settings > .gx-settings__summary').length===0
      })
      check('Description boxed below navigation and above controls: '+id,fits)
    }
    await mount(page,'slc'); await current(page,'Speed Limit Controller')
    await page.waitForFunction(()=>!document.querySelector('.gx-panel-enter-active, .gx-panel-leave-active'))
    assert.equal(await page.locator('.gx-settings__intro .gx-page-description').innerText(),'Control how speed limits change your set speed.')
    const guide=page.locator('.gx-settings__intro').getByRole('link',{name:'Vision speed limits guide'})
    check('SLC guide is inside the description box with its original destination',
      await guide.getAttribute('href')==='https://wiki.firestar.link/exclusive/speed-limit-controller/#vision-speed-limits' &&
      await guide.getAttribute('target')==='_blank' && (await guide.getAttribute('rel')).includes('noopener'))
    for(const theme of ['dark','light']) for(const width of [320,390,768,1440]) {
      await page.setViewportSize({width,height:844})
      await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme)
      check('SLC description and guide fit '+theme+' '+width,await page.evaluate(()=>{
        const intro=document.querySelector('.gx-settings__intro'),link=intro.querySelector('a')
        return document.documentElement.scrollWidth<=innerWidth && intro.scrollWidth<=intro.clientWidth+1 && link.getBoundingClientRect().right<=intro.getBoundingClientRect().right
      }))
      if([390,1440].includes(width)) await page.screenshot({path:path.join(output,'slc-'+theme+'-'+width+'.png'),fullPage:true})
    }
    await page.evaluate(()=>document.documentElement.style.fontSize='200%')
    check('Description and guide wrap with enlarged text',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
    await page.evaluate(()=>document.documentElement.style.fontSize='')
    await mount(page,'slc/timing'); await current(page,'Timing and confirmation')
    check('Nested page without description has no stale SLC box or guide',await page.locator('.gx-settings__intro').count()===0 && await page.getByRole('link',{name:'Vision speed limits guide'}).count()===0)
    await mount(page,'hub'); await current(page,'Lateral (Steering)')
    check('Category root has no empty description box',await page.locator('.gx-settings__intro').count()===0)
    await mount(page,'slc',false)
    await page.getByRole('link',{name:'Vision speed limits guide'}).waitFor()
    check('Other SettingsPage embeddings retain description and guide',await page.locator('.gx-settings__intro').count()===0 && await page.locator('.gx-settings__summary').count()===1)
    await mount(page, 'lane/activation/modes')
    await current(page, 'Modes'); hold = true
    await page.getByRole('switch', { name: 'Mode 1', exact: true }).click()
    await page.waitForFunction(() => vm.state.status === 'updating')
    await page.evaluate(() => vm.jumpToPage('lane'))
    await page.evaluate(() => vm.selectCategory(vm.sections.find(s => s.id === 'wheel')))
    check('Dispatched save blocks category navigation', await page.evaluate(() => vm.state.data.page) === 'lane/activation/modes')
    check('Dispatched save blocks ancestor navigation', await page.evaluate(() => vm.state.data.page) === 'lane/activation/modes')
    hold = false; json(heldPreview, { intent: 'example', question: 'Save?' }); heldPreview = null
    await page.waitForFunction(() => vm.state.status === 'ready' && !vm.state.pending)
    await page.evaluate(() => { vm.state.pending = { intent: 'pending', question: 'Save example?' }; vm.jumpToPage('lane') })
    await page.evaluate(() => vm.selectCategory(vm.sections.find(s => s.id === 'wheel')))
    check('Pending confirmation blocks category navigation', await page.evaluate(() => vm.state.data.page) === 'lane/activation/modes')
    check('Pending confirmation blocks ancestor navigation', await page.evaluate(() => vm.state.data.page) === 'lane/activation/modes')
    await page.evaluate(() => vm.feed.cancel())
    await page.getByRole('button', { name: 'Lane Centering', exact: true }).click(); await current(page, 'Lane Centering')
    check('Cancel releases navigation guard')
    failedPage = 'lane/activation'
    await mount(page, 'lane/activation/modes'); await current(page, 'Modes')
    check('Unavailable ancestor labels do not break current controls', await page.getByRole('switch', { name: 'Mode 1', exact: true }).isEnabled())
    failedPage = null
    await mount(page, 'lane', false)
    await page.getByRole('switch', { name: 'Enable Lane Centering', exact: true }).waitFor()
    check('Other SettingsPage embeddings keep their existing UI', await page.locator('.gx-settings-path').count() === 0)
    check('Non-Toggles page search retained', await page.getByRole('button', {name:'Search within this page'}).count() === 1)
    await mount(page, 'lane/activation/modes')
    await current(page, 'Modes')
    await page.getByRole('button', { name: 'Lane Centering', exact: true }).focus()
    await page.keyboard.press('Enter'); await current(page, 'Lane Centering')
    check('Keyboard activation works')
    await mount(page, 'hub'); await current(page, 'Lateral (Steering)')
    await page.evaluate(() => vm.open('ui_layout'))
    await page.locator('.gx-layout').waitFor()
    check('Categories remain visible in layout editor', await page.locator('.gx-settings-shell--path > .gx-settings-tabs button').count() === 7)
    await page.locator('.gx-settings-shell--path > .gx-settings-tabs').getByRole('button', {name:'Wheel Controls',exact:true}).click()
    await current(page, 'Wheel Controls')
    check('Clean editor category switch closes editor', await page.locator('.gx-layout').count() === 0)
    await page.goto(base+'#/settings')
    await page.locator('.gx-settings-shell--path > .gx-settings-tabs').getByRole('button',{name:'Longitudinal (Speed & Following)',exact:true}).click()
    await manage(page,'Speed Limit Controller'); await current(page,'Speed Limit Controller')
    await page.waitForFunction(()=>!document.querySelector('.gx-panel-enter-active, .gx-panel-leave-active'))
    check('Actual app SLC description and guide share the box under navigation',await page.locator('.gx-settings__intro').getByRole('link',{name:'Vision speed limits guide'}).count()===1)
    for(const theme of ['dark','light']) for(const width of [390,1440]) {
      await page.setViewportSize({width,height:844})
      await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme)
      await page.screenshot({path:path.join(output,'app-slc-'+theme+'-'+width+'.png'),fullPage:true})
    }
    await page.goto(base+'component-test')
    denyPage = 'lane/activation'
    await mount(page, 'lane/activation/modes')
    await page.waitForFunction(() => expired === 1)
    check('Ancestor metadata honors expired sessions', await page.evaluate(() => vm.feed.active) === false)
    denyPage = null
    await page.evaluate(() => app.unmount())
    check('No browser runtime errors', errors.length === 0)
    for (const [relative, want] of Object.entries(inputs)) assert.equal(hash(path.join(root, relative)), want, 'Frozen input drift: ' + relative)
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify({ result: 'PASS', checks, geometry, errors,
      browser: await browser.version(), inputs, servedAssets: [...served].map(p => path.relative(root, p).split(path.sep).join('/')),
      scope: 'Actual Galaxy frontend, fixture APIs; local Edge with touch emulation. No real device settings or physical phone/browser validation.' }, null, 2) + '\n')
    console.log(JSON.stringify({ result: 'PASS', checks: checks.length, served: served.size, inputFiles: Object.keys(inputs).length }))
  } finally { await browser.close(); server.closeAllConnections(); await new Promise(resolve => server.close(resolve)) }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1 })
