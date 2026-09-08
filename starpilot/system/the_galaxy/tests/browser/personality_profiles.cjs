// Real Chromium, synthetic API only. Never contacts a device or writes real Params.
// NODE_PATH=<playwright node_modules> CHROMIUM_EXECUTABLE=<optional browser> node this-file
const {chromium}=require('playwright');
const fs=require('fs');const path=require('path');const assert=require('assert');
const root=path.resolve(__dirname,'../../../../..');
const output=process.env.PERSONALITY_BROWSER_OUTPUT || path.join(require('os').tmpdir(),'bigdipper-personality-browser');fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_EXECUTABLE || undefined,args:['--no-sandbox']});
 try {
 const dpr=Number(process.env.PERSONALITY_DPR || 1);const page=await browser.newPage({deviceScaleFactor:dpr,hasTouch:dpr>1});const errors=[]; page.on('pageerror',e=>errors.push(e.message));
 const data=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/personality_profiles.json')));const writes=[];let failWrite=false;
 const faults={};let attempts=0,profileReads=0;const waitGate=async key=>{if(faults[key])await faults[key].promise;};
 const values={IsOnroad:'',IsOffroad:'True',IsMetric:true,VehicleParked:true,CustomPersonalities:true,AggressivePersonalityProfile:true,StandardPersonalityProfile:true,RelaxedPersonalityProfile:true,TrafficPersonalityProfile:true};
 const layout=JSON.parse(fs.readFileSync(root+'/starpilot/common/assets/device_settings_layout.json'));
 for(const p of layout.flatMap(s=>s.params)) if(p.key.includes('Jerk')) values[p.key]=100;
 await page.route('http://bigdipper.test/**',async route=>{
 const u=new URL(route.request().url()); let file;
 if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:`<script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script><link rel="stylesheet" href="/assets/vendor/bootstrap-icons/bootstrap-icons.min.css"><link rel="stylesheet" href="/assets/mobile/css/material.css"><div id="app"></div><div id="snackbar_wrapper"></div><script type="module">import {createApp} from '/assets/vendor/vue/vue.esm-browser.js';import {PersonalityProfiles} from '/assets/mobile/js/components/PersonalityProfiles.js';createApp(PersonalityProfiles).mount('#app');</script>`});
 if(u.pathname==='/api/params/all'){await waitGate('params');return route.fulfill({json:values});}
 if(u.pathname==='/api/params/defaults')return route.fulfill({json:{}});
 if(u.pathname==='/api/params'){const d=route.request().postDataJSON();values[d.key]=d.value;return route.fulfill({json:{success:true}});}
 if(u.pathname==='/api/personality_profiles'){
 if(route.request().method()==='PUT'){attempts++;await waitGate('put');if(failWrite||faults.failPut){failWrite=false;faults.failPut=false;return route.fulfill({status:503,json:{error:'Synthetic save failure'}});}const d=route.request().postDataJSON();writes.push(d);data.profiles[d.profile][d.category]={preset:d.preset,curve:d.curve.length?d.curve:[...data.reference_curves[d.profile][d.category]]};}
 else {profileReads++;if(faults.readFailures){faults.readFailures--;return route.fulfill({status:503,json:{error:'Synthetic readback failure'}});}}
 return route.fulfill({json:data});}
 if(u.pathname.endsWith('device_settings_layout.json'))file=root+'/starpilot/common/assets/device_settings_layout.json';
 else if(u.pathname.startsWith('/assets/'))file=root+'/starpilot/system/the_galaxy'+u.pathname;
 if(file&&fs.existsSync(file))return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.css')?'text/css':file.endsWith('.json')?'application/json':'text/javascript'});
 errors.push(`Unexpected synthetic request: ${route.request().method()} ${u.pathname}`);return route.abort();
 });
 await page.goto('http://bigdipper.test/');
 await page.getByRole('button',{name:'Manage',exact:true}).waitFor();
 assert(!(await page.locator('#gx-personality-settings').isVisible()));
 await page.getByRole('button',{name:'Manage',exact:true}).click();
 await page.waitForSelector('.gx-personalities__profile');
 await page.locator('.gx-manage-btn').click();
 assert(!(await page.locator('#gx-personality-settings').isVisible()));
 await page.getByRole('button',{name:'Manage',exact:true}).click();
 assert.equal(await page.locator('.gx-personalities__profile').count(),4);
 if(process.env.PERSONALITY_POLL_ONLY){
   await require('./personality_poll.cjs')({page,data,values,faults,counts:()=>({attempts}),errors});
   return;
 }
 assert.equal(await page.locator('.gx-manage-btn').getAttribute('class'),'gx-manage-btn');
 const master=page.getByRole('checkbox',{name:'Custom personalities',exact:true});assert(await master.isChecked());
 values.CustomPersonalities='False';await page.waitForTimeout(4200);assert(!(await master.isChecked()),'text False not checked');assert.equal(await page.locator('.gx-personalities__profile').count(),4);
 values.CustomPersonalities=true;await page.waitForSelector('.gx-personalities__profile');
 for(const width of [320,390,768,1280]){
 await page.setViewportSize({width,height:900});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
 await page.screenshot({path:path.join(output,`overview-${width}.png`),fullPage:true});
 }
 await page.locator('.gx-personalities__profile').first().getByRole('button',{name:'Custom',exact:true}).first().click();
 // A click completes before the HTTP write/readback. Assert the same exact
 // write count and payload only after the saved Custom state is rendered.
 await page.waitForFunction(()=>{const vm=document.querySelector('#app').__vue_app__._instance.proxy;return !vm.busy && vm.data.profiles.traffic.acceleration.preset==='custom';});
 assert.equal(writes.length,1);assert.deepEqual(writes[0].curve,[]);
 await page.waitForSelector('.gx-personalities__curve');
 assert(await page.locator('.gx-personalities__curve svg').first().isVisible());
 const curve=page.locator('.gx-personalities__curve').first();
 assert.equal(await curve.locator('svg text').count(),12);
 assert((await curve.locator('svg').textContent()).includes('Speed (km/h)'));
 console.log('PASS: collapsed by default; Manage/Close toggles section; numeric axes and units rendered.');
 for(const width of [390,1280]) {
   await page.setViewportSize({width,height:900});
   const handle=curve.locator('circle[fill="transparent"]').nth(2);
   await handle.scrollIntoViewIfNeeded();
   const before=Number(await curve.locator('input').nth(2).inputValue());
   const box=await handle.boundingBox();
   const writesBeforeDrag=writes.length;
   await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();
   await page.mouse.move(box.x+box.width/2,box.y+box.height/2+15,{steps:5});assert.equal(writes.length,writesBeforeDrag,'preview never writes');await page.mouse.up();
   const after=Number(await curve.locator('input').nth(2).inputValue());
   assert.notEqual(after,before,'drag updates numeric draft');
   await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.busy);
   assert.equal(writes.length,width===390?2:3,'release commits exactly once');
 }
 const touch=await page.context().newCDPSession(page);
 const handle=curve.locator('circle[fill="transparent"]').nth(2);await handle.scrollIntoViewIfNeeded();
 const box=await handle.boundingBox();const x=box.x+box.width/2,y=box.y+box.height/2;
 const beforeTouch=await curve.locator('input').nth(2).inputValue();
 await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
 await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:y-12}]});
 await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 await page.waitForFunction(()=>{const vm=document.querySelector('#app').__vue_app__._instance.proxy;return !vm.drag&&!vm.curvePending&&!vm.busy;});
 assert.notEqual(await curve.locator('input').nth(2).inputValue(),beforeTouch,'touch drag updates draft');
 assert.equal(writes.length,4);
 console.log('PASS: browser touch release commits once.');
 const beforeCancel=await curve.locator('input').nth(2).inputValue();
 await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
 await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:y+10}]});
 await touch.send('Input.dispatchTouchEvent',{type:'touchCancel',touchPoints:[]});
 // CDP acknowledgement can precede pointercancel delivery and Vue's DOM update.
 await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.drag);
 assert.equal(await curve.locator('input').nth(2).inputValue(),beforeCancel,'cancel restores pre-drag draft');
 assert.equal(writes.length,4,'cancel does not write');
 assert.equal(await page.getByRole('button',{name:'Save curve',exact:true}).count(),0);
 const input=curve.locator('input').nth(2);await input.fill('1.234');await input.press('Tab');
 assert((await curve.getByRole('alert').textContent()).includes('0.05'),'step errors inline');assert.equal(writes.length,4);
 await input.fill('1.25');await input.press('Tab');
 await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.curvePending);
 assert.equal(writes.length,5);assert.equal(data.profiles.traffic.acceleration.curve[2],1.25);
 console.log('PASS: mouse release and numeric change persist without Save.');
 assert.equal(await page.getByRole('button',{name:'Refresh',exact:true}).count(),0);
 const advanced=page.locator('.gx-personalities__advanced').first();
 if(!(await advanced.getAttribute('open') !== null)) await advanced.locator(':scope > summary').click();
 assert.equal(await advanced.locator(':scope > .gx-personalities__category input[type=number]').count(),0);
 const row=advanced.locator('.gx-personalities__category').first();
 await row.getByRole('button',{name:'Custom',exact:true}).click();
 assert(await row.locator('input').isVisible());
 await row.getByRole('button',{name:'Chill',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.gx-personalities__advanced .gx-personalities__category input')===null);
 assert.equal(await row.getByRole('button',{name:'Chill',exact:true}).getAttribute('aria-pressed'),'true');
 values.IsOnroad='True';values.IsOffroad='';
 await page.waitForFunction(()=>document.querySelector('.gx-personalities__options button').disabled);
 assert.deepEqual(errors,[]);
 values.IsOnroad='';values.IsOffroad='True';
 await page.waitForFunction(()=>!document.querySelector('.gx-personalities__options button').disabled);
 console.log('PASS: real API road-state encodings unlock parked controls; Custom graph opens; no Refresh; advanced inputs Custom-only; on-road tuning guard retained.');
 assert.deepEqual(errors,[]);
 console.log('PASS: four profile cards; no horizontal overflow at 320/390/768/1280; Custom delegates initial curve to backend; no browser errors. Synthetic API only.');
 const results=[];
 for(let pi=0;pi<4;pi++) for(let ci=0;ci<3;ci++) {
   const card=page.locator('.gx-personalities__profile').nth(pi),category=card.locator(':scope > .gx-personalities__category').nth(ci);
   await category.getByRole('button',{name:'Custom',exact:true}).click();
   const graph=card.locator('.gx-personalities__curve').nth(ci);await graph.waitFor();
   assert.equal(await graph.locator('svg text').count(),12);assert.equal(await graph.locator('input').count(),10);
   const n=graph.locator('input').nth(2);await n.fill('1.5');
   if(pi===0&&ci===0){await page.evaluate(async()=>await document.querySelector('#app').__vue_app__._instance.proxy.refreshContext());assert.equal(await n.inputValue(),'1.5','poll preserves focused curve text');}
   await n.press('Tab');
   await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.curvePending);
   assert.equal(Number(await n.inputValue()),1.5);
   await graph.getByRole('button',{name:'Reset to default',exact:true}).click();
   await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.busy);
   const p=['traffic','aggressive','standard','relaxed'][pi],c=['acceleration','braking','following'][ci];
   assert.deepEqual(await graph.locator('input').evaluateAll(ns=>ns.map(n=>Number(n.value))),data.reference_curves[p][c]);
   results.push({profile:p,category:c,axes:true,numericSave:true,reset:true});
 }

 const advancedResults=[];
 for(let pi=0;pi<4;pi++){
   const rows=page.locator('.gx-personalities__profile').nth(pi).locator('.gx-personalities__advanced > .gx-personalities__category');assert.equal(await rows.count(),5);
   for(let i=0;i<5;i++){
     const r=rows.nth(i);const label=await r.locator('label').textContent();
     await r.getByRole('button',{name:'Custom',exact:true}).click();const n=r.locator('input');
     assert.equal(await n.getAttribute('min'),'25');assert.equal(await n.getAttribute('max'),'200');assert.equal(await n.getAttribute('step'),'1');
     await n.fill('125.5');await n.press('Tab');await r.getByRole('alert').waitFor({state:'visible'});
     await n.fill('125');
     if(pi===0&&i===0){await page.evaluate(async()=>await document.querySelector('#app').__vue_app__._instance.proxy.refreshContext());assert.equal(await n.inputValue(),'125','poll preserves focused advanced text');}
     await n.press('Tab');await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.busy);assert.equal(await n.inputValue(),'125');
     await r.getByRole('button',{name:'Standard',exact:true}).click();await n.waitFor({state:'detached'});advancedResults.push({profile:pi,row:i,label,customSave:true,stepError:true,standard:true});
   }
 }
 // Failed writes restore verified server state, not a silently retained draft.
 const savedBeforeFailure=data.profiles.traffic.acceleration.curve[2];failWrite=true;
 await curve.locator('input').nth(2).fill('1.5');await curve.locator('input').nth(2).press('Tab');
 await page.getByText('Save could not be confirmed. Showing verified saved state; review it before editing again.',{exact:true}).waitFor();
 await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.curvePending);
 assert.equal(Number(await curve.locator('input').nth(2).inputValue()),savedBeforeFailure);
 // Historical high points must stay visible and unchanged while another point is authored.
 data.profiles.traffic.acceleration.curve[0]=6;
 await page.evaluate(async()=>await document.querySelector('#app').__vue_app__._instance.proxy.load());
 assert.equal(await curve.locator('input').first().inputValue(),'6');assert.equal(await curve.locator('input').first().getAttribute('max'),'3.5');
 assert((await curve.locator('svg text').allTextContents()).includes('6'));
 await curve.locator('input').nth(2).fill('1.5');await curve.locator('input').nth(2).press('Tab');
 await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.busy);assert.equal(data.profiles.traffic.acceleration.curve[0],6);
 values.IsMetric='False';await page.evaluate(async()=>await document.querySelector('#app').__vue_app__._instance.proxy.refreshContext());
 assert((await curve.locator('svg').textContent()).includes('Speed (mph)'));
 const matrix=[];
 await page.locator('.snackbar').waitFor({state:'detached'});
 for(const width of [320,375,390,768,1280,1920]) for(const zoom of [.75,1,1.25,1.5,2]) {
   await page.setViewportSize({width,height:1000});await page.evaluate(z=>document.documentElement.style.zoom=z,zoom);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth / Number(document.documentElement.style.zoom)+1),`overflow width ${width} zoom ${zoom}`);
   await curve.scrollIntoViewIfNeeded();
   await page.screenshot({path:path.join(output,`curve-${width}-${zoom}.png`)});
   const h=curve.locator('circle[fill="transparent"]').nth(3);await h.scrollIntoViewIfNeeded();const b=await h.boundingBox();
   const old=await curve.locator('input').nth(3).inputValue();
   await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2,b.y+b.height/2-5,{steps:3});await page.mouse.up();

   assert.notEqual(await curve.locator('input').nth(3).inputValue(),old,`drag ${width}/${zoom}`);
   await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.curvePending);
   await curve.locator('input').nth(3).fill(old);await curve.locator('input').nth(3).press('Tab');
   await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.curvePending);
   await page.locator('.snackbar').waitFor({state:'detached'});matrix.push({width,zoom,overflow:false,drag:true});
 }
 await page.evaluate(()=>document.documentElement.style.zoom=1);await page.setViewportSize({width:1280,height:900});
 // Verify validation and draft reconciliation on the actual Vue instance, without API writes.
 const edgeCases=await page.evaluate(async()=>{
   const v=document.querySelector('#app').__vue_app__._instance.proxy;const copy=()=>JSON.parse(JSON.stringify(v.data));
   const cases=[];for(const mutate of [d=>delete d.reference_curves.traffic.acceleration,d=>d.speed_breakpoints_mph.braking[1]=NaN,d=>d.bounds.following=[3,1],d=>d.profiles.standard.braking.preset='bogus']){
     const d=copy();mutate(d);let rejected=false;try{v.validate(d)}catch{rejected=true}if(!rejected)throw Error('malformed metadata accepted');cases.push('malformed rejected');
   }
   for(const c of ['braking','following'])if(v.graphMin('traffic',c)!==v.data.bounds[c][0])throw Error('nonzero lower bound');
   v.point('traffic','acceleration',2,{target:{value:'1.5'}},true);const d=copy();d.profiles.traffic.acceleration.curve[2]=1.4;v.acceptData(d);if(v.drafts.trafficacceleration)throw Error('stale preview retained');
   for(const p of v.PROFILES){const suffixes=['Acceleration','Deceleration','Danger','SpeedDecrease','Speed'];if(JSON.stringify(v.advancedParams(p).map(p=>p.key).sort())!==JSON.stringify(suffixes.map(s=>v.label(p)+'Jerk'+s).sort()))throw Error('advanced key set');}
   return cases;
 });
 const lifecycle=await require('./personality_lifecycle.cjs')({page,curve,data,values,faults,counts:()=>({attempts,profileReads}),errors});
 // Actual Settings -> SettingTree integration, not a hand-built replacement row.
 values.GalaxyDeveloperMode=true;
 await page.evaluate(async()=>{
   document.querySelector('#app').__vue_app__.unmount();
   const {createApp}=await import('/assets/vendor/vue/vue.esm-browser.js');const {Settings}=await import('/assets/mobile/js/views/Settings.js');const {store}=await import('/assets/mobile/js/store.js');
   store.route='/settings/longitudinal-speed-following';store.params={open:'CustomPersonalities'};store.search='';createApp(Settings).mount('#app');
 });
 await page.locator('.gx-personalities__grid').waitFor();assert(await page.locator('#gx-personality-settings').isVisible());
 assert.equal(await page.locator('.gx-longitudinal-mode').count(),0,'personality-only settings do not introduce unified mode');
 for(const theme of ['dark','light']) {
   await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);
   await page.locator('.gx-personalities__heading').scrollIntoViewIfNeeded();
   await page.screenshot({path:path.join(output,`settings-${theme}.png`)});
 }
 await page.evaluate(async()=>{const {store}=await import('/assets/mobile/js/store.js');store.search='TrafficJerkAcceleration'});
 await page.waitForFunction(()=>document.querySelector('#app').__vue_app__._instance.proxy.searchResults.length>0);
 assert.equal(await page.locator('.gx-personalities').count(),1,'search shows editor once');
 assert.deepEqual(await page.evaluate(()=>document.querySelector('#app').__vue_app__._instance.proxy.searchResults.flatMap(s=>s.matches.map(p=>p.key))),['CustomPersonalities']);
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(output,'browser-results.json'),JSON.stringify({syntheticAPI:true,dpr,curves:results,advanced:advancedResults,matrix,edgeCases,lifecycle,settingsIntegration:true,search:true,browserErrors:errors},null,2));
 console.log(`PASS: ${results.length} profile/category combinations axes, numeric save/reset; ${matrix.length} viewport/zoom drag cases; failed-write verified recovery; historical 6.0 preservation; textual imperial units.`);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
