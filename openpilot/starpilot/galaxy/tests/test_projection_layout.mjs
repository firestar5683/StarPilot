import assert from "node:assert/strict"
import { compile } from "../web/vendor/vue/vue.esm-browser.js"
import { snapshot } from "./test_onroad_layout.mjs"
import { editorSnapshot, projectionPayload } from "../web/js/projection-layout.js"
import { OnroadLayoutFeed, OnroadLayoutPage, validSnapshot, validDocument } from "../web/js/onroad-layout.js"

const copy = (v) => JSON.parse(JSON.stringify(v))
const native = snapshot()
const metadata = copy(native.metadata.profiles.large)
metadata.width = 2880
metadata.bounds.width = 2820
metadata.widgets.current_speed.default.x += 510
metadata.widgets.steering_wheel.default.x += 1020
const widgets = Object.fromEntries(Object.entries(metadata.widgets).map(([id, widget]) => [id,
  { ...widget.default, ...(widget.resizable ? { size: widget.resizable.default } : {}) }]))
const doc = { version: 1, canvas: { width: 2880, height: 1080 }, widgets }
const raw = { version: 1, document: doc, defaults: copy(doc), metadata,
  screen: { width: 1280, height: 720, margin_width: 0, margin_height: 240 },
  revision: "aa-screen-and-layout", editable: true, valid: true,
  colors: { palette: native.document.palette, widgetColors: native.document.widgetColors.large, roadColors: {} } }
const data = editorSnapshot(raw)
assert.equal(validSnapshot(data), true)
assert.equal(validDocument(data.document, data.metadata), true)
assert.equal(validSnapshot({ ...data, projection: false }), false)
assert.equal(validSnapshot({ ...data, metadata: { ...data.metadata, projection: false } }), false)
assert.equal(validDocument(data.document, native.metadata), false)
assert.deepEqual(projectionPayload({ revision: raw.revision, document: data.document }, data.metadata),
  { revision: raw.revision, document: raw.document })
assert.throws(() => editorSnapshot({ version: 1, screen: null, reason: "Connect Android Auto once" }), /Connect Android Auto once/)
assert.equal(editorSnapshot({ ...raw, editable: false, reason: "Enable Android Auto" }).editable, false)
assert.ok(!OnroadLayoutPage.template.includes('<section class="gx-layout__colors" aria-label="Path'))
assert.ok(OnroadLayoutPage.template.includes('v-if="!projection && colorFields.length"'))
assert.ok(OnroadLayoutPage.template.includes('v-if="!projection && state.profile ==='))
compile(OnroadLayoutPage.template, { decodeEntities: value => value.replaceAll("&amp;", "&") }) // Actual Vue compiler, including projection conditionals.

const emissions = []
const vm = { busy: false, dirty: true, state: { drag: null, discard: null },
  hideDevicePreview() {}, $emit: (...args) => emissions.push(args), feed: { load() {} } }
vm.leave = OnroadLayoutPage.methods.leave.bind(vm)
OnroadLayoutPage.methods.requestLeave.call(vm, "projection")
assert.equal(vm.state.discard, "projection")
assert.deepEqual(emissions, [])
vm.leave(vm.state.discard)
assert.deepEqual(emissions, [["target", "projection"]])

const setup = OnroadLayoutPage.setup({ projection: true, mode: "local", unauthorized() {} })
assert.equal(setup.feed.projection, true)
assert.equal(setup.state.profile, "large")
setup.feed.stop()

const requests = []
const updates = []
const feed = new OnroadLayoutFeed({ projection: true, publish: v => updates.push(v),
  later: () => 1, cancelTimer() {}, fetcher: async (url, options) => {
    requests.push({ url, body: options.body ? JSON.parse(options.body) : null })
    return { ok: true, status: 200, json: async () => raw }
  } })
await feed.start()
const draft = copy(feed.data.document)
draft.layouts.large.current_speed.x += 20
await feed.save(draft)
assert.equal(requests[0].url, "./api/android-auto/layout")
assert.equal(requests[1].body.document.version, 1)
assert.deepEqual(Object.keys(requests[1].body.document).sort(), ["canvas", "version", "widgets"])
assert.equal(requests[1].body.document.widgets.current_speed.x, 1170)
assert.equal(updates.at(-1).notice, "Android Auto layout saved.")
feed.stop()
console.log("Projection editor: isolated document, strict snapshot, routing confirmation, actual Vue template, endpoint and placement-only save passed")
