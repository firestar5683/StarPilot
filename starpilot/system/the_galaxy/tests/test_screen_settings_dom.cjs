// Local-only Vue interaction tests. All API requests use synthetic state.
// GALAXY_REPO / PLAYWRIGHT_MODULE may point at an isolated checkout/runtime.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const repo = process.env.GALAXY_REPO || path.resolve(__dirname, '../../../..')
const assets = path.join(repo, 'starpilot/system/the_galaxy/assets')
const layout = JSON.parse(fs.readFileSync(path.join(repo, 'starpilot/common/assets/device_settings_layout.json')))
const section = layout.find(s => s.params.some(p => p.key === 'ScreenManagement'))
const wakeDefaults = {
  StandbyWakeEngage:true, StandbyWakeDisengage:true, StandbyWakeInfoAlert:true, StandbyWakeWarningAlert:true,
  StandbyWakeCriticalAlert:true, StandbyWakeTurnSignal:false, StandbyWakeBrake:false, StandbyWakeAccelerator:false,
  StandbyWakeTouch:true, StandbyWakeDriveState:true, StandbyWakeButton:false,
}
const wakes = Object.keys(wakeDefaults)
const fixture = `
import {createApp, reactive} from 'vue';
import {SettingTree} from '/assets/mobile/js/components/SettingTree.js';
import {applyParamChange, isSettingVisible} from '/assets/mobile/js/params.js';
import {api} from '/assets/mobile/js/api.js';
const layout = ${JSON.stringify(layout)};
const values = reactive({ScreenManagement:true, ScreenBrightness:101, ScreenBrightnessManual:67, ScreenBrightnessOffset:0,
  ScreenBrightnessOnroad:101, ScreenBrightnessOnroadOffset:0, ScreenTimeout:30, ScreenTimeoutOnroad:15, StandbyMode:false,
  ...${JSON.stringify(wakeDefaults)}});
window.values=values; window.writes=[]; window.holdWrite=false; window.failWrite=false;
window.fetch=async (input,init={}) => {
  const url=new URL(input,location.href);
  if(url.pathname==='/assets/components/tools/device_settings_layout.json') return new Response(JSON.stringify(layout),{status:200});
  if(url.pathname!=='/api/params' || init.method!=='PUT') throw new Error('Unexpected API: '+url.pathname);
  const {key,value}=JSON.parse(init.body); window.writes.push({key,value});
  if(window.holdWrite) await new Promise(resolve=>window.releaseWrite=resolve);
  if(window.failWrite) return new Response(JSON.stringify({error:'Injected save failure'}),{status:500});
  const updated={[key]:value};
  if(/^ScreenBrightness(Onroad)?$/.test(key) && value<=100) updated[key+'Manual']=value;
  return new Response(JSON.stringify({updated}),{status:200});
};
const section=(await api.getLayout()).find(s=>s.params.some(p=>p.key==='ScreenManagement'));
createApp({components:{SettingTree},setup:()=>({values}),
  data:()=>({expanded:{ScreenManagement:true}}),
  computed:{params(){return section.params.filter(p=>isSettingVisible(section,p,this.values))}},
  methods:{change(patch){Object.assign(values,applyParamChange(values,patch))}},
  template:'<div class="gx-card"><SettingTree :params="params" :values="values" :expanded="expanded" @change="change" @manage="expanded[$event]=!expanded[$event]" /></div>'
}).mount('#app');
`
;(async () => {
  assert.equal(section.params.find(p => p.key === 'ScreenBrightness').ui_type, 'numeric', 'shared layout preserves old Galaxy brightness rendering')
  assert.equal(section.params.find(p => p.key === 'ScreenBrightness').galaxy_ui_type, 'brightness', 'New Galaxy needs its separate Auto/Manual control')
  const browser = await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_EXECUTABLE})
  try {
    const page=await browser.newPage({viewport:{width:1100,height:1000}})
    const errors=[]
    page.on('pageerror',e=>errors.push(e.message))
    await page.route('**/*',async route=>{
      const url=new URL(route.request().url())
      assert.equal(url.hostname,'offline.invalid','all network must stay synthetic')
      if(url.pathname==='/') return route.fulfill({contentType:'text/html',body:'<html data-theme="dark"><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/assets/mobile/css/material.css"><script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script></head><body><main id="app"></main><div id="snackbar_wrapper"></div><script type="module" src="/setup.js"></script></body></html>'})
      if(url.pathname==='/setup.js') return route.fulfill({contentType:'text/javascript',body:fixture})
      const file=path.join(assets,url.pathname.slice('/assets/'.length))
      if(url.pathname.startsWith('/assets/') && fs.existsSync(file) && fs.statSync(file).isFile()) return route.fulfill({path:file})
      return route.fulfill({status:404,body:'not found'})
    })
    await page.goto('http://offline.invalid/')
    const offMode=page.locator('#gx-ScreenBrightness-mode')
    const onMode=page.locator('#gx-ScreenBrightnessOnroad-mode')
    const offSlider=page.locator('#gx-ScreenBrightness-slider')
    const onSlider=page.locator('#gx-ScreenBrightnessOnroad-slider')
    await offMode.waitFor()
    assert.equal(await offMode.inputValue(),'auto')
    assert.equal(await onMode.inputValue(),'auto')
    assert.deepEqual(await offMode.locator('option').allTextContents(),['Auto','Manual'])
    assert.equal(await offSlider.getAttribute('min'),'-30')
    assert.equal(await offSlider.getAttribute('max'),'30')
    assert.equal(await offSlider.inputValue(),'0')
    assert.equal(await offSlider.getAttribute('aria-valuetext'),'0%')
    assert.equal(await page.getByText('-30%',{exact:true}).count(),2)
    assert.equal(await page.getByText('+30%',{exact:true}).count(),2)
    assert.equal(await page.getByText(/5% while the screen is awake/).count(),2)
    assert.equal(await page.getByText('Screen Timeout (Offroad)',{exact:true}).count(),1)
    assert.equal(await page.getByText('Screen Timeout (Onroad)',{exact:true}).count(),0)
    assert.equal(await page.getByText(/Works independently of Standby Mode/).count(),0)
    assert.ok(section.params.filter(p => /^ScreenTimeout/.test(p.key)).every(p => p.unit === ' seconds'),'timeouts display seconds')
    assert.equal(await page.getByText('30 seconds',{exact:true}).count(),1,'offroad timeout readout includes its unit')
    assert.equal(await page.evaluate(()=>window.writes.length),0,'initial render cannot write settings')
    assert.equal(await page.getByText('101',{exact:true}).count(),0,'internal Auto sentinel cannot appear')

    await offMode.selectOption('manual')
    await page.waitForFunction(()=>window.values.ScreenBrightness===67)
    assert.equal(await offSlider.getAttribute('min'),'0')
    assert.equal(await offSlider.getAttribute('max'),'100')
    assert.equal(await offSlider.inputValue(),'67','mode change restores saved manual brightness')
    await onMode.selectOption('manual')
    await page.waitForFunction(()=>window.values.ScreenBrightnessOnroad===100)
    assert.equal(await onSlider.inputValue(),'100','missing manual memory defaults to 100')
    await onSlider.fill('45'); await onSlider.dispatchEvent('change')
    await page.waitForFunction(()=>window.values.ScreenBrightnessOnroadManual===45)
    await page.locator('.gx-brightness').filter({has:onSlider}).getByRole('button',{name:'Default',exact:true}).click()
    await page.waitForFunction(()=>window.values.ScreenBrightnessOnroadManual===100)
    assert.equal(await onSlider.inputValue(),'100','manual Default restores 100%')
    await offSlider.fill('0'); await offSlider.dispatchEvent('change')
    await page.waitForFunction(()=>window.values.ScreenBrightnessManual===0)
    await offMode.selectOption('auto')
    await page.waitForFunction(()=>window.values.ScreenBrightness===101)
    await offSlider.fill('-30'); await offSlider.dispatchEvent('change')
    await page.waitForFunction(()=>window.values.ScreenBrightnessOffset===-30)
    assert.equal(await offSlider.getAttribute('aria-valuetext'),'-30%')
    await offSlider.fill('30'); await offSlider.dispatchEvent('change')
    await page.waitForFunction(()=>window.values.ScreenBrightnessOffset===30)
    assert.equal(await offSlider.getAttribute('aria-valuetext'),'+30%')
    await offMode.selectOption('manual')
    await page.waitForFunction(()=>window.values.ScreenBrightness===0)
    assert.equal(await offSlider.inputValue(),'0','manual zero survives Auto roundtrip')
    assert.equal(await onSlider.inputValue(),'100','onroad and offroad remain independent')

    // A poll/re-render during a drag must preserve the preview and mode.
    await offSlider.evaluate(input=>{input.value='83';input.dispatchEvent(new Event('input',{bubbles:true}))})
    await page.evaluate(()=>{window.values.ScreenBrightness=20;window.values.ScreenBrightnessOffset=-10})
    assert.equal(await offSlider.inputValue(),'83')
    await offSlider.dispatchEvent('change')
    await page.waitForFunction(()=>window.values.ScreenBrightnessManual===83)
    await page.evaluate(()=>{window.holdWrite=true})
    await offMode.selectOption('auto')
    await page.waitForFunction(()=>!!window.releaseWrite)
    assert.equal(await offMode.isDisabled(),true)
    await page.evaluate(()=>{window.values.ScreenBrightness=83})
    assert.equal(await offMode.inputValue(),'auto','stale props cannot reverse pending mode change')
    await page.evaluate(()=>{window.holdWrite=false;window.releaseWrite()})
    await page.waitForFunction(()=>!document.querySelector('#gx-ScreenBrightness-mode').disabled)
    assert.equal(await offMode.inputValue(),'auto')

    await page.evaluate(()=>{window.failWrite=true})
    await offMode.selectOption('manual')
    await page.waitForFunction(()=>!document.querySelector('#gx-ScreenBrightness-mode').disabled)
    assert.equal(await offMode.inputValue(),'auto','failed mode saves roll back')
    await offSlider.fill('24'); await offSlider.dispatchEvent('change')
    await page.waitForFunction(()=>!document.querySelector('#gx-ScreenBrightness-mode').disabled)
    assert.equal(await offSlider.inputValue(),'-10','failed offset saves roll back')
    await page.evaluate(()=>{window.failWrite=false})

    const standbyNode=page.locator('.gx-tree-node').filter({has:page.getByText('Standby Mode',{exact:true})})
    const standby=standbyNode.locator('.gx-switch input')
    const wakeRow=key=>page.locator('.gx-row').filter({has:page.getByText(section.params.find(p=>p.key===key).label,{exact:true})})
    assert.equal(await wakeRow(wakes[0]).count(),0)
    assert.equal(await standbyNode.getByRole('button',{name:'Manage',exact:true}).count(),0)
    await standby.check()
    await standbyNode.getByRole('button',{name:'Manage',exact:true}).waitFor()
    assert.equal(await wakeRow(wakes[0]).count(),0,'Standby children start collapsed')
    assert.equal(await page.getByText('Screen Timeout (Onroad)',{exact:true}).count(),0,'onroad timeout waits for Manage')
    await standbyNode.getByRole('button',{name:'Manage',exact:true}).click()
    await wakeRow(wakes[0]).waitFor()
    assert.equal(await page.getByText('Screen Timeout (Onroad)',{exact:true}).count(),1)
    assert.equal(await page.getByText('15 seconds',{exact:true}).count(),1,'onroad timeout readout includes its unit')
    assert.equal(await page.getByText(/Also sets the duration of a temporary wake at 0% brightness/).count(),0)
    assert.equal(section.params.find(p=>p.key==='ScreenTimeoutOnroad').parent_key,'StandbyMode')
    assert.equal(await page.locator('.gx-wake-choice, [data-wake-choice]').count(),0,'wake events use ordinary Galaxy switches')
    for(const key of wakes) {
      const param=section.params.find(p=>p.key===key)
      assert.ok(param && param.ui_type==='toggle','all eleven wake events use standard toggles')
      assert.equal(param.default,wakeDefaults[key],key+' retains its required default')
      assert.match(param.description,/wake.*standby|standby.*wake/i,key+' explains waking Standby')
      assert.equal(await wakeRow(key).getByText(param.description,{exact:true}).count(),1,key+' description is visible')
      const checkbox=wakeRow(key).locator('.gx-switch input')
      assert.equal(await checkbox.isChecked(),wakeDefaults[key])
      await checkbox.setChecked(!wakeDefaults[key])
      await page.waitForFunction(({key,expected})=>window.values[key]===expected,{key,expected:!wakeDefaults[key]})
    }
    assert.equal(await page.getByText(/Touch always wakes|ignition changes also wake/).count(),0)
    assert.match(section.params.find(p=>p.key==='StandbyMode').description,/only.*selected/i)
    assert.match(section.params.find(p=>p.key==='StandbyWakeDriveState').description,/Park.*Reverse.*Neutral.*Drive/)
    assert.match(section.params.find(p=>p.key==='StandbyWakeDriveState').description,/ignition.*driving/)
    assert.match(section.params.find(p=>p.key==='StandbyWakeButton').description,/Bluetooth.*steering wheel/)
    await page.waitForFunction(()=>!Array.from(document.querySelectorAll('.gx-switch input')).some(input=>input.disabled))
    await page.evaluate(()=>{window.values.ScreenBrightnessOffset=80})
    assert.equal(await offSlider.inputValue(),'30','older saved offsets stay within the new display range')
    await page.evaluate(defaults=>{
      Object.assign(window.values,defaults)
      window.values.ScreenBrightnessOffset=0
      document.querySelector('#snackbar_wrapper').replaceChildren()
    },wakeDefaults)
    await page.waitForTimeout(350) // Let the standard switch transitions settle for preview images.
    if(process.env.GALAXY_DOM_SCREENSHOT) await page.screenshot({path:process.env.GALAXY_DOM_SCREENSHOT+'-desktop.png',fullPage:true})
    await page.setViewportSize({width:390,height:844})
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,'mobile must not overflow')
    if(process.env.GALAXY_DOM_SCREENSHOT) await page.screenshot({path:process.env.GALAXY_DOM_SCREENSHOT+'-mobile.png',fullPage:true})
    await standbyNode.getByRole('button',{name:'Close',exact:true}).click()
    await wakeRow(wakes[0]).waitFor({state:'detached'})
    assert.equal(await page.getByText('Screen Timeout (Onroad)',{exact:true}).count(),0,'Close hides timeout with wake choices')
    assert.equal(await page.getByText('Screen Timeout (Offroad)',{exact:true}).count(),1,'offroad timeout stays outside submenu')
    if(process.env.GALAXY_DOM_SCREENSHOT) await page.screenshot({path:process.env.GALAXY_DOM_SCREENSHOT+'-mobile-collapsed.png',fullPage:true})
    await standbyNode.getByRole('button',{name:'Manage',exact:true}).click()
    await wakeRow(wakes[0]).waitFor()
    await standby.uncheck()
    await wakeRow(wakes[0]).waitFor({state:'detached'})
    assert.equal(await page.getByText('Screen Timeout (Onroad)',{exact:true}).count(),0)
    assert.equal(await standbyNode.getByRole('button',{name:'Manage',exact:true}).count(),0)
    await page.evaluate(()=>{window.values.StandbyMode=true;window.values.ScreenManagement=false})
    assert.equal(await wakeRow(wakes[0]).count(),0,'disabled Screen Settings hides wake choices')
    assert.deepEqual(errors,[])
    console.log('PASS: real Vue Auto/Manual controls, manual100 default/reset, +/-30% offsets, memory/zero, independent contexts, drag/pending stability, save rollback, eleven described standard wake toggles, Manage/Close submenu, seconds readouts, mobile layout, zero page errors')
  } finally {await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1})
