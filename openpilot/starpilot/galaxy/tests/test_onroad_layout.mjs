import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { LayoutWidgetPreview, OnroadLayoutFeed, OnroadLayoutPage, validSnapshot, validDocument, clampPlacement, previewPoint, withAlpha, widgetPalette } from "../web/js/onroad-layout.js"
import { SettingsPage, SETTINGS_SECTIONS } from "../web/js/settings.js"
import { loadCatalog } from "../web/js/startup.js"

const copy = (data) => JSON.parse(JSON.stringify(data))
const widget = (label, kind, width, height, x, y) => ({ label, kind, width, height, default: { x, y, enabled: true } })
export function snapshot() {
  const metadata = { profiles: {
    large: { label: "Large UI", width: 2160, height: 1080, bounds: { x: 30, y: 30, width: 1800, height: 1020 }, reservedZones: [], widgets: {
      current_speed: widget("Current speed", "current_speed", 580, 300, 640, 30),
      cruise_limits: widget("Cruise and speed limit", "cruise_limits", 176, 483, 88, 75),
      speed_limit_actions: widget("Speed limit actions", "speed_limit_actions", 176, 58, 88, 500),
      steering_wheel: widget("Steering wheel", "steering_wheel", 192, 192, 1588, 75),
      driver_monitor: widget("Driver monitoring", "driver_monitor", 192, 192, 88, 808),
      torque_bar: { ...widget("Torque bar", "torque_bar", 998, 240, 439, 759), layer: "underlay" },
    } },
    compact: { label: "Small UI", width: 536, height: 240, bounds: { x: 0, y: 0, width: 476, height: 240 },
      protectedWidget: "speed_limit_actions", reservedZones: [], widgets: {
      max_speed: widget("Maximum speed", "max_speed", 162, 162, 0, 0),
      speed_limit: widget("Speed limit", "speed_limit", 118, 132, 330, 20),
      speed_limit_actions: widget("Speed limit actions", "speed_limit_actions", 282, 54, 174, 180),
      steering_wheel: widget("Steering wheel", "steering_wheel", 50, 50, 21, 176),
      driver_monitor: widget("Driver monitoring", "driver_monitor", 60, 60, 16, 10),
      torque_bar: { ...widget("Torque bar", "torque_bar", 260, 61, 116, 167), layer: "underlay" },
      model_confidence: { ...widget("Model confidence", "model_confidence", 60, 80, 476, 0), bounds: { x: 0, y: 0, width: 536, height: 240 } },
      conditional_mode: { ...widget("CEM and driving mode", "conditional_mode", 60, 80, 476, 80), bounds: { x: 0, y: 0, width: 536, height: 240 } },
      following_distance: { ...widget("Following distance", "following_distance", 60, 80, 476, 160), bounds: { x: 0, y: 0, width: 536, height: 240 } },
    } },
  }, paletteFields: [
    { id: "cardFill", label: "Card fill", default: "#000000A6" },
    { id: "cardBorder", label: "Card border", default: "#C4CDD0B4" },
    { id: "text", label: "Text", default: "#FFFFFFFF" },
  ] }
  const frame = { cardFill: "#00000000", cardBorder: "#00000000" }
  const actions = { cardFill: "#0C1820EB", cardBorder: "#A6DFBEFF", text: "#FFFFFFFF" }
  const colors = {
    large: { current_speed: { text: null }, cruise_limits: { cardFill: null, cardBorder: null, text: null },
      speed_limit_actions: actions, steering_wheel: { cardFill: null, cardBorder: "#00000000" }, driver_monitor: frame },
    compact: { max_speed: { text: null }, speed_limit_actions: actions, driver_monitor: frame, model_confidence: frame,
      conditional_mode: frame, following_distance: { ...frame, text: "#FFFFFFFF" } },
  }
  for (const [profile, data] of Object.entries(metadata.profiles))
    for (const [id, widget] of Object.entries(data.widgets)) widget.colors = { ...colors[profile][id] }
  metadata.profiles.large.widgets.steering_wheel.resizable = { min: 144, default: 192, max: 240 }
  metadata.profiles.compact.widgets.steering_wheel.resizable = { min: 40, default: 50, max: 70 }
  metadata.roadColorFields = [{ id: 'path', label: 'Path', default: '#30FF9CFF' },
    { id: 'pathEdge', label: 'Path edges', default: '#00FF40FF' }, { id: 'laneLines', label: 'Lane lines', default: '#FFFFFFFF' }]
  metadata.profiles.compact.widgets.speed_limit_actions.visualInsetTop = 32
  const document = { version: 4, roadColors: { large: {}, compact: {} }, widgetColors: { large: {}, compact: {} }, palette: Object.fromEntries(metadata.paletteFields.map((field) => [field.id, field.default])),
    layouts: Object.fromEntries(Object.entries(metadata.profiles).map(([id, profile]) => [id,
      Object.fromEntries(Object.entries(profile.widgets).map(([key, definition]) => [key,
        { ...definition.default, ...(definition.resizable ? { size: definition.resizable.default } : {}) }]))])) }
  return { document, defaults: copy(document), metadata, revision: "saved-revision", editable: true, valid: true, activeProfile: null }
}

