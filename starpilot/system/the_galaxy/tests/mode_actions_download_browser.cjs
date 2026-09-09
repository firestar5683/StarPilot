// Real shipped Vue components; all APIs below are synthetic, never the vehicle.
const {chromium}=require('/opt/data/workspace/galaxy-responsive-evidence/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve('starpilot/system/the_galaxy');
const evidence='/opt/data/workspace/galaxy-mode-actions-evidence';
const modeOptions=JSON.parse(fs.readFileSync(evidence+'/options.json'));
const actionSlots=()=>modeOptions.slice(0,3).map(o=>({key:o.key,label:o.label,enabled:true,show_onroad:true}));
const layout=JSON.parse(fs.readFileSync('starpilot/common/assets/device_settings_layout.json'));
const profiles=JSON.parse(fs.readFileSync('/opt/data/workspace/bigdipper-fixture.json'));
const values={IsOnroad:false,IsOffroad:true,VehicleParked:true,GalaxyDeveloperMode:true,CustomPersonalities:true,IsMetric:false};
for(const s of layout)for(const p of s.params){if(!(p.key in values))values[p.key]=p.data_type==='bool'?true:p.options?.[0]?.value??p.min??1;}
const mode={mode:'conditional_experimental',locked:false,reason:'',experimental_confirmed:true,values:{ExperimentalMode:false,ConditionalExperimental:true,ConditionalChill:false}};
(async()=>{
 const browser=await chromium.launch({headless:true});
 const results=[];
 try{
 for(const width of [320,390,768,1280]){
  const page=await browser.newPage({viewport:{width,height:900},hasTouch:width<768});
  const errors=[],writes=[];
  let gpu=false,onroad=false,statusFail=false,downloadFail=false;
  const modelRows=()=>[{value:'gpu',label:'GPU test model',requiresGpu:true,gpuAvailable:gpu,installed:false},{value:'small',label:'Comma test model',requiresGpu:false,gpuAvailable:true,installed:false}];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://fixture/**',async route=>{
   const request=route.request(),u=new URL(request.url());
   if(u.pathname.startsWith('/api/')){
    if(request.method()!=='GET') {if(u.pathname==='/api/favorites/slots')return route.fulfill({json:{slots:request.postDataJSON().slots,options:modeOptions,values:{}}});writes.push({path:u.pathname,data:request.postDataJSON()});return route.fulfill(downloadFail?{status:503,json:{error:'Synthetic download failure'}}:{json:{message:'Synthetic success'}});}
    if(u.pathname==='/api/favorites/slots')return route.fulfill({json:{slots:actionSlots(),options:modeOptions,values:{}}});
    if(u.pathname==='/api/wheel-controls/status')return route.fulfill({json:{available:true,offroad:true,controller_slots:[{key:null,enabled:false}],controller_options:modeOptions}});
    if(u.pathname==='/api/models/status')return route.fulfill(statusFail?{status:503,json:{error:'Synthetic status failure'}}:{json:{models:modelRows(),isOnroad:onroad,summary:{installed:0,missing:2,total:2}}});
    if(u.pathname==='/api/params/all')return route.fulfill({json:values});
    if(u.pathname==='/api/params/defaults')return route.fulfill({json:{}});
    if(u.pathname==='/api/personality_profiles')return route.fulfill({json:profiles});
    if(u.pathname==='/api/longitudinal_mode')return route.fulfill({json:{...mode,action_expires_at:1234}});
    return route.fulfill({json:{}});
   }
   if(u.pathname.includes('device_settings_layout.json'))return route.fulfill({json:layout});
   if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:`<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/assets/mobile/css/material.css"><script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script><style>body{background:#101420;color:#e9eaf2;font:14px system-ui;margin:12px}*{box-sizing:border-box}</style><div id="app"></div>`});
   if(process.env.MODEL_ONLY && u.pathname.endsWith("/longitudinal_help.js"))return route.fulfill({contentType:"text/javascript",body:"export const LONGITUDINAL_HELP = {}; // Explicitly synthetic; model prompt test only."});
   const file=path.join(root,u.pathname);
   if(!fs.existsSync(file))return route.fulfill({status:404,body:'Missing fixture asset'});
   return route.fulfill({body:fs.readFileSync(file),contentType:u.pathname.endsWith('.css')?'text/css':u.pathname.endsWith('.woff2')?'font/woff2':'text/javascript'});
  });
  await page.goto('http://fixture/');
  await page.evaluate(async()=>{const Vue=await import('vue');window.__galaxyVue=Vue;const {ModelManager}=await import('/assets/mobile/js/views/ModelManager.js');window.app=Vue.createApp(ModelManager);window.vm=app.mount('#app');});
  await page.getByText('GPU test model',{exact:true}).waitFor();
  assert.equal(await page.getByText('Download GPU models without GPU',{exact:true}).count(),0);
  assert.equal(await page.getByText('GPU = external GPU / Chestnut. Comma = on-device model.',{exact:true}).count(),0);
  const download=page.locator('section').filter({has:page.getByText('GPU test model',{exact:true})}).getByRole('button',{name:'Download',exact:true});
  await download.click();await page.getByRole('dialog').waitFor();assert.equal(writes.length,0);
  await page.getByRole('button',{name:'Cancel',exact:true}).click();assert.equal(writes.length,0);
  await download.click();await page.keyboard.press('Escape');assert.equal(await page.getByRole('dialog').count(),0);assert.equal(writes.length,0);
  await download.click();await page.getByRole('button',{name:'Download anyway',exact:true}).click();
  await page.waitForFunction(()=>!window.vm.busy);
  assert.deepEqual(writes.pop(),{path:'/api/models/download',data:{model:'gpu',allowGpuWithoutGpu:true}});
  // Approval must not persist to the next download.
  await download.click();await page.getByRole('dialog').waitFor();
  onroad=true;await page.getByRole('button',{name:'Download anyway',exact:true}).click();
  await page.waitForFunction(()=>!window.vm.busy);assert.equal(writes.length,0);
  onroad=false;await page.evaluate(()=>vm.refresh());
  await download.click();statusFail=true;await page.getByRole('button',{name:'Download anyway',exact:true}).click();
  await page.waitForFunction(()=>!window.vm.busy);assert.equal(writes.length,0);
  statusFail=false;gpu=true;await page.evaluate(()=>vm.refresh());
  await download.click();await page.waitForFunction(()=>!window.vm.busy);
  assert.equal(await page.getByRole('dialog').count(),0);assert.deepEqual(writes.pop(),{path:'/api/models/download',data:{model:'gpu',allowGpuWithoutGpu:false}});
  gpu=false;await page.evaluate(()=>vm.refresh());
  await page.getByRole('button',{name:'Download all missing — entire catalogue'}).click();await page.getByRole('dialog').waitFor();
  await page.getByRole('button',{name:'Download anyway',exact:true}).click();await page.waitForFunction(()=>!window.vm.busy);
  assert.deepEqual(writes.pop(),{path:'/api/models/download_all',data:{allowGpuWithoutGpu:true}});
  await page.locator('section').filter({has:page.getByText('Comma test model',{exact:true})}).getByRole('button',{name:'Download',exact:true}).click();await page.waitForFunction(()=>!window.vm.busy);
  assert.deepEqual(writes.pop(),{path:'/api/models/download',data:{model:'small',allowGpuWithoutGpu:false}});
  // Failed downloads restore controls; hash navigation cancels outstanding confirmation.
  downloadFail=true;gpu=true;await page.evaluate(()=>vm.refresh());await download.click();await page.waitForFunction(()=>!window.vm.busy);writes.length=0;
  gpu=false;downloadFail=false;await page.evaluate(()=>vm.refresh());await download.click();await page.evaluate(()=>location.hash='/elsewhere');await page.waitForFunction(()=>!window.vm.busy);assert.equal(writes.length,0);
  await page.evaluate(async()=>{window.app.unmount();const{createApp}=await import('vue');const{Settings}=await import('/assets/mobile/js/views/Settings.js');window.app=createApp(Settings);window.vm=app.mount('#app');});
  await page.waitForFunction(()=>!vm.loading);
  await page.evaluate(()=>{vm.activeSectionSlug='longitudinal-speed-following';vm.expanded=Object.fromEntries(vm.layout.flatMap(s=>s.params.map(p=>[p.key,true])));});
  await page.locator('#gx-longitudinal-mode').waitFor();
  await page.locator('.gx-longitudinal-mode .gx-manage-btn').click();
  assert.equal(await page.locator('[data-help-key], .gx-help-button').count(),0);
  assert.equal(await page.getByRole('button',{name:/^Help:/}).count(),0);
  assert.equal(await page.getByRole('dialog').count(),0);
  await page.evaluate(async()=>{app.unmount();const{createApp}=await import('vue');const{FavoritesEditor}=await import('/assets/mobile/js/components/FavoritesEditor.js');window.app=createApp(FavoritesEditor);window.vm=app.mount('#app');});
  await page.waitForFunction(()=>!vm.loading);
  assert.equal(await page.locator('select').first().locator('option').count(),6);
  for(const option of modeOptions){
    await page.locator('select').first().selectOption(option.key);
    await page.waitForFunction(()=>!vm.saving);
    await page.getByRole('button',{name:'Press',exact:true}).first().click();
    await page.waitForFunction(()=>!vm.actionPending);
    assert.deepEqual(writes.pop(),{path:'/api/favorites/action',data:{key:option.key,expected:mode.values,expires_at:1234,acknowledged:true}});
  }
  await page.evaluate(async()=>{app.unmount();const{createApp}=await import('vue');const{WheelControls}=await import('/assets/mobile/js/components/WheelControls.js');window.app=createApp(WheelControls);window.vm=app.mount('#app');});
  await page.waitForFunction(()=>!vm.loading);
  for(const option of modeOptions){
    await page.getByRole('button',{name:/Choose action/}).first().click();
    await page.getByRole('dialog').waitFor();
    const row=page.locator(`[data-action-key="${option.key}"]`);
    await row.click();await page.waitForFunction(()=>!vm.busy);
    assert.equal(await page.getByRole('dialog').count(),0);
    assert.deepEqual(writes.pop(),{path:'/api/wheel-controls/action',data:{slot:0,key:option.key,value:null}});
  }
  assert.deepEqual(errors,[]);
  await page.screenshot({path:evidence+`/menus-${width}.png`,fullPage:true});
  results.push({width,helpRemoved:true,modelDownloadPromptPreserved:true,fiveFavouriteAndBluetoothActions:true});
  await page.close();
 }
 } finally {await browser.close();}
 fs.writeFileSync(evidence+'/browser-results.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results));
})().catch(e=>{console.error(e);process.exit(1)});
