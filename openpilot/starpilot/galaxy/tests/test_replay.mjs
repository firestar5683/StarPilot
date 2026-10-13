import assert from 'node:assert/strict'
import { ReplayClient, ReplayViewer, replayableSegment, validReplayStatus, replayTime, replayBufferTime, replaySeekPosition, replaySeekGaps } from '../web/js/replay.js'

const ownerId = '1'.repeat(32), sessionId = '2'.repeat(32), clientId = '3'.repeat(32)
const status = { schemaVersion: 1, ownerId, sessionId, state: 'playing', revision: 3, epoch: 2,
  position: 12, start: 0, end: 60, rate: 1, paused: false, offroad: true, owned: true, codec: null, sourceWarnings: [] }
assert.equal(validReplayStatus(status), true)
const idle = { ...status, state: "idle", sessionId: null, owned: false }
delete idle.codec
assert.equal(validReplayStatus(idle), true, "idle and another viewer legitimately omit codec")
for (const change of [{ position: Infinity }, { end: -1 }, { rate: 4 }, { ownerId: '../owner' }, { epoch: -1 }, { offroad: undefined }, { state: 'invented' }]) {
  assert.equal(validReplayStatus({ ...status, ...change }), false)
}
assert.equal(replayTime(65), '1:05')
assert.match(ReplayViewer.template, /<video/)
assert.doesNotMatch(ReplayViewer.template, /<img|takeover|recordings\/media/)

const video = { pause() {}, play: () => Promise.resolve(), removeAttribute() {}, load() {}, currentTime: 0 }
const updates = [], requests = [], timers = new Map()
let nextTimer = 0, unauthorized = 0
const client = new ReplayClient({ clientId, video: () => video, unauthorized: () => unauthorized++, publish: value => updates.push(value),
  later: (fn, ms) => { timers.set(++nextTimer, { fn, ms }); return nextTimer }, cancelTimer: id => timers.delete(id),
  fetcher: async (url, options) => {
    requests.push({ url, options })
    return { ok: true, status: 200, json: async () => status }
  } })
client.active = true
client.status = status
client.ownedSession = sessionId
client.receive({ ...status, revision: 2, epoch: 1 })
assert.equal(client.status.epoch, 2, 'late status cannot restore an earlier seek epoch')
client.busy = true
await client.stop()
assert.match(requests[0].url, /\/stop$/)
assert.equal(JSON.parse(requests[0].options.body).sessionId, sessionId, 'Stop remains available during another action')

class Buffer extends EventTarget {
  appendBuffer() {}
  remove() {}
}
client.buffer = new Buffer()
const pending = client.append(new Uint8Array([1]), client.mediaGeneration)
client.retireMedia()
await assert.rejects(pending, /decode/)
assert.equal(client.buffer, null, 'retirement releases even a stalled decoder append')
assert.equal(client.source, null)
client.ownedSession = sessionId
client.receive({ ...status, offroad: false, revision: 4 })
assert.equal(client.source, null, "loss of live offroad evidence retires browser media immediately")

client.buffer = new Buffer()
const removed = client.updateBuffer(buffer => buffer.remove(0, 1), client.mediaGeneration)
client.retireMedia()
await assert.rejects(removed, /decode/)

client.close(false)
const revoked = new ReplayClient({ clientId, video: () => video, unauthorized: () => unauthorized++, publish() {},
  later: () => 1, cancelTimer() {}, fetcher: async () => ({ ok: false, status: 401, json: async () => ({ error: 'Sign in' }) }) })
revoked.active = true
await revoked.refresh()
assert.equal(unauthorized, 1)
assert.equal(revoked.active, false)
assert.equal(revoked.source, null)
console.log('Replay: validated state, stale epoch rejection, busy Stop, stalled MSE retirement and auth loss passed')

