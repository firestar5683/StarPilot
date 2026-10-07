import assert from "node:assert/strict"
import { compile } from "../web/vendor/vue/vue.esm-browser.js"
import { snapshot } from "./test_onroad_layout.mjs"
import { editorSnapshot, projectionPayload } from "../web/js/projection-layout.js"
import { OnroadLayoutPage, clampBox, clampPlacement, orderedWidgetIds, placementLimits, validDocument, validSnapshot, widgetSize } from "../web/js/onroad-layout.js"

const copy = (v) => JSON.parse(JSON.stringify(v))
const native = snapshot()
const metadata = copy(native.metadata.profiles.large)
metadata.width = 2880
metadata.bounds.width = 2820
metadata.widgets.current_speed.default.x += 510
metadata.widgets.steering_wheel.default.x += 1020
// Mirrors projection_layout.layout_metadata_for_viewport((2880, 1080)).
metadata.widgets.nav_card = { label: "Turn-by-turn", kind: "nav_card", width: 560, height: 195, colors: {},
  default: { x: 2250, y: 415, enabled: true } }
metadata.widgets.nav_map = { label: "Map overlay", kind: "nav_map", width: 860, height: 410, colors: {},
  box: { minWidth: 280, maxWidth: 2820, minHeight: 200, maxHeight: 1020 }, opacity: { min: 15, max: 100, default: 70 },
  default: { x: 1950, y: 625, enabled: false, width: 860, height: 410, opacity: 70 } }
for (const [index, label] of ["Home", "Work"].entries()) {
  const key = `nav_${label.toLowerCase()}`
  metadata.widgets[key] = { label, kind: key, width: 320, height: 110, iconSize: 110, colors: {},
    default: { x: 2195 + index * 335, y: 280, enabled: false, display: 'words' } }
}
metadata.widgetOrder = ["nav_map", ...(metadata.widgetOrder || Object.keys(native.metadata.profiles.large.widgets)), "nav_card", "nav_home", "nav_work"]
const widgets = Object.fromEntries(Object.entries(metadata.widgets).map(([id, widget]) => [id,
  { ...widget.default, ...(widget.resizable ? { size: widget.resizable.default } : {}) }]))
const doc = { version: 1, clock24Hour: false, canvas: { width: 2880, height: 1080 }, widgets }
const raw = { version: 1, document: doc, defaults: copy(doc), metadata,
  screen: { width: 1280, height: 720, margin_width: 0, margin_height: 240 },
  revision: "aa-map", editable: true, valid: true,
  colors: { palette: native.document.palette, widgetColors: native.document.widgetColors.large, roadColors: {} } }
const data = editorSnapshot(raw)
const profile = data.metadata.profiles.large
assert.equal(validSnapshot(data), true)

// Size follows the placement for box widgets, the size field for the wheel, and the metadata otherwise.
const layout = data.document.layouts.large
assert.deepEqual(widgetSize(profile.widgets.nav_map, layout.nav_map), [860, 410])
assert.deepEqual(widgetSize(profile.widgets.steering_wheel, { ...layout.steering_wheel, size: 200 }), [200, 200])
assert.deepEqual(widgetSize(profile.widgets.nav_card, layout.nav_card), [560, 195])
layout.nav_map.width = 1200
assert.equal(placementLimits(profile, "nav_map", layout).maxX, 30 + 2820 - 1200)
assert.equal(clampPlacement(profile, "nav_map", 5000, 5000, layout).x, 1650)
layout.nav_map.width = 860

// Resizing stays inside the box limits and the screen from the current corner.
assert.deepEqual(clampBox(profile, "nav_map", { x: 1950, y: 625 }, 5000, 5000), { width: 900, height: 425 })
assert.deepEqual(clampBox(profile, "nav_map", { x: 30, y: 30 }, 10, 10), { width: 280, height: 200 })
assert.equal(clampBox(profile, "nav_card", { x: 30, y: 30 }, 600, 300), null, "the turn card has a fixed size")

// Documents: width, height and opacity are required for the map and range-checked.
const good = copy(data.document)
assert.equal(validDocument(good, data.metadata), true)
for (const change of [{ opacity: 101 }, { opacity: 14 }, { opacity: 50.5 }, { width: 279 }, { height: 1021 }, { width: 860.5 }]) {
  const bad = copy(good)
  Object.assign(bad.layouts.large.nav_map, change)
  assert.equal(validDocument(bad, data.metadata), false, JSON.stringify(change))
}
const missing = copy(good)
delete missing.layouts.large.nav_map.opacity
assert.equal(validDocument(missing, data.metadata), false)
const offscreen = copy(good)
Object.assign(offscreen.layouts.large.nav_map, { x: 2000, width: 900 })
assert.equal(validDocument(offscreen, data.metadata), false, "a wide map cannot hang off the right edge")

// Box metadata is Android Auto only, and only for the map.
const comma = snapshot()
comma.metadata.profiles.large.widgets.current_speed.box = { minWidth: 100, maxWidth: 600, minHeight: 100, maxHeight: 300 }
comma.metadata.profiles.large.widgets.current_speed.opacity = { min: 10, max: 100, default: 50 }
assert.equal(validSnapshot(comma), false)
const wrongKind = copy(data)
wrongKind.metadata.profiles.large.widgets.nav_card.box = { minWidth: 100, maxWidth: 600, minHeight: 100, maxHeight: 300 }
assert.equal(validSnapshot(wrongKind), false)

