import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { LocalHistoryFeed, LocalRecordingsPage, availableFiles, validLocalHistory, quickRoadUrl,
  segmentSummaryUrl, validSegmentSummary, routeFiles, firstQuickVideo, routeDate, connectRouteUrl } from '../web/js/record-history.js'

const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve() }
const current = '0000021e--371eaf116b'
const history = { schemaVersion: 1, source: 'local', partialHistory: true, scanIncomplete: true,
  routes: [{ routeId: current, segmentCount: 2, segments: [
    { number: 0, segmentName: `${current}--0`, files: { rlog: true, qlog: true, fcamera: true, dcamera: false, ecamera: false, qcamera: true } },
    { number: 2, segmentName: `${current}--2`, files: { rlog: false, qlog: true, fcamera: false, dcamera: true, ecamera: false, qcamera: true } },
  ] }] }
assert.equal(validLocalHistory(history), true)
assert.equal(validLocalHistory({ ...history, source: 'cloud' }), false)
assert.equal(validLocalHistory({ ...history, routes: [{ ...history.routes[0], routeId: '<script>' }] }), false)
assert.equal(validLocalHistory({ ...history, routes: [{ ...history.routes[0], segmentCount: 3 }] }), false)
assert.deepEqual(availableFiles(history.routes[0].segments[0].files), ['Full log', 'Quick log', 'Road video', 'Quick video'])
assert.equal(quickRoadUrl(`${current}--0`), `./api/recordings/media/${current}--0`)
assert.equal(quickRoadUrl('../qcamera.ts'), null)
assert.equal(segmentSummaryUrl(`${current}--0`), `./api/recordings/segment-summary?segmentName=${current}--0`)
assert.equal(segmentSummaryUrl('../rlog.zst'), null)
const summary = { schemaVersion: 1, source: 'closed_local_rlog', segmentName: `${current}--0`, sourceSha256: 'a'.repeat(64),
  observedCarSpanSeconds: 2, estimatedDistanceMeters: 15, observedLatActiveSeconds: 2,
  observedLongActiveSeconds: 1, gaps: { carState: 0, carControl: 0 }, sampleCoverageComplete: true }
assert.equal(validSegmentSummary(summary, `${current}--0`), true)
assert.equal(validSegmentSummary({ ...summary, observedLongActiveSeconds: -1 }, `${current}--0`), false)
assert.equal(validSegmentSummary(summary, `${current}--2`), false)
assert.match(LocalRecordingsPage.template, /Local recordings/)
assert.match(LocalRecordingsPage.template, /scan was incomplete/)
assert.doesNotMatch(LocalRecordingsPage.template, /v-html|deleteRoute/)
assert.match(LocalRecordingsPage.template, /<details class="gx-recordings__expand"><summary>/)
assert.doesNotMatch(LocalRecordingsPage.template, /<details[^>]*\sopen[\s=>]/)
assert.deepEqual(routeFiles(history.routes[0]), ['Full log', 'Quick log', 'Road video', 'Driver video', 'Quick video'])
assert.equal(firstQuickVideo(history.routes[0]).number, 0)
assert.equal(firstQuickVideo({ segments: [] }), null)
const dated = { ...history.routes[0], startTime: Date.parse('2026-09-28T01:30:00Z') / 1000, fileTime: 1 }
assert.match(routeDate(dated, 'en-US', 'America/Chicago').label, /Sep 27, 2026/)
assert.equal(routeDate(dated).source, '')
assert.equal(routeDate({ ...dated, startTime: null }, 'en-US', 'UTC').source, 'File date')
assert.equal(routeDate({ ...dated, startTime: '2026-09-28', fileTime: Infinity }).label, 'Date unavailable')
assert.equal(routeDate(history.routes[0]).datetime, null, 'legacy server data remains usable without an invented date')
const connected = { ...dated, connectUrl: `https://connect.comma.ai/abcdef0123456789/${current}` }
assert.equal(connectRouteUrl(connected), connected.connectUrl)
assert.equal(connectRouteUrl({ ...connected, routeId: `abcdef0123456789|${current}` }), connected.connectUrl)
for (const connectUrl of [`https://example.com/abcdef0123456789/${current}`, `${connected.connectUrl}?redirect=evil`,
  `https://connect.comma.ai/abcdef0123456789/wrong-route`, 'javascript:alert(1)', null]) {
  assert.equal(connectRouteUrl({ ...connected, connectUrl }), null)
}
assert.equal(connectRouteUrl({ ...connected, routeId: `0000000000000000|${current}` }), null)
const cards = LocalRecordingsPage.computed.routeCards.call({ data: { routes: [connected] } })
assert.equal(cards[0].connect, connected.connectUrl)
assert.equal(cards[0].firstQuick.number, 0)
assert.equal(cards[0].fileLabels.length, 5)
const app = readFileSync(new URL('../web/js/app.js', import.meta.url), 'utf8')
assert.match(app, /route\.path === '\/recordings'.*LocalRecordingsPage|LocalRecordingsPage v-else-if="route.path === '\/recordings'"/)

