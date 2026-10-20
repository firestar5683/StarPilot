import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { UpdateRestart, UPDATE_RESTART_KEY, UPDATE_RESTART_PREPARED_KEY } from "../web/js/update-restart.js"
import { SoftwareStatusFeed } from "../web/js/software-status.js"

const baseline = { commit: 'a'.repeat(40), branch: 'Dom', target: 'Dom', action: 'fast' }
// Vue evaluates template callbacks against component data, not module scope.
const app = readFileSync(new URL('../web/js/app.js', import.meta.url), 'utf8')
const dataFields = app.match(/data: \(\) => \(\{([^\n]+)\}\),/)?.[1]
assert.ok(dataFields)
const calls = []
const updateRestart = { prepare: value => calls.push(['prepare', value]), start: value => calls.push(['start', value]) }
const deviceRestart = { instance: 'current-instance' }
const context = new Function('state', 'authState', 'authForm', 'route', 'NAV', 'updateRestart', 'deviceRestart', 'UPDATE_RESTART_MESSAGE',
  `return ({${dataFields}})` )({}, {}, {}, {}, [], updateRestart, deviceRestart, '')
for (const [prop, action] of [['preparing', 'prepare'], ['restarting', 'start']]) {
  const expression = app.match(new RegExp(`:${prop}="([^"]+)"`))?.[1]
  assert.ok(expression)
  new Function('context', 'baseline', `with (context) { return (${expression})(baseline) }`)(context, baseline)
  assert.deepEqual(calls.at(-1), [action, { ...baseline, instance: 'current-instance' }])
}
const status = (commit = baseline.commit, request = null) => ({ schemaVersion: 1,
  installed: { commit, branch: 'Dom' }, updater: { state: 'idle' }, operations: { request } })
const pending = { action: 'fast', state: 'pending' }
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve() }
function fixture(saved = null) {
  const values = new Map(saved ? [[UPDATE_RESTART_KEY, JSON.stringify(saved)]] : [])
  const storage = { getItem: key => values.get(key), setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) }
  const states = [], timers = new Map(), requests = []
  let nextTimer = 0
  let reloads = 0
  const recovery = new UpdateRestart({ storage, publish: value => states.push(value),
    request: () => new Promise((resolve, reject) => requests.push({ resolve, reject })),
    later: (fn, ms) => { const id = ++nextTimer; timers.set(id, fn); return id },
    cancel: id => timers.delete(id), reload: () => reloads++ })
  return { recovery, states, requests, timers, values, tick() { const [id, fn] = timers.entries().next().value; timers.delete(id); fn() }, get reloads() { return reloads } }
}
const normal = fixture()
assert.deepEqual(normal.states, [false])
assert.equal(normal.requests.length, 0)
normal.recovery.prepare(baseline)
assert.deepEqual(normal.states, [false], 'preparing must leave the update request page mounted')
assert.equal(normal.values.has(UPDATE_RESTART_PREPARED_KEY), true)
normal.recovery.start(baseline)
assert.deepEqual(normal.states, [false, true])
assert.equal(normal.values.has(UPDATE_RESTART_PREPARED_KEY), false)
normal.recovery.start(baseline)
assert.equal(normal.requests.length, 1)
normal.requests[0].resolve(status(baseline.commit, pending))
await flush()
assert.equal(normal.reloads, 0)
normal.tick()
normal.requests[1].reject(new Error('Device offline'))
await flush()
assert.equal(normal.states.at(-1), true)
normal.tick()
normal.requests[2].resolve(status())
await flush()
normal.tick()
normal.requests[3].resolve(status('b'.repeat(40)))
await flush()
assert.equal(normal.reloads, 1)
assert.equal(normal.states.at(-1), false)
assert.equal(normal.values.has(UPDATE_RESTART_KEY), false)

// A changed on-disk build with an active restart request must not dismiss the waiting screen.
const installing = fixture()
installing.recovery.start(baseline)
installing.requests[0].resolve(status('b'.repeat(40), { state: 'complete', outcome: 'restarting' }))
await flush()
assert.equal(installing.reloads, 0)
const completedAfterReboot = fixture({ ...baseline, instance: 'one' })
completedAfterReboot.requests[0].resolve({ ...status('b'.repeat(40), { state: 'complete', outcome: 'restarting' }), instance: 'two' })
await flush()
assert.equal(completedAfterReboot.reloads, 1)

const canceled = fixture()
canceled.recovery.prepare(baseline)
canceled.recovery.cancelPreparation()
assert.equal(canceled.values.has(UPDATE_RESTART_PREPARED_KEY), false)
const abandoned = fixture()
abandoned.recovery.prepare(baseline)
abandoned.recovery.start(abandoned.recovery.prepared, { provisional: true })
assert.equal(abandoned.values.has(UPDATE_RESTART_PREPARED_KEY), true)
abandoned.recovery.now = () => Date.now() + 31000
abandoned.requests[0].resolve(status())
await flush()
assert.equal(abandoned.reloads, 1)
assert.equal(abandoned.values.has(UPDATE_RESTART_PREPARED_KEY), false)
const recoveryAfterPageError = fixture()
recoveryAfterPageError.recovery.prepare(baseline)
const preparedValues = recoveryAfterPageError.values
const preparedStorage = { getItem: key => preparedValues.get(key), setItem: (key, value) => preparedValues.set(key, value), removeItem: key => preparedValues.delete(key) }
const resumedStates = []
const resumedScreen = new UpdateRestart({ storage: preparedStorage, publish: value => resumedStates.push(value),
  request: () => new Promise(() => {}), later: () => 1 })
assert.equal(resumedScreen.baseline?.commit, baseline.commit)
assert.equal(resumedStates.at(-1), true)

// A same-revision return is ambiguous; keep waiting for explicit completion or a changed build.
const resumed = fixture(baseline)
assert.equal(resumed.states[0], true)
resumed.requests[0].resolve(status())
await flush()
assert.equal(resumed.reloads, 0)
for (const request of [null, { state: 'failed' }, { state: 'complete', outcome: 'up_to_date' }]) {
  const recovery = fixture()
  recovery.recovery.start(baseline)
  recovery.requests[0].resolve(status(request ? baseline.commit : 'b'.repeat(40), request))
  await flush()
  assert.equal(recovery.reloads, 1)
}

const rebooted = fixture({ ...baseline, instance: 'one' })
rebooted.requests[0].resolve({ ...status(), instance: 'one' })
await flush()
assert.equal(rebooted.reloads, 0)
rebooted.tick()
rebooted.requests[1].resolve({ ...status(), instance: 'two' })
await flush()
assert.equal(rebooted.reloads, 1)
const busy = fixture({ ...baseline, instance: 'one' })
busy.requests[0].resolve({ ...status(baseline.commit, pending), instance: 'two' })
await flush()
assert.equal(busy.reloads, 0)
const kept = fixture()
kept.recovery.start({ ...baseline, instance: 'one' })
kept.recovery.start({ ...baseline, instance: 'two' })
assert.equal(JSON.parse(kept.values.get(UPDATE_RESTART_KEY)).instance, 'one')

// Keep update progress visible until Galaxy actually loses the device connection.
const restarts = []
const feed = new SoftwareStatusFeed({ publish() {}, restarting: value => restarts.push(value) })
feed.installBaseline = baseline
feed.data = status(baseline.commit, { action: 'update', state: 'pending' })
feed.emit('ready')
feed.error = 'Updater status is unavailable'
feed.emit('ready')
assert.equal(restarts.length, 0)
feed.connectionLost = true
feed.emit('ready')
assert.deepEqual(restarts, [baseline])