const data = snapshot()
const withMode = copy(data)
const modeId = "driving_mode_descriptions"
withMode.metadata.profiles.compact.widgets[modeId] = {
  ...widget("Driving Mode Descriptions", modeId, 168, 60, 162, 22), colors: { text: "#FFFFFFFF" },
}
withMode.document.layouts.compact[modeId] = { x: 162, y: 22, enabled: false }
withMode.document.layouts.compact.speed_limit_actions.y = 45
withMode.defaults = copy(withMode.document)
assert.equal(validSnapshot(withMode), true)
assert.equal(clampPlacement(withMode.metadata.profiles.compact, modeId, 162, 22, withMode.document.layouts.compact), null)
withMode.document.layouts.compact[modeId].enabled = true
assert.equal(validDocument(withMode.document, withMode.metadata), false)
withMode.document.layouts.compact[modeId].y = 110
assert.equal(validDocument(withMode.document, withMode.metadata), true)
assert.equal(withAlpha("#AABBCC80", 200 / 255), "#AABBCC64")
assert.equal(withAlpha("#AABBCCFF", .9), "#AABBCCe5")
assert.equal(validSnapshot(data), true)
assert.deepEqual(clampPlacement(data.metadata.profiles.compact, "torque_bar", 174, 179), { x: 174, y: 179 })
const registeredUnderlay = copy(data.metadata.profiles.compact)
registeredUnderlay.widgets.max_speed.layer = "underlay"
assert.deepEqual(clampPlacement(registeredUnderlay, "max_speed", 174, 19), { x: 174, y: 19 })
const alternateUnderlayKind = copy(data.metadata.profiles.compact)
alternateUnderlayKind.widgets.torque_bar.kind = "max_speed"
assert.deepEqual(clampPlacement(alternateUnderlayKind, "torque_bar", 174, 179), { x: 174, y: 179 })

for (const mutate of [
  (value) => { value.document.layouts.large.fake = { x: 0, y: 0, enabled: true } },
  (value) => { value.document.layouts.compact.max_speed.y = 79 },
  (value) => { value.document.palette.text = "red" },
  (value) => { value.document.layouts.large.current_speed.x = Infinity },
  (value) => { value.document.layouts.compact.steering_wheel.size = 71 },
  (value) => { value.document.layouts.compact.speed_limit_actions.size = 70 },
  (value) => { delete value.document.layouts.compact },
  (value) => { value.metadata.profiles.compact.bounds.width = 9999 },
  (value) => { value.metadata.paletteFields[1].id = "text" },
  (value) => { value.editable = "true" },
]) {
  const invalid = copy(data); mutate(invalid); assert.equal(validSnapshot(invalid), false)
}
assert.equal(validDocument({ ...data.document, arbitrary: 1 }, data.metadata), false)
assert.equal(clampPlacement(data.metadata.profiles.compact, "max_speed", 999, 999), null)
assert.deepEqual(clampPlacement(data.metadata.profiles.compact, "max_speed", 999, 18), { x: 314, y: 18 })
assert.equal(clampPlacement(data.metadata.profiles.compact, "max_speed", 999, 19), null)
const movedActions = copy(data.document.layouts.compact)
movedActions.speed_limit_actions.x = 100
assert.deepEqual(clampPlacement(data.metadata.profiles.compact, "speed_limit_actions", 100, 180, data.document.layouts.compact), { x: 100, y: 180 })
assert.equal(clampPlacement(data.metadata.profiles.compact, "speed_limit_actions", 10, 180, data.document.layouts.compact), null)
assert.equal(clampPlacement(data.metadata.profiles.compact, "max_speed", 100, 19, movedActions), null)
assert.deepEqual(clampPlacement(data.metadata.profiles.compact, "speed_limit", 330, 20, movedActions), { x: 330, y: 20 })
assert.equal(validDocument({ ...data.document, layouts: { ...data.document.layouts, compact: movedActions } }, data.metadata), true)
const resizedWheel = copy(data.document)
resizedWheel.layouts.compact.steering_wheel.size = 70
resizedWheel.layouts.compact.steering_wheel.y = 160
assert.equal(validDocument(resizedWheel, data.metadata), true)
assert.equal(clampPlacement(data.metadata.profiles.compact, "steering_wheel", 150, 170, resizedWheel.layouts.compact), null)
assert.deepEqual(clampPlacement(data.metadata.profiles.compact, "steering_wheel", 21, 176, resizedWheel.layouts.compact), { x: 21, y: 170 })
assert.deepEqual(clampPlacement(data.metadata.profiles.large, "current_speed", -99, -99), { x: 30, y: 30 })
assert.equal(clampPlacement(data.metadata.profiles.large, "fake", 30, 30), null)
assert.equal(clampPlacement(data.metadata.profiles.large, "current_speed", NaN, 30), null)
assert.deepEqual(previewPoint({ clientX: 316, clientY: 200 }, { left: 100, top: 92, width: 432, height: 216 }, data.metadata.profiles.large), { x: 1080, y: 540 })

function editor() {
  const emitted = [], calls = [], previewCalls = [], captures = new Set()
  const target = { setPointerCapture(id) { captures.add(id) }, hasPointerCapture(id) { return captures.has(id) }, releasePointerCapture(id) { captures.delete(id) } }
  const vm = { ...OnroadLayoutPage.setup({ mode: "local", unauthorized() {} }), $emit: (...args) => emitted.push(args),
    $refs: { preview: { ...target, getBoundingClientRect: () => ({ left: 100, top: 100, width: 1080, height: 540 }) } } }
  for (const [key, getter] of Object.entries(OnroadLayoutPage.computed)) Object.defineProperty(vm, key, { get: () => getter.call(vm) })
  for (const [key, method] of Object.entries(OnroadLayoutPage.methods)) vm[key] = method.bind(vm)
  vm.state.data = snapshot(); vm.state.data.supportedProfiles = ['large', 'compact']; vm.state.draft = copy(vm.state.data.document); vm.state.status = "ready"; vm.state.selected = "current_speed"
  const publish = vm.feed.publish
  vm.feed = { load: () => calls.push("load"), save: (document) => calls.push(copy(document)) }
  vm.previewFeed.start = () => previewCalls.push("start")
  vm.previewFeed.update = (...args) => previewCalls.push(["update", ...args])
  vm.previewFeed.stop = () => previewCalls.push("stop")
  const event = (x, y, pointerId = 1) => ({ clientX: x, clientY: y, pointerId, button: 0, currentTarget: { setPointerCapture() { throw new Error("Capture must belong to the stable preview") } }, preventDefault() {} })
  return { vm, event, emitted, calls, previewCalls, captures, publish }
}

