import assert from "node:assert/strict"
import { compile } from "../web/vendor/vue/vue.esm-browser.js"
import { OfflineRoadMapsPanel, OfflineRoadsClient, areaLabel, estimateArea, formatBytes, radiusLabel, radiusRange, toKm, validOffline } from "../web/js/offline-road-maps.js"
import { RasterMap } from "../web/js/navigation-map.js"
import { NavigationPage } from "../web/js/navigation.js"

const constants = { minRadiusKm: 2, maxRadiusKm: 200, defaultRadiusKm: 25, averageDownloadBytes: 38000, averageStoredBytes: 6500, maxAreas: 24 }
const area = { id: "a".repeat(32), name: "Las Vegas", latitude: 36.11, longitude: -115.17, radiusKm: 25, created: 1, refreshed: 0,
  progress: { state: "downloading", total: 400, done: 100, failed: 0 } }
const snapshot = (extra = {}) => ({ areas: [area], settings: { saveDriven: true }, position: { latitude: 36.1, longitude: -115.2 },
  service: { running: true, network: "wifi", failure: null, noSpace: false, hasKey: true },
  bytes: { saved: 5e6, driven: 2e6, cache: 1e6 }, limits: { saved: 3e9, driven: 6e8, cache: 1.5e8 },
  usage: { tiles: 1234, freeTiles: 200000 }, route: null, constants, ...extra })

assert.equal(validOffline(snapshot()), true)
assert.equal(validOffline(snapshot({ position: null })), true)
for (const bad of [{ areas: {} }, { settings: { saveDriven: "yes" } }, { position: { latitude: 99, longitude: 0 } },
  { areas: [{ ...area, id: "../x" }] }, { areas: [{ ...area, progress: { state: "exploded", total: 1, done: 0 } }] },
  { constants: { ...constants, maxAreas: "24" } }, { service: null }])
  assert.equal(validOffline(snapshot(bad)), false, JSON.stringify(bad))

// The same circle-of-tiles estimate as offline_roads.estimate (Python), e.g. 10 km at 36.1°N is 97 tiles.
assert.equal(estimateArea(36.1, 10, constants).tiles, 97)
assert.equal(estimateArea(36.1, 10, constants).downloadBytes, 97 * 38000)
assert.ok(estimateArea(60, 10, constants).tiles > estimateArea(0, 10, constants).tiles, "tiles shrink toward the poles")

assert.equal(formatBytes(0), "0 KB")
assert.equal(formatBytes(512 * 1024), "512 KB")
assert.equal(formatBytes(5.5 * 1024 ** 2), "5.5 MB")
assert.equal(formatBytes(3 * 1024 ** 3), "3.00 GB")
assert.equal(areaLabel(area), "Downloading · 25%")
assert.equal(areaLabel({ ...area, progress: null }), "Waiting for the downloader")
assert.equal(areaLabel({ ...area, progress: { state: "complete", total: 4, done: 4, failed: 0 } }), "Saved for offline")
assert.equal(areaLabel({ ...area, progress: { state: "incomplete", total: 4, done: 3, failed: 1 } }), "1 tiles missing · retries later")

// Imperial devices pick whole miles; areas are still saved in km within the device's limits.
assert.equal(radiusLabel(24.14, false), "15 mi")
assert.equal(radiusLabel(25, true), "25 km")
assert.deepEqual(radiusRange(constants, false), { min: 2, max: 124, initial: 15 })
assert.deepEqual(radiusRange(constants, true), { min: 2, max: 200, initial: 25 })
assert.equal(toKm(15, false), 24.1)
assert.ok(toKm(2, false) >= constants.minRadiusKm && toKm(124, false) <= constants.maxRadiusKm)
assert.equal(toKm(25, true), 25)

// Map: a coarser tile stands in while zooming, trackpad wheels step one level per gesture, redraws share a frame.
globalThis.ResizeObserver ??= class { observe() {} disconnect() {} }
const frames = []
globalThis.requestAnimationFrame = (fn) => { frames.push(fn); return frames.length }
globalThis.cancelAnimationFrame = () => {}
const listeners = {}
const canvas = { clientWidth: 400, clientHeight: 300, width: 0, height: 0, addEventListener: (name, fn) => { listeners[name] = fn },
  removeEventListener() {}, setPointerCapture() {}, getBoundingClientRect: () => ({ left: 0, top: 0, width: 400, height: 300 }),
  getContext: () => new Proxy({}, { get: (_, key) => key === "drawImage" ? (...args) => drawn.push(args) : () => {}, set: () => true }) }
