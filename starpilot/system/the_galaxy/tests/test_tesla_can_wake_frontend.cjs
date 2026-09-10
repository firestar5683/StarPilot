const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../../..');
const base = path.join(root, 'starpilot/system/the_galaxy/assets/mobile/js');
const layout = JSON.parse(fs.readFileSync(path.join(root, 'starpilot/common/assets/device_settings_layout.json')));
const section = layout.find(s => s.name === 'Vehicle');
const param = section.params.find(p => p.key === 'TeslaWakeOnCAN');
assert.ok(param, 'Wake on CAN must appear in Vehicle settings');
const ctx = { console, FavoritesEditor: {}, window: { confirm: () => false }, api: {}, showSnackbar: () => {} };
vm.createContext(ctx);
function load(file, expose) {
  const src = fs.readFileSync(path.join(base, file), 'utf8').replace(/^import[\s\S]*?from [^\n]+\n/gm, '').replace(/export /g, '');
  vm.runInContext(src + '\n' + expose, ctx);
}
load('params.js', 'this.visible = isSettingVisible');
for (const [make, supported, expected] of [['Tesla', true, true], ['Tesla', false, false], ['Toyota', true, false], ['', false, false]]) {
  assert.equal(ctx.visible(section, param, {CarMake:make, TeslaCANWakeAvailable:supported}), expected);
}
load('components/GalaxyToggleCard.js', 'this.card = GalaxyToggleCard');
(async () => {
  const writes = [], changes = [];
  ctx.api.updateParam = async data => {writes.push(data); return {}};
  const card = {param, value:false, values:{IsOnroad:false}, locked:false, updating:false,
    $emit: (...args) => changes.push(args), rollback: () => {}};
  await ctx.card.methods.commit.call(card, true);
  assert.equal(writes.length, 0, 'cancelled firmware confirmation must not write');
  ctx.window.confirm = () => true;
  card.values.IsOnroad = true;
  await ctx.card.methods.commit.call(card, true);
  assert.equal(writes.length, 0, 'onroad firmware writes must be blocked');
  card.values.IsOnroad = false;
  await ctx.card.methods.commit.call(card, true);
  assert.equal(writes.length, 1);
  assert.equal(writes[0].confirmedPandaFirmwareFlash, true);
  assert.equal(writes[0].value, true);
  const switchEvent = {target:{checked:true}};
  const cancelledCard = {locked:false, value:false, commit: async () => {}};
  await ctx.card.methods.onSwitch.call(cancelledCard, switchEvent);
  assert.equal(switchEvent.target.checked, false, 'cancelled switch must restore its displayed state');
  const network = [];
  const apiCtx = {fetch:async (url, opts) => {network.push(JSON.parse(opts.body)); return {ok:true,json:async()=>({})}}};
  vm.createContext(apiCtx);
  vm.runInContext(fs.readFileSync(path.join(base,'api.js'),'utf8').replace(/export /g,'') + '\nthis.client=api', apiCtx);
  await apiCtx.client.updateParam({key:'TeslaWakeOnCAN',value:true,confirmedPandaFirmwareFlash:true});
  assert.equal(network[0].confirmedPandaFirmwareFlash, true);
  console.log('Tesla New Galaxy visibility, cancellation, offroad and confirmation passed');
})().catch(e => {console.error(e); process.exitCode=1});
