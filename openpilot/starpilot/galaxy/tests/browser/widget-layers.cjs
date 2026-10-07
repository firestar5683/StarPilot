const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const { execFileSync } = require('node:child_process')
const { readFileSync } = require('node:fs')
const path = require('node:path')
const assert = require('node:assert/strict')
const web = path.resolve(__dirname, '../../web')
const snapshot = JSON.parse(execFileSync(process.env.PYTHON || 'python3', ['-c',
  'import json; from openpilot.starpilot.ui.onroad_customization import default_document, customization_metadata; print(json.dumps(dict(document=default_document(), defaults=default_document(), metadata=customization_metadata(), revision="layers", editable=True, valid=True, activeProfile="large")))'], {encoding:'utf8'}))
const projection = JSON.parse(execFileSync(process.env.PYTHON || 'python3', ['-c',
  'import json; from openpilot.starpilot.system.android_auto.projection_layout import default_layout_for_viewport, layout_metadata_for_viewport; from openpilot.starpilot.ui.onroad_customization import default_document; d=default_layout_for_viewport((2880,1080)); c=default_document(); print(json.dumps(dict(version=1,document=d,defaults=d,metadata=layout_metadata_for_viewport((2880,1080)),screen=dict(width=1280,height=720,margin_width=0,margin_height=240),revision="aa-layers",editable=True,valid=True,colors=dict(palette=c["palette"],widgetColors=c["widgetColors"]["large"],roadColors={}))))'], {encoding:'utf8'}))
