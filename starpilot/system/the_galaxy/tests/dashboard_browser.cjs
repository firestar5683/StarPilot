// Full shipped Home components; all API data below is synthetic, never device data.
const {chromium} = require('/opt/data/workspace/galaxy-responsive-evidence/node_modules/playwright');
const fs=require('fs'), path=require('path'), assert=require('assert/strict');
const root=path.resolve('starpilot/system/the_galaxy');
const out=process.env.EVIDENCE || '/opt/data/workspace/galaxy-dashboard-evidence';
const stats={available:true,assistedMeters:16093.44,interventionMeters:16093.44,disengagementMeters:16093.44,interventions:2,disengagements:1};
const models=[{value:'a',label:'Recorded Alpha',stats:{...stats,assistedMeters:32186.88}},{value:'b',label:'No-event Beta',stats:{...stats,assistedMeters:48280.32,interventions:0,disengagements:0}},{value:'c',label:'Recorded Gamma',stats:{...stats,assistedMeters:null,interventions:4,disengagements:2}},{value:'zero',label:'Unused Zero',stats:{...stats,interventionMeters:0,disengagementMeters:0}},{value:'missing',label:'Unavailable',stats:{available:false}}];
(async()=>{
 const browser=await chromium.launch({headless:true}); const results=[];
 try {
  for(const theme of ['classic','dipper']) for(const width of [1200,390]) {
   const page=await browser.newPage({viewport:{width,height:900}}); const errors=[],writes=[];let mode='fresh',modelMode='ok';
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('http://fixture/**',async route=>{
    const u=new URL(route.request().url());
    if(u.pathname.startsWith('/api/')) {
     if(route.request().method()!=='GET') writes.push(u.pathname);
     if(u.pathname==='/api/models/status') return route.fulfill(modelMode==='error'?{status:503,body:'unavailable'}:{json:{models:modelMode==='empty'?[]:models}});
     if(u.pathname==='/api/vitals/external-gpu') {
      if(mode==='hang') return;
      return route.fulfill({json:{tempC:73.4,maxAgeMs:350}});
     }
     if(u.pathname==='/api/stats') return route.fulfill({json:{dashboard:{recentDrives:[{date:'2026-09-01T12:00:00Z',model:'Fixture drive',distance:10,duration:600,attentionKnown:true}],device:{status:'Parked'},week:{},records:{},storage:{}}}});
     return route.fulfill({json:{}});
    }
    if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:`<link rel="stylesheet" href="/assets/${theme==='classic'?'components/home/home.css':'mobile/css/material.css'}"><link rel="stylesheet" href="/assets/mobile/css/home.css"><script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script><style>body{background:#101420;color:#e9eaf2;font:14px system-ui;margin:16px}*{box-sizing:border-box}:root{--text-color:#e9eaf2;--secondary-bg:#262c3c;--card-bg:#1b2030}</style><div id="app"></div>`});
    let s=fs.readFileSync(path.join(root,u.pathname));
    if(process.env.BASELINE && u.pathname.endsWith('external_gpu_temperature.js')) s=fs.readFileSync('/opt/data/workspace/galaxy-dashboard-evidence/live-before/starpilot/system/the_galaxy/assets/components/home/external_gpu_temperature.js');
    return route.fulfill({body:s,contentType:u.pathname.endsWith('.css')?'text/css':'text/javascript'});
   });
   await page.goto('http://fixture/');
   await page.evaluate(async theme=>{
    if(theme==='classic'){const {html}=await import('/assets/vendor/arrow-core.js');const {Home}=await import('/assets/components/home/home.js');html`${()=>Home()}`(document.querySelector('#app'));}
    else{const {createApp}=await import('vue'); const {Home}=await import('/assets/mobile/js/views/Home.js');createApp(Home).mount('#app');}
   },theme);
   await page.getByText('Recorded Alpha',{exact:true}).waitFor();
   const details=page.locator('details').filter({has:page.getByText('Recent drives',{exact:true})});
   const summary=details.locator('summary');
   assert.equal(await details.evaluate(e=>e.open),theme==='classic');
   if(theme==='classic') await summary.click();assert.equal(await details.evaluate(e=>e.open),false);assert.equal(await page.getByText('Fixture drive',{exact:true}).isVisible(),false);
   await summary.focus();await page.keyboard.press('Enter');assert.equal(await details.evaluate(e=>e.open),true);
   const top=page.locator('top-models');
   if(theme==='dipper'){assert.equal(await top.locator('select').inputValue(),'distance');await top.locator('select').selectOption('interventions');}
   assert.deepEqual(await top.locator('article strong').allTextContents(),['Recorded Alpha','Recorded Gamma','No-event Beta']);
   assert.match(await top.innerText(),/No events · 10.0 mi/);assert.match(await top.innerText(),/Recorded sample: 10.0 mi/);assert.match(await top.innerText(),/not a safety ranking/);
   assert.doesNotMatch(await top.innerText(),/Unused Zero|Unavailable|Infinity/);
   const totals=()=>top.locator('article div:first-of-type').allTextContents();
   const expectedTotals=['Total recorded assisted: 20.0 mi','Total recorded assisted: —','Total recorded assisted: 30.0 mi'];
   assert.deepEqual(await totals(),expectedTotals);
   assert.deepEqual(await top.locator('option').evaluateAll(es=>es.map(e=>e.value)),theme==='dipper'?['distance','interventions','disengagements']:['interventions','disengagements']);
   await top.locator('select').selectOption('disengagements');assert.match(await top.locator('article').first().innerText(),/10.0 mi · 1 event/);
   assert.deepEqual(await totals(),expectedTotals,'Total mileage is independent of selected event exposure');
   await top.locator('select').selectOption('interventions');
   assert.deepEqual(await totals(),expectedTotals);
   await page.waitForFunction(()=>document.querySelector('external-gpu-temperature').textContent==='73°C');
   // Detect visible expiry pulses when the remaining envelope lifetime is shorter than polling.
   await page.evaluate(()=>{window.flashes=0;const e=document.querySelector('external-gpu-temperature');window.observer=new MutationObserver(()=>{if(e.textContent==='--')window.flashes++});window.observer.observe(e,{childList:true});});
   await page.waitForTimeout(1700); assert.equal(await page.evaluate(()=>window.flashes),0,'Fresh telemetry must not pulse unavailable between polls');
   mode='hang'; await page.waitForFunction(()=>document.querySelector('external-gpu-temperature').textContent==='--');
   await summary.click();
   await page.getByRole('button',{name:'Refresh',exact:true}).click();await page.getByText('Recorded Alpha',{exact:true}).waitFor();
   assert.equal(await details.evaluate(e=>e.open),false,'Collapse survives refresh');
   assert.deepEqual(await totals(),expectedTotals,'Mileage survives Home refresh');
   await page.screenshot({path:`${out}/${theme}-${width}.png`,fullPage:true});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Page overflow');
   modelMode='empty';await page.reload();
   // The fixture intentionally mounts by evaluate, so exercise empty/error via fresh elements.
   await page.evaluate(async()=>{await import('/assets/components/home/top_models.js');document.querySelector('#app').innerHTML='<top-models></top-models>'});
   await page.getByText('No recorded exposure for this metric yet.',{exact:true}).waitFor();
   modelMode='error';await page.evaluate(()=>document.querySelector('#app').innerHTML='<top-models></top-models>');await page.getByText('Recorded model statistics unavailable.',{exact:true}).waitFor();
   assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);results.push({theme,width,collapse:true,rankedSamples:true,zeroExcluded:true,noFreshFlashes:true,staleCleared:true,noWrites:true});await page.close();
  }
  fs.writeFileSync(`${out}/browser-results.json`,JSON.stringify(results,null,2));console.log(JSON.stringify(results));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
