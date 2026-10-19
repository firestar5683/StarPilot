import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { compile } from "../web/vendor/vue/vue.esm-browser.js"
import { FlmPage } from "../web/js/flm.js"
import { SURFACE_NAMES, PID_UNSUPPORTED, fullCoordinates, surfaceRows, validTrainingResults, coordinateText } from "../web/js/flm-training-results.js"

const report = () => ({ version: 1, history: [], current: { fresh: true, ageSeconds: .1, enabled: true,
  status: "collecting", reason: "capturing_steering_evidence", progress: { samples: 120, blocks: 3, requiredBlocks: 16 },
  fit: null, application: { applied: false, reason: "no_current_controller_application" }, details: {} } })
const map = amount => SURFACE_NAMES.map((name, i) => [name, i === 0 ? amount : 0])
assert.equal(SURFACE_NAMES.length, 30)
assert.equal(new Set(SURFACE_NAMES).size, 30)
assert.equal(PID_UNSUPPORTED.length, 4)
const source = readFileSync(new URL("../../flm/canonical_surface_adapter.py", import.meta.url), "utf8")
for (const name of SURFACE_NAMES) assert(source.includes("'" + name + "'"))
const pid = readFileSync(new URL("../../flm/pid_stages.py", import.meta.url), "utf8")
for (const name of PID_UNSUPPORTED) assert(pid.includes("'" + name + "'"))
assert.equal(surfaceRows(null).length, 30)
assert(surfaceRows(null).every(row => row.baseline === 0 && row.learned === null && row.applied === null))
const value = report()
value.current.details["Full surface coordinates"] = map(.005)
value.current.details["Actual full surface coordinates"] = map(.002)
assert(validTrainingResults(value))
// The real producer's two canonical30 maps must cross the wire validator.
for (const key of ["Full surface coordinates", "Actual full surface coordinates"]) {
  const accepted = report(); accepted.current.details[key] = map(.005)
  assert(validTrainingResults(accepted), key)
  const repeated = map(.005); repeated[1] = repeated[0]
  const unknown = map(.005); unknown[0] = ["unknown", 0]
  const extraCell = map(.005); extraCell[0] = [...extraCell[0], 0]
  for (const invalid of [null, {}, map(.3), map(Infinity), map(NaN), map(true), map("0"),
    map(.005).reverse(), map(.005).slice(1), [...map(.005), ["unknown", 0]], repeated, unknown, extraCell]) {
    const malformed = report(); malformed.current.details[key] = invalid
    assert.equal(validTrainingResults(malformed), false, key)
  }
}
// No broad array relaxation, key aliases, or nested canonical escape hatch.
for (const [key, item] of [["Other details", Array(17).fill(0)],
  ["Full surface coordinates ", map(.005)], ["Actual full surface coordinates", Array(16).fill(["ff_gain_left", 0])],
  ["Other details", { "Full surface coordinates": map(.005) }]]) {
  const oversized = report(); oversized.current.details[key] = item
  assert.equal(validTrainingResults(oversized), false, key)
}
const ordinary = report(); ordinary.current.details["Other details"] = Array(16).fill(0)
assert(validTrainingResults(ordinary))
assert.equal(surfaceRows(value, true)[0].learned, .005)
assert.equal(surfaceRows(value, true)[0].applied, null)
value.current.application.applied = true
assert.equal(surfaceRows(value, true)[0].applied, .002)
assert.equal(surfaceRows(value, false)[0].applied, null)
for (const rows of [map(.3), map(NaN), map(true), map(.005).reverse(), map(.005).slice(1), [...map(.005), ["unknown", 0]]]) assert.equal(fullCoordinates(rows), null)
const duplicate = map(.005); duplicate[1] = duplicate[0]
assert.equal(fullCoordinates(duplicate), null)
assert.equal(coordinateText(null), "Not reported")
assert.equal(coordinateText(.005), "+0.005")
compile(FlmPage.template, { decodeEntities: value => value.replaceAll("&amp;", "&") })
assert.doesNotMatch(FlmPage.template, /v-html|Analyze selected|GM Trial|Choose Full Logs/)
assert.match(FlmPage.template, /Currently applied/)
assert.match(FlmPage.template, /PID unsupported/)
const app = readFileSync(new URL("../web/js/app.js", import.meta.url), "utf8")
assert(app.includes("['/tuning', '/tuning/plots'].includes(route.path)"))
assert.doesNotMatch(app, /Recorded-drive analysis/)
const settings = readFileSync(new URL("../web/js/settings.js", import.meta.url), "utf8")
assert.doesNotMatch(settings, /FLMTrainingResults|View FLM training results/)
const catalog = JSON.parse(readFileSync(new URL("../web/data/catalog.json", import.meta.url), "utf8"))
assert(catalog.tools.some(tool => tool.path === "/tuning/plots"))
assert(catalog.tools.some(tool => tool.path === "/tuning/flm"))
const route = readFileSync(new URL("../web/js/route-workspace.js", import.meta.url), "utf8")
assert.doesNotMatch(route, /Analyze driving logs/)

function instance() {
  const vm = { ...FlmPage.data(), activePage: true, mode: "local", unauthorized: () => vm.auth++, auth: 0,
    feed: { stop() {} }, poller: { stop() {} } }
  for (const [name, method] of Object.entries(FlmPage.methods)) vm[name] = method.bind(vm)
  for (const [name, method] of Object.entries(FlmPage.computed)) Object.defineProperty(vm, name, { get: () => method.call(vm) })
  return vm
}
const originalFetch = globalThis.fetch, originalDocument = globalThis.document
try {
  globalThis.document = { hidden: false, removeEventListener() {} }
  const calls = []
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return { ok: true, json: async () => value } }
  const vm = instance(); await vm.load()
  assert.equal(calls[0].url, "./api/flm/training-results")
  assert.equal(calls[0].options.method, undefined)
  assert.equal(calls[0].options.cache, "no-store")
  assert.equal(calls[0].options.credentials, "same-origin")
  assert(vm.currentApplied)
  vm.now = vm.receivedAt + 2100
  assert(!vm.currentApplied)
  assert(vm.rows.every(row => row.applied === null))
  globalThis.fetch = async () => { throw new TypeError("offline") }
  await vm.load(); assert(!vm.currentApplied); assert.equal(vm.report, value)
  globalThis.fetch = async () => ({ ok: false, status: 401, json: async () => ({ error: "Sign in" }) })
  await vm.load(); assert.equal(vm.auth, 1)
  let resolve
  globalThis.fetch = () => new Promise(done => { resolve = done })
  const closed = instance(), pending = closed.load()
  FlmPage.beforeUnmount.call(closed)
  resolve({ ok: true, json: async () => value }); await pending
  assert.equal(closed.report, null)
  clearTimeout(vm.freshnessTimer)
} finally { globalThis.fetch = originalFetch; globalThis.document = originalDocument }
console.log("Auto Learn canonical routing, exact full30 data, missing/stale application, auth and cancellation contracts passed")
