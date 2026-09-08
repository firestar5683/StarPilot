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
 await page.setViewportSize({width:320,height:1000});await page.evaluate(()=>document.documentElement.style.zoom=2);
 await page.locator('.snackbar').waitFor({state:'detached'});
 const plot=curve.locator('.gx-personalities__plot');await plot.scrollIntoViewIfNeeded();
 const beforeScrollWrites=writes.length;
 await plot.evaluate(el=>{el.scrollLeft=0;el.focus();});
 await page.keyboard.press('ArrowRight');
 await page.waitForFunction(()=>document.querySelector('.gx-personalities__plot').scrollLeft>0);
 const keyboardScroll=await plot.evaluate(el=>el.scrollLeft);
 await plot.evaluate(el=>el.scrollLeft=0);
 const boxScroll=await plot.boundingBox(); const sx=boxScroll.x+boxScroll.width*.85, sy=boxScroll.y+boxScroll.height*.5;
 await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:sx,y:sy}]});
 for(let i=1;i<=6;i++) await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:sx-i*15,y:sy}]});
 await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 await page.waitForFunction(()=>document.querySelector('.gx-personalities__plot').scrollLeft>0);
 await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.drag);
 assert.equal(writes.length,beforeScrollWrites,'horizontal pan must not save a curve');
 const touchScroll=await plot.evaluate(el=>el.scrollLeft);
 const inputs=curve.locator('input');assert.equal(await inputs.count(),10);
 for(let i=0;i<10;i++) {await inputs.nth(i).scrollIntoViewIfNeeded();await inputs.nth(i).focus();assert(await inputs.nth(i).isVisible());assert(await inputs.nth(i).isEnabled());assert(await inputs.nth(i).evaluate(el=>document.activeElement===el));}
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth/2+1),'whole-page horizontal overflow');
 await plot.evaluate(el=>el.scrollLeft=el.scrollWidth);await plot.scrollIntoViewIfNeeded();
 await page.screenshot({path:path.join(output,'320-200-percent-scrolled.png')});
 const result={syntheticAPI:true,width:320,zoom:2,dpr,keyboardScroll,touchScroll,numericPoints:10,panWrites:writes.length-beforeScrollWrites,wholePageOverflow:false,errors};
 fs.writeFileSync(path.join(output,'scroll-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
