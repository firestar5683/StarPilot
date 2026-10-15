import assert from "node:assert/strict"
import { UpdateRestart, UPDATE_RESTART_KEY } from "../web/js/update-restart.js"
import { SoftwareStatusFeed } from "../web/js/software-status.js"

const baseline = { commit: 'a'.repeat(40), branch: 'Dom', target: 'Dom', action: 'fast' }
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
normal.recovery.start(baseline)
assert.deepEqual(normal.states, [false, true])
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

// Only update-related restarts/disconnects trigger the full-screen handoff.
const restarts = []
const feed = new SoftwareStatusFeed({ publish() {}, restarting: value => restarts.push(value) })
feed.data = status(baseline.commit, pending)
feed.error = 'Connection lost'
feed.emit('ready')
assert.equal(restarts.length, 0)
feed.installBaseline = baseline
feed.error = ''
feed.emit('ready')
assert.equal(restarts.length, 0)
feed.error = 'Connection lost'
feed.emit('ready')
assert.equal(restarts.length, 1)
feed.error = ''
feed.data.operations.progress = { stage: 'rebooting' }
feed.emit('ready')
assert.equal(restarts.length, 2)
