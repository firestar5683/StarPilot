// Real Vue Settings renderer + shipped CSS; synthetic API, no device access.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const repo = path.resolve(__dirname, '../../../..')
const assets = path.join(repo, 'starpilot/system/the_galaxy/assets')
const layout = JSON.parse(fs.readFileSync(path.join(repo,'starpilot/common/assets/device_settings_layout.json')))
const out = process.env.MODE_EVIDENCE || '/opt/data/workspace/speed-control-big-dipper-evidence'
fs.mkdirSync(out,{recursive:true})
const fixture = `
import {createApp} from 'vue';
import {Settings} from '/assets/mobile/js/views/Settings.js';
import {store} from '/assets/mobile/js/store.js';
window.store=store; store.route='/settings/longitudinal-speed-following';
const layout=${JSON.stringify(layout)};
const values=Object.fromEntries(layout.flatMap(s=>s.params||[]).map(p=>[p.key,p.data_type==='bool'?false:(p.default??p.min??0)]));
Object.assign(values,{IsOnroad:'True',IsOffroad:'',SafeMode:false,HasRadar:true,GalaxyDeveloperMode:false});
window.writes=[]; window.paramWrites=[]; window.failWrite=false; window.failRead=false; window.holdWrite=false; window.holdRead=false;
window.state={mode:'conditional_experimental',values:{ExperimentalMode:true,ConditionalExperimental:true,ConditionalChill:false},locked:false,reason:'',experimental_confirmed:false};
window.externalMode=mode=>{window.state={...window.state,mode,values:{ExperimentalMode:mode==='experimental',ConditionalExperimental:mode==='conditional_experimental',ConditionalChill:mode==='conditional_chill'}}};
window.fetch=async(input,init={})=>{
 const url=new URL(input,location.href); const json=(data,status=200)=>new Response(JSON.stringify(data),{status});
 if(url.pathname==='/api/longitudinal_mode') {
  if(init.method==='PUT') {
   const body=JSON.parse(init.body); window.writes.push(body);
   if(window.holdWrite) await new Promise(r=>window.releaseWrite=r);
   if(window.failWrite) return json({error:'Injected write failure'},500);
   if(JSON.stringify(body.expected)!==JSON.stringify(window.state.values)) return json({error:'Changed elsewhere'},409);
   window.externalMode(body.mode);
  } else if(window.holdRead) {const captured=structuredClone(window.state); await new Promise(r=>window.releaseRead=r); return json(captured)}
  if(window.failRead) return json({},503);
  return json(window.state);
 }
 if(url.pathname.endsWith('device_settings_layout.json')) return json(layout);
 if(url.pathname==='/api/params/all') return json(values);
 if(url.pathname==='/api/params/defaults') return json({});
 if(url.pathname==='/api/params' && init.method==='PUT') {const body=JSON.parse(init.body);window.paramWrites.push(body);return json({updated:{[body.key]:body.value}})}
 throw new Error('Unmocked request '+url.pathname);
};
window.app=createApp(Settings); window.vm=window.app.mount('#app');
`
;(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE,args:['--no-sandbox']})
 const reports=[]
 try {
  for(const cfg of [{width:1440,height:1000,scale:1,touch:false},{width:1100,height:900,scale:1.25,touch:false},{width:390,height:844,scale:1,touch:true},{width:360,height:800,scale:1.5,touch:true},{width:768,height:1024,scale:2,touch:true}]) {
   const page=await browser.newPage({viewport:{width:cfg.width,height:cfg.height},hasTouch:cfg.touch,deviceScaleFactor:cfg.scale})
   const errors=[];page.on('pageerror',e=>errors.push(e.message))
   await page.route('**/*',async route=>{
    const url=new URL(route.request().url());assert.equal(url.hostname,'offline.invalid')
    if(url.pathname==='/') return route.fulfill({contentType:'text/html',body:`<html data-theme="dark"><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/assets/vendor/bootstrap-icons/bootstrap-icons.min.css"><link rel="stylesheet" href="/assets/mobile/css/material.css"><link rel="stylesheet" href="/assets/mobile/css/home.css"><script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script></head><body><main id="app" style="max-width:1100px;margin:auto;padding:16px"></main><script type="module" src="/setup.js"></script></body></html>`})
    if(url.pathname==='/setup.js') return route.fulfill({contentType:'text/javascript',body:fixture})
    const file=path.join(assets,url.pathname.replace(/^\/assets\//,''));if(fs.existsSync(file)&&fs.statSync(file).isFile()) return route.fulfill({path:file})
    return route.fulfill({status:404,body:'not found'})
   })
   await page.goto('http://offline.invalid/')
   await page.evaluate(scale=>{document.documentElement.style.zoom=String(scale)},cfg.scale)
   const select=page.locator('#gx-longitudinal-mode'), manage=page.locator('[aria-controls="gx-longitudinal-children"]')
   const waitMode=mode=>page.waitForFunction(mode=>{const e=document.querySelector('#gx-longitudinal-mode');return e?.value===mode&&!e.disabled},mode)
   await waitMode('conditional_experimental')
   assert.equal(await page.locator('.gx-mode-select__label span').innerText(),'Conditional Experimental')
   assert.equal(await page.locator('.gx-mode-select__label span').evaluate(e=>e.scrollWidth<=e.clientWidth+1),true)
   await select.focus()
   assert.equal(await page.locator('.gx-mode-select').evaluate(e=>getComputedStyle(e).outlineStyle),'solid')
   assert.deepEqual(await select.locator('option').allTextContents(),['Chill','Experimental','Conditional Experimental','Conditional Chill'])
   assert.equal(await page.evaluate(()=>writes.length),0)
   assert.equal(await manage.getAttribute('aria-expanded'),'false')
   assert.equal(await page.locator('#gx-longitudinal-children').count(),0)
   assert.ok((await page.locator('#gx-longitudinal-description').innerText()).includes('model-controlled gas and brakes'))
   await (cfg.touch?manage.tap():manage.click())
   const children=page.locator('#gx-longitudinal-children')
   assert.ok((await children.innerText()).includes('Persist Experimental State'))
   assert.ok(!(await children.innerText()).includes('Persist Chill State'))
   // Every direct classic child appears with identical description and native control.
   for(const owner of ['ConditionalExperimental','ConditionalChill']) {
    const target=owner==='ConditionalExperimental'?'conditional_experimental':'conditional_chill'
    if(target!=='conditional_experimental') {await select.selectOption(target);await waitMode(target)}
    await page.screenshot({path:path.join(out,`${cfg.width}-${cfg.scale}-${target}.png`),fullPage:true})
    for(const p of layout.flatMap(s=>s.params||[]).filter(p=>p.parent_key===owner)) {
     assert.ok((await children.innerText()).includes(p.label),p.key)
     const card=children.locator('.gx-row').filter({has:page.locator('.gx-row__label',{hasText:p.label})}).first()
     assert.ok(await card.count(),p.key)
     if(p.description) assert.equal(await card.locator('.gx-row__desc').first().textContent(),p.description)
    }
    if(owner==='ConditionalExperimental') {
     const lead=children.locator('.gx-tree-node').filter({has:page.locator('.gx-row__label',{hasText:'Lead Detected Ahead'})}).first()
     await lead.locator('input[type=checkbox]').check()
     await lead.locator('.gx-manage-btn').click()
     for(const p of layout.flatMap(s=>s.params||[]).filter(p=>p.parent_key==='CELead')) {
      const row=children.locator('.gx-row').filter({has:page.locator('.gx-row__label',{hasText:p.label})})
      assert.equal(await row.isVisible(),true,p.key)
      if(p.description) assert.equal(await row.locator('.gx-row__desc').innerText(),p.description)
      await row.locator('input[type=checkbox]').check()
     }
    }
   }
   const slider=children.locator('input[type=range]').first()
   await slider.focus();await slider.press('ArrowRight');await slider.press('Tab')
   assert.ok(await page.evaluate(()=>paramWrites.length>0))
   for(const target of ['chill','experimental']) {
    await select.selectOption(target);await waitMode(target);assert.equal(await manage.count(),0);assert.equal(await children.count(),0)
    await page.screenshot({path:path.join(out,`${cfg.width}-${cfg.scale}-${target}.png`),fullPage:true})
   }
   assert.equal(await page.evaluate(()=>writes.at(-1).acknowledged),true)
   await page.evaluate(()=>{holdWrite=true});await select.selectOption('conditional_chill')
   await page.waitForFunction(()=>!!window.releaseWrite)
   assert.equal(await select.inputValue(),'experimental');assert.equal(await select.isDisabled(),true)
   await page.evaluate(()=>{holdWrite=false;releaseWrite()});await waitMode('conditional_chill')
   await page.evaluate(()=>{failWrite=true});await select.selectOption('chill');await waitMode('conditional_chill')
   assert.ok((await page.locator('[role=alert]').innerText()).includes('Injected'))
   await page.evaluate(()=>{failWrite=false;externalMode('conditional_experimental')});await waitMode('conditional_experimental')
   // Routine polling never dims an available control; stale pre-write GET is ignored.
   await page.evaluate(()=>{holdRead=true});await page.waitForFunction(()=>!!window.releaseRead)
   assert.equal(await select.isEnabled(),true)
   await select.selectOption('conditional_chill');await waitMode('conditional_chill')
   await page.evaluate(()=>{holdRead=false;releaseRead()});await page.waitForTimeout(100)
   assert.equal(await select.inputValue(),'conditional_chill')
   for(const reason of ['Locked by Safe Mode.','openpilot longitudinal unavailable.']) {
    await page.evaluate(reason=>{state={...state,locked:true,reason}},reason)
    await page.waitForFunction(()=>document.querySelector('#gx-longitudinal-mode').disabled)
    assert.ok((await page.locator('.gx-longitudinal-mode').innerText()).includes(reason))
    assert.equal(await children.locator('input:not(:disabled),select:not(:disabled)').count(),0)
    await page.evaluate(()=>{state={...state,locked:false,reason:''}});await waitMode('conditional_chill')
   }
   // CSS zoom covers enlarged UI/text separately from DPR.
   await page.evaluate(scale=>{document.documentElement.style.zoom=String(scale)},cfg.scale)
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1)
   assert.equal(overflow,false,'horizontal overflow '+JSON.stringify(cfg))
   await page.screenshot({path:path.join(out,`${cfg.width}-${cfg.scale}-dark.png`),fullPage:true})
   await page.evaluate(()=>document.documentElement.setAttribute('data-theme','light'))
   await page.screenshot({path:path.join(out,`${cfg.width}-${cfg.scale}-light.png`),fullPage:true})
   await page.evaluate(()=>{failRead=true});await page.waitForFunction(()=>document.querySelector('#gx-longitudinal-mode').value==='')
   assert.equal(await select.isDisabled(),true)
   await page.evaluate(()=>{failRead=false});await waitMode('conditional_chill')
   // Search must use the same guarded selector, never generic Params for virtual key.
   await page.evaluate(()=>{store.search='Longitudinal control mode'})
   await page.locator('.gx-section__header').last().click()
   await waitMode('conditional_chill');await select.selectOption('chill');await waitMode('chill')
   assert.equal(await page.evaluate(()=>paramWrites.some(p=>p.key==='LongitudinalControlMode')),false)
   assert.deepEqual(errors,[])
   reports.push({...cfg,passed:true,writes:await page.evaluate(()=>writes.length)})
   fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(reports,null,2))
   await page.close()
  }
  console.log('PASS Big Dipper Settings: '+JSON.stringify(reports))
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1})
