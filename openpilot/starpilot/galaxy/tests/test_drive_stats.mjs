import assert from "node:assert/strict"
import { DriveStatsFeed, validDriveStats } from "../web/js/drive-stats.js"

const route = { routeId: "2026-09-27--12-00-00", startTime: 1_790_509_200, endTime: 1_790_512_800,
  distanceMeters: 12000, durationSeconds: 3600, engagedSeconds: 2700, engagedPercent: 75,
  model: "Chestnut", distractedMoments: null, unresponsiveMoments: 0,
  complete: true, reason: null, segmentCount: 2, ignored: false }
const fixture = { schemaVersion: 1, isMetric: true, analysis: { running: false, pending: 0, failed: 0, scanIncomplete: false },
  totals: { distanceMeters: 12000, durationSeconds: 3600, engagedSeconds: 2700, drives: 1 },
  week: { days: Array.from({ length: 7 }, (_, i) => ({ date: `2026-09-${String(21 + i).padStart(2, "0")}`,
    distanceMeters: i === 6 ? 12000 : 0 })), distanceMeters: 12000, durationSeconds: 3600,
    engagedPercent: 75, drives: 1, timezone: "UTC" },
  lastDrive: route, recentDrives: [route], records: [{ id: "longestDrive", label: "Longest drive", value: 12000, unit: "m" }],
  models: [{ name: "Chestnut", distanceMeters: 12000, durationSeconds: 3600, drives: 1 }],
  coverage: { scope: "analyzedLocalRoutes", partialHistory: true } }
const response = (body) => ({ ok: true, status: 200, json: async () => body })
const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve() }

assert.equal(validDriveStats(fixture), true)
assert.equal(validDriveStats({ ...fixture, isMetric: null }), false)
assert.equal(validDriveStats({ ...fixture, week: { ...fixture.week, days: [] } }), false)
assert.equal(validDriveStats({ ...fixture, recentDrives: [{ ...route, ignored: "no" }] }), false)
assert.equal(validDriveStats({ ...fixture, totals: { ...fixture.totals, distanceMeters: NaN } }), false)
assert.equal(validDriveStats({ ...fixture, lastDrive: { ...route, routeId: "<script>" } }), false)

const updates = [], requests = [], timers = new Map()
let serial = 0
let ignored = false
const later = (fn, ms) => { const id = ++serial; timers.set(id, { fn, ms }); return id }
const cancelTimer = (id) => timers.delete(id)
const feed = new DriveStatsFeed({ publish: (state) => updates.push(state),
  fetcher: async (url, options) => {
    requests.push({ url, options })
    if (url.endsWith("ignore")) ignored = true
    return response(ignored ? { ...fixture, totals: { ...fixture.totals, drives: 0 },
      recentDrives: [{ ...route, ignored: true }] } : fixture)
  }, later, cancelTimer })
await feed.start()
assert.equal(feed.status, "ready")
assert.equal(feed.data.lastDrive.distractedMoments, null)
assert.deepEqual(requests.map((request) => request.url), ["./api/drives/stats?timezone=" + encodeURIComponent(Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC")])
assert.equal(requests[0].options.credentials, "same-origin")
assert.equal([...timers.values()].some((timer) => timer.ms === 60000), true)
await feed.ignore(route.routeId, true)
assert.deepEqual(JSON.parse(requests[1].options.body), { routeId: route.routeId, ignored: true })
assert.equal(feed.data.totals.drives, 0)
assert.equal(feed.data.recentDrives[0].ignored, true)
await feed.ignore(route.routeId, true)
assert.equal(requests.length, 3, "duplicate selection should not be sent")
assert.equal(requests[2].url, requests[0].url, "mutation refresh retains the viewer timezone")
feed.stop()
assert.equal(timers.size, 0)
assert.equal(feed.data, null)

const pending = []
let revoked = 0
const slow = new DriveStatsFeed({ publish: () => {}, unauthorized: () => { revoked++ },
  fetcher: (url, options) => new Promise((resolve) => pending.push({ url, options, resolve })), later, cancelTimer })
const loading = slow.start()
assert.equal(slow.status, "loading")
slow.stop()
assert.equal(pending[0].options.signal.aborted, true)
pending[0].resolve(response(fixture))
await loading
assert.equal(slow.data, null)
const waiting = slow.start()
pending[1].resolve({ ok: false, status: 401 })
await waiting
assert.equal(revoked, 1)
assert.equal(slow.active, false)

let failedRequest
const uncertain = new DriveStatsFeed({ publish: () => {},
  fetcher: (url, options) => url.includes("stats?") ? Promise.resolve(response(fixture)) :
    new Promise((resolve) => { failedRequest = { resolve, options } }), later, cancelTimer })
await uncertain.start()
const changing = uncertain.ignore(route.routeId, true)
const [deadlineId, deadline] = [...timers.entries()].find(([, timer]) => timer.ms === 5000)
assert.ok(deadline)
timers.delete(deadlineId)
deadline.fn()
assert.equal(failedRequest.options.signal.aborted, true)
assert.equal(uncertain.data.recentDrives[0].ignored, false, "timeout must not invent a saved change")
assert.match(uncertain.error, /timed out/)
failedRequest.resolve(response({ ...fixture, recentDrives: [{ ...route, ignored: true }] }))
await changing
assert.equal(uncertain.data.recentDrives[0].ignored, false, "late reply must not refill state")
uncertain.stop()
assert.equal(timers.size, 0)
assert.ok(updates.some((state) => state.status === "ready"))
await tick()
console.log("Galaxy drive statistics feed checks passed")
