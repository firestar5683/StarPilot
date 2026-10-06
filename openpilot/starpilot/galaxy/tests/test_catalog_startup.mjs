import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
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
const initialize = new Function("loadCatalog", "state", "authState", "auth", `${initializer}; return initialize`)(
  async () => { if (fail) throw new Error("offline"); return loaded }, state, authState,
  { async check() { checks++; authState.status = "authenticated" } },
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
const raced = new Function("loadCatalog", "state", "authState", "auth", `${initializer}; return initialize`)(
  () => new Promise(resolve => queued.push(resolve)), state, authState, { async check() {} },
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