const dmEditor = editor().vm
dmEditor.changePosition("driver_monitor", 700, 600)
dmEditor.selectProfile("compact")
dmEditor.changePosition("driver_monitor", 90, 70)
assert.deepEqual(dmEditor.state.draft.layouts.large.driver_monitor, { x: 700, y: 600, enabled: true })
assert.deepEqual(dmEditor.layout.driver_monitor, { x: 90, y: 70, enabled: true })
dmEditor.changePosition("driver_monitor", 200, 190)
assert.deepEqual(dmEditor.layout.driver_monitor, { x: 90, y: 70, enabled: true })
dmEditor.remove("driver_monitor")
assert.equal(dmEditor.layout.driver_monitor.enabled, false)
dmEditor.add("driver_monitor")
assert.equal(dmEditor.layout.driver_monitor.enabled, true)
dmEditor.resetLayout()
assert.deepEqual(dmEditor.layout.driver_monitor, { x: 16, y: 10, enabled: true })
assert.equal(dmEditor.state.draft.layouts.large.driver_monitor.x, 700)

const actionEditor = editor().vm
actionEditor.changePosition("speed_limit_actions", 388, 600)
assert.deepEqual(actionEditor.layout.speed_limit_actions, { x: 388, y: 600, enabled: true })
actionEditor.selectProfile("compact")
actionEditor.changePosition("speed_limit_actions", 100, 180)
assert.deepEqual(actionEditor.layout.speed_limit_actions, { x: 100, y: 180, enabled: true })
actionEditor.changePosition("speed_limit_actions", 10, 180)
assert.equal(actionEditor.layout.speed_limit_actions.x, 100)
assert.equal(validDocument(actionEditor.state.draft, actionEditor.state.data.metadata), true)

const wheelEditor = editor().vm
wheelEditor.state.selected = "steering_wheel"
wheelEditor.resizeSelected({ target: { value: "240" } })
assert.equal(wheelEditor.layout.steering_wheel.size, 240)
assert.equal(wheelEditor.renderWidgets.find((widget) => widget.id === "steering_wheel").width, 240)
wheelEditor.undo()
assert.equal(wheelEditor.layout.steering_wheel.size, 192)
wheelEditor.redo()
assert.equal(wheelEditor.layout.steering_wheel.size, 240)
wheelEditor.selectProfile("compact")
wheelEditor.state.selected = "steering_wheel"
wheelEditor.resizeSelected({ target: { value: "70" } })
assert.deepEqual(wheelEditor.layout.steering_wheel, { x: 21, y: 170, enabled: true, size: 70 })
assert.equal(wheelEditor.state.draft.layouts.large.steering_wheel.size, 240)
wheelEditor.resetLayout()
assert.equal(wheelEditor.layout.steering_wheel.size, 50)
assert.equal(wheelEditor.state.draft.layouts.large.steering_wheel.size, 240)
const dragWheel = editor()
dragWheel.vm.state.selected = "steering_wheel"
dragWheel.vm.resizeSelected({ target: { value: "240" } })
dragWheel.vm.startDrag("steering_wheel", dragWheel.event(954, 197.5))
dragWheel.vm.moveDrag(dragWheel.event(964, 197.5))
dragWheel.vm.endDrag(dragWheel.event(964, 197.5))
assert.deepEqual(dragWheel.vm.layout.steering_wheel, { x: 1590, y: 75, enabled: true, size: 240 })
assert.equal(dragWheel.captures.size, 0)


