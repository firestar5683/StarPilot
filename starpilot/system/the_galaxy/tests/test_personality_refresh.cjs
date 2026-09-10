// Real component methods, saved-state fixture, and deterministic synthetic API.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(`${__dirname}/../assets/mobile/js/components/PersonalityProfiles.js`, 'utf8')
  .replace(/^import .*$/gm, '').replace('export const PersonalityProfiles =', 'globalThis.PersonalityProfiles =');
const clone = value => JSON.parse(JSON.stringify(value));
const fixture = JSON.parse(fs.readFileSync(`${__dirname}/browser/fixtures/personality_profiles.json`));
const deferred = () => { let resolve; const promise = new Promise(r => {resolve = r}); return {promise, resolve}; };
function setup() {
  const server = clone(fixture), requests = [];
  server.editing_locked = false;
  server.launch_boost_options = ['off', 'low', 'medium', 'high'];
  server.launch_boost = {traffic:'off', aggressive:'off', standard:'off', relaxed:'off'};
  const values = {IsOnroad:false, IsOffroad:true, SafeMode:false};
  const api = {
    getParams: async () => clone(values),
    getPersonalityProfiles: async () => clone(server),
    getLayout: async () => [],
    savePersonalityProfile: async payload => {
      requests.push(clone(payload));
      assert.deepEqual(clone(payload.expected), server.profiles[payload.profile][payload.category], 'CAS expected saved category');
      server.profiles[payload.profile][payload.category] = {preset:payload.preset, curve:clone(payload.curve)};
    },
  };
  const context = {api, showSnackbar() {}, personalityProfileParamKey:p=>p};
  vm.createContext(context); vm.runInContext(source, context);
  const component = context.PersonalityProfiles;
  const state = {...component.data(), ...component.methods, $emit() {}, ready:true, data:clone(server), values:clone(values)};
  for (const [key, get] of Object.entries(component.computed)) if (typeof get === 'function') Object.defineProperty(state, key, {get});
  return {state, server, api, requests};
}
test('idle polling accepts another editor preset, launch level, and migration metadata', async () => {
  const {state, server, requests} = setup();
  server.profiles.standard.acceleration.preset = 'sport';
  server.launch_boost.standard = 'low';
  server.migration_required = true;
  await state.refreshContext();
  assert.equal(state.data.profiles.standard.acceleration.preset, 'sport');
  assert.equal(state.data.launch_boost.standard, 'low');
  assert.equal(state.editingLocked, true);
  server.migration_required = false;
  await state.refreshContext();
  await state.preset('standard', 'acceleration', 'standard');
  assert.equal(requests.length, 1);
  assert.equal(state.data.profiles.standard.acceleration.preset, 'standard');
});
test('unchanged previews and active text survive polling; conflicting category is discarded', async () => {
  const {state, server} = setup();
  state.drafts.standardacceleration = [1, 2];
  state.drafts.relaxedacceleration = [3, 4];
  state.curveText.standardacceleration0 = '1.';
  state.curveText.relaxedacceleration0 = '3.';
  state.advancedText.StandardJerkSpeed = '12';
  state.drag = {profile:'relaxed', category:'acceleration'};
  await state.refreshContext();
  assert.deepEqual(state.drafts.standardacceleration, [1, 2]);
  assert.equal(state.curveText.standardacceleration0, '1.');
  server.profiles.standard.acceleration.preset = 'sport';
  await state.refreshContext();
  assert.equal(state.drafts.standardacceleration, undefined);
  assert.equal(state.curveText.standardacceleration0, undefined);
  assert.deepEqual(state.drafts.relaxedacceleration, [3, 4]);
  assert.equal(state.curveText.relaxedacceleration0, '3.');
  assert.equal(state.drag.profile, 'relaxed');
  assert.equal(state.advancedText.StandardJerkSpeed, '12');
});
test('local write waits for pending poll and leaves verified local readback', async () => {
  const {state, server, api, requests} = setup();
  const pending = deferred();
  const read = api.getPersonalityProfiles;
  api.getPersonalityProfiles = () => pending.promise;
  const poll = state.refreshContext();
  const write = state.preset('standard', 'acceleration', 'sport');
  assert.equal(requests.length, 0);
  api.getPersonalityProfiles = read;
  pending.resolve(clone(server));
  await Promise.all([poll, write]);
  assert.equal(requests.length, 1);
  assert.equal(state.data.profiles.standard.acceleration.preset, 'sport');
});
test('poll conflict cannot pair an obsolete curve preview with a fresh expected snapshot', async () => {
  const {state, server, api, requests} = setup();
  state.data.profiles.standard.acceleration = {preset:'custom', curve:Array(10).fill(1)};
  server.profiles.standard.acceleration = clone(state.data.profiles.standard.acceleration);
  state.drafts.standardacceleration = [2, ...Array(9).fill(1)];
  const pending = deferred();
  const read = api.getPersonalityProfiles;
  api.getPersonalityProfiles = () => pending.promise;
  const poll = state.refreshContext();
  const write = state.saveCurve('standard', 'acceleration');
  server.profiles.standard.acceleration.curve[1] = 3;
  api.getPersonalityProfiles = read;
  pending.resolve(clone(server));
  await Promise.all([poll, write]);
  assert.equal(server.profiles.standard.acceleration.curve[1], 3);
  assert.equal(state.drafts.standardacceleration, undefined);
  assert(requests.length <= 1);
  if (requests.length) assert.equal(requests[0].expected.curve[1], 1);
});
test('malformed polling data locks editing without replacing saved state', async () => {
  const {state, api} = setup();
  const saved = state.data;
  api.getPersonalityProfiles = async () => ({editing_locked:false});
  await state.refreshContext();
  assert.equal(state.ready, false);
  assert.equal(state.data, saved);
});

test('polling during an in-flight local write cannot restore old saved state', async () => {
  const {state, server, api} = setup();
  const pending = deferred();
  const save = api.savePersonalityProfile;
  api.savePersonalityProfile = async payload => {await pending.promise; return save(payload)};
  let reads = 0;
  const read = api.getPersonalityProfiles;
  api.getPersonalityProfiles = async () => {reads++; return read()};
  const write = state.preset('standard', 'acceleration', 'sport');
  assert.equal(state.busy, true);
  await state.refreshContext();
  assert.equal(reads, 0);
  pending.resolve();
  await write;
  assert.equal(state.data.profiles.standard.acceleration.preset, 'sport');
  assert.equal(state.writeGeneration, 1);
  await state.refreshContext();
  assert.equal(state.data.profiles.standard.acceleration.preset, 'sport');
  assert.equal(server.profiles.standard.acceleration.preset, 'sport');
});
