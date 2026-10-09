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
      if (pathname === '/data/runtime.json') return route.fulfill({json:{schemaVersion:1, monitor:'local'}})
      if (pathname === '/api/auth/session') return route.fulfill({json:{state:'configured', authenticated:true, localAccess:true}})
      if (pathname === '/api/device/state') return route.fulfill({json:{state:'parked', maxAgeMs:3000}})
      if (pathname === '/' && new URL(route.request().url()).searchParams.has('shell')) return route.fulfill({contentType:'text/html', body:
        `<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/galaxy.css"><link rel="stylesheet" href="/css/settings.css"><div id="galaxy-app"></div><script type="module" src="/js/app.js"></script>`})
      if (pathname.startsWith('/api/')) return route.fulfill({json: pathname === '/api/android-auto/layout' ? projection : snapshot})
      if (pathname === '/') return route.fulfill({contentType:'text/html', body:`<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/galaxy.css"><link rel="stylesheet" href="/css/settings.css"><main class="gx-content"><div id="app"></div></main><script type="module">
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
    const source = await rows.last().boundingBox(), destination = await rows.first().boundingBox()
    const beforeMouse = await page.evaluate(() => JSON.stringify(window.editor.state.draft))
    await page.mouse.move(source.x + 30, source.y + source.height / 2)
    await page.mouse.down()
    await page.mouse.move(destination.x + 30, destination.y + destination.height / 2, {steps: 5})
    assert.equal(await page.locator('.gx-layout__drag-ghost').isVisible(), true)
    assert.equal(await page.locator('.gx-layout__outline').first().isVisible(), true)
    assert.equal(await page.locator('.is-drop-target').count(), 1)
    assert.equal(await page.evaluate(() => window.editor.renderWidgets.at(-1).id), 'pip_left')
    assert.equal(await page.evaluate(() => window.editor.state.history.undo.length), 0)
    await page.screenshot({path:'/private/tmp/theme-live-layer-drag.png'})
    await page.mouse.up()
    assert.equal(await page.locator('.gx-layout__drag-ghost').count(), 0)
    assert.equal(await page.evaluate(() => window.editor.state.history.undo.length), 1)
    await page.getByRole('button', {name:'Undo', exact:true}).click()
    assert.equal(await page.evaluate(() => JSON.stringify(window.editor.state.draft)), beforeMouse)
    await page.getByRole('button', {name:'Redo', exact:true}).click()
    assert.equal((await rows.locator('.gx-layout__layer-name').allTextContents())[0], initial.at(-1))
    const order = await page.evaluate(() => window.editor.state.draft.widgetOrder.large
      .filter(id => window.editor.state.draft.layouts.large[id].enabled))
    assert.equal(order.at(-1), 'pip_left')
    assert.equal(await page.getByRole('button', {name:/Move .* (forward|backward)/}).count(), 0)
    await page.setViewportSize({width:390,height:844})
    await rows.first().evaluate(row => row.scrollIntoView({block:'center'}))
    const handle = await rows.first().locator('.gx-layout__row-grip').boundingBox()
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
    await rows.first().locator('.gx-layout__layer-name').click()
    await page.getByRole('combobox', {name:'Selected widget', exact:true}).waitFor()
    // Both outputs retain the same workspace and all editor features at phone and desktop sizes.
    for (const aa of [false, true]) {
      await page.goto('http://layers.test/' + (aa ? '?projection=1' : ''))
      await rows.first().waitFor()
      // Swiping names scrolls the page without rearranging widgets or starting an edit.
      await page.setViewportSize({width:390, height:844})
      await client.send('Emulation.setTouchEmulationEnabled', {enabled:true})
      await rows.first().scrollIntoViewIfNeeded()
      const name = await rows.first().locator('.gx-layout__layer-name').boundingBox()
      const beforeScroll = await page.evaluate(() => ({draft:JSON.stringify(window.editor.state.draft), y:scrollY}))
      const scrollX = name.x + name.width / 2, scrollY = name.y + name.height / 2
      await client.send('Input.dispatchTouchEvent', {type:'touchStart', touchPoints:touch(scrollX, scrollY)})
      for (const distance of [30, 60, 100, 150])
        await client.send('Input.dispatchTouchEvent', {type:'touchMove', touchPoints:touch(scrollX, scrollY - distance)})
      await client.send('Input.dispatchTouchEvent', {type:'touchEnd', touchPoints:[]})
      await page.waitForFunction(y => scrollY > y, beforeScroll.y)
      assert.equal(await page.evaluate(() => JSON.stringify(window.editor.state.draft)), beforeScroll.draft)
      assert.equal(await page.evaluate(() => window.editor.state.layerDrag), null)
      assert.equal(await page.evaluate(() => window.editor.state.inspectorPanel), 'widgets')
      // Device preview receives the tentative order before release on both outputs.
      await page.setViewportSize({width:1280, height:1000})
      await client.send('Emulation.setTouchEmulationEnabled', {enabled:false})
      await page.getByRole('button', {name:'Device preview', exact:true}).click()
      const dragId = await rows.last().getAttribute('data-layer-id')
      const deviceSource = await rows.last().boundingBox(), deviceTarget = await rows.first().boundingBox()
      const previewRequest = page.waitForRequest(request => {
        if (!request.url().endsWith('/api/ui/layout/preview')) return false
        const doc = request.postDataJSON()?.document, order = doc?.widgetOrder
        const widgets = aa ? doc.widgets : doc.layouts.large
        return (aa ? order : order?.large)?.filter(id => widgets[id].enabled).at(-1) === dragId
      })
      await page.mouse.move(deviceSource.x + 30, deviceSource.y + deviceSource.height / 2)
      await page.mouse.down()
      await page.mouse.move(deviceTarget.x + 30, deviceTarget.y + deviceTarget.height / 2, {steps:5})
      await previewRequest
      assert.equal(await page.locator('.gx-layout__device-outline .gx-layout__outline').isVisible(), true)
      assert.equal(await page.evaluate(() => window.editor.state.layerDrag.moved), true)
      await page.mouse.up()
      await page.getByRole('button', {name:'Arrange widgets', exact:true}).click()
      for (const width of [360, 390, 768, 1280, 1920]) {
        await page.setViewportSize({width, height:900})
        await page.evaluate(() => window.scrollTo(0, 0))
        const undoLabel = page.getByRole('button', {name:'Undo', exact:true}).locator('.gx-layout__action-label')
        assert.equal(await undoLabel.isVisible(), await page.locator('.gx-layout').evaluate(el => el.clientWidth > 850))
        for (const name of ['Undo', 'Redo', 'Reload saved', 'Reset to stock StarPilot', 'Save changes']) {
          const action = page.getByRole('button', {name, exact:true})
          assert.equal(await action.isVisible(), true)
          if (width <= 768) assert.equal(await action.locator('svg').isVisible(), true)
        }
        assert.equal(await page.getByLabel('More actions', {exact:true}).count(), 0)
        const saveButton = page.getByRole('button', {name:'Save changes', exact:true})
        assert.equal(await saveButton.isVisible(), true)
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
        await page.getByRole('button', {name:'Edit widget', exact:true}).click()
        assert.equal(await page.getByRole('combobox', {name:'Selected widget', exact:true}).isVisible(), true)
        assert.equal(await page.getByLabel('X', {exact:true}).isVisible(), true)
        assert.equal(await page.locator('svg.gx-layout__preview .gx-layout__remove').count(), 0)
        await page.getByRole('button', {name:'Widgets', exact:true}).click()
        await rows.first().locator('.gx-layout__remove').click()
        await page.getByRole('button', {name:'Remove widget', exact:true}).click()
        await page.getByRole('button', {name:'Edit widget', exact:true}).click()
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
      if (aa) {
        // Home and Work independently switch between compact icons and word cards.
        await page.setViewportSize({width:390, height:844})
        await page.getByRole('button', {name:'Edit widget', exact:true}).click()
        await page.evaluate(() => { window.editor.add('nav_home'); window.editor.add('nav_work'); window.editor.state.selected = 'nav_home' })
        const homeDisplay = page.getByRole('group', {name:'Home display', exact:true})
        await homeDisplay.getByRole('button', {name:'Icons', exact:true}).click()
        assert.equal(await page.evaluate(() => window.editor.state.draft.layouts.large.nav_home.display), 'icons')
        assert.equal(await page.evaluate(() => window.editor.state.draft.layouts.large.nav_work.display), 'words')
        const homePreview = page.locator('svg.gx-layout__preview .gx-layout__widget').filter({has:page.locator('.gx-layout__hit[width="110"]')})
        assert.equal(await homePreview.count(), 1)
        assert.equal(await homePreview.locator('.gx-layout-widget-art path').count(), 1)
        assert.equal(await homePreview.locator('.gx-layout-widget-art text').count(), 0)
        await page.getByRole('button', {name:'Undo', exact:true}).click()
        assert.equal(await page.evaluate(() => window.editor.state.draft.layouts.large.nav_home.display), 'words')
        await page.getByRole('button', {name:'Redo', exact:true}).click()
        assert.equal(await homeDisplay.getByRole('button', {name:'Icons', exact:true}).getAttribute('aria-pressed'), 'true')
        await page.evaluate(() => { window.editor.state.selected = 'nav_work' })
        await page.getByRole('group', {name:'Work display', exact:true}).getByRole('button', {name:'Icons', exact:true}).click()
        assert.equal(await homePreview.count(), 2)
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true)
        await page.screenshot({path:'/private/tmp/android-auto-favorite-icons.png',fullPage:true})
        await page.getByRole('group', {name:'Work display', exact:true}).getByRole('button', {name:'Words', exact:true}).click()
        assert.equal(await homePreview.count(), 1)
        await page.evaluate(() => {
          window.editor.state.draft.layouts.large.current_speed.x += 1
          window.editor.requestLeave(() => { window.leaveCompleted = true })
        })
        assert.equal(await page.getByText('Leave without saving your changes?', {exact:true}).isVisible(), true)
        assert.equal(await page.getByRole('button', {name:'Undo', exact:true}).count(), 0)
        for (const name of ['Keep editing', 'Discard and leave', 'Save changes'])
          assert.equal(await page.getByRole('button', {name, exact:true}).isVisible(), true)
        await page.getByRole('button', {name:'Keep editing', exact:true}).click()
        await page.evaluate(() => window.editor.requestLeave(() => { window.leaveCompleted = true }, 'modal'))
        const leaveDialog = page.getByRole('alertdialog')
        assert.equal(await leaveDialog.getByText('Leave without saving your changes?', {exact:true}).isVisible(), true)
        for (const name of ['Keep editing', 'Discard and leave', 'Save changes'])
          assert.equal(await leaveDialog.getByRole('button', {name, exact:true}).isVisible(), true)
        await leaveDialog.getByRole('button', {name:'Keep editing', exact:true}).click()
        assert.equal(await page.evaluate(() => window.leaveCompleted), undefined)
      }
    }
    // Exercise the actual menu/route guard while the widget list is scrolled on phones.
    for (const route of ['/theme_maker', '/theme_maker/android_auto']) {
      for (const width of [360, 390, 1280]) {
        await page.setViewportSize({width, height:844})
        await page.goto('http://layers.test/?shell=1#' + route)
        await rows.first().waitFor()
        await page.getByRole('button', {name:'Edit widget', exact:true}).click()
        const x = page.getByLabel('X', {exact:true})
        await x.fill(String(Number(await x.inputValue()) + 1))
        await x.press('Tab')
        await page.getByRole('button', {name:'Widgets', exact:true}).click()
        await rows.last().scrollIntoViewIfNeeded()
        if (width < 768) await page.locator('.blur-nav').getByRole('button', {name:'Tools', exact:true}).click()
        else {
          await page.getByRole('button', {name:'Menu', exact:true}).click()
          await page.getByRole('complementary', {name:'Galaxy navigation'}).getByRole('button', {name:'Tools', exact:true}).click()
        }
        const dialog = page.getByRole('alertdialog', {name:'Leave without saving your changes?'})
        await dialog.waitFor()
        assert.equal(new URL(page.url()).hash, '#' + route, 'navigation waits for confirmation')
        const bounds = await dialog.boundingBox()
        assert(bounds.x >= 0 && bounds.y >= 0 && bounds.x + bounds.width <= width && bounds.y + bounds.height <= 844)
        assert.equal(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth), true)
        for (const name of ['Keep editing', 'Discard and leave', 'Save changes']) {
          const button = dialog.getByRole('button', {name, exact:true})
          assert.equal(await button.isVisible(), true)
          assert((await button.boundingBox()).height >= 48)
        }
        await page.screenshot({path:`/private/tmp/theme-leave-${route.endsWith('android_auto') ? 'aa' : 'comma'}-${width}.png`})
        await dialog.getByRole('button', {name:'Keep editing', exact:true}).click()
        assert.equal(await dialog.count(), 0)
        assert.equal(new URL(page.url()).hash, '#' + route)
        assert.equal(await page.getByRole('button', {name:'Save changes', exact:true}).isEnabled(), true)
        if (width < 768) await page.locator('.blur-nav').getByRole('button', {name:'Tools', exact:true}).click()
        else {
          await page.getByRole('button', {name:'Menu', exact:true}).click()
          await page.getByRole('complementary', {name:'Galaxy navigation'}).getByRole('button', {name:'Tools', exact:true}).click()
        }
        await dialog.getByRole('button', {name:'Discard and leave', exact:true}).click()
        await page.waitForURL('**#/tools')
        assert.equal(await dialog.count(), 0)
      }
    }
    assert.deepEqual(errors, [])
    console.log('Theme Maker: mouse/touch layering, both outputs, all editor panels, preview switching and 360–1920px layouts passed')
  } finally { await browser.close() }
})().catch(error => {console.error(error);process.exitCode=1})