// An old SourceBuffer callback cannot start a retired epoch, and oversized media
// is rejected before reading its body into memory.
const originalSource = globalThis.MediaSource
class Source extends EventTarget {
  static isTypeSupported() { return true }
  addSourceBuffer() { return new Buffer() }
}
globalThis.MediaSource = Source
let bodyReads = 0
const mediaRequests = []
const mediaClient = new ReplayClient({ clientId, video: () => video, unauthorized() {}, publish() {},
  mediaSource: () => new Source(), createURL: () => 'blob:replay', revokeURL() {},
  later: () => 1, cancelTimer() {}, fetcher: async (url) => {
    mediaRequests.push(url)
    return { ok: true, status: 200, headers: new Headers({ 'Content-Type': 'video/mp4',
      'Content-Length': String(1024 * 1024 + 1), 'X-Replay-Epoch': '2', 'X-Replay-Next-Sequence': '1' }),
      arrayBuffer: async () => { bodyReads++; return new ArrayBuffer(0) } }
  } })
mediaClient.active = true
mediaClient.status = status
mediaClient.ownedSession = sessionId
mediaClient.beginMedia({ ...status, epoch: 1, codec: 'avc1.42E01F' })
const oldSource = mediaClient.source
mediaClient.beginMedia({ ...status, codec: 'avc1.42E01F' })
oldSource.dispatchEvent(new Event('sourceopen'))
assert.equal(mediaRequests.length, 0)
mediaClient.source.dispatchEvent(new Event('sourceopen'))
for (let i = 0; i < 8; i++) await Promise.resolve()
assert.equal(mediaRequests.length, 1)
assert.match(mediaRequests[0], /epoch=2/)
assert.equal(bodyReads, 0)
assert.equal(mediaClient.source, null)
assert.match(mediaClient.error, /budget/)
mediaClient.close(false)
console.log('Replay MSE: retired sourceopen ignored and oversized fragment rejected before body allocation passed')

// Closing while Start is in flight must stop a late accepted session instead
// of losing its identity when the component retires the request.
let acceptStart
const cancellationRequests = []
const canceledStart = new ReplayClient({ clientId, video: () => video, unauthorized() {}, publish() {},
  later: () => 1, cancelTimer() {}, fetcher: (url, options) => {
    cancellationRequests.push({ url, options })
    return url.endsWith('/start') ? new Promise(resolve => { acceptStart = resolve }) : Promise.resolve({ ok: true, status: 200 })
  } })
canceledStart.active = true; canceledStart.status = status; canceledStart.routeId = 'route'
const starting = canceledStart.start()
canceledStart.close()
acceptStart({ ok: true, status: 200, json: async () => status })
await starting
assert.equal(cancellationRequests.length, 2)
assert.match(cancellationRequests[1].url, /\/stop$/)
assert.equal(JSON.parse(cancellationRequests[1].options.body).sessionId, sessionId)
assert.equal(canceledStart.ownedSession, null)
console.log('Replay: closing during Start stops a late accepted session passed')

const acknowledgments = []
const controlClient = new ReplayClient({ clientId, video: () => video, unauthorized() {}, publish() {},
  later: () => 1, cancelTimer() {}, fetcher: async (_url, options) => {
    acknowledgments.push(JSON.parse(options.body))
    return { ok: true, status: 200, json: async () => ({ ...status, revision: 4, lastRequestId: 'old' }) }
  } })
controlClient.active = true; controlClient.status = status; controlClient.ownedSession = sessionId
await controlClient.control('pause', true)
assert.equal(controlClient.busy, true, 'accepted control waits for the engine acknowledgement')
controlClient.receive({ ...status, revision: 4, paused: true, lastRequestId: acknowledgments[0].requestId })
assert.equal(controlClient.busy, false)
controlClient.buffer = new Buffer()
controlClient.source = new Source()
controlClient.receive({ ...status, revision: 5, state: 'seeking', mediaReady: false })
assert.equal(controlClient.source, null, 'accepted seek removes the old video before the next epoch arrives')
controlClient.close(false)
console.log('Replay: pending control acknowledgement and immediate seek media retirement passed')

