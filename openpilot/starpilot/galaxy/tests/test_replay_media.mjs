import assert from 'node:assert/strict'
import { ReplayClient, ReplayViewer } from '../web/js/replay.js'

const originalSource = globalThis.MediaSource, originalManaged = globalThis.ManagedMediaSource
const mime = 'video/mp4; codecs="avc1.42801f"'
const status = { schemaVersion: 1, ownerId: '1'.repeat(32), sessionId: '2'.repeat(32), state: 'playing',
  revision: 3, epoch: 2, position: 12, start: 0, end: 60, rate: 1, paused: false, offroad: true,
  owned: true, codec: 'avc1.42801f', media: { firstSequence: 1 } }
const ranges = (start, end) => ({ length: 1, start: () => start, end: () => end })
const settle = async () => { for (let i = 0; i < 20; i++) await Promise.resolve() }
class Buffer extends EventTarget {
  buffered = { length: 0 }
  appendBuffer(bytes) {
    if (new Uint8Array(bytes)[0]) this.buffered = ranges(0, .05)
    queueMicrotask(() => this.dispatchEvent(new Event('updateend')))
  }
}
class Source extends EventTarget {
  readyState = 'open'
  endOfStream() { this.readyState = 'ended' }
  static isTypeSupported(type) { return type === mime }
  addSourceBuffer(type) { assert.equal(type, mime); return new Buffer() }
}
class Managed extends Source {}
class Unsupported extends Source { static isTypeSupported() { return false } }
function viewer() {
  const video = Object.assign(new EventTarget(), { currentTime: 0, paused: true, seeking: false,
    pause() { this.paused = true }, play() { this.paused = false; return Promise.resolve() },
    removeAttribute() {}, load() {} })
  const requests = [], timers = new Map()
  let timer = 0
  const client = new ReplayClient({ clientId: '3'.repeat(32), video: () => video, publish() {}, unauthorized() {},
    createURL: () => 'blob:replay', revokeURL() {}, later: (fn, ms) => { timers.set(++timer, { fn, ms }); return timer },
    cancelTimer: id => timers.delete(id), fetcher: async url => {
      requests.push(url)
      const sequence = Number(new URL(url, 'http://replay.test').searchParams.get('sequence'))
      if (sequence >= 2) return { status: 202 }
      return { ok: true, status: 200, headers: new Headers({ 'Content-Type': 'video/mp4', 'Content-Length': '1',
        'X-Replay-Epoch': '2', 'X-Replay-Next-Sequence': String(sequence + 1) }),
        arrayBuffer: async () => new Uint8Array([sequence]).buffer }
    } })
  client.active = true; client.status = status; client.ownedSession = status.sessionId
  return { client, video, requests, timers }
}

