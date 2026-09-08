// Real shipped Vue/CSS; delayed synthetic HTTP only, never device writes.
const assert = require('assert');
module.exports = async ({page, data, values, faults, counts, errors}) => {
  await page.waitForFunction(() => document.querySelector('#app').__vue_app__._instance.proxy.ready);
  await page.evaluate(() => clearInterval(document.querySelector('#app').__vue_app__._instance.proxy.timer));
  const group = page.getByRole('group', {name:'Traffic Acceleration', exact:true});
  const eco = group.getByRole('button', {name:'Eco', exact:true});
  const custom = group.getByRole('button', {name:'Custom', exact:true});
  const appearance = () => eco.evaluate(b => ({disabled:b.disabled, opacity:getComputedStyle(b).opacity, color:getComputedStyle(b).color, background:getComputedStyle(b).backgroundColor}));
  const gate = async () => {
    let release; faults.params = {promise:new Promise(r => release=r)};
    await page.evaluate(() => { document.querySelector('#app').__vue_app__._instance.proxy.refreshContext(); });
    await page.waitForFunction(() => document.querySelector('#app').__vue_app__._instance.proxy.contextPending);
    return () => {delete faults.params; release();};
  };
  const idle = () => page.waitForFunction(() => {const v=document.querySelector('#app').__vue_app__._instance.proxy;return !v.contextPending&&!v.busy;});
  const before = await appearance();
  for(let i=0;i<3;i++) {
    const release = await gate();
    assert.deepEqual(await appearance(), before, 'routine polling must not dim/disable preset buttons');
    release(); await idle(); assert.deepEqual(await appearance(), before);
  }
  let release = await gate(); let attempts = counts().attempts;
  await eco.click(); assert.equal(counts().attempts, attempts, 'click waits for context');
  release(); await page.waitForFunction(() => {const v=document.querySelector('#app').__vue_app__._instance.proxy;return !v.busy&&v.data.profiles.traffic.acceleration.preset==='eco';});
  assert.equal(counts().attempts, attempts+1);
  // A road-state change during the read must reject the queued click.
  release = await gate(); attempts = counts().attempts;
  await custom.click(); values.IsOnroad='True'; values.IsOffroad=''; release(); await idle();
  assert.equal(counts().attempts, attempts); assert(await custom.isDisabled());
  values.IsOnroad=''; values.IsOffroad='True';
  await page.evaluate(async () => await document.querySelector('#app').__vue_app__._instance.proxy.refreshContext());
  // Multiple clicks waiting for one poll cannot produce overlapping PUTs.
  release = await gate(); let releasePut; faults.put={promise:new Promise(r=>releasePut=r)};
  await custom.click(); await group.getByRole('button', {name:'Standard', exact:true}).click(); release();
  await page.waitForFunction(() => document.querySelector('#app').__vue_app__._instance.proxy.busy);
  assert.equal(counts().attempts, attempts+1); assert(await custom.isDisabled());
  delete faults.put; releasePut(); await idle();
  assert.equal(data.profiles.traffic.acceleration.preset, 'custom');
  // Disposed editors cannot send a delayed action.
  release = await gate(); attempts = counts().attempts; await eco.click();
  await page.evaluate(() => document.querySelector('#app').__vue_app__.unmount());
  release(); await page.waitForTimeout(100); assert.equal(counts().attempts, attempts);
  assert.deepEqual(errors, []);
  console.log('PASS: stable appearance across 3 polls; deferred click saves once; road transition blocks; pending PUT blocks overlaps; unmount cancels.');
};
