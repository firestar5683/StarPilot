import { widgetSize } from "./onroad-layout-document.js"

export const SNAP_DISTANCE = { touch: 10, fine: 6 }
const NON_TARGET_KINDS = ["torque_bar"]
const PRIORITY = { center: 0, bounds: 1, widget: 2, zone: 3 }
const EPSILON = 1e-6

function lines(box, axis) {
  const start = box[axis], size = box[axis === "x" ? "width" : "height"]
  return { start, center: start + size / 2, end: start + size }
}

export function snapTargets(profile, layout, id, visible) {
  if (!Object.hasOwn(profile.widgets, id)) return []
  const targets = []
  const add = (box, kind, label, names) => {
    for (const axis of ["x", "y"]) {
      const values = lines(box, axis)
      // Keep the line role so widget centers cannot attract moving edges.
      for (const line of names) targets.push({ axis, value: values[line], kind, label, line })
    }
  }
  const bounds = profile.widgets[id].bounds || profile.bounds
  add(bounds, "bounds", "the edge", ["start", "end"])
  add(bounds, "center", "the center", ["center"])
  for (const [key, widget] of Object.entries(profile.widgets)) {
    const at = layout[key]
    if (key === id || !at?.enabled || !Number.isFinite(at.x) || !Number.isFinite(at.y) ||
      !visible(key) || NON_TARGET_KINDS.includes(widget.kind)) continue
    const [width, height] = widgetSize(widget, at)
    add({ x: at.x, y: at.y, width, height }, "widget", widget.label, ["start", "center", "end"])
  }
  for (const zone of profile.reservedZones || []) add(zone, "zone", "a reserved area", ["start", "end"])
  return targets
}

function snapAxis(box, targets, threshold, axis, resize) {
  if (!(threshold > 0)) return { delta: 0, guides: [] }
  const moving = lines(box, axis), names = resize ? ["end"] : ["start", "center", "end"]
  const matches = (name, target) => (name === "center") === (target.line === "center")
  let best = null
  for (const target of targets) {
    if (target.axis !== axis) continue
    for (const name of names) {
      if (!matches(name, target)) continue
      const delta = target.value - moving[name], distance = Math.abs(delta)
      if (distance <= threshold && (!best || distance < best.distance ||
        distance === best.distance && PRIORITY[target.kind] < PRIORITY[best.target.kind])) best = { delta, distance, target }
    }
  }
  if (!best) return { delta: 0, guides: [] }
  const guides = []
  for (const target of targets) {
    if (target.axis !== axis || !names.some(name => matches(name, target) && Math.abs(moving[name] + best.delta - target.value) <= EPSILON)) continue
    const guide = { axis, value: target.value, kind: target.kind, label: target.label }
    const index = guides.findIndex(item => Math.abs(item.value - guide.value) <= EPSILON)
    if (index < 0) guides.push(guide)
    else if (PRIORITY[guide.kind] < PRIORITY[guides[index].kind]) guides[index] = guide
  }
  return { delta: best.delta, guides }
}

export function snapMove(box, targets, threshold) {
  const x = snapAxis(box, targets, threshold, "x", false), y = snapAxis(box, targets, threshold, "y", false)
  return { x: box.x + x.delta, y: box.y + y.delta, guides: [...x.guides, ...y.guides] }
}

export function snapResize(box, targets, threshold) {
  const x = snapAxis(box, targets, threshold, "x", true), y = snapAxis(box, targets, threshold, "y", true)
  return { width: box.width + x.delta, height: box.height + y.delta, guides: [...x.guides, ...y.guides] }
}

export function snapThreshold(profile, rect, pointerType) {
  return rect.width > 0 ? (pointerType === "touch" ? SNAP_DISTANCE.touch : SNAP_DISTANCE.fine) * profile.width / rect.width : 0
}