controlClient.active = true; controlClient.startAttempted = true; controlClient.routeId = 'test-route'; controlClient.ownedSession = null
controlClient.status = { ...status, revision: 5 }
controlClient.receive({ ...status, revision: 6, routeId: 'test-route', owned: true })
assert.equal(controlClient.ownedSession, sessionId, 'status reconciles a lost accepted Start response for this exact viewer and route')
controlClient.receive({ ...status, revision: 7, state: 'ended', paused: true, routeId: 'test-route' })
assert.equal(controlClient.ownedSession, sessionId)
assert.equal(ReplayViewer.computed.playing.call({ client: controlClient, replay: controlClient.status }), true, 'ended replay keeps seek and Stop controls')
assert.match(ReplayViewer.template, /Return to start/)
controlClient.close(false)
console.log('Replay: uncertain Start reconciled and ended session stays seekable passed')

const pausedRanges = { length: 3, start: i => [0, .5, 1][i], end: i => [.05, .55, 1.05][i] }
assert.equal(replayBufferTime(pausedRanges), 1, 'paused sparse frames choose a real sample rather than the gap before it')
const resumedRange = { length: 1, start: () => 10, end: () => 11 }
assert.equal(replayBufferTime(resumedRange), 10.8, 'continuous playback retains bounded live lag')
console.log('Replay: sparse paused buffered ranges choose a decodable timestamp passed')

assert.equal(replayBufferTime(resumedRange, true), 10.999, 'Pause displays the final composed sample instead of consumer lag')

const gapped = { ...status, seekRanges: [[2, 10], [20, 40], [50, 58]] }
assert.equal(validReplayStatus(gapped), true)
for (const ranges of [[[0, 70]], [[10, 2]], [[0, 20], [10, 30]], [[0, NaN]], 'invalid']) {
  assert.equal(validReplayStatus({ ...status, seekRanges: ranges }), false)
}
assert.equal(replaySeekPosition(gapped, 16), 20)
assert.equal(replaySeekPosition(gapped, 12), 10)
assert.equal(replaySeekPosition(gapped, 15), 10, 'equal distances choose the earlier boundary')
assert.equal(replaySeekPosition(gapped, -1), 2)
assert.equal(replaySeekPosition(gapped, 80), 58)
assert.equal(replaySeekPosition(gapped, 30), 30)
assert.deepEqual(replaySeekGaps(gapped), [[0, 2], [10, 20], [40, 50], [58, 60]])
assert.deepEqual(replaySeekGaps({ ...status, seekRanges: [] }), [])
assert.match(ReplayViewer.template, /Missing recordings:/)
const rejectedSeek = new ReplayClient({ clientId, video: () => video, unauthorized() {}, publish() {},
  later: () => 1, cancelTimer() {}, fetcher: async (url, options) => {
    if (options.method === 'POST') {
      assert.equal(JSON.parse(options.body).position, 20, 'all client seek actions clamp through recorded ranges')
      return { ok: false, status: 409, json: async () => ({ code: 'invalid_position', error: 'Recording changed' }) }
    }
    return { ok: true, status: 200, json: async () => gapped }
  } })
rejectedSeek.active = true; rejectedSeek.status = gapped; rejectedSeek.ownedSession = sessionId
const existingVideo = rejectedSeek.source = {}
await rejectedSeek.control('seek', 16)
assert.equal(rejectedSeek.source, existingVideo, 'rejected seek keeps the previous playable video')
assert.equal(rejectedSeek.busy, false)
assert.equal(rejectedSeek.ownedSession, sessionId)
rejectedSeek.close(false)
console.log('Replay: recorded seek gaps clamp, display, and rejected seek recovery passed')
globalThis.MediaSource = originalSource

