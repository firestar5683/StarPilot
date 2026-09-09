const {chromium} = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
import {fileURLToPath} from 'node:url';
import {mkdtempSync, mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import { readFileSync, writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const root = (process.env.REPO || fileURLToPath(new URL('../../../../', import.meta.url))) + '/starpilot/system/the_galaxy';
const out = process.env.EVIDENCE || mkdtempSync(tmpdir() + '/model-manager-browser-');
mkdirSync(out, {recursive:true});
const browser = await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE || undefined, args:['--no-sandbox']});
const errors = [], results = [];
const baseline = !!process.env.BASELINE;
try {
 for (const surface of (process.env.MODEL_SURFACE ? [process.env.MODEL_SURFACE] : ['classic', 'mobile'])) for (const width of [1200,390]) {
  const mobile=surface==='mobile';
  const context=await browser.newContext({viewport:{width,height:850}});
  let downloading=false, target='', polls=0, activeBig='fixture-0';
  const writes=[];
  const models=Array.from({length:36},(_,i)=>({value:`fixture-${i}`,label:`UI fixture model ${String(i).padStart(2,'0')}`,series:`Series ${i%3}`,released:`2026-08-${String(28-i%28).padStart(2,'0')}`,requiresGpu:i%2===0,gpuAvailable:true,installed:i===0 || i===2,userFavorite:i%3===0}));
  for (const [i, model] of models.entries()) {
    model.fileSizeBytes = 1500000000;
    model.stats = {available:true, assistedMeters:(i+1)*1609.344, interventionMeters:(i+1)*1609.344, disengagementMeters:(i+1)*1609.344, interventions:i === 0 ? 0 : 2, disengagements:i === 0 ? 0 : 1};
  }
  const mount = mobile ? `import {createApp} from 'vue';import {ModelManager} from '/assets/mobile/js/views/ModelManager.js';createApp(ModelManager).mount('#app');` : `import {html} from '/assets/vendor/arrow-core.js';import {ModelManager} from '/assets/components/tools/model_manager.js';window.showSnackbar=()=>{};html\`\${()=>ModelManager()}\`(document.querySelector('#app'));`;
  const preview=`<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/assets/vendor/bootstrap-icons/bootstrap-icons.min.css"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="${mobile?'/assets/mobile/css/material.css':'/assets/components/tools/model_manager.css'}"><script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script><style>:root{--text-color:#e9eaf2;--text-muted:#aab0c1;--card-bg:#1b2030;--secondary-bg:#262c3c;--sidebar-border-color:#353e54;--input-bg:#171c29;--success-bg:#81d4b1;--color-black:#10251c;--danger-bg:#883644;--sidebar-active-bg:#384560;--font-size-base:14px;--padding-base:16px;--margin-base:16px;--gap-xs:4px;--gap-sm:8px;--gap-md:12px;--gap-lg:20px;--border-radius-base:8px;--border-radius-lg:12px}body{background:#101420;color:#e9eaf2;font:14px system-ui;margin:16px}*{box-sizing:border-box}</style></head><body><p style="color:#aab0c1">UI DEVELOPMENT PREVIEW — SYNTHETIC CATALOGUE, NO DEVICE CONNECTION</p><main id="app"></main><script type="module">${mount}</script></body></html>`;
  await context.route('**/*',async route=>{
   const url=new URL(route.request().url());
   if(url.origin!=='http://galaxy.invalid') return route.abort();
   if(url.pathname.startsWith('/api/')) {
    if(route.request().method()!=='GET') {
     writes.push({path:url.pathname,body:route.request().postDataJSON()});
     if(url.pathname==='/api/models/active') { assert.equal(writes.at(-1).body.profile,'big'); if (!(process.env.MODEL_FAULT === 'reject' && writes.length === 1)) activeBig=writes.at(-1).body.model;
       if (process.env.MODEL_FAULT && writes.length === 1) return route.fulfill({status:503,json:{error:'Synthetic uncertain response'}});
     }
     else throw new Error('Unexpected write '+url.pathname);
     if(url.pathname==='/api/models/download') {downloading=true;target=writes.at(-1).body.model; models[0].stats.assistedMeters=3218.688;}
     return route.fulfill({json:{message:'Synthetic UI fixture action'}});
    }
    if (url.pathname === '/api/models/stats' && !url.searchParams.has('model')) {
      const period=url.searchParams.get('period'), mode=url.searchParams.get('mode');
      const revisions=period==='7'?['recent']:period==='30'?['recent','month']:['recent','month','old'];
      const modes=mode==='all'?['full','aol']:[mode];
      return route.fulfill({json:{available:true,status:'ok',comparisons:revisions.flatMap(revision=>modes.map(mode=>({identity:{version:1,roles:[{modelId:'fixture-0',backend:'comma',artifact:revision+'-'.repeat(70),artifactVerified:true}]},mode,stats:models[1].stats})))}});
    }
    if (url.pathname === '/api/models/stats') return route.fulfill({json:{available:true,status:'ok',hasMore:url.searchParams.get('offset')==='0',history:[{started:1788652800,complete:true,mode:'full',identity:{roles:[{modelId:'fixture-0',backend:'comma'}]},stats:models[0].stats}]}});
    assert.equal(url.pathname,'/api/models/status');polls++;
    return route.fulfill({json:{models,currentModel:'fixture-0',activeBigModel:activeBig,activeSmallModel:'',summary:{installed:1,missing:35,total:36},downloading,modelToDownload:target,progress:downloading?`${polls}%`:'',isOnroad:false}});
   }
   if(url.pathname.startsWith('/assets/')) {
    try {return route.fulfill({body:readFileSync(root+url.pathname),contentType:url.pathname.endsWith('.css')?'text/css':'text/javascript'});} catch(e) {errors.push(String(e));return route.abort();}
   }
   return route.fulfill({contentType:'text/html',body:preview});
  });
  const page=await context.newPage();page.on('pageerror',e=>{errors.push(e.message); console.error('PAGEERROR',e.message);});
  await page.goto('http://galaxy.invalid/manage_models');
  const rowSelector=mobile?'.gx-card-grid > section':'.mm-row';
  const rows=page.locator(rowSelector);
  await rows.first().waitFor();
  const select=mobile?page.locator('.gx-row').filter({has:page.getByText('Active Big',{exact:true})}).locator('select'):page.locator('#mm-active-big-model-select');
  assert.equal(await select.inputValue(),'fixture-0');
  await select.selectOption('');
  await new Promise(r=>setTimeout(r,350));
  assert.deepEqual(writes,[{path:'/api/models/active',body:{profile:'big',model:''}}],`${surface}: None must disable Active Big through API`);
  assert.equal(await select.inputValue(),process.env.MODEL_FAULT === 'reject' ? 'fixture-0' : '', 'Selection must match authoritative status after uncertain response');
  if (process.env.MODEL_FAULT) assert.ok(polls >= 2, 'Uncertain write requires immediate authoritative readback');
  await select.selectOption('fixture-2');
  await new Promise(r=>setTimeout(r,350));
  assert.equal(writes.length,2);
  assert.deepEqual(writes[1],{path:'/api/models/active',body:{profile:'big',model:'fixture-2'}});
  await page.reload();await rows.first().waitFor();
  assert.equal(await select.inputValue(),'fixture-2');
  results.push({surface,width,writes});
  await context.close();
 }
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({results,errors},null,2));
} finally {await browser.close();}
