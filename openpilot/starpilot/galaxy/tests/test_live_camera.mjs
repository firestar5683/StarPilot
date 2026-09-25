import assert from "node:assert/strict"
import { CameraSnapshotFeed, LiveCameraPreview } from "../web/js/cameras.js"

// A server or body that ignores AbortSignal must release the polling caller.
for (const bodyStalls of [false, true]) {
  let expire, signal
  const updates = []
  const feed = new CameraSnapshotFeed({ publish: value => updates.push(value), unauthorized() {},
    later: fn => { expire = fn; return 1 }, cancelTimer() {},
    fetcher: async (_url, options) => {
      signal = options.signal
      return bodyStalls ? { ok: true, status: 200, headers: new Headers({ 'Content-Type': 'image/jpeg' }),
        blob: () => new Promise(() => {}) } : new Promise(() => {})
    },
  })
  const pending = feed.capture("cabin")
  await Promise.resolve()
  expire()
  await pending
  assert.equal(signal.aborted, true)
  assert.equal(updates.at(-1).capturing, false)
  assert.match(updates.at(-1).error, /timed out/)
  assert.equal(feed.request, null)
}

// Retired image callbacks cannot restore an image after hiding/unmounting.
let image, stopped = 0
const updates = []
const preview = new LiveCameraPreview({ publish: value => updates.push(value), unauthorized() {},
  redraw() {}, enabled: () => true, imageFactory: () => image = {} })
preview.stopped = false
preview.receive({ image: 'blob:frame' })
preview.snapshots.stop = () => stopped++
preview.clear()
image.onload()
assert.equal(preview.image, null)
assert.equal(updates.at(-1).imageName, '')
assert.equal(stopped, 1)
console.log('Live camera: stalled fetch/body settle, explicit failures, stale decode cleanup passed')

const canceled = new CameraSnapshotFeed({ publish() {}, unauthorized() {}, fetcher: () => new Promise(() => {}) })
const canceledCapture = canceled.capture("cabin")
canceled.stop()
await canceledCapture
assert.equal(canceled.request, null)

// Editors warm up once, then keep the frame without background capture or flicker.
const timers = new Map()
let nextTimer = 0, captures = 0
const originalDocument = globalThis.document
const listeners = new Map()
globalThis.document = { hidden: false, addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: name => listeners.delete(name) }
const snapshot = new LiveCameraPreview({ publish() {}, unauthorized() {}, redraw() {}, enabled: () => true,
  later: (fn, ms) => { timers.set(++nextTimer, { fn, ms }); return nextTimer }, cancelTimer: id => timers.delete(id) })
snapshot.snapshots.capture = async () => { captures++; snapshot.image = { src: 'last-good-frame' } }
snapshot.snapshots.stop = () => {}
snapshot.start()
await Promise.resolve()
const warmup = [...timers.values()].find(timer => timer.ms === 5000)
assert.ok(warmup)
warmup.fn()
const heldFrame = snapshot.image
await snapshot.poll()
globalThis.document.hidden = true; listeners.get('visibilitychange')()
globalThis.document.hidden = false; listeners.get('visibilitychange')()
assert.equal(captures, 1)
assert.equal(snapshot.image, heldFrame, 'visibility changes preserve the held snapshot')
snapshot.stop()
globalThis.document = originalDocument
console.log('Camera editor warm-up: five-second deadline, frozen frame and visibility stability passed')