function fixture() {
  const requests = [], states = [], timers = new Map()
  let next = 0, revoked = 0
  const feed = new LocalHistoryFeed({ publish: (state) => states.push(state), unauthorized: () => revoked++,
    fetcher: (url, options) => new Promise((resolve) => requests.push({ url, options, resolve })),
    later: (fn, ms) => { timers.set(++next, { fn, ms }); return next }, cancelTimer: (id) => timers.delete(id) })
  async function reply(index, body, code = 200) {
    requests[index].resolve({ status: code, ok: code === 200, json: async () => body })
    await flush()
  }
  return { feed, requests, states, timers, reply, get revoked() { return revoked } }
}
const normal = fixture()
normal.feed.start()
assert.equal(normal.requests[0].url, './api/recordings/local')
assert.equal(normal.requests[0].options.credentials, 'same-origin')
await normal.reply(0, history)
assert.equal(normal.states.at(-1).status, 'ready')
assert.equal(normal.states.at(-1).data.routes[0].routeId, current)
assert.equal(normal.timers.size, 0)
await flush()
assert.equal(normal.requests.length, 1, 'no repeated scans without explicit refresh')
normal.feed.load()
assert.equal(normal.requests.length, 2)
await normal.reply(1, { ...history, scanIncomplete: false })
normal.feed.stop()
assert.equal(normal.states.at(-1).data, null)

const stale = fixture()
stale.feed.start()
stale.feed.stop()
stale.feed.start()
await stale.reply(1, history)
const count = stale.states.length
await stale.reply(0, { ...history, routes: [] })
assert.equal(stale.states.length, count)
assert.equal(stale.states.at(-1).data.routes.length, 1)

const revoked = fixture()
revoked.feed.start()
await revoked.reply(0, { code: 'setup_required' }, 503)
assert.equal(revoked.revoked, 1)
assert.equal(revoked.feed.data, null)
assert.equal(revoked.timers.size, 0)
const loggedOut = fixture()
loggedOut.feed.start()
await loggedOut.reply(0, {}, 401)
assert.equal(loggedOut.revoked, 1)
const unavailable = fixture()
unavailable.feed.start()
await unavailable.reply(0, { code: 'backend_unavailable' }, 503)
assert.equal(unavailable.revoked, 0)
assert.equal(unavailable.feed.status, 'unavailable')
const late = fixture()
late.feed.start()
let resolveBody
late.requests[0].resolve({ status: 200, ok: true, json: () => new Promise((resolve) => { resolveBody = resolve }) })
await flush()
late.feed.stop()
resolveBody(history)
await flush()
assert.equal(late.feed.data, null)

