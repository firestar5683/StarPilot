import assert from 'node:assert/strict'
import { DeviceState, DeviceStateFeed, validDeviceState } from '../web/js/device-state.js'

for (const state of ['parked', 'driving', 'standby', null]) assert.equal(validDeviceState({ state, maxAgeMs: 3000 }), true)
for (const state of ['unknown', 'constructor', '', false]) assert.equal(validDeviceState({ state, maxAgeMs: 3000 }), false)
for (const maxAgeMs of [undefined, 0, -1, 3001, Infinity, '3000']) assert.equal(validDeviceState({ state: 'parked', maxAgeMs }), false)
assert.equal(DeviceState.computed.label.call({ state: null }), 'State unavailable')
assert.equal(DeviceState.computed.label.call({ state: 'standby' }), 'Standby')
const flush = async () => { for (let n = 0; n < 8; n++) await Promise.resolve() }

function fixture() {
  let now = 0, next = 0, revoked = 0
  const timers = new Map(), requests = [], states = []
  const feed = new DeviceStateFeed({ publish: (update) => states.push(update), clock: () => now,
    unauthorized: () => revoked++,
    later: (fn, ms) => { timers.set(++next, { fn, at: now + ms }); return next }, cancelTimer: (id) => timers.delete(id),
    fetcher: (url, options) => new Promise((resolve) => requests.push({ url, options, resolve })) })
  return { feed, timers, requests, states, get revoked() { return revoked },
    async advance(ms) {
      now += ms
      for (const [key, timer] of [...timers]) if (timer.at <= now && timers.delete(key)) timer.fn()
      await flush()
    },
    async reply(index, state, status = 200) {
      requests[index].resolve({ ok: status === 200, status, json: async () => ({ state, maxAgeMs: 3000 }) })
      await flush()
    } }
}

const live = fixture()
live.feed.start()
assert.equal(live.requests[0].url, './api/device/state')
assert.equal(live.requests[0].options.credentials, 'same-origin')
await live.reply(0, 'parked')
assert.deepEqual(live.states.at(-1), { state: 'parked', stale: false })
const initialUpdates = live.states.length
await live.advance(1500)
await live.reply(1, 'parked')
assert.equal(live.states.length, initialUpdates, 'unchanged healthy polls do not republish presentation')
await live.advance(1500)
await live.reply(2, null)
assert.deepEqual(live.states.at(-1), { state: 'parked', stale: false }, 'one missing source does not erase last state')
await live.advance(1500)
assert.deepEqual(live.states.at(-1), { state: 'parked', stale: true }, 'last-known display becomes explicitly stale')
await live.reply(3, 'driving')
assert.deepEqual(live.states.at(-1), { state: 'driving', stale: false }, 'real transition is immediate')
live.feed.stop()
assert.equal(live.timers.size, 0)
assert.deepEqual(live.states.at(-1), { state: null, stale: false })

const expired = fixture()
expired.feed.start()
await expired.reply(0, 'parked')
await expired.advance(1500)
await expired.advance(4000)
assert.equal(expired.requests[1].options.signal.aborted, true)
assert.deepEqual(expired.states.at(-1), { state: 'parked', stale: true }, 'timeout retains only bounded last-known display')
await expired.reply(1, 'driving')
assert.equal(expired.states.at(-1).state, 'parked', 'late response cannot replace current state')
await expired.advance(2500)
assert.equal(expired.states.at(-1).state, null, 'repeated failure cannot indefinitely preserve last-known state')
expired.feed.stop()

const auth = fixture()
auth.feed.start()
await auth.reply(0, null, 401)
assert.equal(auth.revoked, 1)
assert.equal(auth.states.at(-1).state, null)
assert.equal(auth.timers.size, 0)

const previousDocument = globalThis.document
const listeners = new Map()
globalThis.document = { hidden: true, addEventListener: (key, fn) => listeners.set(key, fn),
  removeEventListener: (key) => listeners.delete(key) }
const page = { $data: { state: null }, unauthorized() {} }
DeviceState.created.call(page)
let requests = 0
page.feed.fetcher = () => { requests++; return new Promise(() => {}) }
DeviceState.mounted.call(page)
assert.equal(requests, 0)
document.hidden = false
listeners.get('visibilitychange')()
assert.equal(requests, 1)
document.hidden = true
listeners.get('visibilitychange')()
assert.equal(page.$data.state, null)
DeviceState.beforeUnmount.call(page)
assert.equal(listeners.size, 0)
globalThis.document = previousDocument
