import assert from "node:assert/strict"
import { PollTimer } from "../web/js/polling.js"

const timers = new Map()
let next = 0, reads = 0, finish
const poller = new PollTimer({ read: () => { reads++; return new Promise(resolve => { finish = resolve }) },
  later: fn => { timers.set(++next, fn); return next }, cancel: id => timers.delete(id) })
poller.start()
const retired = [...timers.values()][0]
poller.stop(); poller.start()
await retired()
assert.equal(reads, 0, "a retired callback must not read after restart")
const [id, tick] = [...timers.entries()][0]
timers.delete(id)
const running = tick()
assert.equal(reads, 1)
assert.equal(timers.size, 0, "polls do not overlap an outstanding read")
poller.stop(); poller.start()
finish(); await running
assert.equal(timers.size, 1, "a retired read must not create another polling loop")
poller.stop()
assert.equal(timers.size, 0)
console.log("Polling lifecycle: stale callbacks, single flight and stop/restart passed")
