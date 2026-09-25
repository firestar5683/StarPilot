import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { SettingsFeed } from "../web/js/settings.js"
import { VasmPage } from "../web/js/vasm.js"
import { annotationDraft, displaySide, sourcePoint, validPolygon } from "../web/js/vasm-geometry.js"

assert.equal(displaySide("cameraRight"), "Vehicle left (camera right)")
assert.equal(displaySide("cameraLeft"), "Vehicle right (camera left)")
const phoneRect = { left: 0, top: 0, width: 390, height: 245 }
assert.deepEqual(sourcePoint(0, 0, phoneRect, 1928, 1208), [1928, 0])
assert.deepEqual(sourcePoint(390, 245, phoneRect, 1928, 1208), [0, 1208])
assert.equal(sourcePoint(-1, 100, phoneRect, 1928, 1208), null)
const right = [[100, 200], [320, 200], [320, 400], [100, 400]]
assert.deepEqual(annotationDraft(1344, 760, [], right), {
  version: 1, width: 1344, height: 760, poly_left: [], poly_right: right,
})
assert.equal(annotationDraft(1344, 760, [], []), null)
assert.equal(annotationDraft(1920, 1080, [], right), null)
assert.equal(validPolygon([[100, 100], [300, 300], [100, 300], [300, 100]], 1344, 760), false)
assert.equal(validPolygon(Array.from({ length: 33 }, (_, i) => [i + 10, i + 20]), 1344, 760), false)
assert.equal(validPolygon([[100, 100], [300, 100], [300, 300]], 1344, 760), true)
const canceledDrag = { _dragIndex: 0, _dragSide: "cameraRight", canEdit: false,
  state: { cameraRight: [[100, 200]] }, point: () => [300, 400], redraw() {} }
VasmPage.methods.pointerMove.call(canceledDrag, { clientX: 30, clientY: 40 })
assert.deepEqual(canceledDrag.state.cameraRight, [[100, 200]])
assert.equal(canceledDrag._dragIndex, -1)

const requests = [], states = []
const feed = new SettingsFeed({ publish: (state) => states.push(state),
  fetcher: (url, options) => new Promise((resolve) => requests.push({ url, options, resolve })),
  later: () => 1, cancelTimer: () => {} })
feed.start("vasm")
requests[0].resolve({ ok: true, status: 200, json: async () => ({ page: "vasm", view: "view1", rows: [] }) })
await new Promise((resolve) => setImmediate(resolve))
feed.preview(3, 0, annotationDraft(1344, 760, [], right))
assert.equal(requests[1].url, "./api/settings/preview")
assert.deepEqual(JSON.parse(requests[1].options.body), {
  view: "view1", row: 3, direction: 0,
  draft: { version: 1, width: 1344, height: 760, poly_left: [], poly_right: right },
})
feed.stop()
requests[1].resolve({ ok: true, status: 200, json: async () => ({ intent: "late", question: "Save?" }) })
await new Promise((resolve) => setImmediate(resolve))
assert.equal(states.at(-1).status, "idle")
assert.equal(states.at(-1).pending, null)

assert.match(VasmPage.template, /type="file" accept="image\/png,image\/jpeg"/)
assert.match(VasmPage.template, /@pointerdown="pointerDown"/)
assert.match(VasmPage.template, /Undo last/)
assert.match(VasmPage.template, /Review saved regions/)
assert.match(VasmPage.template, /state\.pending\.question/)
assert.doesNotMatch(readFileSync(new URL("../web/js/vasm.js", import.meta.url), "utf8"), /getVasmSnapshot|FormData|fetch\(/)
const app = readFileSync(new URL("../web/js/app.js", import.meta.url), "utf8")
assert.match(app, /route\.path === '\/cameras\/vasm'/)

// The file stays in an object URL, and both replacement and unmount revoke it.
let created = 0
const revoked = []
globalThis.URL.createObjectURL = () => `blob:local-${++created}`
globalThis.URL.revokeObjectURL = (url) => revoked.push(url)
let image
globalThis.Image = class {
  constructor() { image = this; this.naturalWidth = 1344; this.naturalHeight = 760 }
  set src(value) { this._src = value }
}
const context = { state: { width: 1344, height: 760, imageName: "", localNote: "", data: { view: "view1" } },
  _imageGeneration: 0, _imageUrl: null, _image: null, dropImage: VasmPage.methods.dropImage,
  redraw() {} }
let fileInput = { files: [{ type: "image/png", size: 100, name: "local.png" }], value: "chosen" }
VasmPage.methods.selectImage.call(context, { target: fileInput })
assert.equal(fileInput.value, "")
image.onload()
assert.equal(context.state.imageName, "local.png")
assert.equal(context._imageUrl, "blob:local-1")
fileInput = { files: [{ type: "image/jpeg", size: 120, name: "new.jpg" }], value: "chosen" }
VasmPage.methods.selectImage.call(context, { target: fileInput })
assert.deepEqual(revoked, ["blob:local-1"])
image.onload()
assert.equal(context.state.imageName, "new.jpg")
fileInput = { files: [{ type: "image/png", size: 120, name: "wrong.png" }], value: "chosen" }
VasmPage.methods.selectImage.call(context, { target: fileInput })
image.naturalWidth = 1928
image.onload()
assert.match(context.state.localNote, /must match 1344 × 760/)
assert.equal(context.state.imageName, "")
assert.deepEqual(revoked, ["blob:local-1", "blob:local-2", "blob:local-3"])
fileInput = { files: [{ type: "image/jpeg", size: 100, name: "final.jpg" }], value: "chosen" }
VasmPage.methods.selectImage.call(context, { target: fileInput })
image.onload()
fileInput = { files: [{ type: "image/png", size: 100, name: "pending.png" }], value: "chosen" }
VasmPage.methods.selectImage.call(context, { target: fileInput })
context.state.data.view = "view2"
image.onload()
assert.equal(context.state.imageName, "")
assert.deepEqual(revoked, ["blob:local-1", "blob:local-2", "blob:local-3", "blob:local-4", "blob:local-5"])
fileInput = { files: [{ type: "image/png", size: 100, name: "current.png" }], value: "chosen" }
VasmPage.methods.selectImage.call(context, { target: fileInput })
image.onload()
context.feed = { stop() {} }
VasmPage.beforeUnmount.call(context)
assert.deepEqual(revoked, ["blob:local-1", "blob:local-2", "blob:local-3", "blob:local-4", "blob:local-5", "blob:local-6"])
