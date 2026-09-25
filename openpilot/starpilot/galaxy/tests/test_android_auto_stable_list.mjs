import assert from 'node:assert/strict';
import { test } from 'node:test';
import { AndroidAutoFeed, AndroidAutoPage } from '../web/js/android-auto.js';

const setup = {enabled: true, parked: true, bluetoothEnabled: true, installReady: true,
  serviceReady: true, identity: {installed: true}, import: {state: 'idle'}, maxUploadBytes: 1024};
const car = {address: 'AA:BB:CC:DD:EE:FF', name: 'IONIQ 6', paired: true, connected: false, android_auto: false};
const adapter = {...car, address: '11:22:33:44:55:66', name: 'Adapter'};
const status = (devices = [car], extra = {}) => ({pairing: {active: true, approved: false,
  receiver: null, prompt: null, state: 'idle', discovering: true, devices, ...extra}, selectedReceiver: null});
const response = (body, code = 200) => ({status: code, ok: code === 200, json: async () => body});
const deferred = () => {let resolve; const promise = new Promise((done) => {resolve = done}); return {promise, resolve};};
function harness(fetcher, unauthorized = () => {}) {
  const states = [], timers = new Map(); let next = 0;
  const feed = new AndroidAutoFeed({fetcher, unauthorized, publish: (value) => states.push(value),
    later: (fn, ms) => {timers.set(++next, {fn, ms}); return next}, cancelTimer: (id) => timers.delete(id)});
  return {feed, states, timers};
}

test('background scans keep selection enabled and retain order while names and statuses update', async () => {
  let devices = [car, adapter, {...car, address: '22:22:22:22:22:22', name: '  '},
    {...car, address: '33:33:33:33:33:33', name: '33:33:33:33:33:33'},
    {...car, address: '44:44:44:44:44:44', name: '44-44-44-44-44-44'}];
  const {feed, states} = harness(async (path) => response(path.endsWith('/setup') ? setup : status(devices)));
  await feed.start();
  assert.deepEqual(feed.pairing.devices.map((d) => d.name), ['IONIQ 6', 'Adapter']);
  devices = [{...adapter, name: 'Adapter renamed'}, {...car, connected: true}];
  await feed.refresh();
  assert.deepEqual(feed.pairing.devices.map((d) => d.name), ['IONIQ 6', 'Adapter renamed']);
  assert.equal(feed.pairing.devices[0].connected, true);
  assert(states.every((s) => s.busy === false));
  assert.equal(AndroidAutoPage.computed.deviceSelectionBlocked.call({...feed, pairingReason: ''}), false);
  devices = [adapter]; await feed.refresh();
  devices = [adapter, car]; await feed.refresh();
  assert.deepEqual(feed.pairing.devices.map((d) => d.address), [car.address, adapter.address]);
  feed.stop();
});

test('selection supersedes a delayed poll JSON body and blocks duplicate actions', async () => {
  const delayed = deferred(), post = deferred(); let poll = false, delayedSignal; const posts = [];
  const {feed, states, timers} = harness(async (path, options) => {
    if (options.method === 'POST') {posts.push(path); return post.promise;}
    if (path.endsWith('/setup')) return response(setup);
    if (poll) {poll = false; delayedSignal = options.signal; return {...response(null), json: () => delayed.promise};}
    return response(status([car], {state: posts.length ? 'connecting' : 'idle'}));
  });
  await feed.start(); poll = true;
  const refreshing = feed.refresh();
  while (!delayedSignal) await Promise.resolve();
  assert.equal(feed.busy, false);
  const selecting = feed.selectDevice(car.address);
  assert.equal(feed.busy, true);
  assert.equal(delayedSignal.aborted, true);
  assert.equal(await feed.selectDevice(car.address), false);
  delayed.resolve(status([adapter], {active: false})); await refreshing;
  assert.equal(feed.pairing.active, true);
  assert.equal(feed.pairing.devices[0].address, car.address);
  assert.equal(feed.busy, true);
  post.resolve(response({ok: true}));
  assert.equal(await selecting, true);
  assert.deepEqual(posts, ['./api/android-auto/pairing/select']);
  assert.equal(feed.pairing.state, 'connecting');
  assert.equal(feed.busy, false);
  assert.equal([...timers.values()].filter((t) => t.ms === 1000).length, 1);
  assert(states.some((s) => s.busy)); feed.stop();
});

