// Fault-injection extension of the real Chromium synthetic-HTTP harness.
const assert=require('assert');
module.exports=async({page,curve,data,values,faults,counts,errors})=>{
  const results=[];
  const gate=key=>{let release;const promise=new Promise(r=>release=r);faults[key]={promise};return()=>{delete faults[key];release();};};
  const idle=()=>page.waitForFunction(()=>{const v=document.querySelector('#app').__vue_app__._instance.proxy;return v.ready&&!v.busy&&!v.curvePending&&!v.contextPending;});
  const poll=()=>page.evaluate(()=>{document.querySelector('#app').__vue_app__._instance.proxy.refreshContext();});
  const edit=async value=>{const n=curve.locator('input').nth(2);await n.fill(value);await n.press('Tab');};
  const remount=async()=>{
    await page.evaluate(async()=>{const {createApp}=await import('/assets/vendor/vue/vue.esm-browser.js');const {PersonalityProfiles}=await import('/assets/mobile/js/components/PersonalityProfiles.js');createApp(PersonalityProfiles).mount('#app');});
    await idle();await page.getByRole('button',{name:'Manage',exact:true}).click();await page.locator('.gx-personalities__advanced').first().locator(':scope > summary').click();
    await page.evaluate(()=>clearInterval(document.querySelector('#app').__vue_app__._instance.proxy.timer));
  };
  const unmount=()=>page.evaluate(()=>{const app=document.querySelector('#app').__vue_app__;window.oldPersonality=app._instance.proxy;window.lateEmits=0;window.oldPersonality.$.emit=()=>window.lateEmits++;app.unmount();});
  await idle();await page.evaluate(()=>clearInterval(document.querySelector('#app').__vue_app__._instance.proxy.timer));
  await page.evaluate(async()=>await document.querySelector('#app').__vue_app__._instance.proxy.load());
  // Change survives a pending context request and is sent only after it resolves.
  let release=gate('params');await poll();const n=curve.locator('input').nth(2);await n.fill('1.65');assert.equal(await n.inputValue(),'1.65');assert(await n.isEnabled());
  let before=counts().attempts;await n.press('Tab');assert.equal(counts().attempts,before);
  assert(await n.isDisabled());release();await idle();assert.equal(counts().attempts,before+1);assert.equal(data.profiles.traffic.acceleration.curve[2],1.65);results.push('numeric pending poll commits once');
  // Off-road state changing while the change waits must prevent the PUT.
  release=gate('params');await poll();before=counts().attempts;await edit('1.7');values.IsOnroad='True';values.IsOffroad='';release();
  await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.curvePending);
  assert.equal(counts().attempts,before);assert.equal(await n.inputValue(),'1.65');assert(await n.isDisabled());results.push('pending change rechecks offroad');
  values.IsOnroad='';values.IsOffroad='True';await poll();await idle();
  // In-flight PUT blocks repeat authoring until verified readback.
  release=gate('put');before=counts().attempts;await edit('1.75');await page.waitForFunction(()=>document.querySelector('#app').__vue_app__._instance.proxy.busy);
  assert(await n.isDisabled());await page.evaluate(()=>document.querySelector('#app').__vue_app__._instance.proxy.point('traffic','acceleration',2,{target:{value:'2'}}));
  assert.equal(counts().attempts,before+1);release();await idle();assert.equal(await n.inputValue(),'1.75');results.push('pending PUT rejects duplicate edit');
  // PUT accepted but both immediate readbacks fail: remain locked, no rollback claim.
  faults.readFailures=2;await edit('1.8');await page.getByRole('button',{name:'Retry loading',exact:true}).waitFor();
  assert(await n.isDisabled());assert.equal(data.profiles.traffic.acceleration.curve[2],1.8);
  assert(!(await page.getByText('Save could not be confirmed. Showing verified saved state; review it before editing again.',{exact:true}).isVisible()));
  await page.getByRole('button',{name:'Retry loading',exact:true}).click();await idle();assert.equal(await n.inputValue(),'1.8');
  await page.getByText('Save could not be confirmed. Showing verified saved state; review it before editing again.',{exact:true}).waitFor();results.push('uncertain PUT readback failure locks until verified retry');
  // Pointer preview cancels on loss of capture or a road-state transition.
  const drag=async()=>{await page.locator('.snackbar').waitFor({state:'detached'});const h=curve.locator('circle[fill="transparent"]').nth(2);await h.scrollIntoViewIfNeeded();const b=await h.boundingBox();await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();await page.mouse.move(b.x+b.width/2,b.y+b.height/2-8,{steps:3});};
  faults.failPut=true;before=counts().attempts;await drag();await page.mouse.up();await idle();assert.equal(counts().attempts,before+1);assert.equal(await n.inputValue(),'1.8');await page.getByText('Save could not be confirmed. Showing verified saved state; review it before editing again.',{exact:true}).waitFor();results.push('failed pointer PUT restores verified state');
  before=counts().attempts;await drag();await curve.locator('svg').evaluate(svg=>svg.releasePointerCapture(document.querySelector('#app').__vue_app__._instance.proxy.drag.pointerId));await page.mouse.up();assert.equal(await n.inputValue(),'1.8');assert.equal(counts().attempts,before);results.push('lost capture rolls back without PUT');
  await drag();values.IsOnroad='True';values.IsOffroad='';await poll();await page.waitForFunction(()=>!document.querySelector('#app').__vue_app__._instance.proxy.contextPending);await page.mouse.up();assert.equal(await n.inputValue(),'1.8');assert.equal(counts().attempts,before);results.push('mid-drag road transition rolls back');
  values.IsOnroad='';values.IsOffroad='True';await poll();await idle();
  release=gate('params');await poll();await drag();await page.mouse.up();assert.equal(counts().attempts,before);release();await idle();assert.equal(counts().attempts,before+1);results.push('pointer release waits for pending poll');
  // Unmount before release cancels preview; remount only loads server state.
  before=counts().attempts;const saved=data.profiles.traffic.acceleration.curve[2];await drag();await unmount();await page.mouse.up();assert.equal(counts().attempts,before);await remount();assert.equal(Number(await n.inputValue()),saved);results.push('unmount drag does not save or resurrect preview');
  // Unmount while waiting for poll prevents an edit from being sent afterward.
  release=gate('params');await poll();await edit('1.95');await unmount();release();await page.waitForFunction(()=>!window.oldPersonality.curvePending);assert.equal(counts().attempts,before);assert.equal(await page.evaluate(()=>window.lateEmits),0);await remount();assert.equal(Number(await n.inputValue()),saved);results.push('unmount pending poll sends no PUT');
  // An already sent PUT may complete, but disposed component must not emit/read/snack.
  await page.locator('.snackbar').waitFor({state:'detached'});release=gate('put');await edit('2.05');await page.waitForFunction(()=>document.querySelector('#app').__vue_app__._instance.proxy.busy);const reads=counts().profileReads;await unmount();release();await page.waitForFunction(()=>!window.oldPersonality.busy);assert.equal(counts().profileReads,reads);assert.equal(await page.evaluate(()=>window.lateEmits),0);assert.equal(await page.locator('.snackbar').count(),0);await remount();assert.equal(await n.inputValue(),'2.05');results.push('unmount in-flight PUT suppresses late effects; remount reads saved result');
  assert.deepEqual(errors,[]);console.log(`PASS: ${results.length} lifecycle fault-injection scenarios.`);return results;
};