// A transport that ignores AbortSignal cannot strand the UI in loading.
const timedOut = fixture()
timedOut.feed.start()
assert.deepEqual([...timedOut.timers.values()].map((timer) => timer.ms), [4000])
const [timeoutId, timeout] = [...timedOut.timers.entries()][0]
timedOut.timers.delete(timeoutId)
timeout.fn()
assert.equal(timedOut.feed.status, 'unavailable')
assert.match(timedOut.feed.error, /timed out/)
timedOut.feed.load()
assert.equal(timedOut.requests.length, 2, 'manual refresh works after timeout')
await timedOut.reply(1, history)
await timedOut.reply(0, { ...history, routes: [] })
assert.equal(timedOut.feed.status, 'ready')
assert.equal(timedOut.feed.data.routes.length, 1)

const slowBody = fixture()
slowBody.feed.start()
let finishSlowBody
slowBody.requests[0].resolve({ status: 200, ok: true, json: () => new Promise((resolve) => { finishSlowBody = resolve }) })
await flush()
const [slowId, slowTimer] = [...slowBody.timers.entries()][0]
slowBody.timers.delete(slowId)
slowTimer.fn()
assert.equal(slowBody.feed.status, 'unavailable')
slowBody.feed.load()
await slowBody.reply(1, history)
finishSlowBody({ ...history, routes: [] })
await flush()
assert.equal(slowBody.feed.data.routes.length, 1, 'old body cannot replace refreshed inventory')

const priorDocument = globalThis.document
const listeners = new Map()
globalThis.document = { hidden: true, addEventListener: (name, cb) => listeners.set(name, cb),
  removeEventListener: (name, cb) => { if (listeners.get(name) === cb) listeners.delete(name) } }
const page = { mode: 'local', $data: { status: 'idle', data: null, error: '' }, $refs: {}, playerGeneration: 0,
  unauthorized() { throw new Error('revoked') } }
Object.assign(page, LocalRecordingsPage.methods)
LocalRecordingsPage.created.call(page)
const pending = []
page.feed.fetcher = (url, options) => new Promise((resolve) => pending.push({ url, options, resolve }))
LocalRecordingsPage.mounted.call(page)
assert.equal(pending.length, 0, 'hidden mount does not scan')
document.hidden = false
listeners.get('visibilitychange')()
assert.equal(pending.length, 1)
document.hidden = true
listeners.get('visibilitychange')()
assert.equal(page.$data.data, null)
LocalRecordingsPage.beforeUnmount.call(page)
assert.equal(listeners.size, 0)
globalThis.document = priorDocument

// A selected segment is immediately visible, and retired media errors cannot act on a new video.
const controls = LocalRecordingsPage.methods
const player = { mode: 'local', status: 'ready', playing: null, playerError: '', playerGeneration: 0,
  sessionProbe: null, $refs: {}, $nextTick(callback) { callback() }, unauthorized() { this.revoked = true } }
for (const [name, method] of Object.entries(controls)) player[name] = method
player.openPlayer(history.routes[0], history.routes[0].segments[0])
assert.equal(player.playing.segments.length, 2)
assert.equal(player.playing.index, 0)
player.chooseSegment(1)
assert.equal(player.playing.index, 1)
const oldVideo = {}
player.$refs.quickVideo = { dataset: { playerGeneration: String(player.playerGeneration) },
  pause() {}, removeAttribute() {}, load() {} }
const oldFetch = globalThis.fetch
let sessionRequest
globalThis.fetch = (_url, options) => new Promise((resolve) => { sessionRequest = { options, resolve } })
await player.videoError({ currentTarget: oldVideo })
assert.equal(sessionRequest, undefined, 'late error from retired element is ignored')
const active = player.$refs.quickVideo
active.dataset.playerGeneration = String(player.playerGeneration - 1)
await player.videoError({ currentTarget: active })
assert.equal(sessionRequest, undefined, 'retired generation on an old element is ignored')
active.dataset.playerGeneration = String(player.playerGeneration)
const checking = player.videoError({ currentTarget: active })
await flush()
assert.equal(sessionRequest.options.credentials, 'same-origin')
player.closePlayer()
assert.equal(sessionRequest.options.signal.aborted, true)
sessionRequest.resolve({ status: 401, json: async () => ({ authenticated: false }) })
await checking
assert.equal(player.revoked, undefined, 'retired session check cannot revoke reopened player')
player.openPlayer(history.routes[0], history.routes[0].segments[0])
player.$refs.quickVideo = { dataset: { playerGeneration: String(player.playerGeneration) },
  pause() {}, removeAttribute() {}, load() {} }
