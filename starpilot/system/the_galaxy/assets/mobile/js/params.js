export const GALAXY_DEVELOPER_MODE_KEY = "GalaxyDeveloperMode"
export const VEHICLE_SPEED_UNIT_TYPE = "vehicle_speed"

const SPEED_OFFSET_RANGES = {
  imperial: ["0–24", "25–34", "35–44", "45–54", "55–64", "65–74", "75–99"],
  metric: ["0–29", "30–49", "50–59", "60–79", "80–99", "100–119", "120–140"],
}

export function usesMetricUnits(values = {}) {
  const value = values?.IsMetric
  if (value === true || value === 1) return true
  return ["1", "true", "yes", "on"].includes(String(value ?? "").trim().toLowerCase())
}

export function vehicleSpeedUnit(values = {}) {
  return usesMetricUnits(values) ? "km/h" : "mph"
}

export function resolveVehicleUnitParam(param, values = {}) {
  if (!param || param.unit_type !== VEHICLE_SPEED_UNIT_TYPE) return param

  const metric = usesMetricUnits(values)
  const mode = metric ? "metric" : "imperial"
  const resolved = {
    ...param,
    unit: ` ${vehicleSpeedUnit(values)}`,
    unit_search_terms: "metric imperial mph km/h vehicle speed units",
  }
  for (const field of ["min", "max", "step", "precision"]) {
    const override = param[`${mode}_${field}`]
    if (override !== undefined && override !== null) resolved[field] = override
  }

  if (Number.isInteger(param.unit_range_index)) {
    const range = SPEED_OFFSET_RANGES[mode][param.unit_range_index]
    if (range) {
      resolved.label = `Speed Offset (${range} ${vehicleSpeedUnit(values)})`
      resolved.description = `How much to offset posted speed limits between ${range} ${vehicleSpeedUnit(values)}.`
    }
  }
  return resolved
}

const HIDDEN_SETTING_KEYS = new Set(["HumanAcceleration"])
const RADAR_REQUIRED_KEYS = new Set(["HumanLaneChanges", "RadarTakeoffs"])
const VEHICLE_SETTING_MAKES = {
  RivianAngleControl: ["Rivian"],
  TeslaCoopSteering: ["Tesla"],
  NAPRadarEnabled: ["Tesla"],
  NAPRadarBehindNosecone: ["Tesla"],
  NAPRadarOffset: ["Tesla"],
  NAPPedalEnabled: ["Tesla"],
  NAPPedalCanBus: ["Tesla"],
  NAPAdaptiveAccel: ["Tesla"],
  NAPPedalCalibDone: ["Tesla"],
  NAPPedalCalibFactor: ["Tesla"],
  NAPPedalCalibZero: ["Tesla"],
  GMPedalLongitudinal: ["Buick", "Cadillac", "Chevrolet", "GMC", "Holden"],
  GMDashSpoofOffsets: ["Buick", "Cadillac", "Chevrolet", "GMC", "Holden"],
  IgnoreIgnitionLine: ["Buick", "Cadillac", "Chevrolet", "GMC", "Holden"],
  LongPitch: ["Buick", "Cadillac", "Chevrolet", "GMC", "Holden"],
  RemoteStartBootsComma: ["Buick", "Cadillac", "Chevrolet", "GMC", "Holden"],
  HKGRemoteStartBootsComma: ["Genesis", "Hyundai", "Kia"],
  VoltSNG: ["Chevrolet", "Holden"],
  GMAutoHold: ["Buick", "Chevrolet", "Holden"],
  VoltOnePedalMode: ["Chevrolet", "Holden"],
  RemapCancelToDistance: ["Chevrolet", "Holden"],
  JeepBrakeHold: ["Jeep"],
  SubaruSNG: ["Subaru"],
  SubaruSNGManualParkingBrake: ["Subaru"],
  SubaruStopStartOff: ["Subaru"],
  SubaruRedneckCruise: ["Subaru"],
  ClusterOffset: ["Lexus", "Toyota"],
  SNGHack: ["Lexus", "Toyota"],
  ToyotaAutoHold: ["Lexus", "Toyota"],
}

export function normalizeVehicleMake(value) {
  return String(value ?? "").trim().toLowerCase()
}

export function isVehicleSettingVisible(section, param, values) {
  const allowedMakes = param.vehicle_makes || (section.name === "Vehicle" ? VEHICLE_SETTING_MAKES[param.key] : null)
  if (!allowedMakes) return true
  const selectedMake = normalizeVehicleMake(values.CarMake)
  return allowedMakes.some((make) => normalizeVehicleMake(make) === selectedMake)
}

function toSelectValue(value) {
  return value === null || value === undefined ? "" : String(value)
}