;(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? {executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH} : {})})
  try {
    const page = await browser.newPage({viewport:{width:1280,height:1000}})
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.route('http://layers.test/**', async route => {
      const pathname = new URL(route.request().url()).pathname
      if (pathname.startsWith('/api/')) return route.fulfill({json: pathname === '/api/android-auto/layout' ? projection : snapshot})
      if (pathname === '/') return route.fulfill({contentType:'text/html', body:`<link rel="stylesheet" href="/css/galaxy.css"><link rel="stylesheet" href="/css/settings.css"><main class="gx-content"><div id="app"></div></main><script type="module">
        import {createApp} from '/vendor/vue/vue.esm-browser.js';
        import {OnroadLayoutPage} from '/js/onroad-layout.js';
        window.editor = createApp(OnroadLayoutPage, {mode:'local', projection:new URLSearchParams(location.search).has('projection'), unauthorized:()=>{}}).mount('#app');
      </script>`})
      const filename = path.join(web, pathname)
      return route.fulfill({body:readFileSync(filename), contentType:pathname.endsWith('.js')?'text/javascript':pathname.endsWith('.css')?'text/css':'application/octet-stream'})
    })
    await page.goto('http://layers.test/')
    const rows = page.locator('.gx-layout__layer')
    await rows.first().waitFor()
    const initial = await rows.locator('.gx-layout__layer-name').allTextContents()
    await rows.last().dragTo(rows.first())
    assert.equal((await rows.locator('.gx-layout__layer-name').allTextContents())[0], initial.at(-1))
    const order = await page.evaluate(() => window.editor.state.draft.widgetOrder.large
      .filter(id => window.editor.state.draft.layouts.large[id].enabled))
    assert.equal(order.at(-1), 'pip_left')
    assert.equal(await page.getByRole('button', {name:/Move .* (forward|backward)/}).count(), 0)
    await page.setViewportSize({width:390,height:844})
    await rows.first().evaluate(row => row.scrollIntoView({block:'center'}))
    const handle = await rows.first().boundingBox()
    const target = await rows.nth(1).boundingBox()
    const client = await page.context().newCDPSession(page)
    await client.send('Emulation.setTouchEmulationEnabled', {enabled:true})
    const touch = (x, y) => [{x, y, id:1}]
    await client.send('Input.dispatchTouchEvent', {type:'touchStart', touchPoints:touch(handle.x + handle.width / 2, handle.y + handle.height / 2)})
    await client.send('Input.dispatchTouchEvent', {type:'touchMove', touchPoints:touch(target.x + target.width / 2, target.y + target.height / 2)})
    await client.send('Input.dispatchTouchEvent', {type:'touchEnd', touchPoints:[]})
    assert.equal(await page.evaluate(() => window.editor.state.draft.widgetOrder.large
      .filter(id => window.editor.state.draft.layouts.large[id].enabled).at(-2)), 'pip_left')
    // A canceled touch must leave the saved draft order untouched.
    const beforeCancel = await page.evaluate(() => JSON.stringify(window.editor.state.draft))
    await client.send('Input.dispatchTouchEvent', {type:'touchStart', touchPoints:touch(handle.x + handle.width / 2, handle.y + handle.height / 2)})
    await client.send('Input.dispatchTouchEvent', {type:'touchMove', touchPoints:touch(target.x + target.width / 2, target.y + target.height / 2)})
    await client.send('Input.dispatchTouchEvent', {type:'touchCancel', touchPoints:[]})
    assert.equal(await page.evaluate(() => JSON.stringify(window.editor.state.draft)), beforeCancel)
    assert.equal(await page.evaluate(() => window.editor.state.layerDrag), null)
    await page.screenshot({path:'/private/tmp/theme-widget-layers.png'})
    // A tap (including a little finger movement) selects without changing the order.
    const firstRow = await rows.first().boundingBox()
    const tapX = firstRow.x + firstRow.width / 2, tapY = firstRow.y + firstRow.height / 2
    const beforeTap = await page.evaluate(() => JSON.stringify(window.editor.state.draft))
    await client.send('Input.dispatchTouchEvent', {type:'touchStart', touchPoints:touch(tapX, tapY)})
    await client.send('Input.dispatchTouchEvent', {type:'touchMove', touchPoints:touch(tapX + 2, tapY + 2)})
    await client.send('Input.dispatchTouchEvent', {type:'touchEnd', touchPoints:[]})
    await page.getByRole('combobox', {name:'Selected widget', exact:true}).waitFor()
    assert.equal(await page.evaluate(() => JSON.stringify(window.editor.state.draft)), beforeTap)
    await page.getByRole('button', {name:'Widgets', exact:true}).click()
    await rows.first().click()
    await page.getByRole('combobox', {name:'Selected widget', exact:true}).waitFor()
    // Both outputs retain the same workspace and all editor features at phone and desktop sizes.
    for (const aa of [false, true]) {
      await page.goto('http://layers.test/' + (aa ? '?projection=1' : ''))
      await rows.first().waitFor()
      for (const width of [360, 390, 768, 1280, 1920]) {
        await page.setViewportSize({width, height:900})
        await page.evaluate(() => window.scrollTo(0, 0))
        const undoLabel = page.getByRole('button', {name:'Undo', exact:true}).locator('.gx-layout__action-label')
        assert.equal(await undoLabel.isVisible(), width > 600)
        const saveButton = page.getByRole('button', {name:'Save changes', exact:true})
        assert.equal(await saveButton.isVisible(), true)
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
        await page.getByRole('button', {name:'Edit widget', exact:true}).click()
        assert.equal(await page.getByRole('combobox', {name:'Selected widget', exact:true}).isVisible(), true)
        assert.equal(await page.getByLabel('X', {exact:true}).isVisible(), true)
        await page.getByRole('button', {name:'Remove from layout', exact:true}).click()
        assert.equal(await page.getByRole('button', {name:'Add to layout', exact:true}).isVisible(), true)
        await page.getByRole('button', {name:'Add to layout', exact:true}).click()
        if (!aa) {
          await page.getByRole('button', {name:'Road colors', exact:true}).click()
          assert.equal(await page.getByRole('combobox', {name:'Path style', exact:true}).isVisible(), true)
        }
        await page.getByRole('button', {name:'Device preview', exact:true}).click()
        assert.equal(await page.locator('svg.gx-layout__preview').isVisible(), false)
        await page.getByRole('button', {name:'Arrange widgets', exact:true}).click()
        assert.equal(await page.locator('svg.gx-layout__preview').isVisible(), true)
        await page.getByRole('button', {name:'Widgets', exact:true}).click()
        await page.evaluate(() => window.scrollTo(0, 0))
        await page.screenshot({path:'/private/tmp/theme-workspace-' + (aa ? 'aa-' : 'comma-') + width + '.png', fullPage:true})
      }
    }
    assert.deepEqual(errors, [])
    console.log('Theme Maker: mouse/touch layering, both outputs, all editor panels, preview switching and 360–1920px layouts passed')
  } finally { await browser.close() }
})().catch(error => {console.error(error);process.exitCode=1})