sessionRequest = undefined
const revokedVideo = player.videoError({ currentTarget: player.$refs.quickVideo })
await flush()
sessionRequest.resolve({ status: 401, json: async () => ({ authenticated: false }) })
await revokedVideo
assert.equal(player.playing, null)
assert.equal(player.revoked, true, 'current media auth loss clears playback and session')
player.mode = 'offline-preview'
sessionRequest = undefined
player.openPlayer(history.routes[0], history.routes[0].segments[0])
await player.videoError({ currentTarget: player.$refs.quickVideo })
assert.equal(player.playing, null, 'offline preview never opens a video')
assert.equal(sessionRequest, undefined, 'offline preview does not request media or session')
globalThis.fetch = oldFetch
assert.match(LocalRecordingsPage.template, /Quick Road Video/)
assert.match(LocalRecordingsPage.template, /@error="videoError\(\$event\)"/)
assert.match(LocalRecordingsPage.template, /Distance is estimated from recorded speed/)
assert.match(LocalRecordingsPage.template, /Steering active/)
assert.match(LocalRecordingsPage.template, /Longitudinal active/)

// The mounted page requests details only on selection; hide, timeout and late responses retire them.
const savedDocument = globalThis.document
const savedSetTimeout = globalThis.setTimeout
const savedClearTimeout = globalThis.clearTimeout
globalThis.document = { hidden: false }
const detailTimers = new Map()
let timerId = 0
globalThis.setTimeout = (callback, delay) => { detailTimers.set(++timerId, { callback, delay }); return timerId }
globalThis.clearTimeout = (id) => detailTimers.delete(id)
const detailsPage = { mode: 'local', status: 'ready', details: null, detailsName: null, detailsStatus: 'idle',
  detailsError: '', detailsGeneration: 0, $refs: {}, unauthorized() { this.revoked = true } }
for (const [name, method] of Object.entries(controls)) detailsPage[name] = method
const detailRequests = []
globalThis.fetch = (url, options) => new Promise((resolve) => detailRequests.push({ url, options, resolve }))
const segment = history.routes[0].segments[0]
const firstDetails = detailsPage.openDetails(segment)
assert.equal(detailRequests.length, 1)
assert.equal(detailRequests[0].options.credentials, 'same-origin')
assert.deepEqual([...detailTimers.values()].map((item) => item.delay), [10000])
detailsPage.closeDetails()
assert.equal(detailRequests[0].options.signal.aborted, true)
detailRequests[0].resolve({ status: 200, ok: true, json: async () => summary })
await firstDetails
assert.equal(detailsPage.details, null)
const timedDetails = detailsPage.openDetails(segment)
const detailTimeout = [...detailTimers.values()][0]
detailTimeout.callback()
assert.equal(detailsPage.detailsStatus, 'unavailable')
const freshDetails = detailsPage.openDetails(segment)
detailRequests[2].resolve({ status: 200, ok: true, json: async () => summary })
await freshDetails
detailRequests[1].resolve({ status: 200, ok: true, json: async () => ({ ...summary, estimatedDistanceMeters: 999 }) })
await timedDetails
assert.equal(detailsPage.details.estimatedDistanceMeters, 15)
const revokeDetails = detailsPage.openDetails(segment)
detailRequests[3].resolve({ status: 503, ok: false, json: async () => ({ code: 'setup_required' }) })
await revokeDetails
assert.equal(detailsPage.revoked, true)
assert.equal(detailsPage.details, null)
detailsPage.mode = 'offline-preview'
await detailsPage.openDetails(segment)
assert.equal(detailRequests.length, 4)
globalThis.fetch = oldFetch
globalThis.document = savedDocument
globalThis.setTimeout = savedSetTimeout
globalThis.clearTimeout = savedClearTimeout
