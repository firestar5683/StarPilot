// Shipped New Galaxy Home with explicitly synthetic API records.
const {chromium}=require('/opt/data/workspace/galaxy-responsive-evidence/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve('starpilot/system/the_galaxy');
const models=[{value:'a',label:'Alpha',stats:{available:true,assistedMeters:16093.44,interventions:1,interventionMeters:16093.44,disengagements:1,disengagementMeters:16093.44}},{value:'b',label:'Beta',stats:{available:true,assistedMeters:32186.88,interventions:4,interventionMeters:32186.88,disengagements:2,disengagementMeters:32186.88}}];
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
 for(const width of [320,390,768,1280]){
  const page=await browser.newPage({viewport:{width,height:900},hasTouch:width<768});
  const errors=[],writes=[];let historyFails=false;
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://fixture/**',async route=>{
   const u=new URL(route.request().url());
   if(u.pathname.startsWith('/api/')){
    if(route.request().method()!=='GET') writes.push(u.pathname);
    if(u.pathname==='/api/models/status')return route.fulfill({json:{models}});
    if(u.pathname==='/api/models/stats')return route.fulfill(historyFails?{status:503,body:'unavailable'}:{json:{available:true,hasMore:false,history:[{drive:'fixture',started:1788264010,updated:1788264550,complete:true,gaps:0,stats:{available:true,interventions:3,disengagements:2}}]}});
    if(u.pathname==='/api/stats')return route.fulfill({json:{dashboard:{modelDistances:[{key:'legacy',name:'Historical model',distanceMeters:80467.2},{key:'b',name:'Beta',distanceMeters:32186.88},{key:'a',name:'Alpha',distanceMeters:16093.44}],recentDrives:[{date:'2026-09-01T12:00:00Z',endDate:'2026-09-01T12:10:00Z',model:'Fixture drive',distance:10,duration:600,attentionKnown:true}],device:{status:'Parked'},week:{},records:{},storage:{}}}});
    return route.fulfill({json:{}});
   }
   if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:'<link rel="stylesheet" href="/assets/mobile/css/material.css"><link rel="stylesheet" href="/assets/mobile/css/home.css"><script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script><style>body{background:#101420;color:#e9eaf2;font:14px system-ui;margin:16px}*{box-sizing:border-box}</style><div id="app"></div>'});
   return route.fulfill({body:fs.readFileSync(path.join(root,u.pathname)),contentType:u.pathname.endsWith('.css')?'text/css':'text/javascript'});
  });
  await page.goto('http://fixture/');
  await page.evaluate(async()=>{const{createApp}=await import('vue');const{Home}=await import('/assets/mobile/js/views/Home.js');window.app=createApp(Home);window.home=window.app.mount('#app');});
  await page.getByText('Beta',{exact:true}).waitFor();
  const details=page.locator('details').filter({has:page.getByText('Recent drives',{exact:true})});
  assert.equal(await details.evaluate(e=>e.open),false);
  const top=page.locator('top-models');
  assert.equal(await top.locator('select').inputValue(),'distance');
  assert.deepEqual(await top.locator('article strong').allTextContents(),['Historical model','Beta','Alpha']);
  await details.locator('summary').click();
  await page.getByText('3 interventions',{exact:true}).waitFor();
  await page.getByText('2 disengagements',{exact:true}).waitFor();
  const badges=details.locator('.dh-drive__stat');
  assert.equal(await badges.count(),5);
  assert.ok(await badges.evaluateAll(nodes=>nodes.every(n=>{const r=n.getBoundingClientRect(),p=n.parentElement.getBoundingClientRect();return r.left>=p.left-1&&r.right<=p.right+1&&n.scrollWidth<=n.clientWidth+1;})), 'All five badges fit their group');
  await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await page.getByText('3 interventions',{exact:true}).waitFor();
  assert.equal(await details.evaluate(e=>e.open),true,'Refresh preserves expanded state');
  await top.locator('select').selectOption('interventions');
  assert.deepEqual(await top.locator('article strong').allTextContents(),['Alpha','Beta']);
  await top.locator('select').selectOption('distance');
  assert.deepEqual(await top.locator('article strong').allTextContents(),['Historical model','Beta','Alpha']);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No horizontal page overflow');
  await page.screenshot({path:`/opt/data/workspace/new-galaxy-dashboard-${width}.png`,fullPage:true});
  await top.evaluate(e=>e.setAttribute('history-rows',JSON.stringify([{key:'new',name:'Refreshed history',distanceMeters:10000}])));
  assert.deepEqual(await top.locator('article strong').allTextContents(),['Refreshed history']);
  historyFails=true;
  await page.getByRole('button',{name:'Refresh',exact:true}).click();
  await page.getByText('— interventions',{exact:true}).waitFor();
  assert.equal(await page.getByText('3 interventions',{exact:true}).count(),0);
  await details.locator('summary').focus();await page.keyboard.press('Enter');
  assert.equal(await details.evaluate(e=>e.open),false);
  assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
  console.log(JSON.stringify({width,collapse:true,counts:true,distanceDefault:true,alternateRanking:true,failedHistory:true,noWrites:true}));
  await page.close();
 }
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
