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
 for (const surface of ['classic', 'mobile']) for (const width of [1200,390]) {
  const mobile=surface==='mobile';
  const context=await browser.newContext({viewport:{width,height:850}});
  let downloading=false, target='', polls=0;
  const writes=[];
  const models=Array.from({length:36},(_,i)=>({value:`fixture-${i}`,label:`UI fixture model ${String(i).padStart(2,'0')}`,series:`Series ${i%3}`,released:`2026-08-${String(28-i%28).padStart(2,'0')}`,requiresGpu:i%2===0,gpuAvailable:true,installed:i===0,userFavorite:i%3===0}));
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
    return route.fulfill({json:{models,currentModel:'fixture-0',activeBigModel:'fixture-0',activeSmallModel:'',summary:{installed:1,missing:35,total:36},downloading,modelToDownload:target,progress:downloading?`${polls}%`:'',isOnroad:false}});
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
  if (mobile) assert.ok(await page.locator('.gx-model-manager .gx-row select').evaluateAll(nodes=>nodes.every(node=>{ const r=node.getBoundingClientRect(), c=node.closest('section').getBoundingClientRect();return r.right<=c.right && r.left>=c.left; })), 'Model controls must fit their card, not be silently clipped');
  if(!baseline) {
   const filter=page.locator(mobile?'#gx-model-hardware':'#mm-hardware-filter-select');
   const userFilter=mobile?page.locator('select').filter({has:page.locator('option[value="all"]', {hasText:'Your Favorite: All'})}):page.locator('#mm-user-filter-select');
   await filter.selectOption('gpu');
   await page.waitForFunction(sel=>document.querySelectorAll(sel).length===18,rowSelector);
   assert.ok((await rows.allTextContents()).every(t=>t.includes('GPU · External')));
   await userFilter.selectOption('yes');
   await page.waitForFunction(sel=>document.querySelectorAll(sel).length===6,rowSelector);
   await userFilter.selectOption('all');
   await filter.selectOption('comma');
   await page.waitForFunction(sel=>document.querySelectorAll(sel).length===18,rowSelector);
   await page.waitForFunction(sel=>[...document.querySelectorAll(sel)].every(r=>r.textContent.includes('Comma · On-device')),rowSelector,{timeout:3000}).catch(async e=>{console.log(JSON.stringify({surface,width,value:await filter.inputValue(),stored:await page.evaluate(()=>localStorage.getItem('galaxy.modelManager.hardwareFilter')),rows:await rows.allTextContents(),errors}));throw e;});
   assert.ok((await rows.allTextContents()).every(t=>t.includes('Comma · On-device')));
   assert.ok((await page.locator(mobile?'.gx-model-manager > section':'.mm-status').first().innerText()).includes('UI fixture model 00'));
   if(!mobile) assert.equal(await page.locator('#mm-active-big-model-select').inputValue(),'fixture-0');
   await page.reload();await rows.first().waitFor();
   assert.equal(await filter.inputValue(),'comma');
   assert.equal(await rows.count(),18);
   await filter.selectOption('both');
   await page.waitForFunction(sel=>document.querySelectorAll(sel).length===36,rowSelector);
   assert.equal(writes.length,0,'Filtering wrote to API');
   const sorter=mobile?page.locator('select').filter({has:page.locator('option[value="distance"]')}):page.locator('#mm-sort-mode-select');
   await sorter.selectOption('distance');
   await page.waitForFunction(sel=>document.querySelector(sel).textContent.includes('UI fixture model 35'),rowSelector);
   await sorter.selectOption('interventions');
   await page.waitForFunction(sel=>document.querySelector(sel).textContent.includes('UI fixture model 35'),rowSelector);
   await sorter.selectOption('release_date');
   await page.waitForFunction(sel=>document.querySelector(sel).textContent.includes('UI fixture model 00'),rowSelector);
   assert.deepEqual(await rows.first().locator('dt').allTextContents(), ['Total distance', 'Avg mi / intervention', 'Avg mi / disengagement']);
   assert.equal(await rows.first().locator('dl span').count(), 0);
   assert.ok(!(await page.locator('body').innerText()).includes('Total distance includes manual driving'));
   assert.ok((await rows.first().innerText()).includes('1.0 mi'));
   assert.ok((await rows.first().innerText()).includes('No events'));
   assert.ok((await rows.first().innerText()).includes('File size: 1.50 GB'));
   await rows.first().getByRole('button',{name:'Drive history',exact:true}).click();
   await rows.first().getByRole('button',{name:'More drives',exact:true}).waitFor({timeout:5000}).catch(async e=>{console.log(JSON.stringify({surface,width,errors,card:await rows.first().innerText()}));throw e;});
   assert.ok((await rows.first().innerText()).includes('fixture-0 (comma)'));
   await rows.first().getByRole('button',{name:'More drives',exact:true}).click();
   await page.waitForFunction(sel=>document.querySelector(sel).querySelectorAll('.mm-history-row,.gx-model-history-row').length===2,rowSelector);
   assert.equal(await rows.first().getByRole('button',{name:'More drives',exact:true}).count(),0);
   await rows.first().getByRole('button',{name:'Close history',exact:true}).click();
   const comparisons=page.locator(mobile?'.gx-model-comparison':'.mm-comparison');
   await comparisons.locator('summary').click();
   const comparisonRows=comparisons.locator('article');
   await comparisonRows.first().waitFor();
   assert.equal(await comparisonRows.count(),6);
   await page.locator(mobile?'#gx-period':'#mm-period').selectOption('7');
   await page.waitForFunction(sel=>document.querySelector(sel).querySelectorAll('article').length===2,mobile?'.gx-model-comparison':'.mm-comparison');
   await page.locator(mobile?'#gx-stats-mode':'#mm-stats-mode').selectOption('aol');
   await page.waitForFunction(sel=>document.querySelector(sel).querySelectorAll('article').length===1,mobile?'.gx-model-comparison':'.mm-comparison');
   assert.ok((await comparisons.innerText()).includes('Lateral only'));
   assert.ok((await comparisons.innerText()).includes('Revision recent'));
   await page.locator(mobile?'#gx-period':'#mm-period').selectOption('30');
   await page.waitForFunction(sel=>document.querySelector(sel).querySelectorAll('article').length===2,mobile?'.gx-model-comparison':'.mm-comparison');
   assert.ok((await comparisons.innerText()).includes('Revision month'));
   assert.ok(!(await comparisons.innerText()).includes('Revision old'));
   assert.equal(writes.length,0,'Comparison wrote control state');
   await comparisons.screenshot({path:`${out}/comparison-${surface}-${width}.png`});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Comparison overflow');
   await comparisons.locator('summary').click();
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
   assert.equal(overflow,false,`${surface}/${width} horizontal overflow`);
   await page.evaluate(()=>scrollTo(0,0));
   await page.screenshot({path:`${out}/metrics-${surface}-overview-${width}.png`});
   await rows.first().screenshot({path:`${out}/metrics-${surface}-card-${width}.png`});
  }
  const button=mobile?rows.filter({hasText:'UI fixture model 10'}).getByRole('button',{name:/Download$/}):page.locator('[data-mm-action="download"][data-model="fixture-10"]');
  await button.scrollIntoViewIfNeeded();await page.waitForTimeout(100);
  const before=await page.evaluate(()=>({y:scrollY,h:document.documentElement.scrollHeight}));
  await button.click();await page.waitForTimeout(2350);
  const after=await page.evaluate(()=>({y:scrollY,h:document.documentElement.scrollHeight}));
  results.push({surface,width,before,after,delta:after.y-before.y,writes});
  assert.equal(writes.length,1);
  assert.ok((await rows.first().innerText()).includes('2.0 mi'), 'Polled metrics did not refresh');
  assert.deepEqual(writes[0],{path:'/api/models/download',body:{model:'fixture-10',allowGpuWithoutGpu:false}});
  // Ordinary user scrolling must remain possible while downloads poll.
  await page.evaluate(()=>scrollBy(0,100));
  const userY=await page.evaluate(()=>scrollY);
  await page.waitForTimeout(2200);
  assert.equal(await page.evaluate(()=>scrollY),userY,'Polling undid user scrolling');
  await context.close();
 }
 const summary={results,errors,checks:baseline?['scroll reproduction']:['GPU/Comma/Both','combined favourite filter','filter persistence','no filter API writes or selection changes','honest unknown metrics','responsive overflow','download request unchanged','scroll while polling','history open/pagination/close','7/30/all revision comparisons','mode separation','polled metrics refresh']};
 console.log(JSON.stringify(summary,null,2));
 writeFileSync(out+(baseline?'/baseline-results.json':'/all-browser-results.json'),JSON.stringify(summary,null,2));
 assert.equal(errors.length,0);
 assert.ok(results.every(r=>Math.abs(r.delta)<5),'Download moved viewport');
} finally {await browser.close();}