const torqueEditor = editor().vm
torqueEditor.changePosition("torque_bar", 500, 650)
torqueEditor.selectProfile("compact")
torqueEditor.changePosition("torque_bar", 174, 179)
assert.deepEqual(torqueEditor.renderWidgets.map(widget => widget.id), torqueEditor.layerWidgets.map(widget => widget.id).reverse())
assert.equal(torqueEditor.state.draft.layouts.large.torque_bar.x, 500)
assert.equal(torqueEditor.layout.torque_bar.y, 179)
torqueEditor.remove("torque_bar")
assert.equal(torqueEditor.layout.torque_bar.enabled, false)
torqueEditor.add("torque_bar")
assert.equal(torqueEditor.layout.torque_bar.enabled, true)
const { vm, event, emitted, calls, previewCalls, captures } = editor()
assert.equal(vm.state.devicePreviewOpen, false)
assert.equal(vm.dirty, false)
vm.changePosition("current_speed", 700, 200)
vm.selectProfile("compact")
vm.changePosition("max_speed", 200, 18)
vm.state.selected = "driver_monitor"
vm.color("cardFill", "#112233aa")
vm.resetLayout()
assert.equal(vm.layout.max_speed.x, 0)
assert.equal(vm.state.draft.layouts.large.current_speed.x, 700)
assert.equal(vm.selectedColors.cardFill, "#112233AA")
vm.changePosition("max_speed", 200, 18)
vm.resetColors()
assert.equal(vm.selectedColors.cardFill, "#00000000")
assert.equal(vm.layout.max_speed.x, 200)
vm.changePosition("max_speed", 200, 65)
assert.equal(vm.layout.max_speed.y, 18)
assert.match(vm.state.placementError, /last valid position/)
const compactPoint = (x, y) => event(100 + x * 1080 / 536, 100 + y * 540 / 240)
vm.startDrag("speed_limit", compactPoint(350, 40))
vm.moveDrag(compactPoint(350, 100))
assert.equal(vm.layout.speed_limit.y, 80) // Intentional sign/action overlap survives dragging.
vm.endDrag(compactPoint(350, 100))
assert.equal(vm.layout.speed_limit.y, 80)
assert.equal(vm.state.drag, null)
vm.selectProfile("large")
assert.equal(vm.layout.current_speed.x, 700)
vm.onKey("current_speed", { key: "ArrowRight", shiftKey: true, preventDefault() {} })
assert.equal(vm.layout.current_speed.x, 710)
vm.onKey("current_speed", { key: "Delete", preventDefault() {} })
assert.equal(vm.state.removeConfirm, "current_speed")
assert.equal(vm.layout.current_speed.enabled, true)
vm.confirmRemove()
assert.equal(vm.layout.current_speed.enabled, false)
assert.equal(vm.inactiveWidgets.length, 1)
vm.startDrag("current_speed", event(1300, 100), true)
vm.moveDrag(event(500, 300))
assert.equal(vm.layout.current_speed.enabled, true)
assert.equal(vm.inactiveWidgets.length, 1) // Keep the captured tray element mounted during the drag.
assert.equal(vm.state.drag.fromTray, true)
assert.deepEqual({ ...vm.layout.current_speed }, { x: 510, y: 250, enabled: true })
assert.equal(captures.has(1), true)
vm.endDrag(event(500, 300))
assert.equal(captures.size, 0)
assert.equal(vm.inactiveWidgets.length, 0)
vm.startDrag("current_speed", event(400, 250))
vm.moveDrag(event(2000, 2000))
assert.deepEqual({ ...vm.layout.current_speed }, { x: 1250, y: 750, enabled: true })
vm.cancelDrag()
assert.deepEqual({ ...vm.layout.current_speed }, { x: 510, y: 250, enabled: true })
vm.remove("current_speed")
vm.startDrag("current_speed", event(1300, 100), true)
vm.moveDrag(event(500, 300, 2)) // A second pointer cannot change this drag.
assert.equal(vm.layout.current_speed.enabled, false)
vm.endDrag(event(1300, 100))
assert.equal(vm.layout.current_speed.enabled, false)
vm.add("current_speed")
assert.deepEqual({ ...vm.layout.current_speed }, { x: 510, y: 250, enabled: true })
vm.color("text", "invalid")
assert.match(vm.state.colorError, /eight hex digits/)
assert.equal(vm.selectedColors.text, "#FFFFFFFF")
vm.colorRgb("text", { target: { value: "#abcdef" } })
vm.colorAlpha("text", { target: { value: "128" } })
assert.equal(vm.selectedColors.text, "#ABCDEF80")
assert.deepEqual(previewCalls, []) // Editing does not select or request Device preview.
const draftBeforePreview = copy(vm.state.draft)
vm.mode = "local"
vm.showDevicePreview()
assert.equal(vm.state.devicePreviewOpen, true)
assert.deepEqual(previewCalls.map((call) => Array.isArray(call) ? call[0] : call), ["start", "update"])
assert.deepEqual(previewCalls[1].slice(1), [draftBeforePreview, "large", "engaged"])
vm.selectProfile("compact")
assert.equal(previewCalls.at(-1)[2], "compact")
vm.state.scene = "braking"
assert.equal(previewCalls.at(-1)[3], "braking")
vm.selectProfile("large")
vm.hideDevicePreview()
assert.equal(vm.state.devicePreviewOpen, false)
assert.equal(previewCalls.at(-1), "stop")
assert.deepEqual(copy(vm.state.draft), draftBeforePreview)
const previewCount = previewCalls.length
vm.state.scene = "engaged"
vm.color("text", "#ABCDEF81")
assert.equal(previewCalls.length, previewCount)
vm.color("text", "#ABCDEF80")
const deviceEditor = editor()
deviceEditor.vm.mode = "local"
deviceEditor.vm.showDevicePreview()
const beforeDeviceDrag = copy(deviceEditor.vm.layout.current_speed)
deviceEditor.vm.startDrag("current_speed", deviceEditor.event(500, 200))
assert.equal(deviceEditor.vm.state.devicePreviewOpen, true)
assert.equal(deviceEditor.previewCalls.at(-1).at(-1), true)
deviceEditor.vm.moveDrag(deviceEditor.event(700, 250))
deviceEditor.vm.cancelDrag()
assert.deepEqual(copy(deviceEditor.vm.layout.current_speed), beforeDeviceDrag)
assert.equal(deviceEditor.vm.state.devicePreviewOpen, true)
deviceEditor.vm.hideDevicePreview()
vm.requestLeave("reload")
assert.equal(vm.state.discard, "reload")
assert.equal(calls.length, 0)
assert.equal(vm.editable, false)
vm.state.discard = null
vm.save()
assert.equal(calls.length, 1)
assert.equal(calls[0].layouts.compact.max_speed.x, 200)
vm.requestLeave("back")
assert.equal(emitted.length, 0)
vm.leave("back")
assert.deepEqual(emitted, [["close"]])
vm.state.data.editable = false
const parkedDraft = copy(vm.state.draft)
vm.changePosition("current_speed", 99, 99); vm.remove(); vm.resetLayout(); vm.resetColors(); vm.color("text", "#00000000"); vm.save()
assert.deepEqual(copy(vm.state.draft), parkedDraft)
assert.equal(calls.length, 1)

const historyEditor = editor()
const history = historyEditor.vm
assert.equal(history.canUndo, false)
assert.equal(history.stockChanged, false)
history.resetToStock()
assert.equal(history.state.history.undo.length, 0)
history.remove("current_speed")
history.changePosition("current_speed", 700, 200) // Disabled widgets keep editable positions.
assert.equal(history.state.history.undo.length, 2)
history.undo()
assert.deepEqual(copy(history.layout.current_speed), { x: 640, y: 30, enabled: false })
history.undo()
assert.deepEqual(copy(history.layout.current_speed), { x: 640, y: 30, enabled: true })
history.redo()
history.redo()
assert.deepEqual(copy(history.layout.current_speed), { x: 700, y: 200, enabled: false })
history.selectProfile("compact")
history.changePosition("max_speed", 200, 18)
history.undo()
assert.equal(history.layout.max_speed.x, 0)
assert.equal(history.state.draft.layouts.large.current_speed.x, 700)
history.redo()
assert.equal(history.layout.max_speed.x, 200)

