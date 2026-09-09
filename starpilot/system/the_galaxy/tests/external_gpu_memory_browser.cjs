// Actual New Galaxy Vitals component and CSS; explicitly synthetic telemetry.
const {chromium}=require('/opt/data/workspace/galaxy-responsive-evidence/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve('starpilot/system/the_galaxy');
(async()=>{
 const browser=await chromium.launch({headless:true});let cases=0;
 try{
 for(const width of [320,390,768,1280])for(const theme of ['dark','light']){
  const page=await browser.newPage({viewport:{width,height:900},hasTouch:width<768});
  let mode='fresh',requests=0;const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://fixture/**',async route=>{
   const u=new URL(route.request().url());
   if(u.pathname==='/api/vitals/external-gpu'){
    requests++;
    if(mode==='hang')return;
    return route.fulfill({json:{tempC:73.4,maxAgeMs:700,memoryUsedBytes:mode==='zero'?0:1073741824,memoryTotalBytes:mode==='invalid'?0:4294967296,memoryMaxAgeMs:mode==='expired'?0:700}});
   }
   if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:`<html data-theme="${theme}"><link rel="stylesheet" href="/assets/mobile/css/material.css"><link rel="stylesheet" href="/assets/mobile/css/home.css"><script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script><style>body{margin:12px}*{box-sizing:border-box}</style><div id="app"></div>`});
   return route.fulfill({body:fs.readFileSync(path.join(root,u.pathname)),contentType:u.pathname.endsWith('.css')?'text/css':'text/javascript'});
  });
  await page.goto('http://fixture/');
  await page.evaluate(async()=>{
   const{createApp}=await import('vue');const{Home}=await import('/assets/mobile/js/views/Home.js');
   const start=Home.template.lastIndexOf('<section',Home.template.indexOf('<span>Vitals</span>'));
   const end=Home.template.indexOf('</section>',start)+10;
   window.app=createApp({template:Home.template.slice(start,end),data:()=>({device:{gpuTempC:58,cpuTempC:62,uptimeSeconds:100}}),computed:{vitalsList:Home.computed.vitalsList}});
   app.mount('#app');
  });
  await page.waitForFunction(()=>document.querySelector('external-gpu-memory')?.textContent==='1.0/4.0 GiB (25%)');
  assert.equal(await page.locator('external-gpu-temperature').textContent(),'73°C');
  assert.ok(await page.locator('external-gpu-memory').evaluate(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth}));
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('section').screenshot({path:`/opt/data/workspace/egpu-memory-work/vitals-${width}-${theme}.png`});
  if(width===320&&theme==='dark'){
   mode='zero';await page.waitForFunction(()=>document.querySelector('external-gpu-memory').textContent==='0.0/4.0 GiB (0%)');
   mode='invalid';await page.waitForFunction(()=>document.querySelector('external-gpu-memory').textContent==='--');
   assert.equal(await page.locator('external-gpu-temperature').textContent(),'73°C');
   mode='fresh';await page.waitForFunction(()=>document.querySelector('external-gpu-memory').textContent==='1.0/4.0 GiB (25%)');
   mode='expired';await page.waitForFunction(()=>document.querySelector('external-gpu-memory').textContent==='--');
   mode='fresh';await page.waitForFunction(()=>document.querySelector('external-gpu-memory').textContent==='1.0/4.0 GiB (25%)');
   mode='hang';await page.waitForFunction(()=>document.querySelector('external-gpu-memory').textContent==='--');
   await page.evaluate(()=>app.unmount());const count=requests;
   await page.waitForTimeout(1100);assert.equal(requests,count);
  }
  assert.deepEqual(errors,[]);cases++;await page.close();
 }
 console.log(JSON.stringify({layouts:cases,zeroInvalidExpiredHangUnmount:true,simulatedTelemetry:true}));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
