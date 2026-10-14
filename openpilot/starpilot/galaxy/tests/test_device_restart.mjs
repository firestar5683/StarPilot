import assert from "node:assert/strict"
import { DeviceRestartWatch } from "../web/js/device-restart.js"

const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve() }
function fixture({ paused = false } = {}) {
  const timers = new Map(), requests = []
  let nextTimer = 0, reloads = 0
  const watch = new DeviceRestartWatch({ hidden: () => false, paused: () => paused,
    request: () => new Promise((resolve, reject) => requests.push({ resolve, reject })),
    later: fn => { const id = ++nextTimer; timers.set(id, fn); return id },
    cancel: id => timers.delete(id), reload: () => reloads++ })
  return { watch, timers, requests, tick() { const [id, fn] = timers.entries().next().value; timers.delete(id); fn() }, get reloads() { return reloads } }
}

const preview = fixture()
preview.watch.track(null)
assert.equal(preview.timers.size, 0)

const blip = fixture()
blip.watch.track("one")
blip.tick()
blip.requests[0].reject(new TypeError("offline"))
await flush()
blip.tick()
blip.requests[1].resolve({ schemaVersion: 1, monitor: "local", instance: "one" })
await flush()
assert.equal(blip.reloads, 0)
assert.equal(blip.timers.size, 1)

const reboot = fixture()
reboot.watch.track("one")
reboot.tick()
reboot.requests[0].reject(new TypeError("offline"))
await flush()
reboot.tick()
reboot.requests[1].resolve({ schemaVersion: 1, monitor: "local", instance: "two" })
await flush()
assert.equal(reboot.reloads, 1)
assert.equal(reboot.timers.size, 0)

const startup = fixture()
startup.watch.track("one")
startup.watch.track("two")
assert.equal(startup.reloads, 1)

const woken = fixture()
woken.watch.track("one")
woken.watch.wake()
assert.equal(woken.requests.length, 1)
assert.equal(woken.timers.size, 0)

const updating = fixture({ paused: true })
updating.watch.track("one")
updating.watch.track("two")
assert.equal(updating.reloads, 0)
