import { GxState } from "./state.js"
import { guardUnload } from "./unload-guard.js"
import { PollTimer, connectionError } from "./polling.js"
import { reactive, watch } from "../vendor/vue/vue.esm-browser.js"
import { LayoutPreviewFeed, PREVIEW_SCENES } from "./layout-preview.js"
import { editorSnapshot, projectionPayload } from "./projection-layout.js"
import { GalaxySelect } from "./galaxy-select.js"
import { GxNotice } from "./notice.js"
import { GxDialog } from "./dialog.js"
import { GalaxySettingRow, switchRow } from "./galaxy-setting-row.js"

const PROFILES = ["large", "compact"]
const previewVisibilityKey = projection => "gx-layout-preview-visibility-v1:" + (projection ? "android-auto" : "comma")
function loadPreviewVisibility(projection) {
  const hidden = { large: { stopped_timer: true }, compact: { stopped_timer: true } }
  try {
    const saved = JSON.parse(localStorage.getItem(previewVisibilityKey(projection)))
    for (const profile of PROFILES) {
      const widgets = saved?.[profile]
      if (!widgets || typeof widgets !== "object" || Array.isArray(widgets)) continue
      hidden[profile] = {
        ...hidden[profile], ...Object.fromEntries(Object.entries(widgets)
          .filter(([id, value]) => typeof value === "boolean" && !(projection && id === "car_exit")))
      }
    }
  } catch { /* Preview controls still work when browser storage is unavailable. */ }
  return hidden
}
const COLORS = ["cardFill", "cardBorder", "text"]
const ROAD_COLORS = ["path", "pathEdge", "laneLines"]
// "default" is a legacy saved value that now renders as acceleration colors.
const PATH_MODES = ["default", "color", "rainbow", "acceleration"]
// Optional widgets start off and never block placement while off.
const OPTIONAL_WIDGETS = ["driving_mode_descriptions", "clock", "stopped_timer"]
const HEX = /^#[0-9a-fA-F]{8}$/
const clone = (value) => JSON.parse(JSON.stringify(value))
const keysEqual = (value, keys) => value && typeof value === "object" && !Array.isArray(value) &&
  Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key))
const positive = (value) => Number.isFinite(value) && value > 0 && value <= 8192
const object = (value) => value && typeof value === "object" && !Array.isArray(value)
const frontmostOrder = (order, profile) => {
  const pinned = Object.entries(profile.widgets || {}).filter(([, widget]) => widget.frontmost === true).map(([id]) => id)
  return pinned.length <= 1 && (!pinned.length || order.at(-1) === pinned[0])
}

// Display preferences ride along in the draft but are not part of the rendered layout.
export const layoutDocument = ({ display, ...document }) => document
// The device sends them beside the layout; the editor keeps them in its draft so Save, undo and reload cover them.
export const withDisplay = (data) => !object(data?.display) || !Array.isArray(data.display.rows) ? data : {
  ...data, display: data.display.rows,
  document: { ...data.document, display: { ...data.display.values } },
  defaults: { ...data.defaults, display: { ...data.display.defaults } }
}

export function orderedWidgetIds(document, metadata, profile) {
  return document.widgetOrder?.[profile] || metadata.profiles[profile].widgetOrder || Object.keys(metadata.profiles[profile].widgets)
}

export function widgetPalette(document, metadata, profile, id) {
  const colors = metadata.profiles[profile].widgets[id].colors
  return {
    ...Object.fromEntries(Object.entries(colors).map(([key, value]) => [key, value ?? document.palette[key]])),
    ...document.widgetColors[profile][id]
  }
}

export const withAlpha = (color, factor) => color.slice(0, 7) + Math.floor(parseInt(color.slice(7), 16) * factor).toString(16).padStart(2, "0")

// Steering wheels resize as a square ("size"); box widgets such as the Android Auto map take a width and height.
export function widgetSize(widget, position) {
  if (widget.iconSize && position?.display === "icons") return [widget.iconSize, widget.iconSize]
  if (widget.box) return [position?.width ?? widget.width, position?.height ?? widget.height]
  if (widget.resizable) return [position?.size ?? widget.width, position?.size ?? widget.height]
  return [widget.width, widget.height]
}

export function placementLimits(profile, id, layout = null) {
  const widget = profile.widgets[id], bounds = widget.bounds || profile.bounds
  const [width, height] = widgetSize(widget, layout?.[id])
  return {
    minX: bounds.x, maxX: bounds.x + bounds.width - width,
    minY: bounds.y, maxY: bounds.y + bounds.height - height
  }
}

// The largest box that still fits from the widget's current corner, within its own limits.
export function clampBox(profile, id, position, width, height) {
  const widget = profile.widgets[id], box = widget.box, bounds = widget.bounds || profile.bounds
  if (!box || !Number.isFinite(width) || !Number.isFinite(height)) return null
  return {
    width: Math.round(Math.max(box.minWidth, Math.min(box.maxWidth, bounds.x + bounds.width - position.x, width))),
    height: Math.round(Math.max(box.minHeight, Math.min(box.maxHeight, bounds.y + bounds.height - position.y, height)))
  }
}

export function clampPlacement(profile, id, x, y, layout = null) {
  if (!Number.isFinite(x) || !Number.isFinite(y) || !Object.hasOwn(profile.widgets, id)) return null
  const { minX, maxX, minY, maxY } = placementLimits(profile, id, layout)
  const position = { x: Math.max(minX, Math.min(maxX, Math.round(x))), y: Math.max(minY, Math.min(maxY, Math.round(y))) }
  return overlapsReserved(profile, id, position.x, position.y, layout) ? null : position
}

export function overlapsReserved(profile, id, x, y, layout = null) {
  const widget = profile.widgets[id]
  if (widget.layer === "underlay") return false
  const [width, height] = widgetSize(widget, layout?.[id])
  const intersects = (left, top, otherWidth, otherHeight) => x < left + otherWidth && x + width > left &&
    y < top + otherHeight && y + height > top
  if (profile.reservedZones.some((zone) => intersects(zone.x, zone.y, zone.width, zone.height))) return true
  const actions = profile.widgets.speed_limit_actions
  if (!actions || profile.protectedWidget !== "speed_limit_actions") return false
  const positions = layout || Object.fromEntries(Object.entries(profile.widgets).map(([key, item]) => [key, item.default]))
  if (id === "speed_limit_actions") return Object.entries(profile.widgets).some(([key, other]) => {
    const at = positions[key]
    return key !== id && key !== "speed_limit" && other.layer !== "underlay" && at &&
      !(OPTIONAL_WIDGETS.includes(key) && !at.enabled) && Number.isFinite(at.x) && Number.isFinite(at.y) &&
      intersects(at.x, at.y, ...widgetSize(other, at))
  })
  if (id === "speed_limit") return false
  const at = positions.speed_limit_actions
  if (!at || !Number.isFinite(at.x) || !Number.isFinite(at.y)) return true
  return intersects(at.x, at.y, actions.width, actions.height)
}

export function previewPoint(event, rect, profile) {
  if (!rect?.width || !rect?.height) return null
  return {
    x: (event.clientX - rect.left) * profile.width / rect.width,
    y: (event.clientY - rect.top) * profile.height / rect.height
  }
}

// Open maker pages; a route switch briefly mounts the next editor before the last one leaves.
let makerPagesOpen = 0

// Screen pixels a pointer may wobble before a press on a preview widget becomes a drag.
const DRAG_SLOP = 6

// Android Auto's own border switches; the comma screen keeps its C4 settings.
const PROJECTION_BORDERS = ["blindSpotBorder", "signalBorder"]

export function validDocument(document, metadata) {
  if (!object(document)) return false
  const profiles = metadata?.projection === true ? ["large"] : PROFILES
  if (!keysEqual(document, ["version", "palette", "layouts", "widgetColors", "roadColors", ...(Object.hasOwn(document, "widgetOrder") ? ["widgetOrder"] : []), ...(Object.hasOwn(document, "speedSources") ? ["speedSources"] : []), ...(Object.hasOwn(document, "clock24Hour") ? ["clock24Hour"] : []), ...(Object.hasOwn(document, "showMaxSpeed") ? ["showMaxSpeed"] : []), ...(metadata?.projection !== true && Object.hasOwn(document, "display") ? ["display"] : []), ...(metadata?.projection === true && Object.hasOwn(document, "largeUiGammaTrial") ? ["largeUiGammaTrial"] : []), ...(metadata?.projection === true ? PROJECTION_BORDERS.filter(key => Object.hasOwn(document, key)) : [])]) || document.version !== 6 ||
    (Object.hasOwn(document, "speedSources") && typeof document.speedSources !== "boolean") ||
    (Object.hasOwn(document, "clock24Hour") && typeof document.clock24Hour !== "boolean") ||
    (Object.hasOwn(document, "showMaxSpeed") && typeof document.showMaxSpeed !== "boolean") ||
    (Object.hasOwn(document, "display") && (!object(document.display) || !Object.values(document.display).every((value) => typeof value === "string"))) ||
    (Object.hasOwn(document, "largeUiGammaTrial") && typeof document.largeUiGammaTrial !== "boolean") ||
    PROJECTION_BORDERS.some(key => Object.hasOwn(document, key) && typeof document[key] !== "boolean") ||
    !keysEqual(document.palette, COLORS) || !COLORS.every((key) => HEX.test(document.palette[key])) ||
    !keysEqual(document.layouts, profiles) || !keysEqual(document.widgetColors, profiles) || !keysEqual(document.roadColors, profiles)) return false
  if (Object.hasOwn(document, "widgetOrder") && (!object(document.widgetOrder) ||
    !Object.entries(document.widgetOrder).every(([name, order]) => profiles.includes(name) && Array.isArray(order) &&
      order.length === Object.keys(metadata.profiles[name].widgets).length && new Set(order).size === order.length &&
      order.every(id => typeof id === "string" && Object.hasOwn(metadata.profiles[name].widgets, id)) &&
      frontmostOrder(order, metadata.profiles[name])))) return false
  return profiles.every((name) => {
    const profile = metadata.profiles[name], layout = document.layouts[name]
    const road = document.roadColors[name]
    if (!object(road) || !Object.entries(road).every(([key, value]) => key === "pathMode" ? PATH_MODES.includes(value) :
      ROAD_COLORS.includes(key) && typeof value === "string" && HEX.test(value))) return false
    const colors = document.widgetColors[name]
    if (!object(colors) || !Object.entries(colors).every(([id, overrides]) => {
      const fields = profile.widgets[id]?.colors
      return fields && Object.keys(fields).length > 0 && object(overrides) && Object.entries(overrides).every(([key, value]) =>
        Object.hasOwn(fields, key) && typeof value === "string" && HEX.test(value))
    })) return false
    return keysEqual(layout, Object.keys(profile.widgets)) && Object.entries(layout).every(([id, position]) => {
      const widget = profile.widgets[id], limits = placementLimits(profile, id, layout)
      const resizable = widget.resizable, box = widget.box, opacity = widget.opacity
      return keysEqual(position, ["x", "y", "enabled", ...(resizable ? ["size"] : []), ...(box ? ["width", "height"] : []),
        ...(opacity ? ["opacity"] : []), ...(widget.iconSize ? ["display"] : []), ...(widget.backgroundToggle ? ["background"] : [])]) &&
        (!widget.iconSize || ["words", "icons"].includes(position.display)) &&
        (!widget.backgroundToggle || typeof position.background === "boolean") &&
        (!opacity || (Number.isInteger(position.opacity) && position.opacity >= opacity.min && position.opacity <= opacity.max)) &&
        (!resizable || (Number.isInteger(position.size) && position.size >= resizable.min && position.size <= resizable.max)) &&
        (!box || (Number.isInteger(position.width) && position.width >= box.minWidth && position.width <= box.maxWidth &&
          Number.isInteger(position.height) && position.height >= box.minHeight && position.height <= box.maxHeight)) &&
        typeof position.enabled === "boolean" && (!widget.required || position.enabled === true) &&
        Number.isFinite(position.x) && Number.isFinite(position.y) &&
        position.x >= limits.minX && position.x <= limits.maxX && position.y >= limits.minY && position.y <= limits.maxY &&
        ((OPTIONAL_WIDGETS.includes(id) && !position.enabled) || !overlapsReserved(profile, id, position.x, position.y, layout))
    })
  })
}

export function validSnapshot(data) {
  const projection = data?.projection === true && data?.metadata?.projection === true
  if ((data?.projection === true) !== (data?.metadata?.projection === true)) return false
  const profiles = projection ? ["large"] : PROFILES
  if (!data || typeof data.revision !== "string" || !data.revision || typeof data.editable !== "boolean" ||
    typeof data.valid !== "boolean" || !keysEqual(data.metadata?.profiles, profiles) ||
    !Array.isArray(data.metadata.paletteFields) || data.metadata.paletteFields.length !== COLORS.length ||
    new Set(data.metadata.paletteFields.map((field) => field.id)).size !== COLORS.length ||
    !data.metadata.paletteFields.every((field) => COLORS.includes(field.id) && typeof field.label === "string" && HEX.test(field.default)) ||
    !Array.isArray(data.metadata.roadColorFields) || data.metadata.roadColorFields.length !== ROAD_COLORS.length ||
    new Set(data.metadata.roadColorFields.map((field) => field.id)).size !== ROAD_COLORS.length ||
    !data.metadata.roadColorFields.every((field) => ROAD_COLORS.includes(field.id) && typeof field.label === "string" && HEX.test(field.default)) ||
    (data.activeProfile != null && !profiles.includes(data.activeProfile))) return false
  for (const profile of Object.values(data.metadata.profiles)) {
    if (profile.widgetOrder != null && (!Array.isArray(profile.widgetOrder) ||
      profile.widgetOrder.length !== Object.keys(profile.widgets || {}).length ||
      new Set(profile.widgetOrder).size !== profile.widgetOrder.length ||
      !profile.widgetOrder.every(id => typeof id === "string" && Object.hasOwn(profile.widgets, id)) ||
      !frontmostOrder(profile.widgetOrder, profile))) return false
    const bounds = profile.bounds
    if (projection && (profile.widgets?.car_exit?.kind !== "car_exit" || profile.widgets.car_exit.required !== true)) return false
    if (profile.protectedWidget != null && (profile.protectedWidget !== "speed_limit_actions" ||
      profile.widgets?.[profile.protectedWidget]?.kind !== "speed_limit_actions")) return false
    if (!positive(profile.width) || !positive(profile.height) || typeof profile.label !== "string" ||
      !bounds || !Number.isFinite(bounds.x) || !Number.isFinite(bounds.y) || bounds.x < 0 || bounds.y < 0 ||
      !positive(bounds.width) || !positive(bounds.height) || bounds.x + bounds.width > profile.width ||
      bounds.y + bounds.height > profile.height || !profile.widgets || Array.isArray(profile.widgets) ||
      Object.keys(profile.widgets).length > 32 || !Array.isArray(profile.reservedZones) || profile.reservedZones.length > 32) return false
    for (const zone of profile.reservedZones) {
      if (typeof zone.label !== "string" || !Number.isFinite(zone.x) || !Number.isFinite(zone.y) ||
        !positive(zone.width) || !positive(zone.height) || zone.x < bounds.x || zone.y < bounds.y ||
        zone.x + zone.width > bounds.x + bounds.width || zone.y + zone.height > bounds.y + bounds.height) return false
    }
    for (const widget of Object.values(profile.widgets)) {
      const area = widget.bounds || bounds
      if (widget.visualInsetTop != null && (!Number.isFinite(widget.visualInsetTop) || widget.visualInsetTop < 0 || widget.visualInsetTop > area.height)) return false
      if (!object(widget.colors) || !Object.entries(widget.colors).every(([key, value]) =>
        COLORS.includes(key) && (value === null || (typeof value === "string" && HEX.test(value))))) return false
      if (!Number.isFinite(area.x) || !Number.isFinite(area.y) || area.x < 0 || area.y < 0 ||
        !positive(area.width) || !positive(area.height) || area.x + area.width > profile.width ||
        area.y + area.height > profile.height || typeof widget.label !== "string" || typeof widget.kind !== "string" ||
        !positive(widget.width) || !positive(widget.height) || widget.width > area.width || widget.height > area.height) return false
      if (widget.box && (data.metadata.projection !== true || widget.kind !== "nav_map" || !object(widget.opacity) ||
        ![widget.box.minWidth, widget.box.maxWidth, widget.box.minHeight, widget.box.maxHeight].every(Number.isInteger) ||
        widget.box.minWidth < 24 || widget.box.minHeight < 24 || widget.box.minWidth > widget.box.maxWidth ||
        widget.box.minHeight > widget.box.maxHeight || widget.box.maxWidth > area.width || widget.box.maxHeight > area.height ||
        ![widget.opacity.min, widget.opacity.max, widget.opacity.default].every(Number.isInteger) ||
        widget.opacity.min < 0 || widget.opacity.max > 100 || widget.opacity.min > widget.opacity.default ||
        widget.opacity.default > widget.opacity.max)) return false
      if (widget.opacity && (!projection || !["nav_map", "nav_home", "nav_work", "bookmark", "car_exit"].includes(widget.kind) ||
        !object(widget.opacity) || ![widget.opacity.min, widget.opacity.max, widget.opacity.default].every(Number.isInteger) ||
        widget.opacity.min < 0 || widget.opacity.max > 100 || widget.opacity.min > widget.opacity.default ||
        widget.opacity.default > widget.opacity.max)) return false
      if (widget.backgroundToggle != null && (!projection || !["nav_home", "nav_work", "bookmark", "car_exit"].includes(widget.kind) ||
        widget.backgroundToggle !== true || !widget.opacity)) return false
      if (widget.resizable && (widget.kind !== "steering_wheel" || !Number.isInteger(widget.resizable.min) ||
        !Number.isInteger(widget.resizable.default) || !Number.isInteger(widget.resizable.max) ||
        widget.resizable.default !== widget.width || widget.width !== widget.height ||
        widget.resizable.min < 24 || widget.resizable.max > area.width || widget.resizable.max > area.height ||
        widget.resizable.min > widget.resizable.default || widget.resizable.default > widget.resizable.max)) return false
      if (widget.iconSize != null && (!projection || !["nav_home", "nav_work", "bookmark"].includes(widget.kind) ||
        !Number.isInteger(widget.iconSize) || widget.iconSize < 44 || widget.iconSize > Math.min(widget.width, widget.height))) return false
      if (widget.required != null && (!projection || widget.kind !== "car_exit" || widget.required !== true)) return false
      if (widget.frontmost != null && (!projection || widget.kind !== "car_exit" || widget.frontmost !== true)) return false
      if (widget.kind === "car_exit" && (widget.required !== true || widget.frontmost !== true)) return false
    }
  }
  return validDocument(data.document, data.metadata) && validDocument(data.defaults, data.metadata)
}

