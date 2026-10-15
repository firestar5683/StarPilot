import assert from "node:assert/strict"
import { SNAP_DISTANCE, snapTargets, snapMove, snapResize, snapThreshold } from "../web/js/layout-snap.js"

const copy = value => structuredClone(value)
// Every helper call also checks that its inputs are unchanged.
function pure(fn, ...args) {
  const before = args.map(arg => typeof arg === "function" ? arg : copy(arg))
  const result = fn(...args)
  assert.deepEqual(args, before)
  return result
}
const profile = { width: 1000, height: 600, bounds: { x: 30, y: 30, width: 900, height: 540 }, reservedZones: [], widgets: {
  moving: { label: "Moving", kind: "clock", width: 100, height: 60 },
  home: { label: "Home", kind: "favorite", width: 100, height: 60 },
} }
const layout = { moving: { x: 200, y: 200, enabled: true }, home: { x: 300, y: 350, enabled: true } }
const targets = pure(snapTargets, profile, layout, "moving", () => true)
const bounds = targets.filter(target => target.kind !== "widget")
const box = { x: 34, y: 113, width: 100, height: 60 }
let result = pure(snapMove, box, bounds, 6)
assert.equal(result.x, 30)
assert.equal(result.y, 113)
assert.deepEqual(result.guides, [{ axis: "x", value: 30, kind: "bounds", label: "the edge" }])
assert.deepEqual(pure(snapMove, { ...box, x: 37 }, bounds, 6), { x: 37, y: 113, guides: [] })
result = pure(snapMove, { ...box, x: 433 }, bounds, 6)
assert.equal(result.x, 430)
assert.equal(result.guides[0].kind, "center")
result = pure(snapMove, { ...box, x: 404 }, targets, 6)
assert.equal(result.x, 400) // Start to another widget's end.
assert.equal(result.guides[0].label, "Home")
assert.deepEqual(pure(snapMove, { ...box, x: 253 }, targets, 6), { x: 253, y: 113, guides: [] })
assert.deepEqual(pure(snapMove, box, bounds, 0), { x: 34, y: 113, guides: [] })
const target = (value, line = "start", kind = "widget", axis = "x", label = "Home") => ({ axis, value, line, kind, label })
result = pure(snapMove, { ...box, x: 100 }, [target(104), target(146, "center", "center")], 6)
assert.equal(result.x, 96) // Equal distance prefers bounds center.
assert.equal(result.guides[0].kind, "center")
for (const kinds of [["zone", "widget"], ["widget", "bounds"], ["bounds", "center"]]) {
  const first = target(104, "start", kinds[0]), second = target(96, "start", kinds[1])
  assert.equal(pure(snapMove, { ...box, x: 100 }, [first, second], 6).x, 96)
}
assert.equal(pure(snapMove, { ...box, x: 100 }, [target(104), target(96)], 6).x, 104)
result = pure(snapMove, { ...box, x: 104 }, [target(100), target(200, "end"), target(100, "end", "bounds")], 6)
assert.deepEqual(result.guides, [
  { axis: "x", value: 100, kind: "bounds", label: "Home" },
  { axis: "x", value: 200, kind: "widget", label: "Home" },
])
const exclusions = copy(profile), placements = copy(layout)
for (const [id, kind, enabled] of [["disabled", "clock", false], ["hidden", "clock", true], ["torque", "torque_bar", true],
  ["pip", "pip_camera", true], ["invalid", "clock", true]]) {
  exclusions.widgets[id] = { label: id, kind, layer: "underlay", width: 60, height: 60 }
  placements[id] = { x: id === "invalid" ? Infinity : 100, y: 100, enabled }
}
exclusions.widgets.missing = { label: "missing", kind: "clock", width: 60, height: 60 }
const filtered = pure(snapTargets, exclusions, placements, "moving", id => id !== "hidden")
assert.deepEqual([...new Set(filtered.filter(item => item.kind === "widget").map(item => item.label))], ["Home", "pip"])
assert.deepEqual(pure(snapTargets, profile, layout, "absent", () => true), [])
const sidebar = copy(profile)
sidebar.widgets.moving.bounds = { x: 940, y: 0, width: 60, height: 600 }
assert.deepEqual(pure(snapTargets, sidebar, layout, "moving", () => false).filter(item => item.axis === "x").map(item => item.value), [940, 1000, 970])
const zones = copy(profile)
zones.reservedZones.push({ x: 150, y: 160, width: 100, height: 80 })
assert.deepEqual(pure(snapTargets, zones, layout, "moving", () => false).filter(item => item.kind === "zone").map(item => item.value), [150, 250, 160, 240])
const resizeBox = { x: 100, y: 150, width: 97, height: 146 }
result = pure(snapResize, resizeBox, [target(200), target(300, "end", "widget", "y")], 6)
assert.deepEqual(result, { width: 100, height: 150, guides: [
  { axis: "x", value: 200, kind: "widget", label: "Home" },
  { axis: "y", value: 300, kind: "widget", label: "Home" },
] })
assert.deepEqual(pure(snapResize, resizeBox, [target(200, "center")], 6), { width: 97, height: 146, guides: [] })
assert.deepEqual(SNAP_DISTANCE, { touch: 10, fine: 6 })
for (const [pointer, expected] of [["touch", 60], ["mouse", 36], ["pen", 36]])
  assert.equal(pure(snapThreshold, { width: 2160 }, { width: 360 }, pointer), expected)
assert.equal(pure(snapThreshold, profile, { width: 0 }, "touch"), 0)
assert.equal(pure(snapThreshold, profile, { width: -1 }, "touch"), 0)
console.log("Layout snapping: targets, matching, priority, guides, resize, scaling and purity passed")