export function matchesSettingValueCondition(param, values) {
  if (!param.visible_when_key) return true
  const allowedValues = Array.isArray(param.visible_when_values) ? param.visible_when_values : []
  const currentValue = toSelectValue(values[param.visible_when_key])
  return allowedValues.some((value) => toSelectValue(value) === currentValue)
}

// Any structural reason a param must not be shown (regardless of dev mode).
function isHiddenByConditions(section, param, values) {
  if (HIDDEN_SETTING_KEYS.has(param.key) || !isVehicleSettingVisible(section, param, values) || !matchesSettingValueCondition(param, values)) return true
  if (param.requires_capability && !values[param.requires_capability]) return true
  if (RADAR_REQUIRED_KEYS.has(param.key) && !values.HasRadar) return true
  if (param.key === "AlphaLongitudinalEnabled" && !values.AlphaLongitudinalAvailable) return true
  return false
}

export function isSettingVisible(section, param, values) {
  if (isHiddenByConditions(section, param, values)) return false
  if (values[GALAXY_DEVELOPER_MODE_KEY]) return true
  return section.name === "Favorites" || param.settings_tier === "simple"
}

export function isAdvancedHiddenByDeveloperMode(section, param, values) {
  if (param.settings_tier !== "advanced") return false
  return !isHiddenByConditions(section, param, values)
}

export function countAdvancedHiddenByDeveloperMode(layout, values) {
  if (values[GALAXY_DEVELOPER_MODE_KEY]) return 0
  let count = 0
  for (const section of layout) {
    if (section.name === "Favorites") continue
    for (const param of section.params || []) {
      if (isAdvancedHiddenByDeveloperMode(section, param, values)) count++
    }
  }
  return count
}

export function numericBounds(param, values = {}) {
  param = resolveVehicleUnitParam(param, values)
  const defaultBounds = {
    min: param.min !== undefined ? param.min : (param.data_type === "float" ? 0.0 : 0),
    max: param.max !== undefined ? param.max : (param.data_type === "float" ? 100.0 : 100),
    step: param.step !== undefined ? param.step : (param.data_type === "float" ? 0.01 : 1),
  }
  const toFinite = (value) => {
    const n = Number(value)
    return Number.isFinite(n) ? n : null
  }
  if (param.key === "ScreenBrightness") {
    return { min: 1, max: 101, step: 1 }
  }
  if (param.key === "ScreenBrightnessOnroad") {
    return { min: 0, max: 101, step: 1 }
  }
  if (param.key === "LaneCenterOffset") {
    return { min: -0.3, max: 0.3, step: 0.01 }
  }
  if (/^(Traffic|Aggressive|Standard|Relaxed)Jerk(Acceleration|Deceleration|Danger|SpeedDecrease|Speed)$/.test(String(param.key || ""))) {
    return { min: 25, max: 200, step: 1 }
  }
  if (param.key === "SteerKP") {
    const base = toFinite(values?.SteerKPStock) || toFinite(values?.SteerKP) || 0.6
    return { min: +(base * 0.5).toFixed(2), max: +(base * 1.5).toFixed(2), step: 0.01 }
  }
  if (param.key === "SteerLatAccel") {
    const base = toFinite(values?.SteerLatAccelStock) || toFinite(values?.SteerLatAccel) || 2.0
    return { min: +(base * 0.5).toFixed(2), max: +(base * 1.25).toFixed(2), step: 0.01 }
  }
  if (param.key === "SteerRatio") {
    const base = toFinite(values?.SteerRatioStock) || toFinite(values?.SteerRatio) || 15.0
    return { min: +(base * 0.25).toFixed(2), max: +(base * 1.5).toFixed(2), step: 0.01 }
  }
  return defaultBounds
}

export function stepPrecision(step, explicitPrecision) {
  if (explicitPrecision !== undefined && explicitPrecision !== null && explicitPrecision !== "") {
    const parsed = Number.parseInt(explicitPrecision, 10)
    if (Number.isFinite(parsed) && parsed >= 0) return parsed
  }
  const stepStr = String(step ?? "")
  if (!stepStr.includes(".")) return 0
  return stepStr.split(".")[1].length
}

export function numericEpsilon(precision) {
  return Math.pow(10, -(precision + 2))
}