const dragEditor = editor()
const dragged = dragEditor.vm
const beforeDrag = copy(dragged.state.draft)
dragged.startDrag("current_speed", dragEditor.event(500, 150))
dragged.moveDrag(dragEditor.event(600, 200))
dragged.moveDrag(dragEditor.event(700, 250))
assert.equal(dragged.state.history.undo.length, 0)
dragged.undo() // History cannot replace a draft during an active gesture.
assert.equal(dragged.state.drag.id, "current_speed")
dragged.endDrag(dragEditor.event(700, 250))
assert.equal(dragged.state.history.undo.length, 1)
const afterDrag = copy(dragged.state.draft)
dragged.undo()
assert.deepEqual(copy(dragged.state.draft), beforeDrag)
dragged.redo()
assert.deepEqual(copy(dragged.state.draft), afterDrag)
dragged.startDrag("current_speed", dragEditor.event(700, 250))
dragged.moveDrag(dragEditor.event(800, 300))
dragged.cancelDrag()
assert.deepEqual(copy(dragged.state.draft), afterDrag)
assert.equal(dragged.state.history.undo.length, 1)
assert.equal(dragged.state.history.redo.length, 0)
dragged.remove("current_speed")
const beforeTray = copy(dragged.state.draft)
const historySize = dragged.state.history.undo.length
dragged.startDrag("current_speed", dragEditor.event(1300, 100), true)
dragged.moveDrag(dragEditor.event(500, 300))
dragged.endDrag(dragEditor.event(500, 300))
assert.equal(dragged.state.history.undo.length, historySize + 1)
dragged.undo()
assert.deepEqual(copy(dragged.state.draft), beforeTray)

const colorEditor = editor().vm
colorEditor.colorAlpha("text", { target: { value: "200" } })
colorEditor.colorAlpha("text", { target: { value: "180" } })
colorEditor.colorAlpha("text", { target: { value: "160" } })
assert.equal(colorEditor.state.history.undo.length, 1)
colorEditor.undo()
assert.equal(colorEditor.selectedColors.text, "#FFFFFFFF")
colorEditor.redo()
assert.equal(colorEditor.selectedColors.text, "#FFFFFFA0")
colorEditor.finishColorEdit()
colorEditor.colorRgb("text", { target: { value: "#abcdef" } })
colorEditor.colorRgb("text", { target: { value: "#123456" } })
assert.equal(colorEditor.state.history.undo.length, 2)
colorEditor.undo()
assert.equal(colorEditor.selectedColors.text, "#FFFFFFA0")
colorEditor.colorText("text", { target: { value: "#01020304" } })
assert.equal(colorEditor.canRedo, false) // A fresh edit replaces the redo branch.

const stockFixture = editor()
const stockEditor = stockFixture.vm
stockEditor.changePosition("current_speed", 700, 200)
stockEditor.remove("driver_monitor")
stockEditor.changePosition("driver_monitor", 100, 700)
stockEditor.selectProfile("compact")
stockEditor.changePosition("max_speed", 200, 18)
stockEditor.state.selected = "driver_monitor"
stockEditor.color("cardFill", "#11223344")
const beforeStock = copy(stockEditor.state.draft)
const beforeStockHistory = stockEditor.state.history.undo.length
stockEditor.resetToStock()
assert.deepEqual(copy(stockEditor.state.draft), stockEditor.state.data.defaults)
assert.equal(stockEditor.state.history.undo.length, beforeStockHistory + 1)
assert.match(stockEditor.state.notice, /Save to apply/)
stockEditor.undo()
assert.deepEqual(copy(stockEditor.state.draft), beforeStock)
stockEditor.redo()
assert.deepEqual(copy(stockEditor.state.draft), stockEditor.state.data.defaults)
stockFixture.publish({ status: "ready", data: { ...snapshot(), document: copy(stockEditor.state.draft) },
  draft: copy(stockEditor.state.draft), notice: "Colors and both layouts saved." })
assert.equal(stockEditor.canUndo, false)
assert.equal(stockEditor.canRedo, false)
stockEditor.changePosition("max_speed", 100, 18)
assert.equal(stockEditor.canUndo, true)
stockFixture.publish({ status: "ready", error: "Reload failed." })
assert.equal(stockEditor.canUndo, true) // Failed reads keep the current draft and history.
stockFixture.publish({ status: "ready", data: snapshot(), draft: copy(snapshot().document) })
assert.equal(stockEditor.canUndo, false)
assert.equal(stockEditor.canRedo, false)
stockEditor.state.data.editable = false
stockEditor.changePosition("max_speed", 200, 18)
stockEditor.undo()
stockEditor.resetToStock()
assert.deepEqual(copy(stockEditor.state.draft), snapshot().document)
assert.match(OnroadLayoutPage.template, /Reset to stock StarPilot/)
assert.match(OnroadLayoutPage.template, /@click="undo"/)
assert.match(OnroadLayoutPage.template, /@click="redo"/)
assert.match(OnroadLayoutPage.template, /class="gx-layout__remove gx-icon-btn"/)
assert.match(OnroadLayoutPage.template, /Remove widget/)
assert.doesNotMatch(OnroadLayoutPage.template, />Remove from layout</)
assert.match(OnroadLayoutPage.template, /:clock24-hour="!!state\.draft\.clock24Hour"/)
assert.match(LayoutWidgetPreview.template, /clock24Hour \? '18:00' : '12:00 PM'/)

const flush = async () => { for (let i = 0; i < 10; i++) await Promise.resolve() }
function feedFixture() {
  const requests = [], updates = [], timers = new Map(); let nextTimer = 0, unauthorized = 0
  const feed = new OnroadLayoutFeed({ publish: (value) => updates.push(value), unauthorized: () => { unauthorized++ },
    fetcher: (url, options) => new Promise((resolve) => requests.push({ url, options, resolve })),
    later: (fn, ms) => { fn.delay = ms; timers.set(++nextTimer, fn); return nextTimer }, cancelTimer: (id) => timers.delete(id) })
  async function reply(index, body = snapshot(), status = 200) {
    requests[index].resolve({ ok: status === 200, status, json: async () => body }); await flush()
  }
  function fire(ms) {
    const entry = [...timers.entries()].find(([, fn]) => fn.delay === ms)
    if (!entry) return false
    timers.delete(entry[0]); entry[1](); return true
  }
  return { feed, requests, updates, timers, reply, fire, get unauthorized() { return unauthorized } }
}
const normal = feedFixture()
normal.feed.start()
assert.equal(normal.requests[0].url, "./api/ui/layout")
await normal.reply(0)
const draft = copy(normal.feed.data.document); draft.layouts.compact.max_speed.x = 80
normal.feed.save(draft)
normal.feed.load(); normal.feed.save(draft)
assert.equal(normal.requests.length, 2) // No load or second save may race a dispatched save.
assert.deepEqual(JSON.parse(normal.requests[1].options.body), { revision: "saved-revision", document: draft })
assert.equal(normal.requests[1].options.credentials, "same-origin")
await normal.reply(1, { ...snapshot(), document: draft, revision: "new-revision" })
assert.equal(normal.updates.at(-1).draft.layouts.compact.max_speed.x, 80)
assert.equal(normal.feed.data.revision, "new-revision")