const drawn = []
const map = new RasterMap(canvas)
map.load = () => {}
const parent = { close() {} }
map.tiles.set("11/600/800", parent)
const cover = map.placeholder(12, 1201, 1600)
assert.equal(cover[0], parent)
assert.deepEqual(cover.slice(1), [256, 0, 256], "the right quarter of the parent tile")
assert.equal(map.placeholder(12, 50, 50), null)
map.zoom = 3
let now = 1000
const realPerformance = globalThis.performance
globalThis.performance = { now: () => now }
for (let i = 0; i < 40; i++) listeners.wheel({ preventDefault() {}, deltaY: -12, deltaMode: 0 })
assert.equal(map.zoom, 4, "one trackpad flick is one zoom level, not ten")
now += 200
for (let i = 0; i < 9; i++) listeners.wheel({ preventDefault() {}, deltaY: -12, deltaMode: 0 })
assert.equal(map.zoom, 5)
globalThis.performance = realPerformance
frames.length = 0
map.requestDraw(); map.requestDraw(); map.requestDraw()
assert.equal(frames.length, 1, "pointer moves within a frame draw once")
let picked = null
map.onTap = point => { picked = point }
listeners.keydown({ key: "Enter", preventDefault() {} })
assert.deepEqual(picked, map.center, "keyboard users can select the map center")
map.close()

// Client: load, act, and hand 401s to the sign-in flow.
const requests = []
let reply = { status: 200, body: snapshot() }
const updates = []
const client = new OfflineRoadsClient({ publish: (update) => updates.push(update), later: () => 1, cancel() {},
  fetcher: async (url, options) => { requests.push({ url, method: options.method || "GET", body: options.body ? JSON.parse(options.body) : null })
    return { ok: reply.status < 400, status: reply.status, json: async () => reply.body } } })
await client.start()
assert.equal(requests[0].url, "./api/navigation/offline")
assert.deepEqual(updates.at(-1).data.areas.map((row) => row.name), ["Las Vegas"])
reply = { status: 200, body: snapshot({ areas: [] }) }
const result = await client.action({ action: "deleteArea", id: area.id })
assert.deepEqual(requests.at(-1), { url: "./api/navigation/offline", method: "POST", body: { action: "deleteArea", id: area.id } })
assert.deepEqual(result.areas, [])
assert.equal(updates.at(-1).busy, false)
reply = { status: 400, body: { error: "Choose a place and a radius between 2 and 200 km" } }
assert.equal(await client.action({ action: "addArea", area: {} }), null)
assert.equal(updates.at(-1).error, "Choose a place and a radius between 2 and 200 km")
reply = { status: 200, body: { areas: "nope" } }
await client.load()
assert.match(updates.at(-1).error, /unexpected answer/)
let signedOut = false
const guarded = new OfflineRoadsClient({ publish() {}, unauthorized: () => { signedOut = true }, later: () => 1, cancel() {},
  fetcher: async () => ({ ok: false, status: 401, json: async () => ({}) }) })
await guarded.start()
assert.equal(signedOut, true)
assert.equal(guarded.active, false)
client.stop()

// An older poll cannot undo a completed setting change, even if fetch ignores abort.
const pending = []
const racing = new OfflineRoadsClient({ publish() {}, later: () => 1, cancel() {},
  fetcher: () => new Promise(resolve => pending.push(resolve)) })
const oldPoll = racing.start()
const changed = racing.action({ action: "settings", patch: { saveDriven: false } })
const response = body => ({ ok: true, status: 200, json: async () => body })
pending[1](response(snapshot({ settings: { saveDriven: false } })))
await changed
pending[0](response(snapshot()))
await oldPoll
assert.equal(racing.data.settings.saveDriven, false)
const stoppedPoll = racing.load()
racing.stop()
pending[2](response(snapshot()))
await stoppedPoll
assert.equal(racing.data.settings.saveDriven, false, "stopped requests cannot publish")

let timeout
const stalled = new OfflineRoadsClient({ publish() {}, cancel() {}, later: (fn, ms) => { if (ms === 10000) timeout = fn; return 1 },
  fetcher: (_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener("abort", () => reject(new DOMException("Timed out", "AbortError")))) })
stalled.active = true
const timedOut = stalled.action({ action: "settings", patch: { saveDriven: true } })
timeout()
await timedOut
assert.equal(stalled.busy, false, "an unresponsive action releases the controls")
assert.ok(stalled.error)
stalled.stop()

// Templates compile with the real Vue compiler, and the Offline Maps tab shows both panels.
const decodeEntities = (value) => value.replaceAll("&amp;", "&")
compile(OfflineRoadMapsPanel.template, { decodeEntities })
compile(NavigationPage.template, { decodeEntities })
assert.ok(NavigationPage.template.includes("<OfflineRoadMapsPanel"))
assert.ok(NavigationPage.template.includes("<MapOperationsPanel"))
console.log("Offline road maps: validation, estimates, client actions, auth and templates passed")
