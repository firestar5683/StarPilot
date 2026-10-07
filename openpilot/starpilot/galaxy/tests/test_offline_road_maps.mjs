import assert from "node:assert/strict"
import { compile } from "../web/vendor/vue/vue.esm-browser.js"
import { OfflineRoadMapsPanel, OfflineRoadsClient, areaLabel, estimateArea, formatBytes, validOffline } from "../web/js/offline-road-maps.js"
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

// Templates compile with the real Vue compiler, and the Offline Maps tab shows both panels.
const decodeEntities = (value) => value.replaceAll("&amp;", "&")
compile(OfflineRoadMapsPanel.template, { decodeEntities })
compile(NavigationPage.template, { decodeEntities })
assert.ok(NavigationPage.template.includes("<OfflineRoadMapsPanel"))
assert.ok(NavigationPage.template.includes("<MapOperationsPanel"))
console.log("Offline road maps: validation, estimates, client actions, auth and templates passed")