export class OnroadLayoutFeed {
  constructor({ publish, projection = false, unauthorized = () => { }, fetcher = (...args) => fetch(...args),
    later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, projection, unauthorized, fetcher, later, cancelTimer })
    this.active = false
    this.generation = 0
    this.request = this.timer = this.data = null
    this.poller = new PollTimer({ read: () => this.load(true), interval: 5000, later, cancel: cancelTimer })
    this.error = ""
    this.needsReload = false
  }

  stop() {
    this.poller.stop()
    this.active = false
    this.generation++
    this.request?.abort()
    if (this.timer !== null) this.cancelTimer(this.timer)
    this.request = this.timer = null
  }

  start() { this.stop(); this.active = true; this.data = null; this.needsReload = false; this.poller.start(); return this.load() }
  load(background = false) { return this.run(null, { background }) }
  save(document) {
    if (!this.data?.editable || this.needsReload || !validDocument(document, this.data.metadata)) return false
    return this.run({ revision: this.data.revision, document: clone(document) })
  }

  async run(body = null, { background = false } = {}) {
    if (!this.active) return
    if (this.request) {
      // Polls yield to anything in flight; an explicit reload replaces a pending poll.
      if (background || this.saving) return
      this.request.abort(); this.generation++; this.cancelTimer(this.timer)
      this.request = this.timer = null
    }
    const saving = body !== null, generation = ++this.generation, request = new AbortController()
    this.request = request
    this.saving = saving
    if (saving || !background || !this.data && !this.error) this.publish({ status: saving ? "saving" : "loading", notice: "" })
    const fail = (message) => {
      this.error = message
      this.needsReload ||= saving
      this.publish({ status: this.data ? "ready" : "unavailable", error: message, needsReload: this.needsReload })
    }
    this.timer = this.later(() => {
      if (!this.active || generation !== this.generation) return
      request.abort()
      this.generation++
      this.request = this.timer = null
      fail(saving ? "Saving timed out. Your edits are kept here, but the saved result is unknown. Reload before saving again." :
        "Reading colors and layouts timed out. Try reloading.")
    }, 5000)
    try {
      const response = await this.fetcher(this.projection ? "./api/android-auto/layout" : "./api/ui/layout", {
        credentials: "same-origin", cache: "no-store", signal: request.signal,
        ...(saving ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(this.projection ? projectionPayload(body, this.data.metadata) : body) } : {})
      })
      if (!this.active || generation !== this.generation) return
      let data = await response.json().catch(() => null)
      if (!this.active || generation !== this.generation) return
      if (response.status === 401 || ["access_unavailable", "setup_required"].includes(data?.code)) {
        this.stop(); this.unauthorized(); return
      }
      if (response.status === 409) throw new Error("Saved values or parked status changed. Your edits are kept here. Reload before saving again.")
      if (!response.ok) throw new Error(saving ? "Colors and layout could not be saved. Your edits are kept here. Reload before trying again." :
        "Colors and layout are unavailable. Try reloading.")
      data = this.projection ? editorSnapshot(data) : withDisplay(data)
      if (!validSnapshot(data)) throw new Error("The device returned an unsupported colors and layout document. Reload to try again.")
      const initial = !this.data
      this.data = data
      this.error = ""
      this.needsReload = false
      this.publish({
        status: "ready", data, ...((saving || initial || !background) ? { draft: clone(data.document) } : {}), error: "", needsReload: false,
        notice: saving ? (this.projection ? "Android Auto layout saved." : data.failed?.length ?
          "Layout saved, but these display options did not change: " + data.failed.join(", ") + ". Reload and try again." :
          "Colors and both layouts saved.") :
          !background && !initial ? "Reloaded the saved layout." : ""
      })
      return true
    } catch (error) {
      if (this.active && generation === this.generation) fail(connectionError(error))
      return false
    } finally {
      if (this.request === request) {
        if (this.timer !== null) this.cancelTimer(this.timer)
        this.request = this.timer = null
        this.saving = false
      }
    }
  }
}

export const LayoutWidgetPreview = {
  props: ["widget", "palette", "profile", "scene", "clock24Hour"],
  methods: {
    withAlpha,
    modeLines(scene, profile) {
      const aol = scene === "aol"
      const experimental = ["experimental", "cem_stop_light", "cem_lead", "cem_curve"].includes(scene)
      if (profile === "compact" && (aol || experimental)) return aol ? ["Always On", "Lateral"] : ["ACC -", "Experimental"]
      return [aol ? "Always On Lateral" : experimental ? "ACC - Experimental" : "ACC - Chill"]
    },
  },
  template: `
    <g aria-hidden="true" class="gx-layout-widget-art" :fill="palette.text || '#ffffff'">
      <rect v-if="['driver_monitor', 'model_confidence', 'conditional_mode', 'following_distance'].includes(widget.kind)"
        x="1" y="1" :width="widget.width - 2" :height="widget.height - 2" :rx="Math.min(widget.width, widget.height) * .1"
        :fill="palette.cardFill" :stroke="palette.cardBorder" :stroke-width="profile === 'large' ? 4 : 2" />
      <template v-if="widget.kind === 'current_speed'">
        <text x="290" y="205" text-anchor="middle" font-size="176" font-weight="500">65</text>
        <text x="290" y="265" text-anchor="middle" font-size="44" font-weight="400" :fill="withAlpha(palette.text, 200 / 255)">mph</text>
      </template>
      <template v-else-if="widget.kind === 'driving_mode_descriptions'">
        <text :x="widget.width / 2" :y="widget.height / 2" text-anchor="middle" dominant-baseline="middle"
          :font-size="profile === 'large' ? 48 : 21" font-weight="600" style="filter: drop-shadow(2px 2px 1px #000000aa)">
          <tspan v-for="(line, index) in modeLines(scene, profile)" :key="index" :x="widget.width / 2"
            :y="widget.height / 2 + (index - (modeLines(scene, profile).length - 1) / 2) * 25">{{ line }}</tspan>
        </text>
      </template>
      <template v-else-if="widget.kind === 'stopped_timer'">
        <text :x="widget.width / 2" :y="widget.height * 53 / 112" text-anchor="middle" dominant-baseline="middle" :font-size="widget.height * 64 / 112" font-weight="700" fill="#b67129"
          style="filter: drop-shadow(2px 2px 1px #000000aa)">2 minutes</text>
        <text :x="widget.width / 2" :y="widget.height * 101 / 112" text-anchor="middle" dominant-baseline="middle" :font-size="widget.height * 30 / 112" font-weight="500" fill="#fffffff2"
          style="filter: drop-shadow(2px 2px 1px #000000aa)">14 seconds</text>
      </template>
      <template v-else-if="widget.kind === 'clock'">
        <text :x="widget.width / 2" :y="widget.height / 2" text-anchor="middle" dominant-baseline="middle"
          :font-size="profile === 'large' ? 48 : 21" font-weight="600"
          style="filter: drop-shadow(2px 2px 1px #000000aa)">{{ clock24Hour ? '18:00' : '12:00 PM' }}</text>
      </template>
      <template v-else-if="widget.kind === 'cruise_limits'">
        <rect x="1" y="1" :width="widget.width - 2" height="468" rx="18" fill="#10191f" stroke="#35434d" />
        <line x1="1" :x2="widget.width - 1" y1="210" y2="210" stroke="#35434d" />
        <g v-for="(label, index) in ['MAX SET', 'SLC LIMIT']" :key="label" :transform="'translate(24 ' + (index ? 210 : 0) + ')'">
          <text y="50" font-size="40" font-weight="500" :fill="index ? '#c5a3ff' : '#acbecb'">{{ label }}</text>
          <text y="160" font-size="138" font-weight="500">{{ index ? '49' : '65' }}</text>
          <text x="190" y="160" font-size="35" font-weight="400" fill="#acbecb">mph</text>
          <text v-if="index" y="208" font-size="37" font-weight="400" fill="#c5a3ff">Using speed limit</text>
          <text :y="index ? 249 : 198" font-size="37" font-weight="400" fill="#acbecb">{{ index ? 'Road limit 45 +4' : 'Your ceiling' }}</text>
        </g>
        <text x="24" y="518" font-size="37" font-weight="400" fill="#acbecb">View sources</text>
      </template>
      <template v-else-if="widget.kind === 'max_speed'">
        <defs><radialGradient id="gx-layout-speed-shadow"><stop offset="0" stop-color="#00000080" /><stop offset="1" stop-color="#00000000" /></radialGradient></defs>
        <circle cx="81" cy="81" r="81" fill="url(#gx-layout-speed-shadow)" />
        <text x="17" y="102" font-size="112" font-weight="700" :fill="withAlpha(palette.text, .9)">65</text>
        <text x="25" y="142" font-size="36" font-weight="600" :fill="withAlpha(palette.text, .9)">MAX</text>
      </template>
      <template v-else-if="widget.kind === 'speed_limit'">
        <rect x="10" y="8" width="100" height="116" rx="14" fill="none" stroke="white" stroke-width="2" />
        <text x="60" y="18" dominant-baseline="text-before-edge" text-anchor="middle" font-size="20" font-weight="600" fill="white">SPEED</text>
        <text x="60" y="36" dominant-baseline="text-before-edge" text-anchor="middle" font-size="20" font-weight="600" fill="white">LIMIT</text>
        <text x="60" y="66" dominant-baseline="text-before-edge" text-anchor="middle" font-size="50" font-weight="700" fill="white">65</text>
      </template>
      <template v-else-if="widget.kind === 'speed_limit_actions'">
        <text v-if="profile === 'compact'" x="6" :y="widget.visualHeaderY ?? -32" dominant-baseline="text-before-edge" font-size="20" font-weight="600" fill="white">NEW LIMIT 55</text>
        <text v-if="profile === 'large'" x="0" y="28" font-size="37" fill="white">New road limit 35</text>
        <g v-for="(label, index) in (profile === 'large' ? ['Apply 39', 'Keep'] : ['ACCEPT', 'REJECT'])" :key="label" :transform="'translate(' + index * (widget.width / 2 + 4) + ' ' + (profile === 'large' ? 44 : 0) + ')'">
          <rect :width="widget.width / 2 - 4" :height="profile === 'large' ? widget.height - 44 : widget.height" rx="12" :fill="palette.cardFill" :stroke="palette.cardBorder" stroke-width="2" />
          <text :x="widget.width / 4 - 2" :y="(profile === 'large' ? widget.height - 44 : widget.height) / 2 + 7" text-anchor="middle" :font-size="profile === 'large' ? 40 : 20" :font-weight="profile === 'large' ? 500 : 600" :fill="palette.text">{{ label }}</text>
        </g>
      </template>
      <g v-else-if="widget.kind === 'model_confidence'">
        <circle cx="30" cy="40" r="18" fill="#32bc82" />
      </g>
      <g v-else-if="widget.kind === 'conditional_mode'">
        <g v-if="scene === 'cem_stop_light'">
          <rect x="17" y="11" width="26" height="58" rx="8" fill="#14181b" stroke="white" stroke-width="2" />
          <circle cx="30" cy="22" r="7" fill="#070c10" /><circle cx="30" cy="22" r="5" fill="#e63442" /><circle cx="28" cy="20" r="2" fill="#ffb6b9" />
          <circle cx="30" cy="40" r="7" fill="#070c10" /><circle cx="30" cy="40" r="5" fill="#45361e" />
          <circle cx="30" cy="58" r="7" fill="#070c10" /><circle cx="30" cy="58" r="5" fill="#1c3f2c" />
        </g>
        <g v-else-if="scene === 'cem_lead'">
          <path d="M13 18 H6 V25 M47 18 H54 V25 M13 62 H6 V55 M47 62 H54 V55" fill="none" stroke="#70c0d8" stroke-width="3" />
          <path d="M15 39 L20 27 H40 L45 39" fill="none" stroke="white" stroke-width="3" />
          <rect x="14" y="37" width="32" height="18" rx="4" fill="white" />
          <path d="M18 53 V59 M42 53 V59" stroke="white" stroke-width="4" />
          <path d="M18 43 H23 M37 43 H42" stroke="#c82030" stroke-width="3" />
          <path d="M26 49 H34" stroke="#14181b" stroke-width="2" />
        </g>
        <g v-else-if="scene === 'cem_curve'" fill="none">
          <path d="M12 64 C11 49 13 31 18 16 M44 64 C43 49 45 31 50 16" stroke="white" stroke-width="3" stroke-linecap="round" />
          <path d="M28 64 C27 49 29 31 34 16" stroke="#70c0d8" stroke-width="4" stroke-dasharray="5 6" stroke-linecap="round" />
        </g>
        <g v-else>
          <circle cx="30" cy="40" r="18" fill="#70c0d8" />
          <text x="30" y="47" text-anchor="middle" font-size="16" font-weight="700" fill="#ffffff">{{ scene === 'experimental' ? 'E' : 'C' }}</text>
        </g>
      </g>
      <g v-else-if="widget.kind === 'following_distance'">
        <g fill="none" stroke-linecap="round" stroke-linejoin="round">
          <path d="M5 64 L17 16 M55 64 L43 16" :stroke="palette.text" stroke-width="3" />
          <path d="M9 59 L12 52 H48 L51 59 M13 46 L16 39 H44 L47 46" stroke="#70c0d8" stroke-width="4" />
        </g>
      </g>
      <g v-else-if="widget.kind === 'steering_wheel'" :transform="'scale(' + widget.width / 192 + ')'">
        <circle v-if="profile === 'large'" cx="96" cy="96" r="96" :fill="palette.cardFill" />
        <circle v-if="profile === 'large'" cx="96" cy="96" r="94.5" fill="none" :stroke="palette.cardBorder" stroke-width="3" />
        <g fill="none" stroke="white" stroke-width="12" stroke-linecap="round">
          <circle cx="96" cy="96" r="61" /><path d="M38 78 Q96 107 154 78 M96 103 V155" />
        </g>
      </g>
      <g v-else-if="widget.kind === 'torque_bar'" fill="none" stroke="white" stroke-linecap="round">
        <path :d="'M 12 ' + widget.height * .8 + ' Q ' + widget.width / 2 + ' ' + widget.height * .55 + ' ' + (widget.width - 12) + ' ' + widget.height * .8" :stroke-width="widget.height * .18" opacity=".3" />
        <path :d="'M ' + widget.width / 2 + ' ' + widget.height * .68 + ' Q ' + widget.width * .65 + ' ' + widget.height * .68 + ' ' + widget.width * .8 + ' ' + widget.height * .74" :stroke-width="widget.height * .18" opacity=".9" />
      </g>
      <g v-else-if="widget.kind === 'pip_camera'">
        <circle :cx="widget.width / 2" :cy="widget.height / 2" :r="widget.width / 2 - 3" fill="#152c39" stroke="#5ee5ee" stroke-width="3" />
        <text :x="widget.width / 2" :y="widget.height / 2" text-anchor="middle" :font-size="widget.height / 10">{{ widget.label }}</text>
      </g>
      <g v-else-if="widget.kind === 'driver_monitor'" :transform="'translate(' + (widget.width - (profile === 'large' ? 128 : 60)) / 2 + ' ' + (widget.height - (profile === 'large' ? 128 : 60)) / 2 + ') scale(' + (profile === 'large' ? 128 : 60) / 60 + ')'">
        <circle cx="30" cy="30" r="30" fill="#000000a6" />
        <path d="M30 30 L8 12 A29 29 0 0 1 52 12 Z" fill="#00ff40" />
        <circle cx="30" cy="31" r="6" fill="white" />
        <path d="M20 47 Q20 38 30 38 Q40 38 40 47 Z" fill="white" />
      </g>
      <g v-else-if="['nav_home', 'nav_work', 'bookmark'].includes(widget.kind)" :opacity="(widget.opacity ?? 100) / 100">
        <rect v-if="widget.background !== false" x="1" y="1" :width="widget.width - 2" :height="widget.height - 2" rx="17" fill="#0f0d17f5" stroke="#c7aef7" stroke-width="3" />
        <g v-if="widget.display === 'icons'" transform="translate(23 23) scale(2.6667)" fill="none" stroke="#c7aef7" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path v-if="widget.kind === 'nav_home'" d="M3 11 L12 3 L21 11 M5 9 V21 H10 V14 H14 V21 H19 V9" />
          <path v-else-if="widget.kind === 'bookmark'" d="M6 3 H18 V21 L12 16 L6 21 Z" />
          <path v-else d="M8 7 V4 H16 V7 M3 7 H21 V21 H3 Z M3 12 L10 15 H14 L21 12 M10 13 V17 H14 V13" />
        </g>
        <template v-else>
        <text :x="widget.width / 2" :y="widget.kind === 'bookmark' ? 48 : 43" text-anchor="middle" :font-size="widget.kind === 'bookmark' ? 34 : 25" :font-weight="widget.kind === 'bookmark' ? 600 : 400" fill="#c7aef7">{{ widget.kind === 'bookmark' ? widget.label : 'Navigate' }}</text>
        <text :x="widget.width / 2" :y="widget.kind === 'bookmark' ? 89 : 88" text-anchor="middle" :font-size="widget.kind === 'bookmark' ? 25 : 34" :font-weight="widget.kind === 'bookmark' ? 400 : 600" fill="#c7aef7">{{ widget.kind === 'bookmark' ? 'Save event' : widget.label }}</text>
        </template>
      </g>
      <g v-else-if="widget.kind === 'car_exit'" :opacity="(widget.opacity ?? 100) / 100">
        <rect v-if="widget.background !== false" x="1" y="1" :width="widget.width - 2" :height="widget.height - 2" rx="15" fill="#0f0d17a6" stroke="#c7aef7c8" stroke-width="3" />
        <g data-preview-icon="door-exit" fill="none" stroke="#c7aef7e6" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M54 20 H24 V76 H54" />
          <path d="M38 48 H78 M67 37 L78 48 L67 59" />
        </g>
      </g>
      <g v-else-if="widget.kind === 'nav_card'">
        <rect x="1" y="1" :width="widget.width - 2" :height="widget.height - 2" rx="39" fill="#0f0d17f5" stroke="#a07edcbe" stroke-width="2" />
        <g transform="translate(24 47) scale(1.7)" fill="none" stroke="white" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M16 56 V30 Q16 18 28 18 H46" /><path d="M38 6 L50 18 L38 30" />
        </g>
        <text x="148" y="78" font-size="40" font-weight="600" fill="white">Turn right onto</text>
        <text x="148" y="121" font-size="40" font-weight="600" fill="white">Las Vegas Blvd</text>
        <text x="148" y="170" font-size="30" font-weight="700" fill="#c7aef7">500 ft</text>
        <text :x="widget.width - 24" y="170" text-anchor="end" font-size="22" fill="#bebbc5">4.2 mi - 9 min</text>
      </g>
      <g v-else-if="widget.kind === 'nav_map'">
        <defs>
          <radialGradient id="gx-nav-map-fade" cx=".5" cy=".55" r=".75"><stop offset=".55" stop-color="white" /><stop offset="1" stop-color="white" stop-opacity="0" /></radialGradient>
          <mask id="gx-nav-map-mask"><rect :width="widget.width" :height="widget.height" :rx="Math.min(widget.width, widget.height) * .08" fill="url(#gx-nav-map-fade)" /></mask>
        </defs>
        <g mask="url(#gx-nav-map-mask)" :transform="'scale(' + widget.width / 600 + ' ' + widget.height / 450 + ')'" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <g :opacity="(widget.opacity ?? 50) / 100">
          <rect width="600" height="450" fill="#0b0f16" opacity=".45" />
          <g stroke="#000000a8" vector-effect="non-scaling-stroke">
            <path d="M-20 120 Q200 150 640 90 M90 -20 L130 480 M430 -20 Q400 200 470 480 M-20 330 L640 360 M260 -20 L250 480" stroke-width="11" vector-effect="non-scaling-stroke" />
          </g>
          <path d="M-20 120 Q200 150 640 90 M-20 330 L640 360" stroke="#ebf0f5" stroke-width="6" vector-effect="non-scaling-stroke" />
          <path d="M90 -20 L130 480 M430 -20 Q400 200 470 480" stroke="#bec8d2" stroke-width="4" vector-effect="non-scaling-stroke" />
          <path d="M260 -20 L250 480" stroke="#ffc45c" stroke-width="8" vector-effect="non-scaling-stroke" />
          </g>
          <path d="M300 330 Q258 300 254 250 L262 -20" stroke="#8f6bff55" stroke-width="20" vector-effect="non-scaling-stroke" />
          <path d="M300 330 Q258 300 254 250 L262 -20" stroke="#a98bff" stroke-width="9" vector-effect="non-scaling-stroke" />
        </g>
        <g :transform="'translate(' + widget.width / 2 + ' ' + widget.height * .7 + ')'">
          <circle r="22" fill="#8f6bff40" /><path d="M0 -17 L13 13 L0 6 L-13 13 Z" fill="white" stroke="#6e4fe0" stroke-width="3" stroke-linejoin="round" />
        </g>
      </g>
      <template v-else>
        <rect :width="widget.width" :height="widget.height" :fill="palette.cardFill" :stroke="palette.cardBorder" />
        <text :x="widget.width / 2" :y="widget.height / 2" text-anchor="middle" :font-size="Math.min(32, widget.width / 10)">{{ widget.label }}</text>
      </template>
    </g>`,
}

