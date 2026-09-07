// Exact classic functions with deterministic synthetic network ordering; no Params/device access.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../assets/components/tools/device_settings.js'), 'utf8');
const start = source.indexOf('function applyLongitudinalMode(data)');
const end = source.indexOf('async function fetchDefaultValues()', start);
assert(start > 0 && end > start);
const snapshot = mode => ({ mode, values: { ExperimentalMode: mode === 'experimental', ConditionalExperimental: mode === 'conditional_experimental', ConditionalChill: mode === 'conditional_chill' }, locked: false, reason: '', experimental_confirmed: true });
const reply = (data, ok = true) => ({ ok, json: async () => data });
function harness() {
  const old = snapshot('experimental');
  const requests = [];
  const state = { longitudinalMode: old, longitudinalModeUpdating: false, longitudinalModeRequestId: 0, values: { ...old.values, LongitudinalControlMode: old.mode } };
  const env = { state, LONGITUDINAL_MODE_KEY: 'LongitudinalControlMode', validLongitudinalSnapshot: () => true,
    scheduleSyncInputs: () => {}, document: { getElementById: () => null },
    getSettingLockReason: () => state.longitudinalModeUpdating ? 'Updating' : '', showParamSnackbar: () => {},
    fetch: (_url, options) => new Promise((resolve, reject) => requests.push({ resolve, reject, options })) };
  vm.createContext(env);
  vm.runInContext(source.slice(start, end), env);
  return { env, state, requests, old };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
function check(state, mode, pending) {
  assert.equal(state.longitudinalMode?.mode ?? null, mode);
  assert.equal(state.values.LongitudinalControlMode, mode ?? '');
  assert.equal(state.longitudinalModeUpdating, pending);
  if (mode) for (const [key, value] of Object.entries(snapshot(mode).values)) assert.equal(state.values[key], value);
}
for (const outcome of ['success', 'http failure', 'network failure']) {
  for (const phase of ['write pending', 'reconcile pending', 'completed']) {
    for (const writeOK of [true, false]) {
      test(`obsolete GET ${outcome}, ${phase}, PUT ${writeOK ? 'succeeds' : 'fails'}`, async () => {
        const { env, state, requests, old } = harness();
        const read = env.fetchLongitudinalMode();
        const write = env.updateLongitudinalMode('chill');
        check(state, 'experimental', true);
        await env.fetchLongitudinalMode();
        assert.equal(requests.length, 2, 'ordinary polling stays suppressed during write');
        assert.equal(requests[1].options.method, 'PUT');
        assert.deepEqual(JSON.parse(requests[1].options.body).expected, old.values);
        if (phase !== 'write pending') {
          requests[1].resolve(reply(writeOK ? snapshot('chill') : { error: 'uncertain write' }, writeOK));
          await flush();
          assert.equal(requests.length, 3, 'always reconcile, including failed PUT');
          if (phase === 'completed') { requests[2].resolve(reply(snapshot('chill'))); await write; }
        }
        if (outcome === 'network failure') requests[0].reject(new Error('offline'));
        else requests[0].resolve(reply(old, outcome === 'success'));
        await read;
        check(state, phase === 'completed' || (phase === 'reconcile pending' && writeOK) ? 'chill' : 'experimental', phase !== 'completed');
        if (phase === 'write pending') {
          requests[1].resolve(reply(writeOK ? snapshot('chill') : { error: 'uncertain write' }, writeOK));
          await flush();
        }
        if (phase !== 'completed') { requests[2].resolve(reply(snapshot('chill'))); await write; }
        check(state, 'chill', false);
        const poll = env.fetchLongitudinalMode();
        requests[3].resolve(reply(snapshot('conditional_chill')));
        await poll;
        check(state, 'conditional_chill', false);
      });
    }
  }
  test(`obsolete forced read ${outcome} cannot supersede newer read`, async () => {
    const { env, state, requests, old } = harness();
    const first = env.fetchLongitudinalMode(true);
    const second = env.fetchLongitudinalMode(true);
    requests[1].resolve(reply(snapshot('conditional_experimental')));
    await second;
    if (outcome === 'network failure') requests[0].reject(new Error('offline'));
    else requests[0].resolve(reply(old, outcome === 'success'));
    await first;
    check(state, 'conditional_experimental', false);
  });
}
test('current reconciliation failure still clears selection and unlocks polling', async () => {
  const { env, state, requests } = harness();
  const write = env.updateLongitudinalMode('chill');
  requests[0].resolve(reply(snapshot('chill')));
  await flush();
  requests[1].reject(new Error('offline'));
  await write;
  check(state, null, false);
  const poll = env.fetchLongitudinalMode();
  requests[2].resolve(reply(snapshot('chill')));
  await poll;
  check(state, 'chill', false);
});
