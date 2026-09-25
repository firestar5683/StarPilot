import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import { MonitorFeed } from "../web/js/monitor-feed.js"

const sample = JSON.parse(await readFile(new URL("../web/data/system-monitor.sample.json", import.meta.url)))
const local = { ...sample, mode: "local-runtime" }
const flush = async () => { for (let n = 0; n < 10; n++) await Promise.resolve() }

function fixture(mode = "local", ignoresAbort = false) {
  let now = 0, id = 0
  const timers = new Map(), requests = [], states = []
  const feed = new MonitorFeed({ mode, publish: (state) => states.push(state), clock: () => now,
    schedule: (fn, delay) => { const key = ++id; timers.set(key, { fn, time: now + delay }); return key },
    cancel: (key) => timers.delete(key),
    fetcher: (url, options) => new Promise((resolve, reject) => {
      requests.push({ url, resolve, reject, signal: options.signal })
      if (!ignoresAbort) options.signal.addEventListener("abort", () => reject(new Error("Aborted")))
    }),
  })
  return { feed, requests, states, timers,
    reply: async (raw = local, ok = true) => { requests.at(-1).resolve({ ok, json: async () => raw }); await flush() },
    advance: async (ms) => {
      now += ms
      for (const [key, timer] of [...timers]) if (timer.time <= now && timers.delete(key)) timer.fn()
      await flush()
    },
  }
}

// Real transport selection, first response, ordinary polling, no overlapping
// request and replacement of the old sample's deadline by the new one.
const live = fixture()
live.feed.start()
assert.equal(live.requests[0].url, "./api/system/monitor")
await live.reply()
assert.equal(live.states.at(-1).status, "current")
await live.advance(2000)
assert.equal(live.requests.length, 2)
live.feed.refresh()
assert.equal(live.requests.length, 2)
await live.reply()
await live.advance(2000)
assert.equal(live.states.at(-1).status, "current")
// Third request is outstanding; the previous sample expires at its original
// request-based deadline, rather than staying current until another reply.
await live.advance(2000)
assert.equal(live.states.at(-1).snapshot, null)
await live.advance(2000)
assert.equal(live.requests.at(-1).signal.aborted, true)
assert.equal(live.states.at(-1).status, "unavailable")
live.feed.stop()
assert.equal(live.timers.size, 0)

// A local source must never turn a synthetic sample into live state.
const wrong = fixture()
wrong.feed.start()
await wrong.reply(sample)
assert.equal(wrong.states.at(-1).snapshot, null)
wrong.feed.stop()

// Failed refresh drops previous values immediately, and unmount cancels work.
const failed = fixture()
failed.feed.start()
await failed.reply()
await failed.advance(2000)
await failed.reply({}, false)
assert.equal(failed.states.at(-1).snapshot, null)
await failed.advance(2000)
failed.feed.stop()
const before = failed.states.length
await failed.reply()
assert.equal(failed.states.length, before)
assert.equal(failed.timers.size, 0)

const preview = fixture("sample")
preview.feed.start()
assert.equal(preview.requests[0].url, "./data/system-monitor.sample.json")
await preview.reply(sample)
await preview.advance(20000)
assert.equal(preview.states.at(-1).status, "sample")
assert.equal(preview.requests.length, 1)
preview.feed.stop()

const stalled = fixture("local", true)
stalled.feed.start()
const abandoned = stalled.requests[0]
await stalled.advance(4000)
await stalled.advance(2000)
assert.equal(stalled.requests.length, 2)
await stalled.reply()
const count = stalled.states.length
abandoned.resolve({ ok: true, json: async () => local })
await flush()
assert.equal(stalled.states.length, count)
assert.equal(stalled.states.at(-1).status, "current")
stalled.feed.stop()
console.log("Monitor transport, source isolation, expiry, cancellation and failure checks passed")