export const OnroadLayoutPage = {
  components: { GxState, LayoutWidgetPreview, GalaxySelect, GxNotice, GxDialog, GalaxySettingRow },
  props: {
    projection: { type: Boolean, default: false }, mode: { type: String, required: true }, unauthorized: { type: Function, required: true },
    initialPanel: { type: String, default: "widgets" }
  },
  emits: ["close", "target"],
  setup(props) {
    const state = reactive({
      status: "idle", data: null, draft: null, needsReload: false, error: "", notice: "",
      profile: "large", scene: "engaged", selected: null, layerDrag: null, drag: null, discard: null, leavePresentation: null, removeConfirm: null, colorError: "", placementError: "",
      inspectorPanel: ["widgets", "edit", "road", "display"].includes(props.initialPanel) && !props.projection ? props.initialPanel : "widgets", previewMode: "layout", showFavoriteZones: false, devicePreviewOpen: false,
      aboutOpen: false, tipsOpen: false, moreOpen: false, widgetsHelpOpen: false, barStuck: false, openColor: null, preview: { status: "idle", error: "", url: null },
      hiddenPreviewWidgets: loadPreviewVisibility(props.projection), history: { undo: [], redo: [], group: null }
    })
    let deferred = null
    const apply = (update) => {
      if (state.drag || state.layerDrag) { deferred = { ...deferred, ...update }; return }
      if (deferred) {
        update = { ...deferred, ...update }
        deferred = null
        if (state.draft && state.data && JSON.stringify(state.draft) !== JSON.stringify(state.data.document)) {
          update = { ...update }
          delete update.draft
          if (update.data && update.data.revision !== state.data.revision) {
            update.needsReload = true
            update.error = "Saved values changed while editing. Your edits are kept here. Reload before saving again."
          }
        }
      }

      if (update.data && state.data && !Object.hasOwn(update, "draft") && JSON.stringify(update.data.document) !== JSON.stringify(state.data.document)) {
        if (JSON.stringify(state.draft) !== JSON.stringify(state.data.document)) {
          update.needsReload = true
          update.error = "Saved values changed while editing. Your edits are kept here. Reload saved to review them."
        } else update.draft = clone(update.data.document)
      }
      if (state.needsReload && update.data && !Object.hasOwn(update, "draft")) {
        update.needsReload = true
        update.error = state.error
      }
      if (update.data) {
        if (!state.data && update.data.activeProfile) state.profile = update.data.activeProfile
        if (!update.data.metadata.profiles[state.profile]) state.profile = Object.keys(update.data.metadata.profiles)[0]
        if (!Object.hasOwn(update.data.metadata.profiles[state.profile].widgets, state.selected))
          state.selected = Object.keys(update.data.metadata.profiles[state.profile].widgets)[0] || null
        state.colorError = ""
        state.placementError = ""
      }
      const draftChanged = Object.hasOwn(update, "draft") && JSON.stringify(state.draft) !== JSON.stringify(update.draft)
      for (const [key, value] of Object.entries(update)) {
        if (JSON.stringify(state[key]) !== JSON.stringify(value)) state[key] = value
      }
      if (draftChanged || ["Colors and both layouts saved.", "Android Auto layout saved."].includes(update.notice)) state.history = { undo: [], redo: [], group: null }
    }
    const feed = new OnroadLayoutFeed({ projection: props.projection, unauthorized: props.unauthorized, publish: apply })
    watch(() => !!state.drag || !!state.layerDrag, (dragging) => { if (!dragging && deferred) apply({}) }, { flush: "sync" })
    const previewFeed = new LayoutPreviewFeed({
      unauthorized: props.unauthorized,
      publish: (update) => Object.assign(state.preview, update)
    })
    watch(() => [state.draft && JSON.stringify(state.draft), state.profile, state.scene, !!state.drag, state.data?.revision],
      () => {
        if (props.projection && state.draft && props.mode === 'local' && !state.devicePreviewOpen) {
          state.devicePreviewOpen = true
          previewFeed.start()
        }
        if (state.devicePreviewOpen && props.mode === "local") {
          const document = props.projection ? projectionPayload({ document: state.draft }, state.data.metadata).document : layoutDocument(state.draft)
          previewFeed.update(document, props.projection ? 'projection' : state.profile, state.scene, !!state.drag)
        }
      }, { flush: "sync" })
    watch(() => props.mode, (mode) => {
      if (mode !== "local") { state.devicePreviewOpen = false; previewFeed.stop() }
    })
    return { state, feed, previewFeed, scenes: PREVIEW_SCENES }
  },
  computed: {
    busy() { return ["loading", "saving"].includes(this.state.status) },
    editAvailable() { return !!this.state.data?.editable && !this.state.error && !this.state.needsReload && !this.state.discard },
    editable() { return this.editAvailable && !this.busy },
    dirty() { return !!this.state.draft && JSON.stringify(this.state.draft) !== JSON.stringify(this.state.data.document) },
    stockChanged() { return !!this.state.draft && JSON.stringify(this.state.draft) !== JSON.stringify(this.state.data.defaults) },
    canUndo() { return this.state.history.undo.length > 0 },
    canRedo() { return this.state.history.redo.length > 0 },
    pendingLeave() { return typeof this.state.discard === "function" || ["back", "device", "projection"].includes(this.state.discard) },
    inlineLeavePrompt() { return (this.pendingLeave || this.state.discard === "reload") && this.state.leavePresentation !== "modal" },
    modalLeavePrompt() { return this.pendingLeave && this.state.leavePresentation === "modal" },
    saveAvailable() { return !!this.state.data?.editable && !this.state.error && !this.state.needsReload && this.dirty && !this.state.drag && !this.state.layerDrag },
    canSavePending() { return this.saveAvailable && !this.busy },
    profile() { return this.state.data?.metadata.profiles[this.state.profile] },
    layout() { return this.state.draft?.layouts[this.state.profile] },
    widgets() { return Object.entries(this.profile?.widgets || {}).map(([id, widget]) => ({ id, ...widget })) },
    layerWidgets() {
      return orderedWidgetIds(this.state.draft, this.state.data.metadata, this.state.profile)
        .slice().reverse().map(id => this.widgets.find(widget => widget.id === id)).filter(widget => this.layout[widget.id].enabled)
    },
    listWidgets() { return this.state.layerDrag ? this.state.layerDrag.rows.map(id => this.widgets.find(widget => widget.id === id)) : this.layerWidgets },
    selectionBox() {
      if (!this.state.layerDrag) return null
      const widget = this.renderWidgets.find(widget => widget.id === this.state.selected)
      if (!widget) return null
      return {
        x: this.selectedPosition.x, y: this.selectedPosition.y - widget.visualInsetTop,
        width: widget.width, height: widget.height + widget.visualInsetTop + widget.visualInsetBottom
      }
    },
    activeWidgets() { return this.widgets.filter(({ id }) => this.layout[id].enabled) },
    renderWidgets() {
      return this.layerWidgets.filter(item => !this.previewHidden(item.id)).reverse().map((item) => {
        const below = item.visualInsetTop && this.layout[item.id].y < item.visualInsetTop
        const widget = {
          ...item, visualInsetTop: below ? 0 : item.visualInsetTop || 0,
          visualInsetBottom: below ? item.visualInsetTop : 0, visualHeaderY: below ? item.height + 8 : -(item.visualInsetTop || 0)
        }
        const [width, height] = widgetSize(widget, this.layout[widget.id])
        return {
          ...widget, width, height, ...(widget.iconSize ? { display: this.layout[widget.id].display } : {}),
          ...(widget.opacity ? { opacity: this.layout[widget.id].opacity } : {}),
          ...(widget.backgroundToggle ? { background: this.layout[widget.id].background } : {})
        }
      })
    },
    inactiveWidgets() { return this.widgets.filter(({ id }) => !this.layout[id].enabled || (this.state.drag?.fromTray && this.state.drag.id === id)) },
    availableProfiles() { return this.state.data?.supportedProfiles || (this.state.data?.activeProfile ? [this.state.data.activeProfile] : []) },
    selectedWidget() { return this.profile?.widgets[this.state.selected] },
    selectedPosition() { return this.layout?.[this.state.selected] },
    selectedSize() { return this.selectedWidget ? widgetSize(this.selectedWidget, this.selectedPosition) : [0, 0] },
    selectedColors() { return this.selectedWidget ? this.widgetColors(this.state.selected) : {} },
    colorFields() {
      return (this.state.data?.metadata.paletteFields || []).filter((field) =>
        Object.hasOwn(this.selectedWidget?.colors || {}, field.id))
    },
    roadStyle() { return this.state.draft?.roadColors[this.state.profile] || {} },
    roadMode() { const mode = this.roadStyle.pathMode || 'acceleration'; return mode === 'default' ? 'acceleration' : mode },
    roadColors() { return { ...Object.fromEntries((this.state.data?.metadata.roadColorFields || []).map(field => [field.id, field.default])), ...this.roadStyle } },
    roadGradient() {
      if (this.roadMode === 'rainbow') return Array.from({ length: 12 }, (_, i) => ({
        offset: i / 11,
        color: 'hsl(' + i / 11 * 120 + ',100%,50%)', alpha: .5 - .4 * i / 11
      }))
      if (this.roadMode === 'color') return [1, .55, .10].map((factor, i) => ({
        offset: 1 - i / 2,
        color: this.roadColors.path.slice(0, 7), alpha: Math.floor(this.alpha(this.roadColors.path) * factor) / 255
      }))
      return [{ offset: 0, color: '#72ff5c', alpha: 0 }, { offset: .5, color: '#72ff5c', alpha: 89 / 255 },
      { offset: 1, color: '#0df87a', alpha: 102 / 255 }]
    },
    limits() { return this.selectedWidget ? placementLimits(this.profile, this.state.selected, this.layout) : null },
    displayGroups() {
      const groups = []
      for (const row of this.state.data?.display || []) {
        if (row.group === "widget") continue
        const group = groups.find(item => item.name === row.group) || groups[groups.push({ name: row.group, rows: [] }) - 1]
        group.rows.push(row)
      }
      return groups
    },
    stockConfidence() { return this.displayValue("StockConfidenceBallWidget") === "Off" },
  },
  mounted() {
    if (this.mode === "local") this.feed.start()
    this._stopUnloadGuard = guardUnload(() => this.dirty || this.state.status === "saving")
    // Double-tap zoom stays off across the whole page, app bar included, while a maker page is open.
    if (makerPagesOpen++ === 0) document.documentElement.classList.add("gx-maker-open")
    this.observePinned()
  },
  updated() { this.observePinned() },
  beforeUnmount() { this.cancelDrag(); this.feed.stop(); this.previewFeed.stop(); this._stopUnloadGuard(); this._pinObserver?.disconnect(); this.unwatchRelease(); this._closeFloating?.()
    if (--makerPagesOpen === 0) document.documentElement.classList.remove("gx-maker-open")
    if (this._onPinScroll) window.removeEventListener("scroll", this._onPinScroll, { capture: true })
  },
  methods: {
    switchRow,
    previewHidden(id) { return !(this.projection && id === "car_exit") && this.state.hiddenPreviewWidgets[this.state.profile]?.[id] === true },
    togglePreviewVisibility(id) {
      if (this.state.drag || this.state.layerDrag || (this.projection && id === "car_exit")) return
      const hidden = this.state.hiddenPreviewWidgets[this.state.profile] ||= {}
      hidden[id] = !hidden[id]
      try { localStorage.setItem(previewVisibilityKey(this.projection), JSON.stringify(this.state.hiddenPreviewWidgets)) } catch { }
    },
    selectWidget(id) {
      this.state.selected = id
      this.state.inspectorPanel = "edit"
    },
    toggleColor(key) {
      this.finishColorEdit()
      this.state.openColor = this.state.openColor === key ? null : key
      // Bring an opened color's picker fully into view.
      if (this.state.openColor) this.$nextTick?.(() => this.$el?.querySelector?.(".gx-layout__color.is-open")?.scrollIntoView?.({ block: "nearest", behavior: "smooth" }))
    },
    // The more menu and the widget help close on any press outside them, including the app bar.
    toggleFloating(key, ref) {
      this.state[key] = !this.state[key]
      this._closeFloating?.()
      if (!this.state[key] || typeof document === "undefined") return
      const outside = (event) => { if (!this.$refs[ref]?.contains(event.target)) { this.state[key] = false; this._closeFloating?.() } }
      document.addEventListener("pointerdown", outside, true)
      this._closeFloating = () => { document.removeEventListener("pointerdown", outside, true); this._closeFloating = null }
    },
    closeFloating(key) {
      this.state[key] = false
      this._closeFloating?.()
    },
    // Keeps a focused editor field clear of the pinned save bar, preview and tabs once the keyboard opens.
    revealField(event) {
      const field = event.target
      if (!field?.matches?.("input:not([type=range]):not([type=checkbox]), .gx-field")) return
      setTimeout(() => {
        const tabs = this.$el?.querySelector?.(".gx-layout__sections")?.getBoundingClientRect()
        const view = window.visualViewport, top = (tabs?.bottom || 0) + 12
        const rect = field.getBoundingClientRect(), bottom = (view ? view.height + view.offsetTop : window.innerHeight) - 12
        if (rect.top < top) window.scrollBy(0, rect.top - top)
        else if (rect.bottom > bottom) window.scrollBy(0, rect.bottom - bottom)
      }, 350)
    },
    // Narrow screens pin the save bar and preview; the editor tabs stick just below their measured height.
    observePinned() {
      if (typeof ResizeObserver === "undefined" || !this.$el?.style) return
      this._pinObserver ||= new ResizeObserver(() => {
        for (const [name, ref] of [["--layout-bar-h", "leaveBar"], ["--layout-pin-h", "pinned"]])
          if (this.$refs[ref]) this.$el.style.setProperty(name, this.$refs[ref].getBoundingClientRect().height + "px")
      })
      // Once the save bar pins under the app bar, it also hides the editor scrolling up behind the app bar.
      if (!this._onPinScroll) {
        this._onPinScroll = () => {
          const bar = this.$refs.leaveBar
          const stuck = !!bar && bar.getBoundingClientRect().top <= (parseFloat(getComputedStyle(bar).top) || 0) + 1
          if (this.state.barStuck !== stuck) this.state.barStuck = stuck
        }
        window.addEventListener("scroll", this._onPinScroll, { passive: true, capture: true })
        this._onPinScroll()
      }
      for (const ref of ["leaveBar", "pinned"]) {
        const element = this.$refs[ref]
        if (element && this._pinned?.[ref] !== element) {
          if (this._pinned?.[ref]) this._pinObserver.unobserve(this._pinned[ref])
          this._pinObserver.observe(element)
          this._pinned = { ...this._pinned, [ref]: element }
        }
      }
    },
    selectPreview(mode) {
      if (this.state.drag) return
      this.state.previewMode = mode
      if (mode === "device") this.showDevicePreview()
    },
    reorderLayer(id, target) {
      if (!this.editable || this.state.drag || id === target ||
        this.profile.widgets[id]?.frontmost || this.profile.widgets[target]?.frontmost) return
      const order = [...orderedWidgetIds(this.state.draft, this.state.data.metadata, this.state.profile)]
      const from = order.indexOf(id), to = order.indexOf(target)
      if (from < 0 || to < 0) return
      const before = clone(this.state.draft)
      order.splice(from, 1)
      order.splice(to, 0, id)
      this.state.draft.widgetOrder ||= {}
      this.state.draft.widgetOrder[this.state.profile] = order
      this.state.selected = id
      this.recordChange(before)
    },
    startLayerDrag(event, id) {
      if (!this.editable || this.state.drag || this.state.layerDrag || event.button !== 0 || this.profile.widgets[id]?.frontmost) return
      this._suppressLayerClick = false
      event.preventDefault()
      event.currentTarget.setPointerCapture(event.pointerId)
      const rect = event.currentTarget.closest("[data-layer-id]").getBoundingClientRect()
      this.state.selected = id
      this.state.layerDrag = {
        id, pointerId: event.pointerId, target: null, startX: event.clientX, startY: event.clientY,
        x: rect.x, y: rect.y, width: rect.width, offsetX: event.clientX - rect.x, offsetY: event.clientY - rect.y,
        rows: this.layerWidgets.map(widget => widget.id), before: clone(this.state.draft), moved: false
      }
      this._layerTarget = event.currentTarget
      this.watchRelease()
    },
    // A lost pointerup (capture dropped, native gesture, re-render) must never leave a drag active,
    // since an active drag disables the tabs, preview switcher and navigation.
    watchRelease() {
      if (this._onRelease || typeof window === "undefined") return
      this._onRelease = (event) => {
        if (this.state.layerDrag?.pointerId === event.pointerId) this.endLayerDrag(event, event.type === "pointercancel")
        if (this.state.drag?.pointerId === event.pointerId) event.type === "pointercancel" ? this.cancelDrag() : this.endDrag(event)
        if (!this.state.drag && !this.state.layerDrag) this.unwatchRelease()
      }
      window.addEventListener("pointerup", this._onRelease)
      window.addEventListener("pointercancel", this._onRelease)
    },
    unwatchRelease() {
      if (!this._onRelease) return
      window.removeEventListener("pointerup", this._onRelease)
      window.removeEventListener("pointercancel", this._onRelease)
      this._onRelease = null
    },
    moveLayerDrag(event) {
      const drag = this.state.layerDrag
      if (!drag || drag.pointerId !== event.pointerId) return
      if (!drag.moved && Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) < 8) return
      drag.moved = true
      drag.x = event.clientX - drag.offsetX
      drag.y = event.clientY - drag.offsetY
      this._layerPoint = [event.clientX, event.clientY]
      this.retargetLayer(event.clientX, event.clientY)
      this.autoScrollLayer()
    },
    retargetLayer(clientX, clientY) {
      const drag = this.state.layerDrag
      if (!drag) return
      // A finger held over the pinned tabs or preview targets the first row visible under them.
      const tabs = this.$el?.querySelector?.(".gx-layout__sections")?.getBoundingClientRect()
      const row = document.elementFromPoint(clientX, tabs ? Math.max(clientY, tabs.bottom + 6) : clientY)?.closest('[data-layer-id]')
      const target = row?.dataset.layerId
      if (target && target !== drag.target && !this.profile.widgets[target]?.frontmost) {
        drag.target = target
        const order = [...orderedWidgetIds(drag.before, this.state.data.metadata, this.state.profile)]
        const from = order.indexOf(drag.id), to = order.indexOf(target)
        drag.after = drag.rows.indexOf(target) > drag.rows.indexOf(drag.id)
        order.splice(from, 1)
        order.splice(to, 0, drag.id)
        this.state.draft.widgetOrder ||= {}
        this.state.draft.widgetOrder[this.state.profile] = order
      }
    },
    // Scrolls while a dragged row is held near the visible edges; the top edge is the bottom of the pinned tabs.
    autoScrollLayer() {
      if (this._layerScroll || typeof requestAnimationFrame === "undefined") return
      const step = () => {
        this._layerScroll = null
        const drag = this.state.layerDrag, point = this._layerPoint
        if (!drag?.moved || !point) return
        const tabs = this.$el?.querySelector?.(".gx-layout__sections")?.getBoundingClientRect()
        const top = Math.max(60, tabs ? tabs.bottom : 0) + 40, bottom = window.innerHeight - 60
        const speed = point[1] < top ? -Math.min(24, 6 + (top - point[1]) / 3) : point[1] > bottom ? Math.min(24, 6 + (point[1] - bottom) / 3) : 0
        if (!speed) return
        const before = window.scrollY
        window.scrollBy(0, speed)
        if (window.scrollY !== before) this.retargetLayer(point[0], point[1])
        this._layerScroll = requestAnimationFrame(step)
      }
      this._layerScroll = requestAnimationFrame(step)
    },
    endLayerDrag(event, cancel = false) {
      const drag = this.state.layerDrag
      if (!drag || drag.pointerId !== event.pointerId) return
      if (cancel) this.state.draft = drag.before
      else if (drag.moved) this.recordChange(drag.before)
      this.state.layerDrag = null
      this._layerPoint = null
      if (this._layerScroll) { cancelAnimationFrame(this._layerScroll); this._layerScroll = null }
      if (this._layerTarget?.hasPointerCapture(event.pointerId)) this._layerTarget.releasePointerCapture(event.pointerId)
      this._layerTarget = null
      this._suppressLayerClick = cancel || drag.moved
    },
    layerClick(event, id) {
      if (event.detail === 0 || !this._suppressLayerClick) this.selectWidget(id)
      this._suppressLayerClick = false
    },
    layerKey(event, id) {
      if (event.key === 'Escape' && this.state.layerDrag) {
        event.preventDefault()
        this.endLayerDrag({ pointerId: this.state.layerDrag.pointerId }, true)
        return
      }
      if (this.state.layerDrag) return
      const direction = event.key === 'ArrowUp' ? -1 : event.key === 'ArrowDown' ? 1 : 0
      if (!direction) return
      event.preventDefault()
      const index = this.layerWidgets.findIndex(widget => widget.id === id)
      const target = this.layerWidgets[index + direction]
      if (target) this.reorderLayer(id, target.id)
    },
    finishColorEdit() { this.state.history.group = null },
    recordChange(before, group = null) {
      if (JSON.stringify(before) === JSON.stringify(this.state.draft)) return
      const history = this.state.history
      if (!group || history.group !== group) {
        history.undo.push(before)
        if (history.undo.length > 50) history.undo.shift()
      }
      history.redo = []
      history.group = group
    },
    undo() {
      if (!this.editable || this.state.drag || !this.canUndo) return
      this.finishColorEdit()
      const history = this.state.history
      history.redo.push(clone(this.state.draft))
      this.state.draft = history.undo.pop()
      this.state.colorError = this.state.placementError = this.state.notice = ""
    },
    redo() {
      if (!this.editable || this.state.drag || !this.canRedo) return
      this.finishColorEdit()
      const history = this.state.history
      history.undo.push(clone(this.state.draft))
      this.state.draft = history.redo.pop()
      this.state.colorError = this.state.placementError = this.state.notice = ""
    },
    resetToStock() {
      if (!this.editable || this.state.drag || !this.stockChanged) return
      const before = clone(this.state.draft)
      this.state.draft = clone(this.state.data.defaults)
      this.recordChange(before)
      this.state.colorError = this.state.placementError = ""
      this.state.notice = "Stock StarPilot colors and both layouts are restored in your draft. Save to apply them."
    },
    showDevicePreview() {
      if (this.mode !== "local" || !this.state.data || !this.state.draft || this.state.drag || this.state.devicePreviewOpen) return
      this.state.devicePreviewOpen = true
      this.previewFeed.start()
      this.previewFeed.update(this.projection ? projectionPayload({ document: this.state.draft }, this.state.data.metadata).document : layoutDocument(this.state.draft), this.projection ? 'projection' : this.state.profile, this.state.scene)
    },
    hideDevicePreview() {
      this.state.previewMode = "layout"
      this.state.devicePreviewOpen = false
      this.previewFeed.stop()
      Object.assign(this.state.preview, { status: "idle", error: "", url: null })
    },
    selectProfile(profile) {
      if (!this.availableProfiles.includes(profile) || this.state.drag) return
      this.finishColorEdit()
      this.state.profile = profile
      this.state.selected = Object.keys(this.profile.widgets)[0] || null
      this.state.placementError = ""
    },
    changePosition(id, x, y) {
      if (!this.editable) return
      const position = clampPlacement(this.profile, id, x, y, this.layout)
      if (position) {
        const before = this.state.drag ? null : clone(this.state.draft)
        Object.assign(this.layout[id], position)
        if (before) this.recordChange(before)
        this.state.placementError = ""
      } else this.state.placementError = "Keep widgets within the screen and clear of Speed limit actions. The last valid position is kept."
      this.state.notice = ""
    },
    add(id) {
      if (!this.editable || this.state.drag || !Object.hasOwn(this.profile.widgets, id)) return
      const before = clone(this.state.draft)
      this.layout[id].enabled = true
      this.recordChange(before)
      this.state.selected = id
      this.state.notice = ""
    },
    remove(id = this.state.selected) {
      if (!this.editable || this.state.drag || !Object.hasOwn(this.profile.widgets, id) || this.profile.widgets[id].required) return
      const before = clone(this.state.draft)
      this.layout[id].enabled = false
      this.recordChange(before)
      this.state.notice = ""
    },
    requestRemove(id = this.state.selected) {
      if (!this.editable || this.state.drag || this.state.layerDrag || !this.layout?.[id]?.enabled ||
        !Object.hasOwn(this.profile.widgets, id) || this.profile.widgets[id].required) return
      this.state.selected = id
      this.state.removeConfirm = id
    },
    cancelRemove() { this.state.removeConfirm = null },
    confirmRemove() {
      const id = this.state.removeConfirm
      this.state.removeConfirm = null
      this.remove(id)
    },
    setClock24Hour(event) {
      if (!this.editable || this.state.drag || this.state.layerDrag || this.selectedWidget?.kind !== "clock") return
      const before = clone(this.state.draft)
      this.state.draft.clock24Hour = event.target.checked
      this.recordChange(before)
      this.state.notice = ""
    },
    displayRow(key) { return this.state.data?.display?.find(row => row.key === key) },
    displayValue(key) { return this.state.draft?.display?.[key] },
    displayAvailable(row) { return !!row?.available && (!row.requires || this.displayValue(row.requires) === "On") },
    displaySettingRow(row) {
      const blocked = row.requires && this.displayValue(row.requires) !== "On"
      return {
        label: row.label, value: this.displayValue(row.key), choices: row.choices, available: this.displayAvailable(row),
        reason: blocked ? "Turn on Lead Indicator first" : row.reason, action: true
      }
    },
    setDisplay(key, value) {
      const row = this.displayRow(key)
      if (!this.editable || this.state.drag || this.state.layerDrag || !this.displayAvailable(row) || !row.choices.includes(value)) return
      const before = clone(this.state.draft)
      this.state.draft.display[key] = value
      this.recordChange(before)
      this.state.notice = ""
    },
    setShowMaxSpeed(event) {
      if (!this.editable || this.state.drag || this.state.layerDrag || this.selectedWidget?.kind !== "cruise_limits") return
      const before = clone(this.state.draft)
      this.state.draft.showMaxSpeed = event.target.checked
      this.recordChange(before)
      this.state.notice = ""
    },
    setLargeUiGammaTrial(value) {
      if (!this.projection || !this.editable || this.state.drag || this.state.layerDrag) return
      const before = clone(this.state.draft)
      this.state.draft.largeUiGammaTrial = value === "On"
      this.recordChange(before)
      this.state.notice = "Save to apply the camera effect on Android Auto."
    },
    setProjectionBorder(key, value) {
      if (!this.projection || !this.editable || this.state.drag || this.state.layerDrag || !PROJECTION_BORDERS.includes(key)) return
      const before = clone(this.state.draft)
      this.state.draft[key] = value === "On"
      this.recordChange(before)
      this.state.notice = "Save to apply the border on Android Auto."
    },
    setFavoriteDisplay(display) {
      if (!this.editable || this.state.drag || this.state.layerDrag || !this.selectedWidget?.iconSize ||
        !["words", "icons"].includes(display)) return
      this.finishColorEdit()
      const before = clone(this.state.draft)
      const [oldWidth] = widgetSize(this.selectedWidget, this.selectedPosition)
      this.selectedPosition.display = display
      if (["nav_home", "nav_work"].includes(this.selectedWidget.kind)) {
        const [newWidth] = widgetSize(this.selectedWidget, this.selectedPosition)
        this.selectedPosition.x += (oldWidth - newWidth) / 2
      }
      Object.assign(this.selectedPosition, clampPlacement(this.profile, this.state.selected,
        this.selectedPosition.x, this.selectedPosition.y, this.layout))
      this.recordChange(before)
      this.state.notice = ""
    },
    positionInput(axis, event) {
      const number = event.target.value.trim() === "" ? NaN : Number(event.target.value)
      if (Number.isFinite(number)) this.changePosition(this.state.selected,
        axis === "x" ? number : this.selectedPosition.x, axis === "y" ? number : this.selectedPosition.y)
      event.target.value = this.selectedPosition[axis]
    },
    resizeSelected(event) {
      if (!this.editable || this.state.drag || !this.selectedWidget?.resizable) return
      const size = Number(event.target.value), range = this.selectedWidget.resizable
      if (!Number.isInteger(size) || size < range.min || size > range.max) {
        event.target.value = this.selectedPosition.size
        return
      }
      const before = clone(this.state.draft), position = this.selectedPosition
      position.size = size
      const next = clampPlacement(this.profile, this.state.selected, position.x, position.y, this.layout)
      if (next) {
        Object.assign(position, next)
        this.recordChange(before)
        this.state.placementError = ""
      } else {
        Object.assign(position, before.layouts[this.state.profile][this.state.selected])
        this.state.placementError = "That size would cover Speed limit actions. The last valid size is kept."
      }
      event.target.value = position.size
    },
    onKey(id, event) {
      if (!this.editable) return
      const movement = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[event.key]
      if (movement) {
        event.preventDefault()
        const step = event.shiftKey ? 10 : 1, position = this.layout[id]
        this.changePosition(id, position.x + movement[0] * step, position.y + movement[1] * step)
      } else if (["Delete", "Backspace"].includes(event.key) && !this.profile.widgets[id]?.required) { event.preventDefault(); this.requestRemove(id) }
      else if (["Enter", " "].includes(event.key)) { event.preventDefault(); this.state.selected = id }
    },
    startDrag(id, event, fromTray = false) {
      if (!this.editable || event.button > 0 || this.state.drag || !Object.hasOwn(this.profile.widgets, id)) return
      const point = previewPoint(event, this.$refs.preview.getBoundingClientRect(), this.profile)
      if (!point) return
      const position = this.layout[id], widget = this.profile.widgets[id]
      const [width, height] = widgetSize(widget, position)
      this.state.selected = id
      this.finishColorEdit()
      this.state.drag = {
        id, pointerId: event.pointerId, fromTray, before: { ...position }, historyBefore: clone(this.state.draft), inside: !fromTray,
        startX: event.clientX, startY: event.clientY, moved: false,
        offsetX: fromTray ? width / 2 : point.x - position.x,
        offsetY: fromTray ? height / 2 : point.y - position.y
      }
      this._dragTarget = this.$refs.preview
      this.watchRelease()
      try { this._dragTarget.setPointerCapture?.(event.pointerId) } catch { }
      event.preventDefault()
    },
    startResize(id, event) {
      const widget = this.profile.widgets[id]
      if (!this.editable || event.button > 0 || this.state.drag || !widget?.box) return
      const point = previewPoint(event, this.$refs.preview.getBoundingClientRect(), this.profile)
      if (!point) return
      const position = this.layout[id]
      this.state.selected = id
      this.finishColorEdit()
      this.state.drag = {
        id, pointerId: event.pointerId, resize: true, before: { ...position }, historyBefore: clone(this.state.draft),
        inside: true, offsetX: point.x - position.width, offsetY: point.y - position.height
      }
      this._dragTarget = this.$refs.preview
      this.watchRelease()
      try { this._dragTarget.setPointerCapture?.(event.pointerId) } catch { }
      event.stopPropagation()
      event.preventDefault()
    },
    resizeBox(id, width, height, group = null) {
      if (!this.editable) return false
      const position = this.layout[id], next = clampBox(this.profile, id, position, width, height)
      if (!next) return false
      const before = this.state.drag ? null : clone(this.state.draft)
      Object.assign(position, next)
      if (before) this.recordChange(before, group)
      this.state.placementError = this.state.notice = ""
      return true
    },
    boxSlider(axis, event) {
      const number = Number(event.target.value)
      if (!Number.isFinite(number) || this.state.drag || this.state.layerDrag) return
      this.resizeBox(this.state.selected, axis === "width" ? number : this.selectedPosition.width,
        axis === "height" ? number : this.selectedPosition.height, this.state.profile + ":" + this.state.selected + ":" + axis)
    },
    sizeSlider(event) {
      const size = Number(event.target.value), range = this.selectedWidget?.resizable
      if (!this.editable || this.state.drag || this.state.layerDrag || !range || !Number.isInteger(size) || size < range.min || size > range.max) return
      const before = clone(this.state.draft), position = this.selectedPosition, previous = position.size
      position.size = size
      const next = clampPlacement(this.profile, this.state.selected, position.x, position.y, this.layout)
      if (next) {
        Object.assign(position, next)
        this.recordChange(before, this.state.profile + ":" + this.state.selected + ":size")
        this.state.placementError = ""
      } else {
        position.size = previous
        event.target.value = previous
        this.state.placementError = "That size would cover Speed limit actions. The last valid size is kept."
      }
    },
    boxInput(axis, event) {
      const number = event.target.value.trim() === "" ? NaN : Number(event.target.value)
      if (Number.isFinite(number)) this.resizeBox(this.state.selected, axis === "width" ? number : this.selectedPosition.width,
        axis === "height" ? number : this.selectedPosition.height)
      event.target.value = this.selectedPosition[axis]
    },
    opacityInput(event) {
      const value = Number(event.target.value), range = this.selectedWidget?.opacity
      if (!this.editable || this.state.drag || this.state.layerDrag || !range || !Number.isInteger(value) || value < range.min || value > range.max) return
      const before = clone(this.state.draft)
      this.selectedPosition.opacity = value
      this.recordChange(before, this.state.profile + ":" + this.state.selected + ":opacity")
    },
    setWidgetBackground(event) {
      if (!this.editable || this.state.drag || this.state.layerDrag || !this.selectedWidget?.backgroundToggle) return
      this.finishColorEdit()
      const before = clone(this.state.draft)
      this.selectedPosition.background = event.target.checked
      this.recordChange(before)
      this.state.notice = ""
    },
    moveDrag(event) {
      const drag = this.state.drag
      if (!drag || drag.pointerId !== event.pointerId) return
      const point = previewPoint(event, this.$refs.preview.getBoundingClientRect(), this.profile)
      if (!point) return
      if (drag.resize) { this.resizeBox(drag.id, point.x - drag.offsetX, point.y - drag.offsetY); return }
      // A finger wobbles a few pixels on every tap; only a deliberate move drags the widget.
      if (!drag.moved && Math.hypot(event.clientX - drag.startX, event.clientY - drag.startY) < DRAG_SLOP) return
      drag.moved = true
      drag.inside = point.x >= 0 && point.y >= 0 && point.x <= this.profile.width && point.y <= this.profile.height
      if (!drag.fromTray || drag.inside) {
        const x = point.x - drag.offsetX, y = point.y - drag.offsetY
        if (drag.fromTray) drag.inside = clampPlacement(this.profile, drag.id, x, y, this.layout) !== null
        this.changePosition(drag.id, x, y)
      }
      if (drag.fromTray) this.layout[drag.id].enabled = drag.inside
    },
    endDrag(event) {
      const drag = this.state.drag
      if (!drag || drag.pointerId !== event.pointerId) return
      this.moveDrag(event)
      if (drag.fromTray && !drag.inside) Object.assign(this.layout[drag.id], drag.before)
      const before = drag.historyBefore, position = this.layout[drag.id]
      if (!drag.fromTray && !drag.resize && !drag.moved) this.state.inspectorPanel = "edit"
      this.releaseDrag()
      this.recordChange(before)
    },
    releaseDrag() {
      const id = this.state.drag?.pointerId
      this.state.drag = null
      if (this._dragTarget?.hasPointerCapture?.(id)) this._dragTarget.releasePointerCapture(id)
      this._dragTarget = null
    },
    cancelDrag() {
      if (this.state.layerDrag) this.endLayerDrag({ pointerId: this.state.layerDrag.pointerId }, true)
      const drag = this.state.drag
      if (drag) Object.assign(this.layout[drag.id], drag.before)
      this.releaseDrag()
    },
    resetLayout() {
      if (!this.editable || this.state.drag) return
      const before = clone(this.state.draft)
      this.state.draft.layouts[this.state.profile] = clone(this.state.data.defaults.layouts[this.state.profile])
      if (this.state.draft.widgetOrder) {
        delete this.state.draft.widgetOrder[this.state.profile]
        if (!Object.keys(this.state.draft.widgetOrder).length) delete this.state.draft.widgetOrder
      }
      this.recordChange(before)
      this.state.placementError = ""
      this.state.notice = "This layout is reset in your draft. Save to apply it."
    },
    resetColors() {
      if (!this.editable || this.state.drag || !this.colorFields.length) return
      const before = clone(this.state.draft)
      const profile = this.state.profile, id = this.state.selected
      delete this.state.draft.widgetColors[profile][id]
      const inherited = this.selectedColors
      const stock = widgetPalette(this.state.data.defaults, this.state.data.metadata, profile, id)
      const overrides = Object.fromEntries(Object.entries(stock).filter(([key, value]) => value !== inherited[key]))
      if (Object.keys(overrides).length) this.state.draft.widgetColors[profile][id] = overrides
      this.recordChange(before)
      this.state.colorError = ""
      this.state.notice = "This widget’s colors are reset in your draft. Save to apply them."
    },
    roadPoints(points) {
      const r = this.profile.bounds
      return points.map(([x, y]) => (r.x + x * r.width) + ',' + (r.y + y * r.height)).join(' ')
    },
    roadLabel(id) {
      if (id === 'pathEdge') return this.state.profile === 'large' ? 'Path border' : 'Closest lane markings'
      if (id === 'laneLines') return this.state.profile === 'large' ? 'Lane lines' : 'Outer lane lines'
      return 'Path'
    },
    setRoadMode(mode) {
      if (!this.editable || this.state.drag || !PATH_MODES.includes(mode)) return
      const before = clone(this.state.draft)
      this.state.draft.roadColors[this.state.profile].pathMode = mode
      this.recordChange(before)
    },
    roadColor(id, value, group = null) {
      if (!this.editable || this.state.drag || !ROAD_COLORS.includes(id)) return
      if (!HEX.test(value)) { this.state.colorError = "Use eight hex digits, for example #30FF9CFF."; return }
      const before = clone(this.state.draft)
      this.state.draft.roadColors[this.state.profile][id] = value.toUpperCase()
      if (id === 'path') this.state.draft.roadColors[this.state.profile].pathMode = 'color'
      this.recordChange(before, group && this.state.profile + ':road:' + group)
      this.state.colorError = this.state.notice = ''
    },
    roadRgb(id, event) {
      const alpha = this.roadColors[id].slice(7)
      this.roadColor(id, event.target.value + (alpha === '00' ? 'FF' : alpha), 'rgb:' + id)
    },
    roadAlpha(id, event) {
      const value = Number(event.target.value)
      if (Number.isInteger(value) && value >= 0 && value <= 255)
        this.roadColor(id, this.roadColors[id].slice(0, 7) + value.toString(16).padStart(2, '0'), 'alpha:' + id)
    },
    resetRoad() {
      if (!this.editable || this.state.drag) return
      const before = clone(this.state.draft)
      this.state.draft.roadColors[this.state.profile] = {}
      this.recordChange(before)
      this.state.colorError = ''
    },
    widgetColors(id) { return widgetPalette(this.state.draft, this.state.data.metadata, this.state.profile, id) },
    color(id, value, group = null) {
      if (!this.editable || this.state.drag || !Object.hasOwn(this.selectedWidget?.colors || {}, id)) return
      if (!HEX.test(value)) { this.state.colorError = "Use eight hex digits, for example #000000A6. The last two digits set opacity."; return }
      const before = clone(this.state.draft)
      const profile = this.state.profile, widget = this.state.selected
      this.state.draft.widgetColors[profile][widget] ||= {}
      this.state.draft.widgetColors[profile][widget][id] = value.toUpperCase()
      this.recordChange(before, group && profile + ':' + widget + ':' + group)
      this.state.colorError = this.state.notice = ""
    },
    colorText(id, event) { this.color(id, event.target.value.trim()); this.finishColorEdit(); event.target.value = this.selectedColors[id] },
    colorRgb(id, event) {
      const alpha = this.selectedColors[id]?.slice(7)
      if (alpha) this.color(id, event.target.value + (alpha === '00' ? (id === 'cardFill' ? 'A6' : 'FF') : alpha), "rgb:" + id)
    },
    colorAlpha(id, event) {
      const value = Number(event.target.value)
      if (Number.isInteger(value) && value >= 0 && value <= 255)
        this.color(id, this.selectedColors[id].slice(0, 7) + value.toString(16).padStart(2, "0"), "alpha:" + id)
    },
    alpha(color) { return parseInt(color.slice(7), 16) },
    flashLeavePrompt() {
      const bar = this.$refs.leaveBar
      if (!bar) return
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      bar.scrollIntoView({ block: 'nearest', behavior: reduced ? 'instant' : 'smooth' })
      bar.querySelector('button')?.focus({ preventScroll: true })
    },
    requestLeave(action, presentation = "inline") {
      if (this.inlineLeavePrompt) { this.flashLeavePrompt(); return }
      // Saving must finish first; a load or a stray drag must not swallow navigation.
      if (this.state.status === "saving") return
      if (this.state.drag || this.state.layerDrag) this.cancelDrag()
      this.state.removeConfirm = null
      if (this.dirty) {
        this.state.discard = action
        this.state.leavePresentation = (typeof action === "function" || ["back", "device", "projection"].includes(action)) ? presentation : "inline"
      }
      else this.leave(action)
    },
    cancelLeave() {
      if (this.busy) return
      this.state.discard = null
      this.state.leavePresentation = null
    },
    leave(action) {
      this.state.discard = null
      this.state.leavePresentation = null
      if (typeof action === "function") { this.hideDevicePreview(); action() }
      else if (action === "back") { this.hideDevicePreview(); this.$emit("close") }
      else if (["projection", "device"].includes(action)) { this.hideDevicePreview(); this.$emit("target", action) }
      else this.feed.load()
    },
    save() { if (this.editable && this.dirty && !this.state.drag && !this.state.layerDrag) return this.feed.save(this.state.draft) },
    async saveAndLeave() {
      if (!this.canSavePending || !this.pendingLeave) return false
      const action = this.state.discard
      const saved = await this.feed.save(this.state.draft)
      if (saved && this.state.discard === action) this.leave(action)
      return saved
    },
  },
  template: `
    <section class="gx-settings gx-layout" aria-label="Colors and layout" :aria-busy="busy || undefined">
      <div class="gx-settings__header gx-page-header"><div><h2>{{ projection ? 'Android Auto Layout' : 'Colors & Layout' }}</h2></div>
        <button class="gx-icon-btn gx-layout__info" type="button" :aria-expanded="state.aboutOpen" aria-controls="gx-layout-about" aria-label="About this editor" title="About this editor" @click="state.aboutOpen = !state.aboutOpen"><i class="bi bi-info-circle" aria-hidden="true"></i></button>
      </div>
      <GxNotice v-if="mode === 'local' && state.data && !state.data.editable && !(projection && state.data.reason)" tone="warn">Park the vehicle and reload to edit. If it stays unavailable, reload saved settings.</GxNotice>
      <div class="gx-layout__targets">
        <nav class="gx-layout__tabs gx-layout__segment" aria-label="Layout target">
          <button class="gx-btn gx-btn--tonal" :aria-pressed="!projection" :disabled="!!state.drag" @click="$emit('target', 'device')">Comma</button>
          <button class="gx-btn gx-btn--tonal" :aria-pressed="projection" :disabled="!!state.drag" @click="$emit('target', 'projection')">Android Auto</button>
        </nav>
        <div v-if="mode === 'local' && state.data && state.draft && !projection && availableProfiles.length" class="gx-layout__tabs gx-layout__segment" role="group" aria-label="Layout size">
          <button v-for="tab in [{id:'large',label:'Big'}, {id:'compact',label:'Small'}].filter(tab => availableProfiles.includes(tab.id))" :key="tab.id" class="gx-btn gx-btn--tonal" type="button"
            :aria-pressed="state.profile === tab.id" :disabled="!!state.drag" @click="selectProfile(tab.id)">{{ tab.label }}<span v-if="state.data.activeProfile === tab.id" class="gx-layout__active" title="Active UI on the comma"><span class="gx-sr-only"> (active UI)</span></span></button>
        </div>
      </div>
      <div v-show="state.aboutOpen" id="gx-layout-about" class="gx-layout__about">
        <p v-if="!projection" class="gx-note">Choose a widget to move it or change its colors. Edit the layout available on this comma.</p><p v-else class="gx-note">Move widgets for the last connected Android Auto screen. The comma layout stays separate. Colors follow the comma theme. Changes apply on the next connection.</p>
        <p v-if="projection && state.data?.screen" class="gx-note">Last usable screen: {{ state.data.screen.width - state.data.screen.margin_width }} × {{ state.data.screen.height - state.data.screen.margin_height }} pixels.</p>
      </div>
      <p v-if="projection && state.data?.reason" class="gx-note">{{ state.data.reason }}</p>
      <GxState v-if="mode !== 'local'">Connect to local Galaxy to edit this device’s colors and layouts.</GxState>
      <template v-else>
        <div ref="leaveBar" class="gx-layout__savebar" :class="{'gx-layout__savebar--leave': inlineLeavePrompt, 'is-stuck': state.barStuck}" :inert="busy">
          <span role="status" :class="{'is-dirty': dirty && !inlineLeavePrompt && state.status !== 'saving'}">{{ inlineLeavePrompt ? (pendingLeave ? 'Leave without saving your changes?' : 'Discard your edits and reload the saved colors and layouts?') : state.status === 'saving' ? 'Saving…' : state.status === 'loading' ? 'Loading…' : !state.data ? 'No saved layout loaded' : dirty ? 'Unsaved' : state.notice || 'Saved' }}</span>
          <template v-if="inlineLeavePrompt">
            <button class="gx-btn gx-btn--tonal" type="button" aria-label="Keep editing" title="Keep editing" @click="cancelLeave"><svg class="gx-layout__action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 12a8 8 0 1 0 3-6M4 4v6h6"/></svg><span class="gx-layout__action-label">Keep editing</span></button>
            <button class="gx-btn gx-btn--danger" type="button" :aria-label="pendingLeave ? 'Discard and leave' : 'Discard and reload'" :title="pendingLeave ? 'Discard and leave' : 'Discard and reload'" @click="leave(state.discard)"><svg class="gx-layout__action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13"/></svg><span class="gx-layout__action-label">{{ pendingLeave ? 'Discard and leave' : 'Discard and reload' }}</span></button>
            <button v-if="pendingLeave" class="gx-btn" type="button" :disabled="!saveAvailable" aria-label="Save changes" title="Save changes" @click="saveAndLeave"><svg class="gx-layout__action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 3h12l4 4v14H3V3h2Zm2 0v6h10V3M7 21v-8h10v8"/></svg><span class="gx-layout__action-label">{{ state.status === 'saving' ? 'Saving…' : 'Save changes' }}</span></button>
          </template>
          <template v-else>
            <button class="gx-btn gx-btn--tonal" type="button" :disabled="!editAvailable || !canUndo || !!state.drag || !!state.layerDrag" aria-label="Undo" title="Undo" @click="undo"><svg class="gx-layout__action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5 4 10l5 5M4 10h10a6 6 0 0 1 0 12"/></svg><span class="gx-layout__action-label">Undo</span></button>
            <button class="gx-btn gx-btn--tonal" type="button" :disabled="!editAvailable || !canRedo || !!state.drag || !!state.layerDrag" aria-label="Redo" title="Redo" @click="redo"><svg class="gx-layout__action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 5 5 5-5 5m5-5H10a6 6 0 0 0 0 12"/></svg><span class="gx-layout__action-label">Redo</span></button>
            <div ref="moreMenu" class="gx-layout__more" @keydown.esc="closeFloating('moreOpen')">
              <button class="gx-btn gx-btn--tonal" type="button" :aria-expanded="state.moreOpen" aria-haspopup="menu" aria-label="More actions" title="More actions" @click="toggleFloating('moreOpen', 'moreMenu')"><svg class="gx-layout__action-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/></svg><span class="gx-layout__action-label">More</span></button>
              <template v-if="state.moreOpen">
                <div class="gx-layout__menu" role="menu" aria-label="More actions">
                  <button class="gx-layout__menu-item" type="button" role="menuitem" :disabled="!!state.drag || !!state.layerDrag" @click="closeFloating('moreOpen'); requestLeave('reload')"><svg class="gx-layout__action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 7v5h-5M20 12a8 8 0 1 0-2 5"/></svg>Reload saved</button>
                  <button class="gx-layout__menu-item" type="button" role="menuitem" :disabled="!editAvailable || !stockChanged || !!state.drag || !!state.layerDrag" @click="closeFloating('moreOpen'); resetToStock()"><svg class="gx-layout__action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 11 9-8 9 8M5 10v11h14V10M9 21v-7h6v7"/></svg>Reset to stock StarPilot</button>
                </div>
              </template>
            </div>
            <button class="gx-btn gx-layout__save" type="button" :disabled="!editAvailable || !dirty || !!state.drag || !!state.layerDrag" aria-label="Save changes" title="Save changes" @click="save"><svg class="gx-layout__action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 3h12l4 4v14H3V3h2Zm2 0v6h10V3M7 21v-8h10v8"/></svg><span class="gx-layout__action-label gx-layout__save-label">Save<span class="gx-layout__long"> changes</span></span></button>
          </template>
        </div>
        <GxNotice tone="danger" v-if="state.error">{{ state.error }}</GxNotice>
        <template v-if="state.data && state.draft">
          <p v-if="!state.data.valid" class="gx-note" role="status">{{ projection ? 'Default Android Auto positions are shown. Save to keep your separate layout.' : 'The saved customization is invalid. Default colors and positions are shown; save your edits to replace it.' }}</p>
          <div class="gx-layout__workspace" :inert="busy">
            <section ref="pinned" class="gx-card gx-layout__preview-card" aria-label="Driving screen preview" :style="{'--layout-ratio': profile.width / profile.height}">
              <div class="gx-layout__subhead"><strong>Layout preview</strong><span>{{ state.layerDrag ? "Adjusting " + selectedWidget.label : profile.width + " × " + profile.height }}</span></div>
              <div class="gx-layout__preview-bar">
                <nav class="gx-layout__switcher gx-settings-tabs" aria-label="Preview type">
                  <button class="gx-btn gx-btn--tonal" :aria-pressed="state.previewMode === 'layout'" :disabled="!!state.drag" @click="selectPreview('layout')"><span>Arrange<span class="gx-layout__long"> widgets</span></span></button>
                  <button class="gx-btn gx-btn--tonal" :aria-pressed="state.previewMode === 'device'" :disabled="!!state.drag" @click="selectPreview('device')"><span>Device<span class="gx-layout__long"> preview</span></span></button>
                </nav>
                <button v-if="!projection && profile.inputZones?.length" class="gx-icon-btn gx-layout__bar-toggle" type="button" :aria-pressed="state.showFavoriteZones" aria-label="Show Favorite tap areas" title="Show Favorite tap areas" @click="state.showFavoriteZones = !state.showFavoriteZones"><i class="bi bi-grid-3x3-gap" aria-hidden="true"></i></button>
                <button class="gx-icon-btn gx-layout__bar-toggle" type="button" :aria-expanded="state.tipsOpen" aria-controls="gx-layout-tips" aria-label="Preview tips and display behavior" title="Preview tips and display behavior" @click="state.tipsOpen = !state.tipsOpen"><i class="bi bi-question-circle" aria-hidden="true"></i></button>
              </div>
              <div class="gx-layout__stage">
              <span v-if="!projection && state.showFavoriteZones && state.previewMode === 'layout'" class="gx-layout__stage-chip" aria-hidden="true"><i class="bi bi-grid-3x3-gap"></i>Tap areas</span>
              <svg v-show="state.previewMode === 'layout'" ref="preview" class="gx-layout__preview" :viewBox="'0 0 ' + profile.width + ' ' + profile.height" :width="profile.width" :height="profile.height"
                @pointermove="moveDrag" @pointerup="endDrag" @pointercancel="cancelDrag" @lostpointercapture="cancelDrag"
                role="group" :aria-label="projection ? 'Android Auto layout preview' : (state.profile === 'large' ? 'Big' : 'Small') + ' layout preview'">
                <rect width="100%" height="100%" fill="#252b32" />
                <polygon :points="roadPoints([[0,1],[.4,.45],[.55,.45],[.83,1]])" fill="#303943" />
                <defs><linearGradient id="layout-road-gradient" gradientUnits="userSpaceOnUse" x1="0" :y1="profile.bounds.y" x2="0" :y2="profile.bounds.y + profile.bounds.height">
                  <stop v-for="stop in roadGradient" :key="stop.offset" :offset="stop.offset" :stop-color="stop.color" :stop-opacity="stop.alpha" />
                </linearGradient></defs>
                <defs><linearGradient id="layout-edge-gradient" gradientUnits="userSpaceOnUse" x1="0" :y1="profile.bounds.y" x2="0" :y2="profile.bounds.y + profile.bounds.height">
                  <stop offset="0" :stop-color="roadColors.pathEdge.slice(0,7)" stop-opacity="0" />
                  <stop offset=".5" :stop-color="roadColors.pathEdge.slice(0,7)" :stop-opacity="Math.floor(alpha(roadColors.pathEdge) * .35) / 255" />
                  <stop offset="1" :stop-color="roadColors.pathEdge.slice(0,7)" :stop-opacity="Math.floor(alpha(roadColors.pathEdge) * .4) / 255" />
                </linearGradient></defs>
                <polygon v-if="state.profile === 'large' && roadStyle.pathEdge" v-for="strip in [[[.18,1],[.44,.45],[.447,.45],[.231,1]], [[.639,1],[.503,.45],[.51,.45],[.69,1]]]"
                  :points="roadPoints(strip)" fill="url(#layout-edge-gradient)" />
                <polygon :points="roadPoints(state.profile === 'large' && roadStyle.pathEdge ? [[.231,1],[.447,.45],[.503,.45],[.639,1]] : [[.18,1],[.44,.45],[.51,.45],[.69,1]])" fill="url(#layout-road-gradient)" />
                <path v-for="(line,index) in [[[.16,1],[.43,.45]],[[.71,1],[.52,.45]],[[.02,1],[.38,.45]],[[.85,1],[.57,.45]]]" :key="'road-line-'+index"
                  :d="'M'+roadPoints(line).replace(' ', ' L')"
                  :stroke="state.profile === 'compact' && index < 2 ? (roadStyle.pathEdge || '#00ff40ff') : roadColors.laneLines"
                  opacity=".7" :stroke-width="state.profile === 'compact' ? 2 : 5" />
                <rect v-if="!projection" :x="state.profile === 'large' ? 1860 : 476" y="0" :width="state.profile === 'large' ? 300 : 60" :height="profile.height" fill="#090c10" />
                <g v-if="!projection && state.profile === 'large'" aria-hidden="true" pointer-events="none">
                  <text x="1874" y="17" font-size="14" font-weight="600" fill="#ffffffd2">SAMPLE DATA</text>
                  <g v-for="(sample, index) in [{label:'ACCEL',value:'1.08 ft/s²',accent:'#ffffff'}, {label:'STEER DELAY',value:'0.15000',accent:'#3b82f6'}, {label:'FRICTION',value:'0.12000',accent:'#22c55e'}, {label:'LAT ACCEL',value:'2.50000',accent:'#3b82f6'}, {label:'LATERAL %',value:'78.00%',accent:'#ffffff'}, {label:'TORQUE %',value:'42%',accent:'#ffffff'}, {label:'CHESTNUT',value:'',accent:'#ffffff'}]" :key="sample.label" :transform="'translate(1873 ' + (24 + index * 150) + ')'">
                    <rect width="275" height="126" rx="16" fill="#000000" stroke="#ffffff55" stroke-width="2" />
                    <rect x="253" y="4" width="18" height="118" rx="4" :fill="sample.accent" />
                    <text x="137" :y="sample.value ? 51 : 75" text-anchor="middle" :font-size="sample.label === 'STEER DELAY' ? 26 : 30" font-weight="600" fill="#ffffff">{{ sample.label }}</text>
                    <text v-if="sample.value" x="137" y="91" text-anchor="middle" font-size="30" font-weight="600" fill="#ffffff">{{ sample.value }}</text>
                  </g>
                </g>
                <rect :x="profile.bounds.x" :y="profile.bounds.y" :width="profile.bounds.width" :height="profile.bounds.height" fill="none" stroke="#8495a855" stroke-width="2" stroke-dasharray="8 8" />
                <g v-if="!projection && state.showFavoriteZones" aria-hidden="true" pointer-events="none">
                  <g v-for="zone in profile.inputZones || []" :key="zone.id">
                    <rect :x="zone.x" :y="zone.y" :width="zone.width" :height="zone.height" fill="#b799ff16" stroke="#b799ff88" :stroke-width="state.profile === 'large' ? 3 : 1" stroke-dasharray="5 5" />
                    <text :x="zone.x + zone.width / 2" :y="zone.y + zone.height - 8" text-anchor="middle" :font-size="state.profile === 'large' ? 20 : 10" fill="#d8c8ff">{{ zone.label }}</text>
                  </g>
                </g>
                <g v-for="widget in renderWidgets" :key="widget.id" class="gx-layout__widget" :class="{'is-selected': state.drag?.id === widget.id}"
                  :transform="'translate(' + layout[widget.id].x + ' ' + layout[widget.id].y + ')'" tabindex="0" role="button"
                  :aria-label="widget.label + ', x ' + layout[widget.id].x + ', y ' + layout[widget.id].y +
                    (widget.frontmost ? '. Arrow keys move; Shift moves ten pixels; required and always frontmost widget.' :
                      widget.required ? '. Arrow keys move; Shift moves ten pixels; required widget.' : '. Arrow keys move; Shift moves ten pixels; Delete removes.')"
                  :aria-pressed="state.selected === widget.id" @focus="state.selected = widget.id" @keydown="onKey(widget.id, $event)"
                  @pointerdown="startDrag(widget.id, $event)">
                  <rect class="gx-layout__hit" :y="-(widget.visualInsetTop || 0)" :width="widget.width" :height="widget.height + (widget.visualInsetTop || 0) + (widget.visualInsetBottom || 0)" fill="transparent" />
                  <LayoutWidgetPreview :widget="widget" :palette="widgetColors(widget.id)" :profile="state.profile" :scene="state.scene" :clock24-hour="!!state.draft.clock24Hour" />
                  <rect class="gx-layout__selection" :y="-(widget.visualInsetTop || 0)" :width="widget.width" :height="widget.height + (widget.visualInsetTop || 0) + (widget.visualInsetBottom || 0)" fill="none" stroke="#b799ff" :stroke-width="state.profile === 'large' ? 5 : 1.5" stroke-dasharray="6 4" />
                  <g v-if="widget.box && state.selected === widget.id && editable" class="gx-layout__resize" role="button" :aria-label="'Resize ' + widget.label"
                    :transform="'translate(' + widget.width + ' ' + widget.height + ')'" @pointerdown="startResize(widget.id, $event)">
                    <circle r="34" fill="transparent" /><circle r="16" fill="#b799ff" stroke="#16121f" stroke-width="4" />
                    <path d="M-6 6 L6 -6 M0 6 L6 0" stroke="#16121f" stroke-width="3" stroke-linecap="round" />
                  </g>
                </g>
                <rect v-if="selectionBox" class="gx-layout__outline" :x="selectionBox.x" :y="selectionBox.y" :width="selectionBox.width" :height="selectionBox.height" rx="4" fill="none" stroke="#d4baff" stroke-width="2" vector-effect="non-scaling-stroke" />
              </svg>
              </div>
              <section v-if="state.devicePreviewOpen" class="gx-layout__device" v-show="state.previewMode === 'device'" aria-label="Device preview">
                <div class="gx-layout__subhead"><strong>{{ projection ? 'Android Auto renderer preview' : 'Device preview' }}</strong><span>Preview scene</span></div>
                <div class="gx-layout__scenes" aria-label="Device preview scene">
                  <button v-for="scene in scenes" :key="scene.id" class="gx-btn gx-btn--tonal" type="button" :aria-pressed="state.scene === scene.id"
                    :disabled="!!state.drag" @click="state.scene = scene.id">{{ scene.label }}</button>
                </div>
                <div class="gx-layout__device-frame" :style="{ aspectRatio: profile.width + ' / ' + profile.height }">
                  <button class="gx-icon-btn gx-layout__device-stop" type="button" :disabled="!!state.drag" aria-label="Stop Device preview" title="Stop Device preview" @click="hideDevicePreview"><i class="bi bi-x-lg" aria-hidden="true"></i></button>
                  <svg class="gx-layout__device-outline" :viewBox="'0 0 ' + profile.width + ' ' + profile.height" aria-hidden="true"><rect v-if="selectionBox" class="gx-layout__outline" :x="selectionBox.x" :y="selectionBox.y" :width="selectionBox.width" :height="selectionBox.height" rx="4" fill="none" stroke="#d4baff" stroke-width="2" vector-effect="non-scaling-stroke" /></svg>
                  <img v-if="state.preview.url" :src="state.preview.url" alt="Device-rendered sample driving screen" />
                  <span v-else role="status">{{ state.preview.status === 'editing' ? 'Finish moving the widget to refresh Device preview.' : state.preview.status === 'updating' ? 'Updating Device preview…' : state.preview.status === 'unavailable' ? state.preview.error : 'Device preview is waiting.' }}</span>
                </div>

              </section>
              <div v-show="state.tipsOpen" id="gx-layout-tips" class="gx-layout__tips">
                <p class="gx-note">Drag widgets in Arrange widgets to place them. Readings are samples.</p>
                <p class="gx-note">Add Stopped timer to preview its minutes and seconds. Device preview renders the same widget as the driving screen; choose Stopped timer for a sample at rest.</p>
              <p class="gx-note">The steering wheel can be resized in each layout{{ projection ? ', and the map overlay takes any size and opacity' : '' }}. Existing display preferences and driving state still control when widgets appear.</p>
              <p v-if="!projection" class="gx-note">Small speed-limit signs can overlap confirmation actions. Live confirmations hide an overlapping sign until the decision ends. Select either widget in the list to edit it.</p>
              <p v-if="!projection && state.showFavoriteZones" class="gx-note">Favorite tap areas apply to enabled slots. Speed-limit controls and the steering wheel take priority when the drawer is closed.</p>
              </div>
              <p v-if="state.placementError" class="gx-note" role="status">{{ state.placementError }}</p>
            </section>
            <section class="gx-card gx-layout__inspector" aria-label="Widget placement" @focusin="revealField">
              <nav class="gx-layout__switcher gx-layout__sections gx-settings-tabs" aria-label="Editor sections">
                <button class="gx-btn gx-btn--tonal" :aria-pressed="state.inspectorPanel === 'widgets'" :disabled="!!state.drag || !!state.layerDrag" @click="state.inspectorPanel = 'widgets'">Widgets</button>
                <button class="gx-btn gx-btn--tonal" :aria-pressed="state.inspectorPanel === 'edit'" :disabled="!!state.drag || !!state.layerDrag" @click="state.inspectorPanel = 'edit'"><span>Edit<span class="gx-layout__long"> widget</span></span></button>
                <button v-if="!projection" class="gx-btn gx-btn--tonal" :aria-pressed="state.inspectorPanel === 'road'" :disabled="!!state.drag || !!state.layerDrag" @click="state.inspectorPanel = 'road'"><span>Road<span class="gx-layout__long"> colors</span></span></button>
                <button v-if="projection || displayGroups.length" class="gx-btn gx-btn--tonal" :aria-pressed="state.inspectorPanel === 'display'" :disabled="!!state.drag || !!state.layerDrag" @click="state.inspectorPanel = 'display'">Display</button>
              </nav>
              <div v-show="state.inspectorPanel === 'widgets'" class="gx-layout__panel">
              <div ref="widgetsHelp" class="gx-layout__subhead gx-layout__help-anchor"><h3>Widgets</h3><span>{{ activeWidgets.length }} active</span>
                <button class="gx-icon-btn gx-layout__info" type="button" :aria-expanded="state.widgetsHelpOpen" aria-controls="gx-layout-widgets-help" aria-label="How the widget list works" title="How the widget list works" @click="toggleFloating('widgetsHelpOpen', 'widgetsHelp')"><i class="bi bi-info-circle" aria-hidden="true"></i></button>
                <div v-show="state.widgetsHelpOpen" id="gx-layout-widgets-help" class="gx-layout__popover" @click="closeFloating('widgetsHelpOpen')" @keydown.esc="closeFloating('widgetsHelpOpen')">
                  <p>Tap a widget to edit it.</p><p>Drag ⠿ to reorder. The top row is in front, and alerts stay above all widgets.</p><p>The eye hides a widget in this preview only. The driving screen doesn't change.</p>
                </div>
              </div>
              <div class="gx-layout__widget-list"><div v-for="widget in listWidgets" :key="widget.id" class="gx-layout__layer" :data-layer-id="widget.id"
                :class="{'is-dragging': state.layerDrag?.id === widget.id && state.layerDrag?.moved, 'is-drop-target': state.layerDrag?.target === widget.id && state.layerDrag?.id !== widget.id, 'is-drop-after': state.layerDrag?.after}">
                <button class="gx-layout__row-grip gx-icon-btn" type="button"
                  :aria-label="widget.frontmost ? widget.label + ' is pinned above all widgets' : 'Reorder ' + widget.label"
                  :disabled="!editAvailable || !!state.drag || widget.frontmost"
                  :title="widget.frontmost ? 'Always above other widgets' : 'Drag to reorder. Up and down keys reorder.'"
                  @pointerdown="startLayerDrag($event, widget.id)" @pointermove="moveLayerDrag($event)"
                  @pointerup="endLayerDrag($event)" @pointercancel="endLayerDrag($event, true)" @lostpointercapture="endLayerDrag($event, true)"
                  @keydown="layerKey($event, widget.id)" @click="layerClick($event, widget.id)"><span aria-hidden="true">{{ widget.frontmost ? '↑' : '⠿' }}</span></button>
                <button class="gx-layout__layer-name" type="button" :aria-pressed="state.selected === widget.id" :disabled="!!state.drag || !!state.layerDrag"
                  @click="selectWidget(widget.id)">{{ widget.label }}</button>
                <button v-if="!projection || widget.id !== 'car_exit'" class="gx-layout__visibility gx-icon-btn" type="button" :disabled="!!state.drag || !!state.layerDrag"
                  :aria-label="(previewHidden(widget.id) ? 'Show ' : 'Hide ') + widget.label + ' in arrangement preview'"
                  :title="(previewHidden(widget.id) ? 'Show ' : 'Hide ') + widget.label + ' in arrangement preview only'"
                  :aria-pressed="!previewHidden(widget.id)" @click="togglePreviewVisibility(widget.id)">
                  <i class="bi" :class="previewHidden(widget.id) ? 'bi-eye-slash' : 'bi-eye'" aria-hidden="true"></i>
                </button>
                <button v-if="!widget.required" class="gx-layout__remove gx-icon-btn" type="button" :aria-label="'Remove ' + widget.label" :disabled="!editAvailable || !!state.drag || !!state.layerDrag"
                  @click="requestRemove(widget.id)"><span aria-hidden="true">−</span></button>
                <span v-else class="gx-note gx-layout__required" title="This control cannot be removed or placed below another widget.">Required</span>
              </div></div>
              <Teleport to="body"><div v-if="state.layerDrag?.moved" class="gx-layout__drag-ghost" aria-hidden="true"
                :style="{left: state.layerDrag.x + 'px', top: state.layerDrag.y + 'px', width: state.layerDrag.width + 'px'}">
                <span aria-hidden="true">⠿</span><strong>{{ selectedWidget.label }}</strong><span>↕</span>
              </div></Teleport>
              <div class="gx-layout__tray" role="group" aria-labelledby="gx-layout-tray-title">
                <div class="gx-layout__subhead"><h4 id="gx-layout-tray-title">Inactive widgets</h4><span>{{ inactiveWidgets.length }}</span></div>
                <p v-if="inactiveWidgets.length" class="gx-note">Drag a widget onto the preview, or tap + to add it.</p>
                <div v-if="inactiveWidgets.length" class="gx-layout__chips">
                  <div v-for="widget in inactiveWidgets" :key="widget.id" class="gx-layout__tray-item">
                    <button class="gx-layout__drag-handle" type="button" :disabled="!editAvailable || state.previewMode !== 'layout'" :aria-label="'Drag ' + widget.label + ' onto preview'"
                      @pointerdown="startDrag(widget.id, $event, true)"><i class="bi bi-grip-vertical" aria-hidden="true"></i></button><span class="gx-layout__inactive-name">{{ widget.label }}</span>
                    <button class="gx-icon-btn gx-layout__chip-add" type="button" :aria-label="'Add ' + widget.label" :title="'Add ' + widget.label" :disabled="!editAvailable || !!state.drag" @click="add(widget.id)"><i class="bi bi-plus-lg" aria-hidden="true"></i></button>
                  </div>
                </div>
                <p v-else class="gx-note">All available widgets are on this layout.</p>
              </div>
              <button class="gx-btn gx-btn--tonal gx-layout__reset" type="button" :disabled="!editAvailable || !!state.drag" @click="resetLayout">Reset this layout</button>
              </div>
              <div v-show="state.inspectorPanel === 'edit'" class="gx-layout__panel">
                <label class="gx-layout__widget-picker"><span class="gx-layout__picker-head">Selected widget<span v-if="selectedWidget && selectedPosition.enabled" class="gx-note">{{ selectedSize[0] }} × {{ selectedSize[1] + (selectedWidget.box ? 0 : selectedWidget.visualInsetTop || 0) }} px</span></span><GalaxySelect class="gx-field gx-field--full" :value="state.selected" :disabled="!!state.drag" @change="state.selected = $event.target.value">
                  <option v-for="widget in widgets" :key="widget.id" :value="widget.id">{{ widget.label }}{{ layout[widget.id].enabled ? '' : ' · Inactive' }}</option>
                </GalaxySelect></label>
                <div v-if="selectedWidget && !selectedPosition.enabled" class="gx-layout__panel"><p class="gx-note">Add this widget to edit its position and colors.</p><button class="gx-btn" :disabled="!editAvailable" @click="add(state.selected)">Add to layout</button></div>
              <div v-if="selectedWidget && selectedPosition.enabled" class="gx-layout__position">
                <label v-if="selectedWidget.resizable">Size
                  <input class="gx-field" type="number" step="1" :min="selectedWidget.resizable.min" :max="selectedWidget.resizable.max"
                    :value="selectedPosition.size" :disabled="!editAvailable || !!state.drag" @change="resizeSelected($event)"></label>
                <input v-if="selectedWidget.resizable" class="gx-slider" type="range" step="1" aria-label="Size" :min="selectedWidget.resizable.min" :max="selectedWidget.resizable.max"
                  :value="selectedPosition.size" :disabled="!editAvailable || !!state.drag || !!state.layerDrag" @input="sizeSlider($event)" @change="finishColorEdit" @blur="finishColorEdit">
                <template v-if="selectedWidget.opacity">
                  <label for="layout-widget-opacity">{{ selectedWidget.box ? 'Map opacity' : 'Opacity' }} · {{ selectedPosition.opacity }}%</label>
                  <input id="layout-widget-opacity" class="gx-slider" type="range" step="1" :min="selectedWidget.opacity.min" :max="selectedWidget.opacity.max"
                    :value="selectedPosition.opacity" :disabled="!editAvailable || !!state.drag || !!state.layerDrag" @input="opacityInput($event)" @change="finishColorEdit" @blur="finishColorEdit">
                </template>
                <label v-if="selectedWidget.backgroundToggle"><input type="checkbox" :checked="selectedPosition.background"
                  :disabled="!editAvailable || !!state.drag || !!state.layerDrag" @change="setWidgetBackground"> Show background</label>
                <p v-if="selectedWidget.defaultAnchor === 'driver_side'" class="gx-note">The default position follows the driver’s side. A moved position stays where you place it.</p>
                <p v-if="selectedWidget.note" class="gx-note">{{ selectedWidget.note }}</p>
                <label v-if="selectedWidget.kind === 'clock'" class="gx-layout__clock-format"><input type="checkbox" :checked="!!state.draft.clock24Hour" :disabled="!editAvailable || !!state.drag || !!state.layerDrag" @change="setClock24Hour"> Use 24-hour time</label>
                <label v-if="!projection && selectedWidget.kind === 'cruise_limits'" class="gx-layout__clock-format"><input type="checkbox" :checked="state.draft.showMaxSpeed !== false" :disabled="!editAvailable || !!state.drag || !!state.layerDrag" @change="setShowMaxSpeed"> Show MAX speed</label>
                <label v-if="!projection && selectedWidget.kind === 'steering_wheel' && displayRow('ShowBrakeStatus')" class="gx-layout__clock-format"><input type="checkbox" :checked="displayValue('ShowBrakeStatus') === 'On'"
                  :disabled="!editAvailable || !!state.drag || !!state.layerDrag || !displayAvailable(displayRow('ShowBrakeStatus'))" @change="setDisplay('ShowBrakeStatus', $event.target.checked ? 'On' : 'Off')"> Brake and acceleration colors</label>
                <div v-if="!projection && selectedWidget.kind === 'model_confidence' && displayRow('StockConfidenceBallWidget')" class="gx-layout__favorite-display">
                  <span>Style</span>
                  <div class="gx-segment" role="group" aria-label="Model confidence style">
                    <button v-for="choice in [['On', 'StarPilot widgets'], ['Off', 'Stock confidence ball']]" :key="choice[0]" class="gx-btn" type="button"
                      :class="displayValue('StockConfidenceBallWidget') === choice[0] ? 'gx-btn--primary' : 'gx-btn--tonal'"
                      :aria-pressed="displayValue('StockConfidenceBallWidget') === choice[0]"
                      :disabled="!editAvailable || !!state.drag || !!state.layerDrag || !displayAvailable(displayRow('StockConfidenceBallWidget'))"
                      @click="setDisplay('StockConfidenceBallWidget', choice[0])">{{ choice[1] }}</button>
                  </div>
                </div>
                <p v-if="!projection && stockConfidence && selectedWidget.kind === 'conditional_mode'" class="gx-note">Hidden while Model confidence uses the stock confidence ball.</p>
                <div v-if="projection && selectedWidget.iconSize" class="gx-layout__favorite-display">
                  <span>Show as</span>
                  <div class="gx-segment" role="group" :aria-label="selectedWidget.label + ' display'">
                    <button v-for="display in ['icons', 'words']" :key="display" class="gx-btn" type="button"
                      :class="selectedPosition.display === display ? 'gx-btn--primary' : 'gx-btn--tonal'"
                      :aria-pressed="selectedPosition.display === display" :disabled="!editAvailable || !!state.drag || !!state.layerDrag"
                      @click="setFavoriteDisplay(display)">{{ display === 'icons' ? 'Icons' : 'Words' }}</button>
                  </div>
                </div>
                <div class="gx-layout__coordinates"><label>X<input class="gx-field" type="number" step="1" :min="limits.minX" :max="limits.maxX" :value="selectedPosition.x" :disabled="!editAvailable || !!state.drag" @change="positionInput('x', $event)"></label>
                  <label>Y<input class="gx-field" type="number" step="1" :min="limits.minY" :max="limits.maxY" :value="selectedPosition.y" :disabled="!editAvailable || !!state.drag" @change="positionInput('y', $event)"></label><template v-if="selectedWidget.box">
                  <label>Width<input class="gx-field" type="number" step="10" :min="selectedWidget.box.minWidth" :max="selectedWidget.box.maxWidth" :value="selectedPosition.width" :disabled="!editAvailable || !!state.drag" @change="boxInput('width', $event)"></label>
                  <label>Height<input class="gx-field" type="number" step="10" :min="selectedWidget.box.minHeight" :max="selectedWidget.box.maxHeight" :value="selectedPosition.height" :disabled="!editAvailable || !!state.drag" @change="boxInput('height', $event)"></label></template></div>
                <template v-if="selectedWidget.box">
                  <label :for="'layout-box-width'">Width · {{ selectedPosition.width }}</label>
                  <input id="layout-box-width" class="gx-slider" type="range" step="10" :min="selectedWidget.box.minWidth" :max="selectedWidget.box.maxWidth"
                    :value="selectedPosition.width" :disabled="!editAvailable || !!state.drag || !!state.layerDrag" @input="boxSlider('width', $event)" @change="finishColorEdit" @blur="finishColorEdit">
                  <label :for="'layout-box-height'">Height · {{ selectedPosition.height }}</label>
                  <input id="layout-box-height" class="gx-slider" type="range" step="10" :min="selectedWidget.box.minHeight" :max="selectedWidget.box.maxHeight"
                    :value="selectedPosition.height" :disabled="!editAvailable || !!state.drag || !!state.layerDrag" @input="boxSlider('height', $event)" @change="finishColorEdit" @blur="finishColorEdit">
                  <span class="gx-note">Smaller sizes let more of the road show through.</span>
                </template>
                <span class="gx-note gx-layout__keys-note">Use arrow keys on a preview widget to move 1 pixel, or Shift + arrow for 10.</span>
                <section v-if="!projection && colorFields.length" class="gx-layout__colors" :aria-label="selectedWidget.label + ' colors'">
                  <div class="gx-layout__subhead"><h4>{{ selectedWidget.label }} colors</h4><button class="gx-btn gx-btn--tonal" type="button" :disabled="!editAvailable" @click="resetColors" aria-label="Reset widget colors" title="Reset widget colors">Reset</button></div>
                  <p class="gx-note">Changes this widget in the {{ state.profile === 'large' ? 'Big' : 'Small' }} layout only. Status indicators keep their meaning.</p>
                  <div class="gx-layout__palette"><div v-for="field in colorFields" :key="field.id" class="gx-layout__color" :class="{'is-open': state.openColor === 'widget:' + field.id}">
                    <button class="gx-layout__color-row" type="button" :aria-expanded="state.openColor === 'widget:' + field.id" :aria-controls="'layout-color-panel-' + field.id" @click="toggleColor('widget:' + field.id)">
                      <span class="gx-layout__swatch" :style="{'--swatch': selectedColors[field.id]}" aria-hidden="true"></span>
                      <span class="gx-layout__color-name">{{ field.label }}</span>
                      <span class="gx-layout__color-value">{{ selectedColors[field.id].slice(0,7) }}</span>
                      <span class="gx-layout__color-alpha">{{ Math.round(alpha(selectedColors[field.id]) / 255 * 100) }}%</span>
                      <i class="bi bi-chevron-down" aria-hidden="true"></i>
                    </button>
                    <div v-if="state.openColor === 'widget:' + field.id" :id="'layout-color-panel-' + field.id" class="gx-layout__color-editor">
                    <label class="gx-sr-only" :for="'layout-color-' + field.id">{{ field.label }} hex</label><div class="gx-layout__color-values">
                      <input type="color" :aria-label="field.label + ' color'" :value="selectedColors[field.id].slice(0,7)" :disabled="!editAvailable || !!state.drag" @input="colorRgb(field.id, $event)" @change="finishColorEdit" @blur="finishColorEdit">
                      <input :id="'layout-color-' + field.id" class="gx-field" type="text" spellcheck="false" maxlength="9" :value="selectedColors[field.id]" :disabled="!editAvailable || !!state.drag" @change="colorText(field.id, $event)"></div>
                    <label :for="'layout-alpha-' + field.id">Opacity · {{ Math.round(alpha(selectedColors[field.id]) / 255 * 100) }}%</label>
                    <input :id="'layout-alpha-' + field.id" class="gx-slider" type="range" min="0" max="255" step="1" :value="alpha(selectedColors[field.id])" :disabled="!editAvailable || !!state.drag" @input="colorAlpha(field.id, $event)" @change="finishColorEdit" @blur="finishColorEdit">
                    <p v-if="!alpha(selectedColors[field.id])" class="gx-note">Hidden at 0%. Picking a color makes it visible.</p>
                    </div>
                  </div></div>
                  <GxNotice tone="danger" v-if="state.colorError">{{ state.colorError }}</GxNotice>
                </section>
                <p v-if="!projection && !colorFields.length" class="gx-note">This widget uses its original status colors.</p>
              </div>
              </div>
              <section v-if="!projection" v-show="state.inspectorPanel === 'road'" class="gx-layout__colors" aria-label="Path and lane colors">
                <div class="gx-layout__subhead"><h4>Path &amp; Lane Colors</h4><button class="gx-btn gx-btn--tonal" type="button" :disabled="!editAvailable || !!state.drag" @click="resetRoad" aria-label="Reset road colors" title="Reset road colors">Reset</button></div>
                <label>Path style<GalaxySelect class="gx-field gx-field--full" :value="roadMode" :disabled="!editAvailable || !!state.drag" @change="setRoadMode($event.target.value)">
                  <option value="acceleration">Acceleration colors</option>
                  <option value="color">Custom color</option><option value="rainbow">Rainbow Road</option>
                </GalaxySelect></label>
                <p class="gx-note">These colors apply to this layout only. The preview uses a sample road.</p>
                <details class="gx-layout__help"><summary>About path &amp; lane colors</summary><div>
                <p class="gx-note">Choose how the path is colored. Acceleration colors change with acceleration and braking. Custom color stays one color. Rainbow Road shows a moving rainbow.</p>
                <p class="gx-note">{{ state.profile === 'large' ? 'Path border colors the strips along the path. Lane lines keep their own color.' : 'Lane marking colors apply to the lines beside your lane and the outer lines separately.' }} Blue lane-centering and orange steering-effort indicators stay blue and orange.</p>
                </div></details>
                <div class="gx-layout__palette"><div v-for="field in state.data.metadata.roadColorFields" :key="field.id" class="gx-layout__color" :class="{'is-open': state.openColor === 'road:' + field.id}">
                  <button class="gx-layout__color-row" type="button" :aria-expanded="state.openColor === 'road:' + field.id" :aria-controls="'road-color-panel-' + field.id" @click="toggleColor('road:' + field.id)">
                    <span class="gx-layout__swatch" :style="{'--swatch': roadColors[field.id]}" aria-hidden="true"></span>
                    <span class="gx-layout__color-name">{{ roadLabel(field.id) }}</span>
                    <span class="gx-layout__color-value">{{ roadColors[field.id].slice(0,7) }}</span>
                    <span class="gx-layout__color-alpha">{{ Math.round(alpha(roadColors[field.id]) / 255 * 100) }}%</span>
                    <i class="bi bi-chevron-down" aria-hidden="true"></i>
                  </button>
                  <div v-if="state.openColor === 'road:' + field.id" :id="'road-color-panel-' + field.id" class="gx-layout__color-editor">
                  <label class="gx-sr-only" :for="'road-color-' + field.id">{{ roadLabel(field.id) }} hex</label><div class="gx-layout__color-values">
                    <input type="color" :aria-label="roadLabel(field.id) + ' color'" :value="roadColors[field.id].slice(0,7)" :disabled="!editAvailable || !!state.drag" @input="roadRgb(field.id, $event)" @change="finishColorEdit" @blur="finishColorEdit">
                    <input :id="'road-color-' + field.id" class="gx-field" type="text" spellcheck="false" maxlength="9" :value="roadColors[field.id]" :disabled="!editAvailable || !!state.drag" @change="roadColor(field.id, $event.target.value.trim())"></div>
                  <label :for="'road-alpha-' + field.id">Opacity · {{ Math.round(alpha(roadColors[field.id]) / 255 * 100) }}%</label>
                  <input :id="'road-alpha-' + field.id" class="gx-slider" type="range" min="0" max="255" step="1" :value="alpha(roadColors[field.id])" :disabled="!editAvailable || !!state.drag" @input="roadAlpha(field.id, $event)" @change="finishColorEdit" @blur="finishColorEdit">
                  </div>
                </div></div>
                <GxNotice tone="danger" v-if="state.colorError">{{ state.colorError }}</GxNotice>
              </section>
            <section v-if="projection" v-show="state.inspectorPanel === 'display'" class="gx-layout__colors gx-layout__display" aria-label="Android Auto display">
              <GalaxySettingRow :row="switchRow('Large UI Gamma Effect Trial', state.draft.largeUiGammaTrial)" :index="0"
                :disabled="!editable || !!state.drag || !!state.layerDrag" :save-value="(index, value) => setLargeUiGammaTrial(value)" />
              <GalaxySettingRow :row="switchRow('Red blind-spot border', state.draft.blindSpotBorder === true)" :index="1"
                :disabled="!editable || !!state.drag || !!state.layerDrag" :save-value="(index, value) => setProjectionBorder('blindSpotBorder', value)" />
              <GalaxySettingRow :row="switchRow('Amber signal border', state.draft.signalBorder === true)" :index="2"
                :disabled="!editable || !!state.drag || !!state.layerDrag" :save-value="(index, value) => setProjectionBorder('signalBorder', value)" />
              <p class="gx-note">Gamma trial: the large comma UI's road-camera color effect (not shown in the preview). Borders are separate from the comma screen's C4 settings. Save to apply.</p>
            </section>
              <section v-if="!projection && displayGroups.length" v-show="state.inspectorPanel === 'display'" class="gx-layout__colors gx-layout__display" aria-label="Display options">
                <div class="gx-layout__subhead"><h4>Display options</h4></div>
                <p class="gx-note">These apply to the whole driving screen on both layouts. Save changes to apply them.</p>
                <template v-for="group in displayGroups" :key="group.name">
                  <h5 class="gx-layout__display-group">{{ group.name }}</h5>
                  <GalaxySettingRow v-for="(row, index) in group.rows" :key="row.key" :row="displaySettingRow(row)" :index="index"
                    :disabled="!editable || !!state.drag || !!state.layerDrag || !displayAvailable(row)" :save-value="(_, value) => setDisplay(row.key, value)" />
                </template>
              </section>
            </section>
          </div>
        </template>
      </template>
      <GxDialog v-if="state.removeConfirm && profile" labelledby="gx-layout-remove-title" describedby="gx-layout-remove-body" alert @close="cancelRemove">
        <div><h3 id="gx-layout-remove-title">Remove {{ profile.widgets[state.removeConfirm]?.label }}?</h3>
          <p id="gx-layout-remove-body">Remove this widget from the {{ projection ? 'Android Auto' : state.profile === 'large' ? 'Big' : 'Small' }} layout? You can add it again from Inactive Widgets.</p></div>
        <div class="gx-settings__controls">
          <button type="button" class="gx-btn gx-btn--tonal" @click="cancelRemove">Cancel</button>
          <button type="button" class="gx-btn gx-btn--danger" @click="confirmRemove">Remove widget</button>
        </div>
      </GxDialog>
      <GxDialog v-if="modalLeavePrompt" class="gx-layout__leave-dialog" :inert="busy" labelledby="gx-layout-leave-title" describedby="gx-layout-leave-body" alert @close="cancelLeave">
        <div class="gx-layout__leave-copy"><h3 id="gx-layout-leave-title">Leave without saving your changes?</h3>
          <p id="gx-layout-leave-body">Save your {{ projection ? 'Android Auto' : 'comma' }} layout before leaving, keep editing, or discard this draft.</p></div>
        <GxNotice v-if="state.error" tone="danger">{{ state.error }}</GxNotice>
        <div class="gx-layout__leave-actions">
          <button type="button" class="gx-btn gx-btn--tonal" @click="cancelLeave">Keep editing</button>
          <button type="button" class="gx-btn gx-btn--danger" @click="leave(state.discard)">Discard and leave</button>
          <button type="button" class="gx-btn" :disabled="!saveAvailable" @click="saveAndLeave">{{ state.status === 'saving' ? 'Saving…' : 'Save changes' }}</button>
        </div>
      </GxDialog>
    </section>`,
}
