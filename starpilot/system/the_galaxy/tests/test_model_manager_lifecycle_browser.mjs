// Real Chromium, shipped components, synthetic API only. No device/network fall-through.
import assert from 'node:assert/strict';
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = (process.env.REPO || fileURLToPath(new URL('../../../../', import.meta.url))) + '/starpilot/system/the_galaxy';
const out = process.env.EVIDENCE;
if (out) mkdirSync(out, {recursive:true});
const browser = await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE, args:['--no-sandbox']});
const results=[];
const tick=()=>new Promise(r=>setTimeout(r,100));
try {
for (const surface of ['classic','mobile']) for (const scenario of ['stale-poll','reject-read-failure','abort-read-failure','leave-write','leave-readback']) {
 const context=await browser.newContext({viewport:{width:1200,height:850}});
 const writes=[], unexpected=[], errors=[]; let active='gpu-a', heldGet=null, heldPut=null, holdNext=false, failReads=false, gets=0;
 const models=['gpu-a','gpu-b','small'].map(value=>({value,label:value,installed:true,requiresGpu:value!=='small',gpuAvailable:true}));
 const payload=()=>({models,activeBigModel:active,activeSmallModel:'small',currentModel:'small',summary:{installed:3,total:3},isOnroad:false,downloading:true,modelToDownload:'other'});
 const mobile=surface==='mobile';
 const mount=mobile ? `import {createApp} from 'vue';import {ModelManager} from '/assets/mobile/js/views/ModelManager.js';let app;window.mount=()=>{app=createApp(ModelManager);window.vm=app.mount('#app')};window.leave=()=>app.unmount();window.poll=()=>window.vm.refresh();window.act=(a)=>window.vm.runAction(a);` : `import {html} from '/assets/vendor/arrow-core.js';import {ModelManager} from '/assets/components/tools/model_manager.js';window.mount=()=>html\`\${()=>ModelManager()}\`(document.querySelector('#app'));window.leave=()=>document.querySelector('#app').replaceChildren();`;
 await context.route('**/*',async route=>{
  const req=route.request(),u=new URL(req.url());
  if(u.origin!=='http://galaxy.invalid') {unexpected.push(req.url());return route.abort();}
  if(u.pathname==='/api/models/status' && req.method()==='GET') {
   gets++; const json=payload();
   if(holdNext) {holdNext=false;heldGet={route,json};return;}
   return route.fulfill(failReads?{status:503,json:{error:'Synthetic read failure'}}:{json});
  }
  if(req.method()!=='GET') {
   writes.push({method:req.method(),path:u.pathname,body:req.postData()?req.postDataJSON():null});
   if(u.pathname==='/api/models/cancel') return route.fulfill({json:{message:'cancelled'}});
   if(u.pathname!=='/api/models/active') {unexpected.push(req.url());return route.abort();}
   if(scenario==='leave-write') {heldPut=route;return;}
   if(scenario!=='reject-read-failure') active=writes.at(-1).body.model;
   if(scenario.includes('read-failure')) {failReads=true;return scenario.startsWith('abort')?route.abort('connectionreset'):route.fulfill({status:503,json:{error:'Synthetic rejection'}});}
   if(scenario==='leave-readback') holdNext=true;
   return route.fulfill({json:{message:'selected'}});
  }
  if(u.pathname.startsWith('/assets/')) {
   try {
    let body=readFileSync(root+u.pathname);
    if(u.pathname.endsWith('/tools/model_manager.js')) body=body.toString()+ '\nwindow.poll=()=>fetchStatus();window.act=(a)=>runAction(a);';
    return route.fulfill({body,contentType:u.pathname.endsWith('.css')?'text/css':'text/javascript'});
   } catch(e) {unexpected.push(u.pathname);return route.abort();}
  }
  if(u.pathname!=='/manage_models') {unexpected.push(u.pathname);return route.abort();}
  return route.fulfill({contentType:'text/html',body:`<script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script><div id="snackbar_wrapper"></div><main id="app"></main><script type="module">${mount}window.mount();</script>`});
 });
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 // Capture snackbar effects without changing the shipped API module.
 await page.addInitScript(()=>{
  // Hold periodic polling; every race uses explicitly released real requests.
  const timeout=window.setTimeout;window.setTimeout=(fn,ms,...args)=>timeout(fn,[1000,2000,4000].includes(ms)?60000:ms,...args);
  window.notices=[];window.showSnackbar=(...a)=>window.notices.push(a);
  new MutationObserver(records=>{for(const r of records) if(r.target.id==='snackbar_wrapper') for(const n of r.addedNodes) window.notices.push(n.textContent);}).observe(document,{childList:true,subtree:true});
 });
 const select=mobile?page.locator('.gx-row').filter({has:page.getByText('Active Big',{exact:true})}).locator('select'):page.locator('#mm-active-big-model-select');
 const until=async(fn,msg)=>{for(let i=0;i<80;i++){if(await fn())return;await tick();}throw new Error(msg);};
 let failure=null;
 try {
  await page.goto('http://galaxy.invalid/manage_models');
  await until(async()=>await select.count() && await select.inputValue()==='gpu-a','initial selection');
  if(scenario==='stale-poll') {holdNext=true;await page.evaluate(()=>{window.poll()});await until(()=>heldGet,'held prewrite poll');}
  await select.selectOption('');
  await until(()=>writes.length===1,'selection PUT');
  assert.deepEqual(writes,[{method:'PUT',path:'/api/models/active',body:{profile:'big',model:''}}]);
  if(scenario==='stale-poll') {
   await tick(); await heldGet.route.fulfill({json:heldGet.json});heldGet=null;await tick();
   assert.equal(await select.inputValue(),'','old poll must not overwrite accepted selection');
   assert.equal(await select.isDisabled(),false,'post-write readback unlocks');
  } else if(scenario.includes('read-failure')) {
   await until(()=>gets>=2,'failed readback requested');await tick();
   assert.equal(await select.isDisabled(),true,'uncertain selection stays locked');
   await page.evaluate(()=>window.act('select-big'));await tick();assert.equal(writes.length,1,'programmatic second selection blocked');
   await page.evaluate(()=>window.act('cancel'));await until(()=>writes.length===2,'cancel remains usable');
   assert.deepEqual(writes[1],{method:'POST',path:'/api/models/cancel',body:null});
   failReads=false;await page.evaluate(()=>window.poll());
   await until(async()=>!(await select.isDisabled()),'authoritative retry unlocks');
   assert.equal(await select.inputValue(),scenario.startsWith('abort')?'':'gpu-a');
  } else {
   await until(()=>scenario==='leave-write'?heldPut:heldGet,'held write/readback');
   await page.evaluate(()=>{history.pushState({},'', '/elsewhere');window.leave();});await tick();
   const before=await page.evaluate(()=>window.notices.length);
   if(scenario==='leave-readback') active='gpu-b';
   await page.evaluate(()=>{history.pushState({},'', '/manage_models');window.mount();});await tick();
   if(heldPut) {
    // A remount GET before this acceptance cannot establish the final selection.
    active='';await heldPut.fulfill({json:{message:'selected'}});heldPut=null;
   } else {active='gpu-b';await heldGet.route.fulfill({json:heldGet.json});heldGet=null;}
   await tick();await tick();
   assert.equal(await page.evaluate(()=>window.notices.length),before,'old generation must not notify');
   await until(async()=>await select.count() && await select.inputValue()===active && !(await select.isDisabled()),'remount must read current state after pending write');
   assert.equal(writes.length,1,'navigation must not duplicate writes');
  }
  assert.deepEqual(errors,[]);assert.deepEqual(unexpected,[]);
 } catch(e) {failure=e.stack;}
 results.push({surface,scenario,passed:!failure,failure,gets,writes,unexpected,errors});
 if(heldGet) await heldGet.route.abort().catch(()=>{});
 if(heldPut) await heldPut.abort().catch(()=>{});
 await context.close();
}
} finally {await browser.close();}
if(out)writeFileSync(out+'/results.json',JSON.stringify(results,null,2));
console.log(JSON.stringify(results,null,2));
assert.equal(results.length,10);assert.equal(results.filter(r=>!r.passed).length,0);
