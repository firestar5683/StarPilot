// Local-only real DOM smoke. Requires Playwright + its Chromium; no live API.
// PLAYWRIGHT_MODULE can point at an existing isolated Playwright installation.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const repo = path.resolve(__dirname, '../../../..')
const assets = path.join(repo, 'starpilot/system/the_galaxy/assets')
const fixturePath = process.env.GALAXY_DOM_FIXTURE
if (!fixturePath) throw new Error('Set GALAXY_DOM_FIXTURE to the existing offline setup.js fixture')
let fixture = fs.readFileSync(fixturePath, 'utf8').replace(/import \{DeviceSettings\}[^\n]+/g, '')
fixture += `
paramsFixture.IsOnroad = ${process.env.GALAXY_DOM_ONROAD === '1'};
paramsFixture.GalaxyDeveloperMode = false;
let modeState = {mode:'conditional_experimental', values:{ExperimentalMode:true,ConditionalExperimental:true,ConditionalChill:false},locked:false,reason:'',experimental_confirmed:false};
window.modeWrites=[]; window.failModeWrite=false; window.failModeRead=false;
window.holdModeWrite=false;
const fixtureFetch=window.fetch;
window.fetch=async (input, init={}) => {
  const url=new URL(input,location.href);
  if(url.pathname!='/api/longitudinal_mode') return fixtureFetch(input,init);
  if(init.method==='PUT') {
    const body=JSON.parse(init.body); window.modeWrites.push(body);
    if(window.holdModeWrite) await new Promise(resolve => {window.releaseModeWrite=resolve});
    if(window.failModeWrite) return new Response(JSON.stringify({error:'Injected failure'}),{status:500});
    modeState={...modeState,mode:body.mode,values:{ExperimentalMode:body.mode==='experimental',ConditionalExperimental:body.mode==='conditional_experimental',ConditionalChill:body.mode==='conditional_chill'}};
  }
  if(window.failModeRead) return new Response('{}',{status:503});
  return new Response(JSON.stringify(modeState),{status:200});
};
window.lockMode=()=>{modeState={...modeState,locked:true,reason:'Safe Mode locked'};};
import {DeviceSettings} from '/assets/components/tools/device_settings.js';
DeviceSettings({params:{section:'longitudinal-speed-following'}})(document.querySelector('#app'));
`
;(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] })
  try {
    const page = await browser.newPage({ viewport: { width: 1100, height: 900 } })
    const errors = []
    const dialogs = []
    page.on('dialog', dialog => { dialogs.push(dialog.message()); dialog.dismiss() })
    page.on('pageerror', error => errors.push(error.message))
    await page.route('**/*', async route => {
      const url = new URL(route.request().url())
      if (url.hostname !== 'offline.invalid') throw new Error('External access blocked')
      if (url.pathname === '/device_settings') return route.fulfill({contentType:'text/html',body:'<html><head><link rel="stylesheet" href="/assets/components/main.css"><link rel="stylesheet" href="/assets/components/settings.css"><link rel="stylesheet" href="/assets/components/tools/device_settings.css"></head><body><main id="app"></main><script type="module" src="/setup.js"></script></body></html>'})
      if (url.pathname === '/setup.js') return route.fulfill({contentType:'text/javascript',body:fixture})
      if (url.pathname.startsWith('/assets/')) {
        const file = path.join(assets, url.pathname.slice('/assets/'.length))
        if (fs.existsSync(file) && fs.statSync(file).isFile()) return route.fulfill({path:file})
      }
      return route.fulfill({status:404,body:'not found'})
    })
    await page.goto('http://offline.invalid/device_settings')
    await page.getByRole('button', {name:'Longitudinal (Speed & Following)',exact:true}).click()
    const select = page.locator('#ds-LongitudinalControlMode')
    await select.waitFor()
    await page.waitForFunction(() => document.querySelector('#ds-LongitudinalControlMode')?.value === 'conditional_experimental')
    assert.equal(await select.isEnabled(), true)
    assert.deepEqual(await select.locator('option').allTextContents(), ['Chill','Experimental','Conditional Experimental','Conditional Chill'])
    assert.equal(await page.locator('#ds-ConditionalExperimental, #ds-ConditionalChill').count(), 0)
    assert.equal(await page.locator('#ds-manual-CESpeed').count(), 0)
    const manage = page.locator('[aria-controls="ds-LongitudinalControlMode-children"]')
    assert.equal(await manage.getAttribute('aria-expanded'), 'false')
    if(process.env.GALAXY_DOM_SCREENSHOT) await page.screenshot({path:process.env.GALAXY_DOM_SCREENSHOT.replace('.png','-collapsed.png'),fullPage:true})
    await manage.click()
    assert.equal(await page.locator('#ds-manual-CESpeed').isVisible(), true)
    await manage.click()
    assert.equal(await page.locator('#ds-manual-CESpeed').count(), 0)
    assert.equal(await select.isVisible(), true)
    await manage.click()
    assert.equal(await page.locator('#ds-manual-CCMSpeed').count(), 0)
    assert.equal(await page.evaluate(() => window.modeWrites.length), 0)
    for (const target of ['conditional_chill','chill']) {
      await select.selectOption(target)
      await page.waitForFunction(target => document.querySelector('#ds-LongitudinalControlMode')?.value === target && !document.querySelector('#ds-LongitudinalControlMode')?.disabled, target)
      assert.equal(await page.locator('#ds-manual-CESpeed').count(), 0)
      assert.equal(await manage.count(), target === 'chill' ? 0 : 1)
      assert.equal(await page.locator('#ds-manual-CCMSpeed').count(), target === 'conditional_chill' ? 1 : 0)
    }
    const beforeExperimental = await page.evaluate(() => window.modeWrites.length)
    await page.evaluate(() => { window.holdModeWrite=true })
    await select.selectOption('experimental')
    await page.waitForFunction(() => !!window.releaseModeWrite && document.querySelector('#ds-LongitudinalControlMode')?.disabled)
    await page.evaluate(() => { window.holdModeWrite=false; window.releaseModeWrite() })
    await page.waitForFunction(() => document.querySelector('#ds-LongitudinalControlMode')?.value === 'experimental' && !document.querySelector('#ds-LongitudinalControlMode')?.disabled)
    assert.equal(await page.evaluate(() => window.modeWrites.at(-1).acknowledged), true)
    assert.equal(await page.evaluate(() => window.modeWrites.length), beforeExperimental + 1)
    assert.deepEqual(dialogs, [])
    assert.equal(await manage.count(), 0)
    assert.equal(await page.locator('#ds-manual-CESpeed, #ds-manual-CCMSpeed').count(), 0)
    await page.evaluate(() => { window.failModeWrite = true })
    await select.selectOption('conditional_chill')
    await page.waitForFunction(() => document.querySelector('#ds-LongitudinalControlMode')?.value === 'experimental' && !document.querySelector('#ds-LongitudinalControlMode')?.disabled)
    await page.evaluate(() => { window.failModeWrite = false })
    await select.selectOption('conditional_experimental')
    await page.waitForFunction(() => document.querySelector('#ds-manual-CESpeed'))
    await page.screenshot({path:process.env.GALAXY_DOM_SCREENSHOT || '/tmp/galaxy-longitudinal-mode.png',fullPage:true})
    await page.evaluate(() => window.lockMode())
    await page.waitForFunction(() => document.querySelector('#ds-LongitudinalControlMode')?.disabled)
    await page.evaluate(() => { window.failModeRead=true })
    await page.waitForFunction(() => document.querySelector('#ds-LongitudinalControlMode')?.value === '')
    assert.equal(await select.isDisabled(), true)
    assert.deepEqual(errors, [])
    console.log('PASS: real DOM initial CEM precedence/no writes; collapsed Manage disclosure/visible dropdown; all four choices; mode-specific children; no experimental dialog; request acknowledgement; failed-write readback; Safe Mode and missing-state locks; zero page errors')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode=1 })