try {
  for (const [classic, managed, selected] of [[Source, undefined, Source], [undefined, Managed, Managed],
    [Source, Managed, Source], [Unsupported, Managed, Managed]]) {
    globalThis.MediaSource = classic; globalThis.ManagedMediaSource = managed
    const { client, video } = viewer()
    client.beginMedia(status)
    assert.equal(client.source.constructor, selected, 'capability check and construction use the same supported API')
    assert.equal(client.error, '')
    if (selected === Managed) assert.equal(video.disableRemotePlayback, true, 'managed playback is enabled before attaching video')
    client.close(false)
  }
  const preparing = viewer()
  preparing.client.beginMedia({ ...status, codec: null, mediaReady: false })
  assert.equal(preparing.requests.length, 0, 'unready video cannot be mistaken for an unsupported codec and stop preparation')
  preparing.client.close(false)
  globalThis.MediaSource = globalThis.ManagedMediaSource = undefined
  const unavailable = viewer()
  await unavailable.client.start()
  assert.equal(unavailable.requests.length, 0, 'unsupported streaming does not start device work')
  assert.match(unavailable.client.error, /streaming is unavailable/)
  unavailable.client.beginMedia(status)
  assert.match(unavailable.requests.at(-1), /\/stop$/, 'an unplayable owned stream releases device work')
  const failedGeneration = unavailable.client.mediaGeneration
  unavailable.client.receive({ ...status, revision: 4 })
  assert.equal(unavailable.client.mediaGeneration, failedGeneration, 'status polling does not retry unsupported playback')
  globalThis.MediaSource = Unsupported
  unavailable.client.beginMedia(status)
  assert.match(unavailable.client.error, /H\.264 video/, 'codec rejection differs from missing streaming API')
  unavailable.client.close(false)

  globalThis.MediaSource = undefined; globalThis.ManagedMediaSource = Managed
  const { client, video, requests, timers } = viewer()
  client.error = 'Previous error'
  client.beginMedia(status)
  assert.equal(client.error, '', 'explicit retry clears its previous error')
  const source = client.source
  source.dispatchEvent(new Event('startstreaming'))
  assert.equal(requests.length, 0, 'managed demand waits for sourceopen')
  assert.equal(timers.size, 1, 'early managed demand retains the sourceopen timeout')
  source.dispatchEvent(new Event('sourceopen'))
  await settle()
  assert.match(requests[0], /sequence=0/)
  source.dispatchEvent(new Event('endstreaming'))
  client.status = { ...status, paused: true }
  await client.loadMedia(client.mediaGeneration, status.sessionId, status.epoch)
  assert.equal(client.buffer.buffered.length, 1, 'a paused or newly opened viewer can bootstrap its first frame')
  const afterBootstrap = requests.length
  await client.loadMedia(client.mediaGeneration, status.sessionId, status.epoch)
  assert.equal(requests.length, afterBootstrap, 'managed endstreaming stops requests once the paused preview is buffered')
  client.status = status
  source.dispatchEvent(new Event('startstreaming'))
  source.dispatchEvent(new Event('startstreaming'))
  await settle()
  assert.equal(requests.length, afterBootstrap + 1, 'duplicate managed demand retains one in-flight request')
  source.dispatchEvent(new Event('endstreaming'))
  video.seeking = true
  video.dispatchEvent(new Event('seeking'))
  source.dispatchEvent(new Event('endstreaming'))
  await settle()
  assert.equal(requests.length, afterBootstrap + 2, 'seeking resumes without Safari emitting startstreaming')
  assert.equal(client.mediaDemand, true, 'endstreaming during a seek cannot latch the loader off')
  video.seeking = false
  source.dispatchEvent(new Event('endstreaming'))
  client.status = { ...status, paused: true }
  client.receive({ ...status, revision: 4 })
  await settle()
  assert.equal(requests.length, afterBootstrap + 3, 'Play resumes without waiting for managed demand')

  let pausedSeeks = 0, pausedTime = .049
  Object.defineProperty(video, 'currentTime', { get: () => pausedTime,
    set(value) { pausedSeeks++; pausedTime = value }, configurable: true })
  client.receive({ ...status, paused: true, revision: 5 })
  client.receive({ ...status, paused: true, revision: 6 })
  assert.equal(pausedSeeks, 0, 'paused status polling does not repeatedly seek to an unchanged frame')

  const buffer = client.buffer, evicted = new Event('bufferedchange')
  video.currentTime = .025
  evicted.removedRanges = ranges(0, .01)
  buffer.dispatchEvent(evicted)
  assert.equal(client.source, source, 'removing already played data retains playback')
  evicted.removedRanges = ranges(0, .05)
  buffer.buffered = { length: 0 }
  buffer.dispatchEvent(evicted)
  assert.notEqual(client.source, source, 'evicting the current video reopens at an available keyframe')
  const replacement = client.source, beforeStaleEvents = requests.length
  source.dispatchEvent(new Event('startstreaming')); buffer.dispatchEvent(evicted)
  assert.equal(client.source, replacement, 'retired managed callbacks cannot replace the current epoch')
  client.close(false)
  replacement.dispatchEvent(new Event('sourceopen')); video.dispatchEvent(new Event('seeking'))
  await settle()
  assert.equal(requests.length, beforeStaleEvents, 'closing retires managed callbacks and removes the seek listener')
  assert.equal(timers.size, 0)

  const automatic = viewer()
  automatic.client.status = { ...status, paused: true, state: 'paused' }
  automatic.client.autoplay = true
  const resumes = []
  automatic.client.control = async (action, value) => {
    assert.equal(automatic.client.buffer.buffered.length, 1, 'auto-play waits for a real buffered frame')
    resumes.push([action, value])
    automatic.client.status = status
  }
  automatic.client.beginMedia(automatic.client.status)
  assert.equal(resumes.length, 0, 'opening a source does not resume an unbuffered route')
  automatic.client.source.dispatchEvent(new Event('sourceopen'))
  await settle()
  await automatic.client.loadMedia(automatic.client.mediaGeneration, status.sessionId, status.epoch)
  assert.deepEqual(resumes, [['pause', false]])
  await automatic.client.loadMedia(automatic.client.mediaGeneration, status.sessionId, status.epoch)
  assert.equal(resumes.length, 1, 'later fragments cannot repeatedly resume the route')
  automatic.client.close(false)

  const manual = viewer()
  manual.client.autoplay = true
  manual.client.ownedSession = null
  manual.client.control('pause', true)
  assert.equal(manual.client.autoplay, false, 'manual controls cancel automatic playback')
  manual.client.close(false)

  const stalled = viewer()
  stalled.client.beginMedia(status)
  const timeout = [...stalled.timers.values()].find(({ ms }) => ms === 4000)
  timeout.fn()
  assert.match(stalled.client.error, /could not open/)
  assert.equal(stalled.client.source, null)
  assert.equal(stalled.client.videoFailed, true, 'a source that cannot open waits for an explicit retry')
  stalled.client.close(false)
  const interrupted = viewer()
  interrupted.client.beginMedia(status)
  interrupted.client.mediaFailed(new Error('Replay video was incomplete.'), interrupted.client.mediaGeneration)
  interrupted.client.receive({ ...status, revision: 4 })
  assert.ok(interrupted.client.source, 'temporary media delivery failures recover from current status')
  interrupted.client.close(false)

  for (const Api of [Source, Managed]) {
    globalThis.MediaSource = Api === Managed ? undefined : Api
    globalThis.ManagedMediaSource = Api === Managed ? Managed : undefined
    const playback = viewer()
    playback.client.beginMedia(status)
    playback.client.source.dispatchEvent(new Event('sourceopen'))
    await settle()
    await playback.client.loadMedia(playback.client.mediaGeneration, status.sessionId, status.epoch)
    assert.equal(playback.video.paused, true, 'one frame cannot start browser playback')
    playback.client.buffer.buffered = ranges(0, .6)
    playback.client.receive({ ...status, revision: 4 })
    assert.equal(playback.video.paused, false, 'status updates use the same buffered playback gate')
    const generation = playback.client.mediaGeneration
    playback.video.currentTime = .6
    playback.client.videoWaiting()
    assert.equal(playback.video.paused, true)
    assert.equal(playback.client.status.paused, false, 'buffering pauses only the browser, leaving the producer running')
    assert.equal(playback.client.mediaGeneration, generation, 'an underrun retains the decoder and buffered video')
    playback.client.buffer.buffered = { length: 2, start: i => [0, 1][i], end: i => [.7, 2][i] }
    playback.client.playVideo()
    assert.equal(playback.video.paused, true, 'a gap cannot count toward the playback reserve')
    playback.client.buffer.buffered = ranges(0, 1.2)
    playback.client.playVideo()
    assert.equal(playback.video.paused, false, 'refilling the contiguous range resumes playback')
    playback.client.receive({ ...status, paused: true, state: 'paused', revision: 5 })
    assert.equal(playback.video.paused, true, 'user Pause remains immediate')
    playback.client.receive({ ...status, revision: 6 })
    assert.equal(playback.video.paused, true, 'Play rebuilds reserve after the paused preview')
    playback.client.receive({ ...status, revision: 7, state: 'ended', paused: true,
      media: { ...status.media, lastSequence: playback.client.sequence - 1 } })
    assert.equal(playback.video.paused, false, 'a short buffered tail finishes without waiting for future frames')
    assert.equal(playback.client.source.readyState, 'ended', 'only a fully appended route finalizes its media source')
    playback.client.close(false)
    playback.client.videoWaiting()
    await settle()
    assert.equal(playback.timers.size, 0, 'retired waiting callbacks cannot restart the loader')
  }
  globalThis.MediaSource = undefined; globalThis.ManagedMediaSource = Managed
  const bounded = viewer()
  bounded.client.beginMedia(status)
  bounded.client.source.dispatchEvent(new Event('sourceopen'))
  await settle()
  await bounded.client.loadMedia(bounded.client.mediaGeneration, status.sessionId, status.epoch)
  await bounded.client.loadMedia(bounded.client.mediaGeneration, status.sessionId, status.epoch)
  const nextLoad = [...bounded.timers.values()].find(({ ms }) => ms !== 4000)
  assert.equal(nextLoad.ms, 50, 'pending fragments retry after 50ms during playback')
  bounded.client.buffer.buffered = ranges(0, 1.4)
  bounded.video.currentTime = .1
  const beforeFull = bounded.requests.length
  await bounded.client.loadMedia(bounded.client.mediaGeneration, status.sessionId, status.epoch)
  assert.equal(bounded.requests.length, beforeFull, 'a full forward buffer applies backpressure without an HTTP request')
  assert.equal(bounded.video.currentTime, .1, 'buffering does not skip valid replay frames')
  bounded.video.currentTime = .6
  bounded.client.mediaDemand = true
  await bounded.client.loadMedia(bounded.client.mediaGeneration, status.sessionId, status.epoch)
  assert.equal(bounded.requests.length, beforeFull + 1, 'consuming the buffer releases backpressure')
  bounded.client.close(false)
  const finishing = viewer()
  finishing.client.beginMedia(status)
  finishing.client.source.dispatchEvent(new Event('sourceopen'))
  await settle()
  await finishing.client.loadMedia(finishing.client.mediaGeneration, status.sessionId, status.epoch)
  finishing.client.source.dispatchEvent(new Event('endstreaming'))
  const beforeFinish = finishing.requests.length
  finishing.client.receive({ ...status, state: 'ended', paused: true, revision: 4, media: { firstSequence: 1, lastSequence: 2 } })
  await settle()
  assert.equal(finishing.requests.length, beforeFinish + 1, 'route end requests its remaining fragment even after managed demand stopped')
  assert.equal(finishing.client.source.readyState, 'open', 'an unfetched tail cannot be mistaken for end of stream')
  finishing.client.close(false)
  await settle()
  assert.equal(finishing.timers.size, 0)
  assert.doesNotMatch(ReplayViewer.template, /<video[^>]*\bautoplay\b/, 'HTML autoplay cannot bypass the playback gate')
  assert.match(ReplayViewer.template, /!replayError.*preparing/, 'preparation does not mask a browser playback failure')
  console.log('Replay media: classic/managed capability selection, activation, bounded demand, seeking, eviction, retirement and errors passed')
} finally {
  globalThis.MediaSource = originalSource; globalThis.ManagedMediaSource = originalManaged
}
