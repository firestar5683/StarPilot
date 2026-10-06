import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { LocalAuth } from "../web/js/auth-client.js"
import { SnapshotFeed } from "../web/js/snapshot-feed.js"
import { loadCatalog, requestJson } from "../web/js/startup.js"

const app = readFileSync(new URL("../web/js/app.js", import.meta.url), "utf8")
const catalog = JSON.parse(readFileSync(new URL("../web/data/catalog.json", import.meta.url), "utf8"))
const requested = []
const response = body => ({ ok: true, json: async () => body })
const fetcher = async path => {
  requested.push(path)
  return response(path === "./data/catalog.json" ? catalog : { schemaVersion: 1, monitor: "local" })
}
const loaded = await loadCatalog({ fetcher })
assert.deepEqual(requested, ["./data/catalog.json", "./data/runtime.json"])
assert.equal(loaded.mode, "local")
assert.ok(loaded.tools.some(tool => tool.path === "/galaxy" && tool.availability === "local-only"))
assert.deepEqual(loaded.tools.map(tool => tool.name), loaded.tools.map(tool => tool.name).sort((a, b) => a.localeCompare(b)))

for (const invalid of [null, {}, { mode: "offline-preview", tools: [{ path: "/logs", availability: "local-only", name: "Logs" }] }]) {
  await assert.rejects(loadCatalog({ fetcher: async path => response(path.includes("catalog") ? invalid :
    { schemaVersion: 1, monitor: "local" }) }), /Invalid Galaxy catalog/)
}
await assert.rejects(loadCatalog({ fetcher: async path => response(path.includes("catalog") ? catalog :
  { schemaVersion: 2, monitor: "local" }) }), /Invalid Galaxy runtime/)
await assert.rejects(requestJson("/test", { fetcher: async () => ({ ok: false }) }), /could not be reached/)

// Neither a stalled connection nor a stalled JSON body can strand startup.
for (const hangInBody of [false, true]) {
  let expire, signal, canceled
  const pending = requestJson("/test", {
    fetcher: async (_url, options) => {
      signal = options.signal
      return hangInBody ? { ok: true, json: () => new Promise(() => {}) } : new Promise(() => {})
    },
    later: fn => { expire = fn; return 42 }, cancel: id => { canceled = id },
  })
  expire()
  await assert.rejects(pending, /too long/)
  assert.equal(signal.aborted, true)
  assert.equal(canceled, 42)
}

// Exercise actual startup recovery and stale request ordering.
const initializer = app.slice(app.indexOf("let startupGeneration = 0"), app.lastIndexOf("initialize()"))
assert.ok(initializer.startsWith("let startupGeneration = 0"))
const state = { tools: [], loading: true, error: "", monitorMode: "sample" }
const authState = { status: "checking" }
let fail = true, checks = 0
const initialize = new Function("loadCatalog", "state", "authState", "auth", "document", `${initializer}; return initialize`)(
  async () => { if (fail) throw new Error("offline"); return loaded }, state, authState,
  { async check() { checks++; authState.status = "authenticated" } }, { hidden: false },
)
await initialize()
assert.match(state.error, /could not connect/)
assert.equal(state.loading, false)
fail = false
await initialize()
assert.equal(state.error, "")
assert.equal(state.loading, false)
assert.equal(checks, 1)
assert.equal(authState.status, "authenticated")

const queued = []
const raced = new Function("loadCatalog", "state", "authState", "auth", "document", `${initializer}; return initialize`)(
  () => new Promise(resolve => queued.push(resolve)), state, authState, { async check() {} }, { hidden: false },
)
const old = raced(), current = raced()
queued[0]({ tools: [], mode: "sample" })
await old
assert.equal(state.loading, false) // Existing tools remain mounted during a reconnect.
queued[1](loaded)
await current
assert.equal(state.loading, false)
assert.equal(state.monitorMode, "local")
assert.equal(state.tools, loaded.tools)

