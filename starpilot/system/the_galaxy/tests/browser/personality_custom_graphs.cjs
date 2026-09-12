const assert = require('assert');
const path = require('path');

module.exports = async ({page, data, values, writes, errors, output}) => {
  const categories = ['acceleration', 'braking', 'following'];
  for (const category of categories) data.profiles.traffic[category] = {preset:'custom', curve:Array(10).fill(1.15)};
  data.reference_curves.traffic.braking = Array(10).fill(0.35);
  const reload = async () => {
    await page.reload();
    await page.getByRole('button', {name:'Manage', exact:true}).click();
    await page.locator('.gx-personalities__profile').first().locator('.gx-personalities__advanced > summary').click();
  };
  const settled = () => page.waitForFunction(() => {
    const vm = document.querySelector('#app').__vue_app__._instance.proxy;
    return !vm.busy && !vm.curvePending && vm.ready;
  });
  await reload();
  const profile = page.locator('.gx-personalities__profile').first();
  for (let i=0;i<categories.length;i++) {
    const category = categories[i];
    const section = profile.locator('.gx-personalities__category').nth(i);
    await section.getByRole('button',{name:i===2?'Far':'Eco',exact:true}).click();
    await settled();
    await section.getByRole('button',{name:'Custom',exact:true}).click();
    await settled();
    assert.deepEqual(data.profiles.traffic[category].curve,Array(10).fill(1.15));
    const graph = profile.locator('.gx-personalities__curve').nth(i);
    const reset = graph.getByRole('button',{name:/reset to default/i});
    const other = JSON.stringify(data.profiles.traffic[categories[(i+1)%3]]);
    await reset.click();
    await settled();
    assert.equal(writes.at(-1).reset,true);
    assert.deepEqual(writes.at(-1).curve,[]);
    assert(writes.at(-1).expected);
    assert.deepEqual(data.profiles.traffic[category].curve,data.reference_curves.traffic[category]);
    assert.equal(JSON.stringify(data.profiles.traffic[categories[(i+1)%3]]),other);
    assert.deepEqual(await graph.locator('input').evaluateAll(inputs=>inputs.map(input=>Number(input.value))),data.reference_curves.traffic[category]);
    assert.equal(await graph.locator('polyline').nth(0).getAttribute('points'),await graph.locator('polyline').nth(1).getAttribute('points'));
  }
  await reload();
  assert.equal(Number(await profile.locator('.gx-personalities__curve').nth(1).locator('input').first().inputValue()),0.35);
  const points = await profile.locator('.gx-personalities__curve').nth(1).locator('polyline').first().getAttribute('points');
  assert(points.split(' ').every(pair=>Number(pair.split(',')[1])<=90),'low default stays inside graph axes');
  for (const width of [320,1280]) {
    await page.setViewportSize({width,height:1000});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,`custom-reset-${width}.png`),fullPage:true});
  }
  values.IsOnroad=true; values.IsOffroad=false;
  await page.reload();
  await page.getByRole('button',{name:'Manage',exact:true}).click();
  await profile.locator('.gx-personalities__advanced > summary').click();
  for (const button of await profile.getByRole('button',{name:/reset to default/i}).all()) assert(await button.isDisabled());
  assert.deepEqual(errors,[]);
  console.log('PASS: rendered reset controls, retained presets, reload persistence, per-category defaults/reference parity, narrow/wide layout and onroad lock');
};
