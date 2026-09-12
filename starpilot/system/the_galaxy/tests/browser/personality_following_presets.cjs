const assert = require('assert');
const path = require('path');

module.exports = async ({page, data, writes, errors, output}) => {
  const profiles = ['traffic', 'aggressive', 'standard', 'relaxed'];
  const legacy = ['legacy_close', 'legacy_medium', 'legacy_far'];
  const custom = Array(10).fill(1.55);
  const settled = () => page.waitForFunction(() => {
    const vm = document.querySelector('#app').__vue_app__._instance.proxy;
    return !vm.busy && !vm.curvePending && vm.ready;
  });
  for (let i = 0; i < profiles.length; i++) {
    data.profiles[profiles[i]].following = {preset: legacy[i % 3], curve: [...custom]};
  }
  await page.reload();
  await page.getByRole('button', {name: 'Manage', exact: true}).click();
  for (let i = 0; i < profiles.length; i++) {
    const profile = page.locator('.gx-personalities__profile').nth(i);
    const section = profile.locator('.gx-personalities__category').nth(2);
    const previousName = 'Previous ' + ['Close', 'Medium', 'Far'][i % 3];
    const previous = section.getByRole('button', {name: previousName, exact: true});
    assert.equal(await previous.getAttribute('aria-pressed'), 'true');
    assert(await section.getByText('Previous fixed following distance retained.', {exact: false}).isVisible());
    for (const preset of ['Traffic', 'Close', 'Medium', 'Far', 'Custom']) {
      await section.getByRole('button', {name: preset, exact: true}).click();
      await settled();
      assert.equal(writes.at(-1).preset, preset.toLowerCase());
      assert.deepEqual(data.profiles[profiles[i]].following.curve, custom);
      assert.equal(await previous.count(), 0);
      assert.equal(await section.getByRole('button', {name: preset, exact: true}).getAttribute('aria-pressed'), 'true');
    }
  }
  await page.reload();
  await page.getByRole('button', {name: 'Manage', exact: true}).click();
  for (const profile of profiles) assert.deepEqual(data.profiles[profile].following, {preset: 'custom', curve: custom});
  for (const width of [320, 1280]) {
    await page.setViewportSize({width, height: 1000});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({path: path.join(output, `following-presets-${width}.png`), fullPage: true});
  }
  assert.deepEqual(errors, []);
  console.log('PASS: Previous Close/Medium/Far retained and selected; explicit new Traffic/Close/Medium/Far selection; dormant Custom restoration in all four profiles; reload and responsive layout');
};