for (const status of [409, 503, 400]) {
  const conflict = feedFixture(); conflict.feed.start(); await conflict.reply(0)
  conflict.feed.save(draft); await conflict.reply(1, {}, status)
  assert.equal(conflict.feed.needsReload, true)
  assert.equal(conflict.updates.at(-1).draft, undefined) // Failure never replaces the unsaved document.
  conflict.feed.save(draft); assert.equal(conflict.requests.length, 2)
  conflict.feed.load(); await conflict.reply(2)
  assert.equal(conflict.feed.needsReload, false)
}
const timeout = feedFixture(); timeout.feed.start(); await timeout.reply(0); timeout.feed.save(draft)
const expire = timeout.timers.get(timeout.feed.timer); expire()
assert.match(timeout.updates.at(-1).error, /result is unknown/)
assert.equal(timeout.requests[1].options.signal.aborted, true)
await timeout.reply(1, { ...snapshot(), document: draft })
assert.equal(timeout.feed.data.document.layouts.compact.max_speed.x, 0)
const late = feedFixture(); late.feed.start(); late.feed.stop(); await late.reply(0)
assert.equal(late.feed.data, null)
const invalid = feedFixture(); invalid.feed.start(); await invalid.reply(0, { ...snapshot(), editable: "yes" })
assert.equal(invalid.feed.data, null)
assert.equal(invalid.updates.at(-1).status, "unavailable")
const unauthorized = feedFixture(); unauthorized.feed.start(); await unauthorized.reply(0, {}, 401)
assert.equal(unauthorized.unauthorized, 1)

const settling = feedFixture()
settling.feed.start(); await settling.reply(0, { ...snapshot(), editable: false })
assert.equal(settling.updates.at(-1).data.editable, false)
assert.equal(settling.fire(5000), true)
assert.equal(settling.requests.length, 2)
await settling.reply(1, { ...snapshot(), editable: true })
assert.equal(settling.updates.at(-1).data.editable, true)
assert.equal([...settling.timers.values()].some((fn) => fn.delay === 5000), true)

const stoppedRetry = feedFixture()
stoppedRetry.feed.start(); await stoppedRetry.reply(0, { ...snapshot(), editable: false })
const pendingRetry = [...stoppedRetry.timers.values()].find((fn) => fn.delay === 5000)
stoppedRetry.feed.stop(); pendingRetry()
assert.equal(stoppedRetry.requests.length, 1)

const manualRetry = feedFixture()
manualRetry.feed.start(); await manualRetry.reply(0, { ...snapshot(), editable: false })
const cancelledRetry = [...manualRetry.timers.values()].find((fn) => fn.delay === 5000)
manualRetry.feed.load()
cancelledRetry()
assert.equal(manualRetry.requests.length, 2)
await manualRetry.reply(1, snapshot())
assert.equal(manualRetry.updates.at(-1).data.editable, true)

const boundedRetry = feedFixture()
boundedRetry.feed.start()
for (let index = 0; index < 4; index++) {
  await boundedRetry.reply(index, { ...snapshot(), editable: false })
  boundedRetry.fire(5000)
}
assert.equal(boundedRetry.requests.length, 5)
boundedRetry.feed.stop()
assert.equal([...boundedRetry.timers.values()].some((fn) => fn.delay === 5000), false)

const visual = SETTINGS_SECTIONS.find(({ id }) => id === "visual")
const rows = SettingsPage.computed.visibleRows.call({ initialPage: "hub", activeSection: visual,
  state: { data: { page: "hub" }, query: "" } })
assert.equal(rows.filter(({ row }) => row.page === "ui_layout").length, 1)
const navigated = [], host = { initialPage: "hub", state: {}, feed: { stop: () => navigated.push("stop"), load: () => assert.fail("Layout is not a generic settings endpoint"), start: (page) => navigated.push(page) } }
SettingsPage.methods.open.call(host, "ui_layout")
assert.equal(host.state.layoutOpen, true)
SettingsPage.methods.closeLayout.call(host)
assert.equal(host.state.section, "visual")
assert.deepEqual(navigated, ["stop", "hub"])
host.initialPage = "appearance"
SettingsPage.methods.open.call(host, "ui_layout")
SettingsPage.methods.closeLayout.call(host)
assert.deepEqual(navigated.slice(-2), ["stop", "appearance"])
const appSource = readFileSync(new URL("../web/js/app.js", import.meta.url), "utf8")
const editorSource = readFileSync(new URL("../web/js/onroad-layout.js", import.meta.url), "utf8")
const catalog = JSON.parse(readFileSync(new URL("../web/data/catalog.json", import.meta.url), "utf8"))
assert.ok(appSource.includes("['/theme_maker', '/theme_maker/android_auto'].includes(route.path)"))
assert.ok(appSource.includes(':key="route.path" :projection="route.path ==='))
assert.ok(appSource.includes('@target="go($event ==='))
assert.match(appSource, /goFromMenu\(path\)/)
assert.match(appSource, /requestLeave\(proceed, presentation\)/)
assert.match(appSource, /@click="goFromMenu\(item\.path\)"/)
assert.match(editorSource, /<LayoutWidgetPreview :widget="widget"/)
assert.doesNotMatch(editorSource, /<LayoutWidgetPreview v-if="!state\.preview\.url"/)
assert.match(editorSource, /<section v-if="state\.devicePreviewOpen" class="gx-layout__device"/)
assert.match(editorSource, /<img v-if="state\.preview\.url"/)
const loadedCatalog = await loadCatalog({ fetcher: async (url) => ({ ok: true,
  json: async () => url.endsWith("catalog.json") ? catalog : { schemaVersion: 1, monitor: "local" },
}) })
assert.ok(loadedCatalog.tools.some(tool => tool.path === "/theme_maker"))
assert.equal(catalog.tools.find((tool) => tool.path === "/theme_maker")?.availability, "local-only")
console.log("Colors and layout: stable editor, explicit Device preview, placement, drag/cancel, resets, save races, errors, auth and Visual navigation passed")