export function clampNumeric(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

export function snapNumericToBoundsAndStep(rawValue, bounds, precision) {
  const min = Number(bounds.min)
  const max = Number(bounds.max)
  const step = Number(bounds.step)
  const value = Number(rawValue)
  if (!Number.isFinite(min) || !Number.isFinite(max) || !Number.isFinite(value)) return null
  const clamped = clampNumeric(value, min, max)
  if (!Number.isFinite(step) || step <= 0) {
    return clampNumeric(Number(clamped.toFixed(precision)), min, max)
  }
  const snapped = min + Math.round((clamped - min) / step) * step
  return clampNumeric(Number(snapped.toFixed(precision)), min, max)
}

export function coerceValueByType(rawValue, dataType) {
  if (dataType === "int") {
    const n = Number.parseInt(rawValue, 10)
    return Number.isFinite(n) ? n : rawValue
  }
  if (dataType === "float") {
    const n = Number.parseFloat(rawValue)
    return Number.isFinite(n) ? n : rawValue
  }
  return rawValue
}

export function formatSliderValue(val, stepStr, precisionInt, key) {
  if (val === null || val === undefined) return "--"
  const v = parseFloat(val)
  if (Number.isNaN(v)) return val
  if (key === "SwitchbackModeCooldown") {
    if (v === 0) return "Off"
    return v === 1 ? "1 min" : `${v} min`
  }
  if (key === "DeviceShutdown") {
    return v === 1 ? "1 hour" : `${v} hours`
  }
  const volumeKeys = [
    "BelowSteerSpeedVolume", "DisengageVolume", "EngageVolume", "PromptVolume",
    "PromptDistractedVolume", "RefuseVolume", "WarningImmediateVolume", "WarningSoftVolume",
  ]
  if (key && volumeKeys.includes(key)) {
    if (v === 0) return "Muted"
    if (v === 101) return "Auto"
    return `${v}%`
  }
  if (precisionInt !== undefined && precisionInt !== null) {
    return Number(v.toFixed(precisionInt)).toString()
  }
  if (!stepStr || !stepStr.includes(".")) return Math.round(v).toString()
  const dec = stepStr.split(".")[1].length
  return Number(v.toFixed(dec)).toString()
}

export function formatNumericParamValue(param, value, values = {}) {
  const resolved = resolveVehicleUnitParam(param, values)
  const bounds = numericBounds(resolved, values)
  const formatted = formatSliderValue(value, String(bounds.step), resolved.precision, resolved.key)
  return resolved.unit && formatted !== "--" ? `${formatted}${resolved.unit}` : formatted
}

export function formatReadoutValue(p, value) {
  const raw = value
  const parsed = parseFloat(raw)
  if (raw === undefined || raw === null || Number.isNaN(parsed)) return "--"
  const precision = p.precision !== undefined && p.precision !== null ? Number(p.precision) : 2
  const formatted = Number(parsed.toFixed(Math.max(0, precision))).toString()
  return p.unit ? `${formatted}${p.unit}` : formatted
}

export function normalizeHexColor(rawValue) {
  const value = String(rawValue ?? "").trim()
  if (!value || value.toLowerCase() === "stock") return ""
  const stripped = value.startsWith("#") ? value.slice(1) : value
  if (!/^[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(stripped)) return ""
  return `#${stripped.slice(0, 6).toLowerCase()}`
}

export function getColorDefault(param) {
  const candidate = normalizeHexColor(param?.default_color)
  if (candidate) return candidate
  return { LaneLinesColor: "#00ff00", PathEdgesColor: "#00ff00", PathColor: "#30ff9c" }[param?.key] || "#ffffff"
}

export function slugifySectionName(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

export function isGroupParam(param) {
  return !!param && param.ui_type === "group"
}

export function applyParamChange(values, patch) {
  const next = { ...(values || {}) }
  if (!patch || typeof patch !== "object") return next
  if ("key" in patch && "value" in patch) {
    next[patch.key] = patch.value
    for (const [k, v] of Object.entries(patch)) {
      if (k !== "key" && k !== "value") next[k] = v
    }
  } else {
    Object.assign(next, patch)
  }
  return next
}

export function isParamEnabledForChildren(paramOrKey, values) {
  const param = typeof paramOrKey === "string" ? { key: paramOrKey } : paramOrKey
  if (isGroupParam(param)) return true
  return !!(param && param.key && values[param.key])
}

export function hasChildParams(paramsList, key) {
  return (paramsList || []).some((param) => (param.parent_key || null) === key)
}

export function buildRenderTree(paramsList, values, expanded, isVisible) {
  const out = []
  const list = paramsList || []
  const visible = isVisible || (() => true)

  function walk(parentKey, depth) {
    for (const param of list) {
      if ((param.parent_key || null) !== parentKey) continue
      if (!visible(param)) continue
      out.push({ param, depth })
      if (hasChildParams(list, param.key) && isParamEnabledForChildren(param, values) && expanded[param.key]) {
        walk(param.key, depth + 1)
      }
    }
  }

  walk(null, 0)
  return out
}
