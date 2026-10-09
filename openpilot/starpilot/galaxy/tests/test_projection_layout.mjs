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
metadata.widgets.car_exit = { label: "Exit to car", kind: "car_exit", width: 96, height: 96, colors: {}, required: true, frontmost: true,
  note: "Returns to the car's own screen without disconnecting Android Auto. Always enabled and above other widgets.",
  default: { x: 30, y: 954, enabled: true } }
metadata.widgetOrder = [...(metadata.widgetOrder || Object.keys(native.metadata.profiles.large.widgets)), "car_exit"]
const widgets = Object.fromEntries(Object.entries(metadata.widgets).map(([id, widget]) => [id,
  { ...widget.default, ...(widget.resizable ? { size: widget.resizable.default } : {}) }]))
const doc = { version: 1, clock24Hour: false, largeUiGammaTrial: false, canvas: { width: 2880, height: 1080 }, widgets }
const raw = { version: 1, document: doc, defaults: copy(doc), metadata,
  screen: { width: 1280, height: 720, margin_width: 0, margin_height: 240 },
  revision: "aa-screen-and-layout", editable: true, valid: true,
  colors: { palette: native.document.palette, widgetColors: native.document.widgetColors.large, roadColors: {} } }
const data = editorSnapshot(raw)
assert.equal(validSnapshot(data), true)
assert.equal(validDocument(data.document, data.metadata), true)
const missingFrontmost = copy(data)
delete missingFrontmost.metadata.profiles.large.widgets.car_exit.frontmost
assert.equal(validSnapshot(missingFrontmost), false)
const buriedDefault = copy(data)
buriedDefault.metadata.profiles.large.widgetOrder = ["car_exit", ...buriedDefault.metadata.profiles.large.widgetOrder.filter(id => id !== "car_exit")]
assert.equal(validSnapshot(buriedDefault), false)
assert.equal(validSnapshot({ ...data, projection: false }), false)
assert.equal(validSnapshot({ ...data, metadata: { ...data.metadata, projection: false } }), false)
assert.equal(validDocument(data.document, native.metadata), false)
assert.deepEqual(projectionPayload({ revision: raw.revision, document: data.document }, data.metadata),
  { revision: raw.revision, document: raw.document })
data.document.clock24Hour = true
assert.equal(projectionPayload({ revision: raw.revision, document: data.document }, data.metadata).document.clock24Hour, true)
data.document.clock24Hour = false
data.document.largeUiGammaTrial = true
assert.equal(projectionPayload({document: data.document}, data.metadata).document.largeUiGammaTrial, true)
assert.equal(validDocument({...data.document, largeUiGammaTrial: 1}, data.metadata), false)
data.document.largeUiGammaTrial = false
assert.match(OnroadLayoutPage.template, /Large UI Gamma Effect Trial/)
const gammaChanges = []
const gammaVm = { projection: true, editable: true,
  state: { draft: { largeUiGammaTrial: false }, drag: null, layerDrag: null, notice: '' },
  recordChange: before => gammaChanges.push(before) }
OnroadLayoutPage.methods.setLargeUiGammaTrial.call(gammaVm, { target: { checked: true } })
assert.equal(gammaVm.state.draft.largeUiGammaTrial, true)
assert.deepEqual(gammaChanges, [{ largeUiGammaTrial: false }])
assert.match(gammaVm.state.notice, /Save and reconnect/)
for (const blocked of [{ projection: false }, { editable: false }]) {
  OnroadLayoutPage.methods.setLargeUiGammaTrial.call({ ...gammaVm, ...blocked }, { target: { checked: false } })
  assert.equal(gammaVm.state.draft.largeUiGammaTrial, true)
}
assert.throws(() => editorSnapshot({ version: 1, screen: null, reason: "Connect Android Auto once" }), /Connect Android Auto once/)
assert.equal(editorSnapshot({ ...raw, editable: false, reason: "Enable Android Auto" }).editable, false)
assert.ok(!OnroadLayoutPage.template.includes('<section class="gx-layout__colors" aria-label="Path'))
assert.ok(OnroadLayoutPage.template.includes('v-if="!projection && colorFields.length"'))
assert.ok(OnroadLayoutPage.template.includes('v-if="!projection && state.profile ==='))
compile(OnroadLayoutPage.template, { decodeEntities: value => value.replaceAll("&amp;", "&") }) // Actual Vue compiler, including projection conditionals.