// Opening the selected route is the only launch step; polling must not restart it.
globalThis.MediaSource = Source
try {
  for (const [offroad, playable, state, expected] of [[true, true, 'idle', 1], [false, true, 'idle', 0],
    [true, false, 'idle', 0], [true, true, 'playing', 0]]) {
    const launched = []
    const automatic = new ReplayClient({ clientId, video: () => video, unauthorized() {}, publish() {},
      later: () => 1, cancelTimer() {}, fetcher: async (url, options) => {
        if (url.includes('/detail?')) return { ok: true, status: 200, json: async () => ({ playable }) }
        if (url.endsWith('/start')) launched.push(JSON.parse(options.body))
        return { ok: true, status: 200, json: async () => ({ ...idle, offroad, state }) }
      } })
    await automatic.open('selected-route')
    await automatic.refresh()
    assert.equal(launched.length, expected, 'auto-start requires playable, parked, idle replay and runs once')
    if (expected) assert.equal(launched[0].routeId, 'selected-route')
    automatic.close(false)
  }
  for (const segment of [null, 0, 2]) {
    const starts = []
    const selected = new ReplayClient({ clientId, video: () => video, unauthorized() {}, publish() {},
      later: () => 1, cancelTimer() {}, fetcher: async (url, options) => {
        if (url.includes('/detail?')) return { ok: true, status: 200, json: async () => ({ playable: true }) }
        if (url.endsWith('/start')) starts.push(JSON.parse(options.body))
        return { ok: true, status: 200, json: async () => idle }
      } })
    await selected.open('selected-route', segment)
    assert.equal(starts.length, 1)
    if (segment === null) assert.equal(Object.hasOwn(starts[0], 'segment'), false)
    else assert.equal(starts[0].segment, segment, 'exact segment numbers, including zero, reach the shared owner')
    selected.close(false)
  }
  let finishDetail
  const closed = new ReplayClient({ clientId, video: () => video, unauthorized() {}, publish() {},
    later: () => 1, cancelTimer() {}, fetcher: url => url.includes('/detail?') ? new Promise(resolve => { finishDetail = resolve }) :
      Promise.resolve({ ok: true, status: 200, json: async () => idle }) })
  let starts = 0
  closed.start = () => starts++
  const opening = closed.open('selected-route')
  closed.close()
  finishDetail({ ok: true, status: 200, json: async () => ({ playable: true }) })
  await opening
  assert.equal(starts, 0, 'closing during availability checks cannot launch replay')
  let finishStatus, statusReads = 0
  const retried = new ReplayClient({ clientId, video: () => video, unauthorized() {}, publish() {},
    later: () => 1, cancelTimer() {}, fetcher: url => {
      if (url.includes('/status?') && ++statusReads === 1) return new Promise(resolve => { finishStatus = resolve })
      return Promise.resolve({ ok: true, status: 200, json: async () => url.includes('/detail?') ? { playable: true } : idle })
    } })
  const launches = []
  retried.start = () => launches.push(retried.routeId)
  const firstOpen = retried.open('old-route')
  await retried.open('new-route')
  finishStatus({ ok: true, status: 200, json: async () => idle })
  await firstOpen
  assert.deepEqual(launches, ['new-route'], 'reopening during an old status request launches only the new route')
  retried.close(false)
} finally { globalThis.MediaSource = originalSource }
assert.doesNotMatch(ReplayViewer.template, />Replay route<|>Refresh status</)
assert.match(ReplayViewer.template, /ref="player"[\s\S]*gx-replay__media-controls/)
console.log('Replay: automatic launch, parked/playable/busy guards and close-during-open passed')

const selectedRates = []
const speedControl = { client: { control: (action, value) => selectedRates.push([action, value]) }, replay: { rate: .5 } }
for (const rate of [.5, 1, 2]) {
  speedControl.replay.rate = rate
  ReplayViewer.methods.cycleRate.call(speedControl)
}
assert.deepEqual(selectedRates, [['rate', 1], ['rate', 2], ['rate', .5]])
assert.ok(ReplayViewer.template.indexOf('gx-replay__timeline') < ReplayViewer.template.indexOf('class="gx-replay__controls"'))
assert.match(ReplayViewer.template, /@click="seek\(replay.position-10\)">-10 s/)
assert.match(ReplayViewer.template, /@click="seek\(replay.position\+10\)">\+10 s/)
assert.match(ReplayViewer.template, /@click="close">Stop/)
assert.doesNotMatch(ReplayViewer.template, /GalaxySelect/)
console.log('Replay controls: native button order, seek actions, speed cycling and Stop-to-close passed')

for (const [files, expected] of [[{ rlog: true, fcamera: true }, true], [{ qlog: true, qcamera: true }, true],
  [{ rlog: true, ecamera: true }, false], [{ rlog: true }, false], [{ fcamera: true }, false]]) {
  assert.equal(replayableSegment({ files }), expected)
}