// The actual app expiry callback must re-enter the same reconnect owner as boot.
const expiryBody = app.match(/sessionExpired\(\) \{ ([^\n]+) \},/)[1]
const timers = new Map()
let timerId = 0, sessionChecks = 0
const transientState = { tools: loaded.tools, error: "", monitorMode: "local" }
const transientAuth = { status: "authenticated" }
const visibility = { hidden: false, removeEventListener() {} }
const sessionAuth = new LocalAuth({
  publish: update => Object.assign(transientAuth, update),
  fetcher: async () => {
    sessionChecks++
    return sessionChecks === 1 ? { ok: false, status: 503, json: async () => ({}) } :
      response({ state: "configured", authenticated: true, localAccess: true })
  },
})
const unmountBody = app.match(/  beforeUnmount\(\) \{([\s\S]*?)\n  \},/)[1]
const harness = new Function("loadCatalog", "state", "authState", "auth", "document", "setTimeout", "clearTimeout",
  `${initializer}; return { expire() { ${expiryBody} }, initialize, stop() { ${unmountBody} } }`)(
    async () => loaded, transientState, transientAuth, sessionAuth, visibility,
    (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id }, id => timers.delete(id),
  )
const expiredFeed = new SnapshotFeed({ publish: () => {}, unauthorized: () => harness.expire(),
  fetcher: async () => ({ ok: false, status: 401 }) })
await expiredFeed.start()
await new Promise(resolve => setImmediate(resolve))
assert.equal(transientAuth.status, "unavailable")
assert.equal([...timers.values()].filter(timer => timer.delay === 3000).length, 1)
const retry = [...timers.entries()].find(([, timer]) => timer.delay === 3000)
timers.delete(retry[0]); await retry[1].fn()
await new Promise(resolve => setImmediate(resolve))
assert.equal(transientAuth.status, "authenticated")
assert.equal(sessionChecks, 2)
assert.equal(timers.size, 0)
class ReadyFeed extends SnapshotFeed { static interval = 0; static valid = value => value.ready === true }
const readyFeed = new ReadyFeed({ publish: () => {}, fetcher: async () => response({ ready: true }) })
await readyFeed.start()
assert.equal(readyFeed.status, "ready")
readyFeed.stop()
sessionChecks = 0
const unavailableFeed = new SnapshotFeed({ publish: () => {}, unauthorized: () => harness.expire(),
  fetcher: async () => ({ ok: false, status: 503, json: async () => ({ code: "access_unavailable" }) }) })
await unavailableFeed.start()
await new Promise(resolve => setImmediate(resolve))
assert.equal(transientAuth.status, "unavailable")
const unavailableRetry = [...timers.entries()].find(([, timer]) => timer.delay === 3000)
timers.delete(unavailableRetry[0]); await unavailableRetry[1].fn()
await new Promise(resolve => setImmediate(resolve))
assert.equal(transientAuth.status, "authenticated")
// Old feeds can report unauthorized concurrently while one real auth check is pending.
let settleSession
let deferredChecks = 0
sessionAuth.fetcher = () => { deferredChecks++; return new Promise(resolve => { settleSession = resolve }) }
harness.expire()
await new Promise(resolve => setImmediate(resolve))
const checkingGeneration = sessionAuth.generation
harness.expire()
assert.equal(sessionAuth.generation, checkingGeneration)
assert.equal(deferredChecks, 1)
settleSession(response({ state: "configured", authenticated: true, localAccess: true }))
await new Promise(resolve => setImmediate(resolve))
assert.equal(transientAuth.status, "authenticated")
sessionAuth.fetcher = async () => {
  sessionChecks++
  return sessionChecks === 1 ? { ok: false, status: 503, json: async () => ({}) } :
    response({ state: "configured", authenticated: true, localAccess: true })
}
// A queued retry cannot undo an explicit logout, nor run while hidden or stopped.
transientAuth.status = "unavailable"
sessionChecks = 0
await harness.initialize()
transientAuth.status = "login"
const loggedOutRetry = [...timers.entries()].find(([, timer]) => timer.delay === 3000)
timers.delete(loggedOutRetry[0]); await loggedOutRetry[1].fn()
assert.equal(sessionChecks, 1)
visibility.hidden = true
await harness.initialize()
assert.equal([...timers.values()].filter(timer => timer.delay === 3000).length, 0)
harness.stop()
visibility.hidden = false
await harness.initialize()
assert.equal([...timers.values()].filter(timer => timer.delay === 3000).length, 0)