const railEditor = editor().vm
railEditor.selectProfile("compact")
railEditor.changePosition("conditional_mode", 260, 90)
assert.deepEqual(railEditor.layout.conditional_mode, { x: 260, y: 90, enabled: true })
railEditor.remove("conditional_mode")
assert(railEditor.inactiveWidgets.some(widget => widget.id === "conditional_mode"))
railEditor.add("conditional_mode")
assert(railEditor.activeWidgets.some(widget => widget.id === "conditional_mode"))
railEditor.undo()
assert.equal(railEditor.layout.conditional_mode.enabled, false)
railEditor.resetToStock()
assert.deepEqual(railEditor.layout.conditional_mode, { x: 476, y: 80, enabled: true })
const badRail = snapshot()
badRail.metadata.profiles.compact.widgets.model_confidence.bounds.width = 900
assert.equal(validSnapshot(badRail), false)
assert.equal(clampPlacement(data.metadata.profiles.compact, "conditional_mode", 260, 101), null)

const scoped = editor().vm
const legacyPalette = copy(scoped.state.draft.palette)
scoped.selectProfile('compact')
scoped.state.selected = 'conditional_mode'
assert.deepEqual(scoped.colorFields.map(({ id }) => id), ['cardFill', 'cardBorder'])
scoped.colorRgb('cardFill', { target: { value: '#224466' } })
assert.equal(scoped.selectedColors.cardFill, '#224466A6') // Picking a color reveals a transparent frame.
assert.deepEqual(copy(scoped.state.draft.palette), legacyPalette)
assert.equal(widgetPalette(scoped.state.draft, scoped.state.data.metadata, 'compact', 'model_confidence').cardFill, '#00000000')
scoped.state.selected = 'following_distance'
scoped.color('text', '#FEDCBAFF')
assert.equal(scoped.selectedColors.text, '#FEDCBAFF')
scoped.undo()
assert.equal(scoped.selectedColors.text, '#FFFFFFFF')
assert.equal(scoped.state.draft.widgetColors.compact.conditional_mode.cardFill, '#224466A6')
scoped.redo()
scoped.resetColors()
assert.equal(scoped.selectedColors.text, '#FFFFFFFF')
assert.equal(scoped.state.draft.widgetColors.compact.conditional_mode.cardFill, '#224466A6')
scoped.selectProfile('large')
scoped.state.selected = 'driver_monitor'
assert.equal(scoped.selectedColors.cardFill, '#00000000')
scoped.color('cardFill', '#11223344')
assert.equal(scoped.state.draft.widgetColors.compact.conditional_mode.cardFill, '#224466A6')
scoped.state.selected = 'torque_bar'
assert.equal(scoped.colorFields.length, 0)
const beforeUnsupported = copy(scoped.state.draft)
scoped.color('text', '#11223344')
assert.deepEqual(copy(scoped.state.draft), beforeUnsupported)
assert.equal(validDocument(scoped.state.draft, scoped.state.data.metadata), true)
for (const mutate of [
  doc => { doc.widgetColors.large.current_speed = { cardFill: '#FFFFFFFF' } },
  doc => { doc.widgetColors.compact.speed_limit = { text: '#FFFFFFFF' } },
  doc => { doc.widgetColors.large.unknown = {} },
  doc => { doc.widgetColors.compact = [] },
  doc => { doc.widgetColors.compact.driver_monitor = { cardFill: true } },
]) {
  const invalid = copy(scoped.state.draft); mutate(invalid)
  assert.equal(validDocument(invalid, scoped.state.data.metadata), false)
}
const migrated = editor().vm
migrated.state.draft.palette.text = '#FF0000FF'
migrated.state.selected = 'current_speed'
assert.equal(migrated.selectedColors.text, '#FF0000FF')
migrated.resetColors()
assert.equal(migrated.selectedColors.text, '#FFFFFFFF')
assert.equal(widgetPalette(migrated.state.draft, migrated.state.data.metadata, 'large', 'cruise_limits').text, '#FF0000FF')
console.log('Widget colors: real fields, visible picks, profile/widget isolation, undo/reset, legacy inheritance and invalid fields passed')
const savedSelection = editor()
savedSelection.vm.selectProfile('compact')
savedSelection.vm.state.selected = 'speed_limit_actions'
savedSelection.vm.color('cardFill', '#12345680')
const savedData = snapshot()
savedData.document = copy(savedSelection.vm.state.draft)
savedSelection.publish({ status: 'ready', data: savedData, draft: copy(savedData.document) })
assert.equal(savedSelection.vm.state.selected, 'speed_limit_actions')
assert.equal(savedSelection.vm.selectedColors.cardFill, '#12345680')