// The payload carries the map's size and opacity through untouched.
const draft = copy(data.document)
Object.assign(draft.layouts.large.nav_map, { enabled: true, width: 640, height: 480, opacity: 45 })
assert.deepEqual(projectionPayload({ revision: "r", document: draft }, data.metadata).document.widgets.nav_map,
  { x: 1950, y: 625, enabled: true, width: 640, height: 480, opacity: 45 })

// Editor methods: drag the corner handle, type a size, slide the opacity; each is one undo step.
const vm = {
  state: { drag: null, profile: "large", selected: "nav_map", draft: copy(data.document), history: { undo: [], redo: [], group: null },
    placementError: "", notice: "", colorError: "" },
  editable: true, $refs: { preview: { getBoundingClientRect: () => ({ left: 0, top: 0, width: 2880, height: 1080 }),
    setPointerCapture() {}, hasPointerCapture: () => false, releasePointerCapture() {} } },
  finishColorEdit() { this.state.history.group = null },
}
Object.defineProperties(vm, {
  profile: { get: () => profile },
  layout: { get: () => vm.state.draft.layouts.large },
  selectedWidget: { get: () => profile.widgets[vm.state.selected] },
  selectedPosition: { get: () => vm.state.draft.layouts.large[vm.state.selected] },
})
for (const name of ["recordChange", "resizeBox", "boxInput", "opacityInput", "startResize", "moveDrag", "endDrag", "releaseDrag", "changePosition", "add", "remove", "reorderLayer", "setFavoriteDisplay"])
  vm[name] = OnroadLayoutPage.methods[name].bind(vm)
const pointer = (x, y) => ({ clientX: x, clientY: y, pointerId: 7, button: 0, preventDefault() {}, stopPropagation() {} })
vm.startResize("nav_map", pointer(1950 + 860, 625 + 410))
assert.equal(vm.state.drag.resize, true)
vm.moveDrag(pointer(1950 + 700, 625 + 300))
vm.endDrag(pointer(1950 + 700, 625 + 300))
assert.deepEqual([vm.layout.nav_map.width, vm.layout.nav_map.height], [700, 300])
assert.equal(vm.state.history.undo.length, 1)
vm.boxInput("width", { target: { value: "99999" } })
assert.equal(vm.layout.nav_map.width, 900, "typed sizes clamp to the room from the current corner")
vm.opacityInput({ target: { value: "40" } })
vm.opacityInput({ target: { value: "35" } })
assert.equal(vm.layout.nav_map.opacity, 35)
assert.equal(vm.state.history.undo.length, 3, "one slide is one undo step")
vm.opacityInput({ target: { value: "5" } })
assert.equal(vm.layout.nav_map.opacity, 35, "below the minimum is ignored")
assert.equal(validDocument(vm.state.draft, data.metadata), true)

// Home and Work use the same add, place, layer-order, remove and save controls.
vm.state.data = data
for (const key of ["nav_home", "nav_work"]) {
  assert.equal(vm.layout[key].enabled, false)
  vm.add(key)
  assert.equal(vm.layout[key].enabled, true)
  vm.changePosition(key, 400, 700)
  assert.deepEqual([vm.layout[key].x, vm.layout[key].y], [400, 700])
  vm.reorderLayer(key, "nav_map")
  const order = orderedWidgetIds(vm.state.draft, data.metadata, "large")
  assert.ok(order.indexOf(key) < order.indexOf("nav_map"))
  vm.remove(key)
  assert.equal(vm.layout[key].enabled, false)
}
const savedFavorites = projectionPayload({ revision: "favorites", document: vm.state.draft }, data.metadata).document
assert.equal(savedFavorites.widgets.nav_home.enabled, false)
assert.equal(savedFavorites.widgets.nav_work.enabled, false)
assert.deepEqual(savedFavorites.widgetOrder, vm.state.draft.widgetOrder.large)
assert.equal(validDocument(vm.state.draft, data.metadata), true)

// Independent icon choices shrink the preview footprint and survive saving.
vm.state.selected = 'nav_home'
const undoBeforeDisplay = vm.state.history.undo.length
vm.setFavoriteDisplay('icons')
assert.deepEqual(widgetSize(profile.widgets.nav_home, vm.layout.nav_home), [110, 110])
assert.equal(vm.layout.nav_work.display, 'words')
assert.equal(vm.state.history.undo.length, undoBeforeDisplay + 1)
vm.changePosition('nav_home', 2740, 700)
assert.equal(vm.layout.nav_home.x, 2740, 'compact icons can sit close to the right edge')
vm.setFavoriteDisplay('words')
assert.equal(vm.layout.nav_home.x, 2530, 'switching back to words keeps the whole card on screen')
assert.deepEqual(widgetSize(profile.widgets.nav_home, vm.layout.nav_home), [320, 110])
vm.setFavoriteDisplay('icons')
assert.equal(projectionPayload({revision:'display', document:vm.state.draft}, data.metadata).document.widgets.nav_home.display, 'icons')
assert.equal(validDocument(vm.state.draft, data.metadata), true)
for (const display of ['emoji', null, true, 1]) {
  const invalid = copy(vm.state.draft)
  invalid.layouts.large.nav_home.display = display
  assert.equal(validDocument(invalid, data.metadata), false)
}

compile(OnroadLayoutPage.template, { decodeEntities: value => value.replaceAll("&amp;", "&") })
console.log("Projection widgets: map resizing/opacity, Home/Work add/move/order/remove, strict documents and payload passed")
