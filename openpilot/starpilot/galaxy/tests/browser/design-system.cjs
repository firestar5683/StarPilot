const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const assert = require('node:assert/strict')

;(async () => {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.route('**/js/boot.js', route => route.fulfill({ body: '' }))
  await page.goto(process.env.GALAXY_URL || 'http://127.0.0.1:8765/')
  await page.evaluate(() => {
    document.body.innerHTML = '<div class="gx-app"><header class="gx-appbar">Header</header><main class="gx-content"><div id="fixture"></div></main></div>'
  })
  await page.evaluate(async () => {
    const { createApp } = await import('./vendor/vue/vue.esm-browser.js')
    const { SoftwarePage } = await import('./js/software-status.js')
    const { GxState } = await import('./js/state.js')
    const { GxNotice } = await import('./js/notice.js')
    const { GxDialog } = await import('./js/dialog.js')
    const { GxSummary } = await import('./js/summary.js')
    const installed = { version: 'Fixture', branch: 'SecretGoodStarPilot', commit: 'a'.repeat(40) }
    const updater = { state: 'idle', lastCheckedAt: null, lastFetchAt: null, targetChangeFound: false }
    const operations = { availableBranches: ['StarPilot', 'Dom'], selectedTarget: 'StarPilot', request: null,
      canCheck: true, canFastUpdate: true, canDownload: true, canSelect: true, canInstall: false }
    const software = { ...SoftwarePage, created() {}, mounted() {}, beforeUnmount() {},
      data: () => ({ ...SoftwarePage.data(), status: 'ready', data: { installed, updater, operations },
        notice: 'Updating SecretGoodStarPilot. Waiting for completion or reconnect.', uncertain: true }) }
    window.fixture = createApp({ components: { software, GxState, GxNotice, GxDialog, GxSummary },
      data: () => ({ dialog: false }),
      template: `<software mode="local" :unauthorized="() => {}" /><div class="gx-card-grid"><section class="gx-card gx-panel">Card</section><section class="gx-card gx-panel">Card</section></div>
        <div class="gx-home__totals"><section class="gx-card"><h2>Time on the Road</h2><p>Saved history</p></section></div><section class="gx-card gx-aa-step"><h2>Android Auto</h2><p>Connect your car</p></section><GxSummary :items="[{label: 'Installed', value: 1}, {label: 'Missing', value: 0}, {label: 'Total', value: 1}]" /><GxState loading>Reading your device…</GxState><GxState>Nothing here yet.</GxState>
        <GxNotice tone="success" title="Saved">Preferences saved.</GxNotice><GxNotice tone="danger">An error occurred.</GxNotice>
        <div class="gx-tabs"><button class="gx-btn" aria-pressed="true">Selected</button><button class="gx-btn gx-btn--tonal">Other</button></div>
        <button class="gx-btn" @click="dialog=true">Open dialog</button>
        <GxDialog v-if="dialog" labelledby="fixture-title" @close="dialog=false"><h3 id="fixture-title">Confirm preference</h3><input class="gx-field" aria-label="Name" /><div class="gx-actions"><button class="gx-btn" @click="dialog=false">Cancel</button><button class="gx-btn">Save</button></div></GxDialog>`,
    }).mount('#fixture')
  })
  for (const theme of ['dark', 'light']) {
    await page.evaluate(theme => document.documentElement.dataset.theme = theme, theme)
    for (const width of [320, 390, 768, 1280, 1920, 3440]) {
      await page.setViewportSize({ width, height: 900 })
      for (const pinned of [false, true]) {
        await page.evaluate(pinned => document.querySelector('.gx-app').classList.toggle('gx-nav-pinned', pinned), pinned)
        const geometry = await page.evaluate(() => {
          const content = document.querySelector('.gx-content').getBoundingClientRect()
          const header = document.querySelector('.gx-appbar').getBoundingClientRect()
          const notice = document.querySelector('.gx-alert').getBoundingClientRect()
          const spinner = document.querySelector('.gx-alert .gx-spinner').getBoundingClientRect()
          const text = document.querySelector('.gx-alert__body').getBoundingClientRect()
          return { width: content.width, left: content.left, right: content.right, header: header.width,
            notice: notice.width, container: document.querySelector('.gx-software-card').clientWidth - 2 * parseFloat(getComputedStyle(document.querySelector('.gx-software-card')).paddingLeft), aligned: Math.abs(spinner.top - text.top) < 6,
            overflow: document.documentElement.scrollWidth > innerWidth }
        })
        assert.equal(geometry.overflow, false, `${theme}/${width}/${pinned}: no overflow`)
        assert.ok(geometry.width <= 1200 && geometry.header <= 1200)
        assert.equal(await page.locator('.gx-tabs').last().evaluate(element => getComputedStyle(element).display), 'flex')
        assert.equal(await page.locator('.gx-card-grid').evaluate(element => getComputedStyle(element).display), 'grid')
        const summary = await page.locator('.gx-summary > div').evaluateAll(elements => elements.map(element => element.getBoundingClientRect().top))
        assert.ok(summary.every(top => Math.abs(top - summary[0]) < 1), 'summary counts share one row')
        assert.ok(Math.abs(geometry.notice - geometry.container) < 1 && geometry.aligned, 'notice fills the padded panel with aligned status icon')
        for (const selector of ['.gx-panel', '.gx-message', '.gx-home__totals > section', '.gx-aa-step']) {
          const padding = await page.locator(selector).first().evaluate(element => { const style = getComputedStyle(element); return [parseFloat(style.paddingLeft), parseFloat(style.paddingRight), parseFloat(style.paddingTop), parseFloat(style.paddingBottom)] })
          assert.ok(padding[0] >= 16 && padding[1] >= 16, `${selector}: horizontal padding survives all themes and widths`)
          assert.ok(padding[2] >= 16 && padding[3] >= 16, `${selector}: vertical padding`)
        }
        assert.equal(await page.locator('.gx-message').first().evaluate(element => element.offsetWidth), await page.locator('#fixture').evaluate(element => element.clientWidth), 'page states fill the available width')
        const inset = pinned && width >= 768 ? 320 : 0
        assert.ok(Math.abs(geometry.left - inset - (width - geometry.right)) < 1, 'centered in available space')
      }
    }
  }
  await page.evaluate(() => { document.querySelector('.gx-app').classList.remove('gx-nav-pinned'); document.documentElement.dataset.theme = 'dark' })
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.waitForTimeout(250)
  await page.screenshot({ path: '/tmp/galaxy-design-desktop.png' })
  await page.setViewportSize({ width: 390, height: 900 })
  await page.screenshot({ path: '/tmp/galaxy-design-phone.png' })
  const trigger = page.getByRole('button', { name: 'Open dialog', exact: true })
  await trigger.click()
  const dialog = page.getByRole('dialog', { name: 'Confirm preference' })
  await dialog.waitFor()
  assert.equal(await dialog.evaluate(element => element.contains(document.activeElement)), true)
  for (let i = 0; i < 5; i++) await page.keyboard.press('Tab')
  assert.equal(await dialog.evaluate(element => element.contains(document.activeElement)), true, 'Tab stays in dialog')
  await page.keyboard.press('Escape')
  assert.equal(await dialog.count(), 0)
  assert.equal(await trigger.evaluate(element => element === document.activeElement), true, 'focus restored')
  await trigger.click()
  await page.mouse.click(2, 2)
  assert.equal(await dialog.count(), 0, 'backdrop cancels')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  assert.equal(await page.locator('.gx-spinner').first().evaluate(element => getComputedStyle(element).animationName), 'none')
  await page.evaluate(async () => {
    const { createApp } = await import('./vendor/vue/vue.esm-browser.js')
    const { NavigationMap } = await import('./js/navigation-map.js')
    const wrapper = document.createElement('div')
    wrapper.className = 'gx-navigation--fullscreen'
    wrapper.innerHTML = '<div id="map-fixture"></div>'
    document.body.appendChild(wrapper)
    createApp({ ...NavigationMap, mounted() {}, beforeUnmount() {},
      data: () => ({ ...NavigationMap.data(), error: 'Map tiles are unavailable.' }) },
      { data: {}, stale: false }).mount('#map-fixture')
  })
  for (const width of [320, 1280, 3440]) {
    await page.setViewportSize({ width, height: 900 })
    const bounds = await page.getByRole('alert').filter({ hasText: 'Map tiles are unavailable.' }).boundingBox()
    assert.ok(bounds.x >= 0 && bounds.y >= 0 && bounds.x + bounds.width <= width && bounds.y + bounds.height <= 900,
      'map errors remain visible above the canvas')
  }
  assert.deepEqual(errors, [])
  // Exercise the real software feed: controls render before a delayed status,
  // history is fetched on demand, and secondary actions retain confirmations.
  const softwareRequests = []
  const snapshot = { schemaVersion: 1,
    installed: {version:'Fixture',branch:'StarPilot',commit:'a'.repeat(40)},
    updater: {state:'idle',targetBranch:'StarPilot',lastSuccessAt:null,lastFetchAt:null,
      targetChangeFound:true,finalizedUpdateReady:true,failedCount:0},
    operations: {parked:true,availableBranches:['StarPilot','Dom'],selectedTarget:'StarPilot',
      canCheck:true,canFastUpdate:true,canDownload:true,canSelect:true,canInstall:true,
      canRollback:true,canConfigure:true,automaticDownloads:true,reason:null,request:null} }
  await page.route('**/api/software/**', async route => {
    const url = new URL(route.request().url())
    softwareRequests.push(url.search)
    await new Promise(resolve => setTimeout(resolve,250))
    const operations = {...snapshot.operations}
    if (url.search !== '?history=0') operations.history = {installed:Array.from({length:20}, (_, index) => ({hash:index.toString(16).padStart(40,'0'),date:'2026-10-07T12:00:00Z',subject:index ? `Version ${index}: rendering and update fixes` : ''})),downloaded:[],
      currentReleaseNotes:'Fixture release notes',downloadedReleaseNotes:null}
    await route.fulfill({json:{...snapshot,operations}})
  })
  await page.evaluate(async () => {
    window.fixture.$.appContext.app.unmount()
    document.querySelector('.gx-navigation--fullscreen')?.remove()
    const {createApp} = await import('./vendor/vue/vue.esm-browser.js')
    const {SoftwarePage} = await import('./js/software-status.js')
    window.fixture = createApp(SoftwarePage,{mode:'local',unauthorized:()=>{}}).mount('#fixture')
  })
  const check = page.getByRole('button',{name:'Check for updates',exact:true})
  await check.waitFor()
  assert.equal(await check.isDisabled(),true,'no mutation before fresh status')
  assert.equal(await page.getByRole('button',{name:'Back up toggles',exact:true}).isEnabled(),true,'backup does not wait for updater status')
  await page.waitForFunction(() => ![...document.querySelectorAll('button')].find(button => button.textContent === 'Check for updates').disabled)
  assert.deepEqual(softwareRequests,['?history=0'])
  for (const width of [320,390,1280,3440]) {
    await page.setViewportSize({width,height:900})
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth),false,'minimal software stays within viewport')
  }
  assert.equal(await page.getByRole('button',{name:'Refresh software status',exact:true}).count(),0)
  assert.equal(await page.getByText('Update activity',{exact:true}).count(),0)
  for (const [width,path] of [[1280,'/tmp/galaxy-updates-clean-desktop.png'],[390,'/tmp/galaxy-updates-clean-phone.png']]) {
    await page.setViewportSize({width,height:900})
    await page.screenshot({path,fullPage:true})
  }
  for (const name of ['Fast Update','Restart & install']) {
    await page.getByRole('button',{name,exact:true}).click()
    await page.getByRole('dialog').waitFor()
    await page.getByRole('button',{name:'Cancel',exact:true}).click()
  }
  await page.getByText('Advanced options',{exact:true}).click()
  await page.getByRole('button',{name:'Previous version',exact:true}).click()
  await page.getByRole('dialog').waitFor()
  await page.getByRole('button',{name:'Cancel',exact:true}).click()
  await page.getByRole('combobox',{name:'Target branch',exact:true}).click()
  await page.getByRole('option',{name:/Development — Dom/}).click()
  await page.getByRole('button',{name:'Switch & update',exact:true}).click()
  await page.getByRole('dialog',{name:'Switch branch'}).waitFor()
  assert.equal(await page.getByRole('dialog').getByText('Download latest version of Dom and restart?',{exact:true}).count(),1)
  await page.getByRole('button',{name:'Cancel',exact:true}).click()
  await page.getByRole('button',{name:'Save target',exact:true}).click()
  await page.getByRole('dialog',{name:'Change target branch'}).waitFor()
  await page.getByRole('button',{name:'Cancel',exact:true}).click()
  await page.getByText('Versions & release notes',{exact:true}).click()
  await page.getByRole('button',{name:'Installed',exact:true}).click()
  await page.getByText('Fixture release notes',{exact:true}).waitFor()
  assert.deepEqual(softwareRequests,['?history=0',''])
  assert.equal(await page.locator('.gx-build-history li').count(),20)
  assert.equal(await page.locator('.gx-build-history li strong').first().textContent(),'000000000000')
  assert.equal(await page.locator('.gx-build-history').evaluate(element=>getComputedStyle(element).listStyleType),'none')
  assert.equal(await page.getByRole('button',{name:'Downloaded',exact:true}).count(),0)
  assert.equal(await check.isEnabled(),true,'history refresh keeps update controls enabled')
  const backup = {format:'galaxy-toggles',version:1,createdAt:'2026-10-07T12:00:00Z',metric:false,vehicle:null,
    settings:[{page:'data',key:'AlwaysAllowUploads',value:'Off'}],layout:null}
  const restores = []
  await page.route('**/api/settings/backup', route => route.fulfill({json:backup}))
  await page.route('**/api/settings/restore', route => {
    restores.push(route.request().postDataJSON())
    return route.fulfill({json:{complete:true,restored:1,unchanged:0,skipped:[]}})
  })
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button',{name:'Back up toggles',exact:true}).click()
  const download = await downloadPromise
  assert.equal(download.suggestedFilename(),'toggle-backup.json')
  const file = {name:'toggle-backup.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(backup))}
  await page.getByLabel('Choose toggle backup',{exact:true}).setInputFiles(file)
  await page.getByRole('dialog',{name:'Restore toggles?'}).waitFor()
  await page.getByRole('button',{name:'Cancel',exact:true}).click()
  assert.equal(restores.length,0,'choosing a file alone never changes settings')
  await page.getByLabel('Choose toggle backup',{exact:true}).setInputFiles(file)
  await page.getByRole('dialog').getByRole('button',{name:'Restore',exact:true}).click()
  await page.getByText('1 toggle restored.',{exact:true}).waitFor()
  assert.deepEqual(restores,[backup])
  await page.evaluate(() => window.fixture.$.appContext.app.unmount())
  assert.deepEqual(errors,[])
  console.log('Design system: six widths, both themes, pinned layout, update banner, state cards, modal keyboard/focus/backdrop and reduced motion passed.')
  await browser.close()
})().catch(error => { console.error(error); process.exit(1) })