const roadEditor = editor().vm
roadEditor.roadRgb('path', { target: { value: '#FF1122' } })
assert.equal(roadEditor.roadMode, 'color')
assert.equal(roadEditor.roadColors.path, '#FF1122FF')
roadEditor.roadAlpha('path', { target: { value: '128' } })
assert.equal(roadEditor.roadGradient[0].alpha, 128 / 255)
assert.equal(roadEditor.roadLabel('pathEdge'), 'Path border')
roadEditor.selectProfile('compact')
assert.equal(roadEditor.roadMode, 'default')
assert.equal(roadEditor.roadLabel('pathEdge'), 'Closest lane markings')
roadEditor.setRoadMode('rainbow')
assert.equal(roadEditor.roadGradient.length, 12)
roadEditor.undo()
assert.equal(roadEditor.roadMode, 'default')
roadEditor.redo()
assert.equal(roadEditor.roadMode, 'rainbow')
roadEditor.resetRoad()
assert.deepEqual(copy(roadEditor.state.draft.roadColors.compact), {})
assert.equal(roadEditor.state.draft.roadColors.large.path, '#FF112280')
roadEditor.roadColor('pathEdge', '#AABBCCFF')
assert.equal(validDocument(roadEditor.state.draft, roadEditor.state.data.metadata), true)
for (const mutate of [
  doc => { doc.roadColors.large.pathMode = 'garbage' },
  doc => { doc.roadColors.compact.path = 1 },
  doc => { doc.roadColors.large = [] },
  doc => { doc.roadColors.compact.fake = '#123456FF' },
]) {
  const invalid = copy(roadEditor.state.draft); mutate(invalid)
  assert.equal(validDocument(invalid, roadEditor.state.data.metadata), false)
}
roadEditor.resetToStock()
assert.deepEqual(copy(roadEditor.state.draft.roadColors), { large: {}, compact: {} })
console.log('Road colors: original defaults, custom/rainbow modes, alpha, profile separation, undo/reset and validation passed')

// Both drag directions permit the sign/action pair and persist the whole draft.
const overlap = editor().vm
const bigBefore = copy(overlap.state.draft.layouts.large)
overlap.selectProfile('compact')
overlap.changePosition('speed_limit', 330, 108)
assert.equal(overlap.layout.speed_limit.y, 108)
overlap.changePosition('speed_limit_actions', 174, 100)
assert.equal(overlap.layout.speed_limit_actions.y, 100)
assert.equal(validDocument(overlap.state.draft, overlap.state.data.metadata), true)
assert.deepEqual(copy(overlap.state.draft.layouts.large), bigBefore)
const originalOrder = overlap.renderWidgets.map(widget => widget.id)
overlap.state.selected = 'speed_limit'
assert.deepEqual(overlap.renderWidgets.map(widget => widget.id), originalOrder)
overlap.state.selected = 'speed_limit_actions'
assert.deepEqual(overlap.renderWidgets.map(widget => widget.id), originalOrder)

overlap.changePosition('speed_limit_actions', 174, 0)
assert.equal(overlap.layout.speed_limit_actions.y, 0)
assert.equal(validDocument(overlap.state.draft, overlap.state.data.metadata), true)
assert.equal(overlap.renderWidgets.find(widget => widget.id === "speed_limit_actions").visualHeaderY, 62)
assert.equal(overlap.renderWidgets.find(widget => widget.id === "speed_limit_actions").visualInsetTop, 0)
assert.equal(overlap.renderWidgets.find(widget => widget.id === "speed_limit_actions").visualInsetBottom, 32)

const synchronizedDrag = editor()
const syncVm = synchronizedDrag.vm
const dragDraft = syncVm.state.draft
syncVm.startDrag("current_speed", synchronizedDrag.event(500, 150))
syncVm.moveDrag(synchronizedDrag.event(600, 200))
const remote = snapshot()
remote.revision = "f".repeat(64)
synchronizedDrag.publish({ status: "ready", data: remote, draft: copy(remote.document) })
assert.equal(syncVm.state.draft, dragDraft)
assert.equal(syncVm.state.drag.id, "current_speed")
assert.equal(synchronizedDrag.captures.has(1), true)
syncVm.endDrag(synchronizedDrag.event(600, 200))
await Promise.resolve()
assert.equal(syncVm.state.draft, dragDraft)
assert.equal(syncVm.state.needsReload, true)
assert.equal(syncVm.state.history.undo.length, 1)

// Persisted documents hold both layouts; connected hardware exposes its supported target only.
const compactHardware = editor().vm
compactHardware.state.data.supportedProfiles = ['compact']
compactHardware.state.profile = 'compact'
compactHardware.selectProfile('large')
assert.equal(compactHardware.state.profile, 'compact')
const largeHardware = editor().vm
largeHardware.state.data.supportedProfiles = ['large']
largeHardware.selectProfile('compact')
assert.equal(largeHardware.state.profile, 'large')

// Layer movement changes only stacking, supports undo/reset, and rejects corrupt orders.
const layers = editor().vm
const positionsBefore = copy(layers.state.draft.layouts)
const initialLayers = layers.layerWidgets.map(widget => widget.id)
layers.reorderLayer(initialLayers.at(-1), initialLayers[0])
assert.equal(layers.layerWidgets[0].id, initialLayers.at(-1))
assert.equal(layers.renderWidgets.at(-1).id, initialLayers.at(-1))
assert.deepEqual(layers.state.draft.layouts, positionsBefore)
assert.equal(validDocument(layers.state.draft, layers.state.data.metadata), true)
const savedLayers = copy(layers.state.draft.widgetOrder)
layers.undo()
assert.equal(layers.state.draft.widgetOrder, undefined)
layers.redo()
assert.deepEqual(layers.state.draft.widgetOrder, savedLayers)
layers.selectProfile('compact')
layers.reorderLayer('max_speed', 'torque_bar')
assert.deepEqual(layers.state.draft.widgetOrder.large, savedLayers.large)
layers.resetLayout()
assert.deepEqual(layers.state.draft.widgetOrder, savedLayers)
for (const order of [[], ['unknown'], [...savedLayers.large, savedLayers.large[0]], savedLayers.large.map(() => savedLayers.large[0])]) {
  const invalid = copy(layers.state.draft)
  invalid.widgetOrder.large = order
  assert.equal(validDocument(invalid, layers.state.data.metadata), false)
}
layers.selectProfile('large')
layers.resetLayout()
assert.equal(layers.state.draft.widgetOrder, undefined)
console.log('Widget layer order: movement, selection, profile isolation, validation, undo and reset passed')
