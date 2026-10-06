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