test('cancel remains usable during a delayed setup poll without stale setup replacing state', async () => {
  const delayed = deferred(); let wait = false, signal; const calls = [];
  const {feed} = harness(async (path, options) => {
    calls.push(path);
    if (options.method === 'POST') return response({ok: true});
    if (path.endsWith('/setup')) {
      if (wait) {wait = false; signal = options.signal; return delayed.promise;}
      return response(setup);
    }
    return response(status([], {active: !calls.some((p) => p.endsWith('/cancel'))}));
  });
  await feed.start(); wait = true; const refreshing = feed.refresh();
  assert.equal(feed.busy, false);
  assert.equal(await feed.action('./api/android-auto/pairing/cancel'), true);
  delayed.resolve(response({...setup, enabled: false})); await refreshing;
  assert.equal(signal.aborted, true);
  assert.equal(feed.setup.enabled, true);
  assert.equal(feed.pairing.active, false);
  assert.equal(feed.endReason, 'canceled'); feed.stop();
});

test('poll authorization failures stop polling and visibility stop cancels active pairing', async () => {
  let unauthorized = 0, deny = false; const calls = [];
  const {feed, timers} = harness(async (path, options) => {
    calls.push([path, options]);
    return deny ? response({}, 401) : response(path.endsWith('/setup') ? setup : status());
  }, () => unauthorized++);
  await feed.start(); feed.stop(true);
  assert(calls.some(([path, options]) => path.endsWith('/cancel') && options.keepalive));
  await feed.start(); deny = true; await feed.refresh();
  assert.equal(unauthorized, 1); assert.equal(feed.active, false); assert.equal(feed.busy, false);
  assert.equal(timers.size, 0);
});

test('upload progress follows the foreground generation and ignores progress after stop', async () => {
  const {feed, states} = harness(async (path) => response(path.endsWith('/setup') ? setup : status()));
  await feed.start();
  let progress; const pending = deferred();
  feed.uploader = async (path, options, onProgress) => {progress = onProgress; onProgress({loaded: 4, total: 16}); return pending.promise};
  const uploading = feed.upload({size: 16});
  assert(states.some((s) => s.uploadProgress?.loaded === 4));
  feed.stop(); const count = states.length; progress({loaded: 8, total: 16});
  assert.equal(states.length, count);
  pending.resolve(response({ok: true})); assert.equal(await uploading, false);
});

test('a failed foreground action resumes the canceled background polling', async () => {
  const {feed, timers} = harness(async (path, options) => {
    if (options.method === 'POST') throw new Error('Temporary network error');
    return response(path.endsWith('/setup') ? setup : status());
  });
  await feed.start();
  assert.equal(await feed.selectDevice(car.address), false);
  assert.equal(feed.busy, false);
  assert.equal([...timers.values()].filter((t) => t.ms === 1000).length, 1);
  const poll = [...timers.values()].find((t) => t.ms === 1000);
  await poll.fn(); assert.equal(feed.error, ''); feed.stop();
});

test('saved receiver selection also hides MAC aliases and retains stable named entries', async () => {
  let receivers = [car, {...adapter, name: 'dev_11_22_33_44_55_66'}];
  const {feed} = harness(async (path) => response(path.endsWith('/setup') ? setup :
    path.endsWith('/receivers') ? {receivers} : status([], {active:false})));
  await feed.start(); await feed.loadReceivers();
  assert.deepEqual(feed.receivers.map(d => d.name), ['IONIQ 6']);
  receivers = [adapter, car]; await feed.loadReceivers();
  assert.deepEqual(feed.receivers.map(d => d.address), [car.address, adapter.address]);
  receivers = [{...adapter, name:'AndroidAuto-8b83'}, {...car, name:'My IONIQ'}];
  await feed.loadReceivers();
  assert.deepEqual(feed.receivers.map(d => d.name), ['My IONIQ', 'AndroidAuto-8b83']);
  feed.stop();
});