const emissions = [], leaveVm = { projection: true, busy: false, dirty: true,
  state: { status: "ready", data: { editable: true }, draft: {}, drag: null, layerDrag: null, discard: null, leavePresentation: null, removeConfirm: null, error: "", needsReload: false },
  hideDevicePreview() {}, $emit: (...args) => emissions.push(args), feed: { load() {}, async save() { return true } } }
for (const name of ["pendingLeave", "inlineLeavePrompt", "modalLeavePrompt", "saveAvailable", "canSavePending"])
  Object.defineProperty(leaveVm, name, { get: () => OnroadLayoutPage.computed[name].call(leaveVm) })
for (const name of ["requestLeave", "cancelLeave", "leave", "saveAndLeave"])
  leaveVm[name] = OnroadLayoutPage.methods[name].bind(leaveVm)
leaveVm.requestLeave("device")
assert.equal(leaveVm.state.discard, "device")
assert.equal(leaveVm.inlineLeavePrompt, true)
assert.equal(leaveVm.modalLeavePrompt, false)
assert.deepEqual(emissions, [])
leaveVm.cancelLeave()
let proceeded = 0
leaveVm.requestLeave(() => { proceeded++ }, "modal")
assert.equal(leaveVm.inlineLeavePrompt, false)
assert.equal(leaveVm.modalLeavePrompt, true)
assert.equal(await leaveVm.saveAndLeave(), true)
assert.equal(proceeded, 1)
assert.equal(leaveVm.state.discard, null)
leaveVm.feed.save = async () => false
leaveVm.requestLeave(() => { proceeded++ }, "modal")
assert.equal(await leaveVm.saveAndLeave(), false)
assert.equal(proceeded, 1)
assert.equal(leaveVm.modalLeavePrompt, true)
leaveVm.cancelLeave()
assert.match(OnroadLayoutPage.template, /inlineLeavePrompt \? 'Leave without saving your changes\?'/)
assert.match(OnroadLayoutPage.template, /v-if="modalLeavePrompt"/)
assert.match(OnroadLayoutPage.template, /@click="saveAndLeave"/)

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
assert.equal(await feed.save(draft), true)
assert.equal(requests[0].url, "./api/android-auto/layout")
assert.equal(requests[1].body.document.version, 1)
assert.deepEqual(Object.keys(requests[1].body.document).sort(), ["canvas", "clock24Hour", "largeUiGammaTrial", "version", "widgets"])
assert.equal(requests[1].body.document.widgets.current_speed.x, 1170)
assert.equal(updates.at(-1).notice, "Android Auto layout saved.")
feed.stop()
console.log("Projection editor: isolated document, strict snapshot, routing confirmation, actual Vue template, endpoint and placement-only save passed")

const orderedRaw = copy(raw)
orderedRaw.document.widgetOrder = [...Object.keys(widgets).filter(id => id !== "car_exit").reverse(), "car_exit"]
const orderedSnapshot = editorSnapshot(orderedRaw)
assert.equal(validSnapshot(orderedSnapshot), true)
assert.deepEqual(orderedSnapshot.document.widgetOrder.large, orderedRaw.document.widgetOrder)
assert.deepEqual(projectionPayload({revision: raw.revision, document: orderedSnapshot.document}, orderedSnapshot.metadata).document,
  orderedRaw.document)
console.log('Projection layers survive editor translation and save payload')
