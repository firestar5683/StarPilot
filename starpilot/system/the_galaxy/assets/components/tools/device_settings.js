import { html, reactive } from "/assets/vendor/arrow-core.js"

const endpointOptionsCache = {}
const endpointOptionsInflight = {}
const COLOR_UI_DEFAULTS = {
  LaneLinesColor: "#00ff00",
  PathEdgesColor: "#00ff00",
  PathColor: "#30ff9c",
}
const FAVORITE_OPTION_COLLATOR = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" })
const FAVORITE_ACTION_PREFIX = "__starpilot_favorite_action__:"
const GALAXY_DEVELOPER_MODE_KEY = "GalaxyDeveloperMode"
const HIDDEN_SECTION_NAMES = new Set(["Model & Customization"])
const HIDDEN_SETTING_KEYS = new Set(["HumanAcceleration", "ReverseCruise"])
const GM_MAKES = ["Buick", "Cadillac", "Chevrolet", "GMC", "Holden"]
const HKG_MAKES = ["Genesis", "Hyundai", "Kia"]
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
  GMPedalLongitudinal: GM_MAKES,
  GMDashSpoofOffsets: GM_MAKES,
  IgnoreIgnitionLine: GM_MAKES,
  LongPitch: GM_MAKES,
  RemoteStartBootsComma: GM_MAKES,
  HKGRemoteStartBootsComma: HKG_MAKES,
  VoltSNG: ["Chevrolet", "Holden"],
  GMAutoHold: ["Chevrolet", "Holden"],
  VoltOnePedalMode: ["Chevrolet", "Holden"],
  RemapCancelToDistance: ["Chevrolet", "Holden"],
  JeepBrakeHold: ["Jeep"],
  SubaruSNG: ["Subaru"],
  SubaruSNGManualParkingBrake: ["Subaru"],
  ClusterOffset: ["Lexus", "Toyota"],
  SNGHack: ["Lexus", "Toyota"],
  ToyotaAutoHold: ["Lexus", "Toyota"],
}
const RADAR_REQUIRED_KEYS = new Set(["HumanLaneChanges", "RadarTakeoffs"])

// Plain variables — scheduling/routing flags that must NOT be reactive
let syncScheduled = false
let lastParams = null
let flmWorkspaceInflight = null
let lastFlmWorkspaceFetch = 0
let favoritePollInflight = null
let favoritePollTimer = null
const DYNAMIC_DEFAULT_DEP_KEYS = new Set(["AccelerationProfile", "EVTuning", "TruckTuning"])
const PANDA_FIRMWARE_TOGGLE_KEYS = new Set(["IgnoreIgnitionLine", "RemoteStartBootsComma", "HKGRemoteStartBootsComma"])
const FLM_ADVANCED_LATERAL_KEYS = new Set([
  "AdvancedLateralTune", "ForceAutoTune", "ForceAutoTuneOff", "UseAutoSteerDelay", "SteerDelay",
  "SteerFriction", "SteerKP", "SteerLatAccel", "SteerRatio",
])

// Module-level state (persists across route changes)
const state = reactive({
  layout: [],
  allKeys: [],
  paramMetaByKey: {},
  values: {},
  defaultValues: {},
  flmActiveTrial: null,
  loadingLayout: true,
  loadingValues: true,
  filter: "",
  expanded: {},
  fetched: false,
  activeSectionSlug: "",
  numericUpdating: {},
  sliderPreviewValues: {},
  actionUpdating: {},
  favoriteLoading: false,
  favoriteSaving: false,
  favoriteOptions: [],
  favoriteSlots: [],
  favoriteFilters: ["", "", ""],
  favoriteValues: {},
})

function slugifySectionName(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

function normalizeVehicleMake(value) {
  return String(value || "").trim().toLowerCase()
}

function isVehicleSettingVisible(section, param) {
  if (section.name !== "Vehicle") return true
  const allowedMakes = VEHICLE_SETTING_MAKES[param.key]
  if (!allowedMakes) return true
  const selectedMake = normalizeVehicleMake(state.values.CarMake)
  return allowedMakes.some(make => normalizeVehicleMake(make) === selectedMake)
}

function isSettingVisible(section, param) {
  // This policy controls Galaxy rendering only; hidden params retain their stored values.
  if (HIDDEN_SETTING_KEYS.has(param.key) || !isVehicleSettingVisible(section, param)) return false
  if (param.requires_capability && !state.values[param.requires_capability]) return false
  if (RADAR_REQUIRED_KEYS.has(param.key) && !state.values.HasRadar) return false
  if (param.key === "AlphaLongitudinalEnabled" && !state.values.AlphaLongitudinalAvailable) return false
  if (state.values[GALAXY_DEVELOPER_MODE_KEY]) return true
  return section.name === "Favorites" || param.settings_tier === "simple"
}

function getSectionsWithSlug() {
  return state.layout
    .filter(section => !HIDDEN_SECTION_NAMES.has(section.name))
    .map(section => ({
      ...section,
      params: (section.params || []).filter(param => isSettingVisible(section, param)),
      slug: slugifySectionName(section.name),
    }))
    .filter(section => section.params.length > 0)
}

function isGroupParam(param) {
  return !!param && param.ui_type === "group"
}

function isParamEnabledForChildren(paramOrKey) {
  const isKey = typeof paramOrKey === "string"
  const param = isKey ? state.paramMetaByKey[paramOrKey] : paramOrKey
  if (isGroupParam(param)) return true

  const key = isKey ? paramOrKey : (param && param.key)
  return !!(key && state.values[key])
}

function getEventValue(event) {
  const source = event && (event.currentTarget || event.target)
  if (!source || !("value" in source)) return ""
  return String(source.value || "")
}

function updateSearchFilter(event) {
  const nextFilter = getEventValue(event)
  if (state.filter === nextFilter) return
  state.filter = nextFilter
  scheduleSyncInputs()
}

function toSelectValue(value) {
  return value === null || value === undefined ? "" : String(value)
}

function normalizeHexColor(rawValue) {
  const value = String(rawValue || "").trim()
  if (!value || value.toLowerCase() === "stock") return ""

  const stripped = value.startsWith("#") ? value.slice(1) : value
  if (!/^[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(stripped)) return ""
  return `#${stripped.slice(0, 6).toLowerCase()}`
}

function getColorDefault(param) {
  const candidate = normalizeHexColor(param?.default_color)
  if (candidate) return candidate
  return COLOR_UI_DEFAULTS[param?.key] || "#ffffff"
}

function resolveColorInputValue(param, rawValue = undefined) {
  return normalizeHexColor(rawValue ?? state.values[param?.key]) || getColorDefault(param)
}

function formatColorDisplayValue(param, rawValue = undefined) {
  const value = normalizeHexColor(rawValue ?? state.values[param?.key])
  return value ? value.toUpperCase() : "Stock"
}

function isStockColorValue(rawValue) {
  return normalizeHexColor(rawValue) === ""
}

function resolveEndpointTemplate(template) {
  if (!template) return ""
  return String(template).replace(/\{([A-Za-z0-9_]+)\}/g, (_, key) => {
    return encodeURIComponent(toSelectValue(state.values[key]))
  })
}

function scheduleSyncInputs() {
  if (syncScheduled) return
  syncScheduled = true
  requestAnimationFrame(() => {
    syncScheduled = false
    syncInputs()
  })
}

function applySelectOptions(el, options) {
  el.innerHTML = ""
  for (const opt of options || []) {
    if (opt?.developer_only && !state.values[GALAXY_DEVELOPER_MODE_KEY]) continue
    const o = document.createElement("option")
    o.value = String(opt.value)
    o.textContent = opt.label
    el.appendChild(o)
  }
}

function syncSelectValue(el, key) {
  const targetValue = toSelectValue(state.values[key])
  if (!targetValue) {
    el.value = ""
    return
  }

  if (key === "CarModel") {
    const targetLabel = toSelectValue(state.values.CarModelName)
    const options = Array.from(el.options)
    const matchingIndex = options.findIndex(opt => {
      if (opt.value !== targetValue) return false
      return !targetLabel || opt.textContent === targetLabel
    })
    if (matchingIndex !== -1) {
      el.selectedIndex = matchingIndex
      return
    }
  }

  el.value = targetValue
}

async function hydrateEndpointOptions(el, key, endpoint) {
  if (endpointOptionsCache[endpoint]) {
    applySelectOptions(el, endpointOptionsCache[endpoint])
    el.dataset.hydrated = "1"
    syncSelectValue(el, key)
    return
  }

  if (!endpointOptionsInflight[endpoint]) {
    endpointOptionsInflight[endpoint] = fetch(endpoint)
      .then(r => r.json())
      .then(options => {
        endpointOptionsCache[endpoint] = options
        return options
      })
      .catch(() => null)
      .finally(() => {
        delete endpointOptionsInflight[endpoint]
      })
  }

  const options = await endpointOptionsInflight[endpoint]
  if (!options || !el.isConnected) return

  applySelectOptions(el, options)
  el.dataset.hydrated = "1"
  syncSelectValue(el, key)
}

function syncInputs() {
  // Sync checkboxes — set DOM property directly (attribute alone is unreliable)
  for (const el of document.querySelectorAll("input[type='checkbox'].ds-toggle[id^='ds-']")) {
    el.checked = !!state.values[el.id.slice(3)]
  }

  // Sync color inputs — map unset/"stock" values to the picker fallback color.
  for (const el of document.querySelectorAll("input[type='color'].ds-color[id^='ds-']")) {
    const key = el.id.slice(3)
    const param = state.paramMetaByKey[key]
    if (!param) continue
    el.value = resolveColorInputValue(param)
  }

  for (const el of document.querySelectorAll("input.ds-text-input[id^='ds-']")) {
    if (document.activeElement === el) continue
    el.value = toSelectValue(state.values[el.id.slice(3)])
  }

  // Sync selects — hydrate options + set value
  for (const el of document.querySelectorAll("select.ds-select[id^='ds-']")) {
    const key = el.id.slice(3)
    const endpointTemplate = el.getAttribute("data-endpoint")
    const endpoint = resolveEndpointTemplate(endpointTemplate)
    const inlineOptions = state.paramMetaByKey[key]?.options

    if (endpoint) {
      if (!el.dataset.hydrated || el.dataset.endpoint !== endpoint) {
        el.dataset.endpoint = endpoint
        hydrateEndpointOptions(el, key, endpoint)
      } else {
        syncSelectValue(el, key)
      }
      continue
    }

    if (Array.isArray(inlineOptions) && inlineOptions.length > 0) {
      if (!el.dataset.hydrated) {
        applySelectOptions(el, inlineOptions)
        el.dataset.hydrated = "1"
      }
      syncSelectValue(el, key)
    }
  }

  const favoriteSlots = normalizeFavoriteSlots(state.favoriteSlots)
  for (const el of document.querySelectorAll("[data-favorite-slot][data-favorite-field]")) {
    const slotIndex = Number.parseInt(el.dataset.favoriteSlot, 10)
    const field = el.dataset.favoriteField
    const slot = favoriteSlots[slotIndex]
    if (!slot) continue

    if (el.tagName === "SELECT" && field === "key") {
      populateFavoriteSelect(slotIndex, el)
      el.disabled = !!state.favoriteSaving
    } else if (el.tagName === "INPUT" && field === "search") {
      el.value = state.favoriteFilters[slotIndex] || ""
      el.disabled = !!state.favoriteSaving
    } else if (el.tagName === "INPUT" && el.type === "checkbox") {
      el.checked = !!slot[field]
      if (field === "enabled") {
        el.disabled = !!state.favoriteSaving
      } else if (field === "show_onroad") {
        el.disabled = !!state.favoriteSaving || !slot.enabled || !slot.key
      }
    }
  }

  for (const el of document.querySelectorAll("input[type='checkbox'][data-favorite-value-key]")) {
    el.checked = !!state.values[el.dataset.favoriteValueKey]
  }
}

async function fetchDefaultValues() {
  try {
    const defaultsRes = await fetch("/api/params/defaults")
    if (!defaultsRes.ok) return false
    const defaultsData = await defaultsRes.json()
    state.defaultValues = defaultsData || {}
    return true
  } catch (e) {
    return false
  }
}

async function fetchFlmWorkspace(force = false) {
  const now = Date.now()
  if (!force && now - lastFlmWorkspaceFetch < 1500) return
  if (flmWorkspaceInflight) return flmWorkspaceInflight

  lastFlmWorkspaceFetch = now
  flmWorkspaceInflight = fetch("/api/flm/workspace", { cache: "no-store" })
    .then(async res => {
      if (!res.ok) return
      const workspace = await res.json()
      state.flmActiveTrial = workspace?.activeTrial || null
    })
    .catch(error => console.warn("Failed to load active FLM trial state:", error))
    .finally(() => {
      flmWorkspaceInflight = null
    })

  return flmWorkspaceInflight
}

async function refreshParamsAndDefaults() {
  await Promise.all([fetchDefaultValues(), fetchFlmWorkspace(true)])

  try {
    const valuesRes = await fetch("/api/params/all")
    if (valuesRes.ok) {
      const data = await valuesRes.json()
      state.values = data || {}
    }
  } catch (e) {
    console.error("Failed to refresh param values:", e)
  }
  scheduleSyncInputs()
}

async function fetchLayoutAndParams() {
  state.loadingLayout = true
  state.loadingValues = true

  try {
    const layoutRes = await fetch("/assets/components/tools/device_settings_layout.json?v=settings-tier-1", { cache: "no-store" })
    const rawLayoutData = await layoutRes.json()

    const layoutData = rawLayoutData
      .map(section => ({
        ...section,
        params: (section.params || []).filter(param => param.key !== "Model"),
      }))
      .filter(section => section.params.length > 0)

    state.layout = layoutData

    const keys = []
    const paramMetaByKey = {}
    for (const section of layoutData) {
      for (const p of section.params) {
        keys.push(p.key)
        paramMetaByKey[p.key] = p
      }
    }

    state.allKeys = keys
    state.paramMetaByKey = paramMetaByKey
  } catch (e) {
    console.error("Failed to fetch UI layout:", e)
  }
  state.loadingLayout = false

  // Pull params once at page load; local state handles subsequent edits.
  try {
    const [defaultsLoaded] = await Promise.all([fetchDefaultValues(), fetchFlmWorkspace(true)])
    if (!defaultsLoaded) {
      state.defaultValues = {}
    }

    const valuesRes = await fetch("/api/params/all")
    const data = await valuesRes.json()
    state.values = data
  } catch (e) {
    console.error("Failed to fetch param values:", e)
    state.defaultValues = {}
  }

  await fetchFavoriteSlots()

  state.loadingValues = false

  // Resolve slug now that layout is available (uses stored route params)
  resolveActiveSectionSlug(lastParams)
  scheduleSyncInputs()
}

function formatSliderValue(val, stepStr, precisionInt, key) {
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
    "PromptDistractedVolume", "RefuseVolume",
    "WarningImmediateVolume", "WarningSoftVolume",
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

function formatNumericForInput(value, precision) {
  const n = Number(value)
  if (!Number.isFinite(n)) return ""
  return Number(n.toFixed(precision)).toString()
}

function formatStepValue(step, precision) {
  const n = Number(step)
  if (!Number.isFinite(n)) return "1"
  return Number(n.toFixed(Math.max(0, precision))).toString()
}

function formatReadoutValue(param, value) {
  const n = Number(value)
  if (value === null || value === undefined || !Number.isFinite(n)) return "--"
  const precision = Number.isFinite(Number(param.precision)) ? Number(param.precision) : 2
  return `${n.toFixed(precision)}${param.unit || ""}`
}

function numericBounds(param) {
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
    return { min: 1, max: 101, step: 1 }
  }

  // Personality jerk params are stored as percentage-style integers (25..200).
  // Layout metadata currently uses normalized 0.5..3.0 ranges, which breaks
  // the +/- stepper and clamps values like 50 down to 3.
  if (/^(Traffic|Aggressive|Standard|Relaxed)Jerk(Acceleration|Deceleration|Danger|SpeedDecrease|Speed)$/.test(String(param.key || ""))) {
    return { min: 25, max: 200, step: 1 }
  }

  if (param.key === "SteerKP") {
    const base = toFinite(state.values.SteerKPStock) || toFinite(state.values.SteerKP) || 0.6
    return { min: +(base * 0.5).toFixed(2), max: +(base * 1.5).toFixed(2), step: 0.01 }
  }
  if (param.key === "SteerLatAccel") {
    const base = toFinite(state.values.SteerLatAccelStock) || toFinite(state.values.SteerLatAccel) || 2.0
    return { min: +(base * 0.5).toFixed(2), max: +(base * 1.25).toFixed(2), step: 0.01 }
  }
  if (param.key === "SteerRatio") {
    const base = toFinite(state.values.SteerRatioStock) || toFinite(state.values.SteerRatio) || 15.0
    return { min: +(base * 0.25).toFixed(2), max: +(base * 1.5).toFixed(2), step: 0.01 }
  }

  return defaultBounds
}

function coerceValueByType(rawValue, dataType) {
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

function defaultFavoriteSlots() {
  return [0, 1, 2].map(() => ({
    enabled: false,
    show_onroad: false,
    key: null,
    label: "",
  }))
}

function normalizeFavoriteSlots(slots) {
  const normalized = defaultFavoriteSlots()
  if (!Array.isArray(slots)) return normalized

  slots.slice(0, 3).forEach((slot, index) => {
    if (!slot || typeof slot !== "object") return
    const key = slot.key ? String(slot.key) : null
    normalized[index] = {
      enabled: !!slot.enabled,
      show_onroad: !!slot.show_onroad,
      key,
      label: key ? String(slot.label || key) : "",
    }
  })

  return normalized
}

function compareFavoriteOptions(a, b) {
  const labelCompare = FAVORITE_OPTION_COLLATOR.compare(String(a?.label || a?.key || ""), String(b?.label || b?.key || ""))
  if (labelCompare !== 0) return labelCompare
  return FAVORITE_OPTION_COLLATOR.compare(String(a?.key || ""), String(b?.key || ""))
}

function normalizeFavoriteOptions(options) {
  if (!Array.isArray(options)) return []
  return [...options].sort(compareFavoriteOptions)
}

function favoriteOptionMatchesFilter(option, filter) {
  if (!filter) return true
  const q = filter.toLowerCase()
  return [option.label, option.key, option.section, option.description]
    .some(value => String(value || "").toLowerCase().includes(q))
}

function isFavoriteActionKey(key) {
  return String(key || "").startsWith(FAVORITE_ACTION_PREFIX)
}

function isFavoriteActionOption(option) {
  return isFavoriteActionKey(option?.key) || !!option?.action
}

function filteredFavoriteOptions(index) {
  const filter = state.favoriteFilters[index] || ""
  return normalizeFavoriteOptions(state.favoriteOptions).filter(opt => favoriteOptionMatchesFilter(opt, filter))
}

function populateFavoriteSelect(index, selectEl = null) {
  const select = selectEl || document.querySelector(`select[data-favorite-slot="${index}"][data-favorite-field="key"]`)
  if (!select) return

  const slots = normalizeFavoriteSlots(state.favoriteSlots)
  const selectedKey = slots[index]?.key || ""
  const options = filteredFavoriteOptions(index)
  select.replaceChildren()
  select.appendChild(new Option("Select a toggle...", "", false, selectedKey === ""))
  for (const opt of options) {
    select.appendChild(new Option(opt.label, opt.key, false, selectedKey === opt.key))
  }
  select.value = options.some(opt => opt.key === selectedKey) ? selectedKey : ""
}

async function fetchFavoriteSlots() {
  state.favoriteLoading = true
  try {
    const res = await fetch("/api/favorites/slots", { cache: "no-store" })
    const data = await res.json()
    if (res.ok) {
      state.favoriteOptions = normalizeFavoriteOptions(data.options)
      state.favoriteSlots = normalizeFavoriteSlots(data.slots)
      state.favoriteValues = data.values || {}
      state.values = { ...state.values, ...state.favoriteValues, StarPilotFavoriteSlots: state.favoriteSlots }
    }
  } catch (e) {
    console.error("Failed to fetch favorite slots:", e)
  }
  state.favoriteLoading = false
}

async function refreshFavoriteValues() {
  if (favoritePollInflight || state.favoriteSaving || state.favoriteLoading) return favoritePollInflight

  favoritePollInflight = fetch("/api/favorites/values", { cache: "no-store" })
    .then(async res => {
      if (!res.ok) return

      const data = await res.json()
      const values = (data.values && typeof data.values === "object") ? data.values : {}
      const changed = Object.entries(values).some(([key, value]) => state.values[key] !== value)
      if (!changed) return

      state.favoriteValues = { ...state.favoriteValues, ...values }
      state.values = { ...state.values, ...values }
      scheduleSyncInputs()
    })
    .catch(() => {})
    .finally(() => {
      favoritePollInflight = null
    })

  return favoritePollInflight
}

function ensureFavoriteValuePolling() {
  if (favoritePollTimer !== null) return

  favoritePollTimer = setInterval(() => {
    if (!window.location.pathname.startsWith("/device_settings")) {
      clearInterval(favoritePollTimer)
      favoritePollTimer = null
      return
    }
    if (document.visibilityState === "visible") {
      refreshFavoriteValues()
    }
  }, 1000)
}

async function saveFavoriteSlots(slots) {
  if (state.favoriteSaving) return

  const previousSlots = state.favoriteSlots
  state.favoriteSlots = normalizeFavoriteSlots(slots)
  state.favoriteSaving = true

  try {
    const res = await fetch("/api/favorites/slots", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slots: state.favoriteSlots }),
    })
    const data = await res.json()

    if (res.ok) {
      state.favoriteOptions = Array.isArray(data.options) ? normalizeFavoriteOptions(data.options) : normalizeFavoriteOptions(state.favoriteOptions)
      state.favoriteSlots = normalizeFavoriteSlots(data.slots)
      state.favoriteValues = data.values || {}
      state.values = { ...state.values, ...state.favoriteValues, StarPilotFavoriteSlots: state.favoriteSlots }
      showParamSnackbar(data.message || "Favorite slots saved.")
      scheduleSyncInputs()
      window.setTimeout(() => window.location.reload(), 250)
    } else {
      state.favoriteSlots = previousSlots
      showParamSnackbar(data.error || "Failed to save favorite slots", "error")
    }
  } catch (e) {
    state.favoriteSlots = previousSlots
    showParamSnackbar("Network error — is the device reachable?", "error")
  }

  state.favoriteSaving = false
}

function updateFavoriteSlot(index, patch) {
  const slots = normalizeFavoriteSlots(state.favoriteSlots)
  const current = slots[index] || defaultFavoriteSlots()[0]
  const nextSlot = { ...current, ...patch }

  if (!nextSlot.key) {
    nextSlot.label = ""
  } else {
    const option = state.favoriteOptions.find(opt => opt.key === nextSlot.key)
    nextSlot.label = option?.label || nextSlot.key
  }

  slots[index] = nextSlot
  saveFavoriteSlots(slots)
}

function updateFavoriteFilter(index, event) {
  const filters = Array.isArray(state.favoriteFilters) ? [...state.favoriteFilters] : ["", "", ""]
  filters[index] = getEventValue(event)
  state.favoriteFilters = filters.slice(0, 3)
  populateFavoriteSelect(index)
  scheduleSyncInputs()
}

async function updateFavoriteValue(key, checked, sourceEl = null) {
  if (!confirmPandaFirmwareToggle(key, checked)) {
    if (sourceEl) sourceEl.checked = !!state.values[key]
    scheduleSyncInputs()
    return
  }

  const current = state.values[key]
  state.values = { ...state.values, [key]: checked }
  state.favoriteValues = { ...state.favoriteValues, [key]: checked }

  try {
    const res = await fetch("/api/params", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value: checked, ...pandaFirmwareConfirmationPayload(key) }),
    })
    const data = await res.json()

    if (res.ok) {
      const updated = (data.updated && typeof data.updated === "object") ? data.updated : {}
      state.values = { ...state.values, [key]: checked, ...updated }
      state.favoriteValues = { ...state.favoriteValues, [key]: state.values[key] }
      showParamSnackbar(data.message || `Parameter '${key}' updated.`)
      scheduleSyncInputs()
    } else {
      state.values = { ...state.values, [key]: current }
      state.favoriteValues = { ...state.favoriteValues, [key]: current }
      showParamSnackbar(data.error || "Failed to update parameter", "error")
    }
  } catch (e) {
    state.values = { ...state.values, [key]: current }
    state.favoriteValues = { ...state.favoriteValues, [key]: current }
    showParamSnackbar("Network error — is the device reachable?", "error")
  }
}

async function activateFavoriteAction(key) {
  try {
    const res = await fetch("/api/favorites/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key }),
    })
    const data = await res.json()

    if (res.ok) {
      showParamSnackbar(data.message || "Favorite action sent.")
    } else {
      showParamSnackbar(data.error || "Failed to send favorite action", "error")
    }
  } catch (e) {
    showParamSnackbar("Network error — is the device reachable?", "error")
  }
}

function stepPrecision(step, explicitPrecision) {
  if (explicitPrecision !== undefined && explicitPrecision !== null && explicitPrecision !== "") {
    const parsed = Number.parseInt(explicitPrecision, 10)
    if (Number.isFinite(parsed) && parsed >= 0) return parsed
  }

  const stepStr = String(step ?? "")
  if (!stepStr.includes(".")) return 0
  return stepStr.split(".")[1].length
}

function clampNumeric(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function snapNumericToBoundsAndStep(rawValue, bounds, precision) {
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

function resolveCurrentNumericValue(param, bounds) {
  const raw = state.values[param.key]
  const precision = stepPrecision(bounds.step, param.precision)
  const snapped = snapNumericToBoundsAndStep(raw, bounds, precision)
  if (snapped !== null) return snapped

  const fallback = Number(bounds.min)
  return Number.isFinite(fallback) ? fallback : 0
}

function resolveDefaultNumericValue(param, bounds) {
  const precision = stepPrecision(bounds.step, param.precision)
  const stockKey = `${param.key}Stock`

  // Prefer live vehicle stock values when available.
  const liveStock = snapNumericToBoundsAndStep(state.values?.[stockKey], bounds, precision)
  if (liveStock !== null) return liveStock

  // Fallback to default table stock value if present.
  const defaultStock = snapNumericToBoundsAndStep(state.defaultValues?.[stockKey], bounds, precision)
  if (defaultStock !== null) return defaultStock

  // Final fallback: generic param default.
  return snapNumericToBoundsAndStep(state.defaultValues?.[param.key], bounds, precision)
}

function isNumericUpdating(key) {
  return !!state.numericUpdating[key]
}

function showParamSnackbar(message, level, timeout = 2200) {
  showSnackbar(message, level, timeout, {
    key: "device-settings-param-update",
    replace: true,
  })
}

function getParamDisplayLabel(key) {
  return state.paramMetaByKey[key]?.label || key
}

function getSliderDescription(param, value) {
  const steps = Array.isArray(param.description_steps) ? param.description_steps : []
  if (!steps.length) return param.description || ""

  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return param.description || ""
  const selected = steps.find(step => numericValue <= Number(step.max)) || steps[steps.length - 1]
  return selected.description || param.description || ""
}

function confirmPandaFirmwareToggle(key, enabled) {
  if (!PANDA_FIRMWARE_TOGGLE_KEYS.has(key)) return true

  const label = getParamDisplayLabel(key)
  const action = enabled ? "Enable" : "Disable"
  return window.confirm(
    `${label} requires a Panda firmware update.\n\n` +
    `${action} ${label} and flash the Panda now?`
  )
}

function pandaFirmwareConfirmationPayload(key) {
  return PANDA_FIRMWARE_TOGGLE_KEYS.has(key) ? { confirmedPandaFirmwareFlash: true } : {}
}

function syncNumericDisplay(param, rawValue) {
  const displayEl = document.getElementById(`ds-display-${param.key}`)
  if (!displayEl) return

  const bounds = numericBounds(param)
  displayEl.textContent = formatSliderValue(
    rawValue,
    String(bounds.step),
    param.precision,
    param.key,
  )
}

async function updateNumericParam(param, numericValue, options = {}) {
  const key = param.key
  const current = options.previousValue !== undefined ? options.previousValue : state.values[key]
  if (Object.prototype.hasOwnProperty.call(state.sliderPreviewValues, key)) {
    const nextPreviewValues = { ...state.sliderPreviewValues }
    delete nextPreviewValues[key]
    state.sliderPreviewValues = nextPreviewValues
  }
  const successMessage = options.successMessage
  state.numericUpdating = { ...state.numericUpdating, [key]: true }
  state.values = { ...state.values, [key]: numericValue }
  syncNumericDisplay(param, numericValue)
  try {
    const res = await fetch("/api/params", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value: coerceValueByType(numericValue, param.data_type) }),
    })
    const data = await res.json()

    if (res.ok) {
      const updated = (data.updated && typeof data.updated === "object") ? data.updated : {}
      const resolvedValue = Object.prototype.hasOwnProperty.call(updated, key) ? updated[key] : numericValue
      state.values = { ...state.values, [key]: resolvedValue, ...updated }
      state.numericUpdating = { ...state.numericUpdating, [key]: false }
      syncNumericDisplay(param, resolvedValue)
      showParamSnackbar(successMessage || data.message || `Parameter '${key}' updated.`)
      scheduleSyncInputs()
    } else {
      state.values = { ...state.values, [key]: current }
      state.numericUpdating = { ...state.numericUpdating, [key]: false }
      syncNumericDisplay(param, current)
      showParamSnackbar(data.error || "Failed to update parameter", "error")
    }
  } catch (e) {
    state.values = { ...state.values, [key]: current }
    state.numericUpdating = { ...state.numericUpdating, [key]: false }
    syncNumericDisplay(param, current)
    showParamSnackbar("Network error — is the device reachable?", "error")
  }
}

function previewSliderParam(param, rawValue) {
  if (isNumericUpdating(param.key)) return

  const bounds = numericBounds(param)
  const precision = stepPrecision(bounds.step, param.precision)
  const snapped = snapNumericToBoundsAndStep(rawValue, bounds, precision)
  if (snapped === null) return

  state.sliderPreviewValues = { ...state.sliderPreviewValues, [param.key]: snapped }
  syncNumericDisplay(param, snapped)
}

function commitSliderParam(param, rawValue) {
  if (isNumericUpdating(param.key)) return

  const bounds = numericBounds(param)
  const precision = stepPrecision(bounds.step, param.precision)
  const next = snapNumericToBoundsAndStep(rawValue, bounds, precision)
  if (next === null) return

  const current = resolveCurrentNumericValue(param, bounds)
  const previewValues = { ...state.sliderPreviewValues }
  delete previewValues[param.key]
  state.sliderPreviewValues = previewValues

  const epsilon = Math.pow(10, -(precision + 2))
  if (Math.abs(next - current) <= epsilon) {
    syncNumericDisplay(param, current)
    return
  }

  updateNumericParam(param, next, { previousValue: current })
}

function stepNumericParam(param, direction) {
  const bounds = numericBounds(param)
  const min = Number(bounds.min)
  const max = Number(bounds.max)
  const step = Number(bounds.step)

  if (!Number.isFinite(min) || !Number.isFinite(max) || !Number.isFinite(step) || step <= 0) return
  if (isNumericUpdating(param.key)) return

  const current = resolveCurrentNumericValue(param, bounds)
  const precision = stepPrecision(step, param.precision)
  const epsilon = Math.pow(10, -(precision + 2))

  const next = snapNumericToBoundsAndStep(current + (direction * step), bounds, precision)
  if (next === null) return
  if (Math.abs(next - current) <= epsilon) return

  updateNumericParam(param, next)
}

function applyManualNumericParam(param) {
  if (isNumericUpdating(param.key)) return

  const inputEl = document.getElementById(`ds-manual-${param.key}`)
  if (!inputEl) return

  const raw = String(inputEl.value ?? "").trim()
  if (!raw) {
    showParamSnackbar("Enter a value first.", "error")
    return
  }

  const parsed = Number.parseFloat(raw)
  if (!Number.isFinite(parsed)) {
    showParamSnackbar("Enter a valid number.", "error")
    return
  }

  const bounds = numericBounds(param)
  const precision = stepPrecision(bounds.step, param.precision)
  const snapped = snapNumericToBoundsAndStep(parsed, bounds, precision)
  if (snapped === null) {
    showParamSnackbar("Value is out of range.", "error")
    return
  }

  inputEl.value = formatNumericForInput(snapped, precision)

  const current = resolveCurrentNumericValue(param, bounds)
  const epsilon = Math.pow(10, -(precision + 2))
  if (Math.abs(snapped - current) <= epsilon) return

  updateNumericParam(param, snapped)
}

async function resetNumericParam(param) {
  const bounds = numericBounds(param)
  let defaultValue = resolveDefaultNumericValue(param, bounds)
  if (defaultValue === null) {
    const loaded = await fetchDefaultValues()
    if (!loaded) {
      showParamSnackbar("Couldn't load defaults. Try refreshing the page.", "error")
      return
    }
    defaultValue = resolveDefaultNumericValue(param, bounds)
  }

  if (defaultValue === null) {
    showParamSnackbar("No default value available for this setting.", "error")
    return
  }
  if (isNumericUpdating(param.key)) return

  const current = resolveCurrentNumericValue(param, bounds)
  const precision = stepPrecision(bounds.step, param.precision)
  const epsilon = Math.pow(10, -(precision + 2))
  if (Math.abs(defaultValue - current) <= epsilon) return

  updateNumericParam(param, defaultValue, {
    successMessage: `Parameter '${param.key}' reset to default.`,
  })
}

async function runSettingAction(param) {
  const key = String(param?.key || "")
  const endpoint = String(param?.action_endpoint || "")
  if (!key || !endpoint || state.actionUpdating[key]) return

  const confirmation = String(param?.confirm_message || `Run ${param?.label || key}?`)
  if (!window.confirm(confirmation)) return

  state.actionUpdating = { ...state.actionUpdating, [key]: true }
  try {
    const response = await fetch(endpoint, { method: "POST" })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Action failed")
    }

    const updated = payload.updated && typeof payload.updated === "object" ? payload.updated : {}
    state.values = { ...state.values, ...updated }
    showParamSnackbar(payload.message || `${param?.label || key} completed.`)
    scheduleSyncInputs()
  } catch (error) {
    showParamSnackbar(error?.message || `${param?.label || key} failed.`, "error")
  } finally {
    const next = { ...state.actionUpdating }
    delete next[key]
    state.actionUpdating = next
  }
}

async function updateParam(key, elType) {
  if (String(key).toLowerCase() === "starpilotfavoriteslots") {
    await saveFavoriteSlots(state.favoriteSlots)
    return
  }

  const current = state.values[key]
  const el = document.getElementById(`ds-${key}`)
  if (!el) return

  const param = state.paramMetaByKey[key] || {}
  let selectedLabel = ""

  let formattedVal
  if (elType === "checkbox") {
    formattedVal = !!el.checked
  } else if (elType === "dropdown") {
    formattedVal = coerceValueByType(el.value, param.data_type)
    selectedLabel = el.options?.[el.selectedIndex]?.textContent || ""
  } else if (elType === "color") {
    formattedVal = normalizeHexColor(el.value) || getColorDefault(param)
  } else {
    formattedVal = coerceValueByType(el.value, param.data_type)
  }

  if (elType === "checkbox" && !confirmPandaFirmwareToggle(key, formattedVal)) {
    revertInput(key, current, elType)
    return
  }

  if (elType === "checkbox" && formattedVal && param.confirm_message && !window.confirm(param.confirm_message)) {
    revertInput(key, current, elType)
    return
  }

  try {
    const res = await fetch("/api/params", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value: formattedVal, label: selectedLabel, ...pandaFirmwareConfirmationPayload(key) }),
    })
    const data = await res.json()

    if (res.ok) {
      const updated = (data.updated && typeof data.updated === "object") ? data.updated : {}
      state.values = { ...state.values, [key]: formattedVal, ...updated }
      showParamSnackbar(data.message || `Parameter '${key}' updated.`)
      if (DYNAMIC_DEFAULT_DEP_KEYS.has(key)) {
        await refreshParamsAndDefaults()
      } else {
        scheduleSyncInputs()
      }
    } else {
      revertInput(key, current, elType)
      showParamSnackbar(data.error || "Failed to update parameter", "error")
    }
  } catch (e) {
    revertInput(key, current, elType)
    showParamSnackbar("Network error — is the device reachable?", "error")
  }
}

async function restoreRhdAutoDetection() {
  const currentValues = { ...state.values }
  try {
    const res = await fetch("/api/params", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: "IsRHDOverride", value: false }),
    })
    const data = await res.json()

    if (res.ok) {
      const updated = (data.updated && typeof data.updated === "object") ? data.updated : {}
      state.values = { ...state.values, IsRHDOverride: false, ...updated }
      showParamSnackbar(data.message || "Right Hand Driving auto detection restored.")
      scheduleSyncInputs()
    } else {
      state.values = currentValues
      showParamSnackbar(data.error || "Failed to restore auto detection", "error")
    }
  } catch (e) {
    state.values = currentValues
    showParamSnackbar("Network error — is the device reachable?", "error")
  }
}

function revertInput(key, current, elType) {
  const el = document.getElementById(`ds-${key}`)
  if (!el) return

  if (elType === "checkbox") {
    el.checked = !!current
    return
  }

  if (elType === "dropdown") {
    el.value = toSelectValue(current)
    return
  }

  if (elType === "color") {
    const param = state.paramMetaByKey[key]
    if (!param) return
    el.value = resolveColorInputValue(param, current)
    return
  }

  el.value = current
}

async function resetColorParam(param) {
  const key = param?.key
  if (!key) return

  const current = state.values[key]
  if (isStockColorValue(current)) return

  try {
    const res = await fetch("/api/params", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value: "stock" }),
    })
    const data = await res.json()

    if (res.ok) {
      const updated = (data.updated && typeof data.updated === "object") ? data.updated : {}
      state.values = { ...state.values, [key]: "stock", ...updated }
      showParamSnackbar(data.message || `Parameter '${key}' reset to stock.`)
      scheduleSyncInputs()
    } else {
      showParamSnackbar(data.error || "Failed to reset parameter", "error")
      revertInput(key, current, "color")
    }
  } catch (e) {
    showParamSnackbar("Network error — is the device reachable?", "error")
    revertInput(key, current, "color")
  }
}

function toggleManage(key) {
  state.expanded = { ...state.expanded, [key]: !state.expanded[key] }
  scheduleSyncInputs()
}

function matchesFilter(p) {
  if (!state.filter) return true
  if (isGroupParam(p)) return false
  const q = state.filter.toLowerCase()
  const label = String(p.label || "").toLowerCase()
  const key = String(p.key || "").toLowerCase()
  const description = String(p.description || "").toLowerCase()
  return label.includes(q) || key.includes(q) || description.includes(q)
}

function clearSearchFilter() {
  if (!state.filter) return
  state.filter = ""
  scheduleSyncInputs()
}

const cancelButtonKeys = new Set(["CancelButtonControl", "LongCancelButtonControl", "VeryLongCancelButtonControl"])

function getSettingLockReason(param) {
  if (param?.requires_offroad && state.values.IsOnroad) {
    return "This setting can only be changed while parked."
  }
  if (param?.requires_parked && !state.values.VehicleParked) {
    return "This setting can only be changed while the vehicle is in Park."
  }
  if (param?.disabled_when_key_true && state.values[param.disabled_when_key_true]) {
    return param.disabled_reason || "Disabled by another setting."
  }
  if (param?.requires_nonempty_key) {
    const val = state.values[param.requires_nonempty_key]
    if (!val || val === "{}" || val === "") {
      return param.disabled_reason || "Required configuration missing."
    }
  }
  return ""
}

function valuesEqual(left, right) {
  if (typeof left === "number" || typeof right === "number") {
    const leftNumber = Number(left)
    const rightNumber = Number(right)
    return Number.isFinite(leftNumber) && Number.isFinite(rightNumber) && Math.abs(leftNumber - rightNumber) < 1e-9
  }
  return left === right
}

function getFlmParamStatus(key) {
  const trial = state.flmActiveTrial
  if (!trial || !FLM_ADVANCED_LATERAL_KEYS.has(key)) return null

  const applied = trial.appliedGenericParams || {}
  const hasExplicitMetadata = Object.prototype.hasOwnProperty.call(applied, key)
  const previous = trial.params || {}
  const hasPreviousValue = Object.prototype.hasOwnProperty.call(previous, key)

  // Older active snapshots did not record the applied bundle, so infer only
  // changed values for compatibility. New snapshots always use explicit metadata.
  if (!hasExplicitMetadata && (!hasPreviousValue || valuesEqual(previous[key], state.values[key]))) return null

  return {
    effectiveValue: state.values[key],
    previousValue: hasPreviousValue ? previous[key] : undefined,
  }
}

function formatFlmValue(param, value) {
  if (value === undefined || value === null) return "not set"
  if (param.data_type === "bool") return value ? "On" : "Off"
  if (param.ui_type === "numeric") {
    const bounds = numericBounds(param)
    return formatSliderValue(value, String(bounds.step), param.precision, param.key)
  }
  return String(value)
}

function getFlmTrialSummary() {
  const trial = state.flmActiveTrial
  if (!trial) return null
  const genericCount = Object.keys(trial.appliedGenericParams || {}).filter(key => key !== "AdvancedLateralTune").length
  const thresholdCount = Object.keys(trial.appliedFrictionThresholds || {}).length
  const vehicleKnobCount = Object.keys(trial.appliedVehicleKnobs || {}).length
  const title = [trial.pathLabel, trial.profileLabel].filter(Boolean).join(" / ") || "Active trial"
  return { title, genericCount, thresholdCount, vehicleKnobCount }
}

function handleSectionTabClick(sectionSlug, event) {
  if (!sectionSlug || sectionSlug === state.activeSectionSlug) return

  // Preserve horizontal tab strip position on mobile when switching sections.
  const tabsEl = event?.currentTarget?.closest(".ds-tabs")
  const preservedScrollLeft = tabsEl ? tabsEl.scrollLeft : null

  state.activeSectionSlug = sectionSlug

  if (preservedScrollLeft !== null) {
    requestAnimationFrame(() => {
      const nextTabsEl = document.getElementById("ds-tabs")
      if (nextTabsEl) nextTabsEl.scrollLeft = preservedScrollLeft
    })
  }
}

function renderFavoriteSlotsPanel() {
  if (state.favoriteLoading) {
    return html`<div class="ds-loading">Loading favorite slots...</div>`
  }

  const slots = normalizeFavoriteSlots(state.favoriteSlots)
  const options = normalizeFavoriteOptions(state.favoriteOptions)
  const optionByKey = new Map(options.map(opt => [opt.key, opt]))
  const quickFavorites = slots
    .map((slot, index) => {
      const selectedKey = slot.key || ""
      const selectedOption = optionByKey.get(selectedKey)
      return {
        index,
        slot,
        selectedKey,
        selectedOption,
        selectedValue: selectedKey ? !!state.values[selectedKey] : false,
      }
    })
    .filter(favorite => favorite.slot.enabled && favorite.selectedKey && favorite.selectedOption)

  return html`
    <div class="ds-favorites-panel">
      ${quickFavorites.length ? html`
        <div class="ds-favorite-quick-grid">
          ${quickFavorites.map(favorite => {
            const selectedOption = favorite.selectedOption
            const selectedKey = favorite.selectedKey
            const selectedValue = favorite.selectedValue
            const isAction = isFavoriteActionOption(selectedOption)
            const quickCopy = html`
              <div class="ds-favorite-quick-copy">
                <span class="ds-favorite-quick-slot">Favorite #${favorite.index + 1}</span>
                <span class="ds-favorite-quick-title">${selectedOption.label || favorite.slot.label || selectedKey}</span>
                ${selectedOption.section ? html`<span class="ds-favorite-quick-section">${selectedOption.section}</span>` : ""}
                ${selectedOption.description ? html`<span class="ds-favorite-quick-desc">${selectedOption.description}</span>` : ""}
              </div>
            `

            if (isAction) {
              return html`
                <button
                  type="button"
                  class="ds-favorite-quick-card ds-favorite-action-card"
                  @click="${() => activateFavoriteAction(selectedKey)}">
                  ${quickCopy}
                  <span class="ds-favorite-action-chip">Press</span>
                </button>
              `
            }

            return html`
              <label class="ds-favorite-quick-card">
                ${quickCopy}
                <input
                  type="checkbox"
                  class="ds-toggle ds-favorite-quick-toggle"
                  data-favorite-value-key="${selectedKey}"
                  checked="${() => selectedValue}"
                  @change="${(e) => updateFavoriteValue(selectedKey, !!e.currentTarget.checked, e.currentTarget)}" />
              </label>
            `
          })}
        </div>
      ` : ""}

      ${slots.map((slot, index) => {
        const selectedOption = optionByKey.get(slot.key)
        const selectedKey = slot.key || ""
        const favoriteFilter = state.favoriteFilters[index] || ""
        const filteredOptions = options.filter(opt => favoriteOptionMatchesFilter(opt, favoriteFilter))

        return html`
          <div class="ds-favorite-card">
            <div class="ds-favorite-card-header">
              <div>
                <div class="ds-row-label">Favorite #${index + 1}</div>
                <div class="ds-row-desc">${selectedOption?.section || "No toggle selected"}</div>
              </div>
              <label class="ds-favorite-switch">
                <span>Enabled</span>
                <input
                  type="checkbox"
                  class="ds-toggle"
                  data-favorite-slot="${index}"
                  data-favorite-field="enabled"
                  checked="${() => slot.enabled}"
                  disabled="${() => state.favoriteSaving}"
                  @change="${(e) => updateFavoriteSlot(index, { enabled: !!e.currentTarget.checked })}" />
              </label>
            </div>

            <div class="ds-favorite-controls">
              <label class="ds-favorite-field">
                <span>Search</span>
                <input
                  type="search"
                  class="ds-search ds-favorite-search"
                  data-favorite-slot="${index}"
                  data-favorite-field="search"
                  value="${() => favoriteFilter}"
                  disabled="${() => state.favoriteSaving}"
                  @input="${(e) => updateFavoriteFilter(index, e)}" />
              </label>

              <label class="ds-favorite-field">
                <span>Toggle</span>
                <select
                  class="ds-select ds-favorite-select"
                  data-favorite-slot="${index}"
                  data-favorite-field="key"
                  disabled="${() => state.favoriteSaving}"
                  @change="${(e) => updateFavoriteSlot(index, { key: e.currentTarget.value || null })}">
                  <option value="" selected="${() => selectedKey === ""}">Select a toggle...</option>
                  ${filteredOptions.map(opt => html`
                    <option value="${opt.key}" selected="${() => selectedKey === opt.key}">${opt.label}</option>
                  `)}
                </select>
              </label>

              <label class="ds-favorite-switch">
                <span>On-Road Button (C4: tap invisible third)</span>
                <input
                  type="checkbox"
                  class="ds-toggle"
                  data-favorite-slot="${index}"
                  data-favorite-field="show_onroad"
                  checked="${() => slot.show_onroad}"
                  disabled="${() => state.favoriteSaving || !slot.enabled || !selectedKey}"
                  @change="${(e) => updateFavoriteSlot(index, { show_onroad: !!e.currentTarget.checked })}" />
              </label>
            </div>
          </div>
        `
      })}
    </div>
  `
}

function renderSettingRow(p) {
  if (p.ui_type === "favorites") {
    return renderFavoriteSlotsPanel()
  }

  if (p.parent_key && !state.filter) {
    if (!isParamEnabledForChildren(p.parent_key)) return ""
    if (!state.expanded[p.parent_key]) return ""
  }
  if (cancelButtonKeys.has(p?.key) && !state.values.RemapCancelToDistance) {
    return ""
  }

  const isNumeric = p.ui_type === "numeric"
  const isSlider = isNumeric && p.control === "slider"
  const isText = p.ui_type === "text"
  const isColor = p.ui_type === "color"
  const isAction = p.ui_type === "action"
  const isGroup = isGroupParam(p)
  const isChild = p.parent_key ? "ds-child-modifier" : ""
  const lockReason = () => getSettingLockReason(p)
  const isLocked = () => lockReason() !== ""
  const flmParamStatus = getFlmParamStatus(p.key)
  const flmTrialSummary = p.key === "AdvancedLateralTune" ? getFlmTrialSummary() : null
  let rowControl = ""

  if (isAction) {
    rowControl = html`
      <button
        class="ds-reset-btn"
        disabled="${() => isLocked() || !!state.actionUpdating[p.key]}"
        @click="${() => runSettingAction(p)}">
        ${() => state.actionUpdating[p.key] ? "Resetting..." : (p.action_label || "Run")}
      </button>
    `
  } else if (isSlider) {
    rowControl = html`
      <div class="ds-slider-container">
        <input
          type="range"
          class="ds-slider"
          min="${numericBounds(p).min}"
          max="${numericBounds(p).max}"
          step="${numericBounds(p).step}"
          aria-label="${p.label}"
          disabled="${() => isLocked() || isNumericUpdating(p.key)}"
          value="${() => {
            const bounds = numericBounds(p)
            const preview = state.sliderPreviewValues[p.key]
            return formatNumericForInput(preview ?? resolveCurrentNumericValue(p, bounds), stepPrecision(bounds.step, p.precision))
          }}"
          @input="${(event) => previewSliderParam(p, event.currentTarget.value)}"
          @change="${(event) => commitSliderParam(p, event.currentTarget.value)}" />
        <div class="ds-slider-scale">
          <span>${formatSliderValue(numericBounds(p).min, String(numericBounds(p).step), p.precision, p.key)}</span>
          <span>${formatSliderValue(numericBounds(p).max, String(numericBounds(p).step), p.precision, p.key)}</span>
        </div>
        <button
          class="ds-reset-btn"
          disabled="${() => {
            const bounds = numericBounds(p)
            const defaultValue = resolveDefaultNumericValue(p, bounds)
            const currentValue = resolveCurrentNumericValue(p, bounds)
            const precision = stepPrecision(bounds.step, p.precision)
            const epsilon = Math.pow(10, -(precision + 2))
            return isLocked() || isNumericUpdating(p.key) || defaultValue === null || Math.abs(defaultValue - currentValue) <= epsilon
          }}"
          @click="${() => resetNumericParam(p)}">Reset to Default</button>
      </div>
    `
  } else if (isNumeric) {
    rowControl = html`
      <div class="ds-stepper-container">
        ${(() => {
      const bounds = numericBounds(p)
      const currentNumeric = resolveCurrentNumericValue(p, bounds)
      const precision = stepPrecision(bounds.step, p.precision)
      const epsilon = Math.pow(10, -(precision + 2))
      const updating = isNumericUpdating(p.key)
      const canDecrease = !updating && currentNumeric > (Number(bounds.min) + epsilon)
      const canIncrease = !updating && currentNumeric < (Number(bounds.max) - epsilon)
      const defaultNumeric = resolveDefaultNumericValue(p, bounds)
      const defaultLabel = defaultNumeric !== null
        ? formatSliderValue(defaultNumeric, String(bounds.step), p.precision, p.key)
        : "N/A"
      const canReset = !updating && defaultNumeric !== null && Math.abs(defaultNumeric - currentNumeric) > epsilon
      const stepLabel = p.key === "DeviceShutdown" ? "1 hour" : formatStepValue(bounds.step, precision)
      return html`
            <div class="ds-stepper">
              <button
                class="ds-stepper-btn"
                disabled="${() => isLocked() || !canDecrease || false}"
                @click="${() => stepNumericParam(p, -1)}">-</button>
              <div class="ds-stepper-meta">
                <span>${formatSliderValue(bounds.min, String(bounds.step), p.precision, p.key)} to ${formatSliderValue(bounds.max, String(bounds.step), p.precision, p.key)}</span>
                <span class="ds-step-value">Step: ${stepLabel} per click</span>
                <span class="ds-default-value">Default: ${defaultLabel}</span>
                <div class="ds-manual-row">
                  <input
                    type="number"
                    class="ds-manual-input"
                    id="ds-manual-${p.key}"
                    min="${bounds.min}"
                    max="${bounds.max}"
                    step="${bounds.step}"
                    disabled="${() => isLocked() || updating}"
                    value="${() => formatNumericForInput(resolveCurrentNumericValue(p, numericBounds(p)), precision)}"
                    @keydown="${(e) => {
                      if (e.key !== "Enter") return
                      e.preventDefault()
                      applyManualNumericParam(p)
                    }}" />
                  <button
                    class="ds-apply-btn"
                    disabled="${() => isLocked() || updating}"
                    @click="${() => applyManualNumericParam(p)}">Apply</button>
                </div>
                <button
                  class="ds-reset-btn"
                  disabled="${() => isLocked() || !canReset || false}"
                  @click="${() => resetNumericParam(p)}">Reset to Default</button>
              </div>
              <button
                class="ds-stepper-btn"
                disabled="${() => isLocked() || !canIncrease || false}"
                @click="${() => stepNumericParam(p, 1)}">+</button>            </div>
          `
    })()}
      </div>
    `
  } else if (p.ui_type === "dropdown") {
    rowControl = html`
      <select
        class="ds-select"
        id="ds-${p.key}"
        data-endpoint="${p.options_endpoint || ""}"
        disabled="${() => isLocked()}"
        @change="${() => updateParam(p.key, "dropdown")}">
        <option value="">Loading...</option>
      </select>
    `
  } else if (isText) {
    rowControl = html`
      <input
        type="${p.input_type || "text"}"
        class="ds-manual-input ds-text-input"
        id="ds-${p.key}"
        value="${() => toSelectValue(state.values[p.key])}"
        placeholder="${p.placeholder || ""}"
        disabled="${() => isLocked()}"
        @change="${() => updateParam(p.key, "text")}" />
    `
  } else if (p.ui_type === "readout") {
    rowControl = html`
      <span class="ds-readout" id="ds-${p.key}">${() => formatReadoutValue(p, state.values[p.key])}</span>
    `
  } else if (p.ui_type === "color") {
    rowControl = html`
      <div style="display:flex; align-items:center; gap:0.75rem;">
        <input
          type="color"
          class="ds-color"
          id="ds-${p.key}"
          disabled="${() => isLocked()}"
          value="${() => resolveColorInputValue(p)}"
          @change="${() => updateParam(p.key, "color")}" />
        <button
          class="ds-reset-btn"
          disabled="${() => isLocked() || isStockColorValue(state.values[p.key])}"
          @click="${() => resetColorParam(p)}">Stock</button>
      </div>
    `
  } else if (!isGroup) {
    if (p.key === "IsRHD") {
      rowControl = html`
        <div style="display:flex; align-items:center; gap:0.75rem;">
          <input
            type="checkbox"
            class="ds-toggle"
            id="ds-${p.key}"
            @change="${() => updateParam(p.key, "checkbox")}" />
          ${() => state.values.IsRHDOverride ? html`
            <button
              class="ds-reset-btn"
              @click="${restoreRhdAutoDetection}">Auto</button>
          ` : ""}
        </div>
      `
    } else {
      rowControl = html`
        <input
          type="checkbox"
          class="ds-toggle"
          id="ds-${p.key}"
          disabled="${() => isLocked()}"
          @change="${() => updateParam(p.key, "checkbox")}" />
      `
    }
  }

  return html`
    <div class="ds-row ${isNumeric ? "ds-row-numeric" : ""} ${isText ? "ds-row-text-input" : ""} ${isChild}">
      <div class="ds-row-info">
        <div class="ds-row-text">
          <div class="ds-row-heading">
            <span class="ds-row-label">${p.label}</span>
            ${flmParamStatus ? html`<span class="ds-flm-badge">Currently overridden by FLM</span>` : ""}
          </div>
          ${p.description_steps
            ? html`<div class="ds-row-desc">${() => getSliderDescription(p, state.sliderPreviewValues[p.key] ?? state.values[p.key])}</div>`
            : (p.description ? html`<div class="ds-row-desc">${p.description}</div>` : "")}
          ${() => {
            const reason = lockReason()
            return reason ? html`<div class="ds-row-desc"><strong>Locked:</strong> ${reason}</div>` : ""
          }}
          ${flmParamStatus ? html`
            <div class="ds-flm-detail">
              Effective now: <strong>${formatFlmValue(p, flmParamStatus.effectiveValue)}</strong>.
              Revert restores: <strong>${formatFlmValue(p, flmParamStatus.previousValue)}</strong>.
              You can still edit this while the trial is active.
            </div>
          ` : ""}
          ${flmTrialSummary ? html`
            <div class="ds-flm-summary">
              <div><strong>FLM trial active:</strong> ${flmTrialSummary.title}</div>
              <div>
                ${flmTrialSummary.genericCount} advanced setting${flmTrialSummary.genericCount === 1 ? "" : "s"},
                ${flmTrialSummary.thresholdCount} friction curve${flmTrialSummary.thresholdCount === 1 ? "" : "s"}, and
                ${flmTrialSummary.vehicleKnobCount} vehicle-specific knob${flmTrialSummary.vehicleKnobCount === 1 ? "" : "s"} active.
              </div>
              <div>Revert from Lateral Tuning restores the exact settings saved before this trial.</div>
              <a class="ds-flm-link" href="/tuning">Open Lateral Tuning</a>
            </div>
          ` : ""}

          ${() => p.is_parent_toggle && isParamEnabledForChildren(p) ? html`
            <div class="ds-manage-btn" @click="${() => toggleManage(p.key)}">
              ${state.expanded[p.key] ? "Close" : "Manage"}
              <i class="bi bi-chevron-${state.expanded[p.key] ? "up" : "down"}"></i>
            </div>
          ` : ""}
        </div>
        ${(isNumeric || isColor) ? html`<span class="ds-row-value" id="ds-display-${p.key}">${() => {
            if (isColor) return formatColorDisplayValue(p)
            const currentValue = state.sliderPreviewValues[p.key] ?? state.values[p.key]
            const bounds = numericBounds(p)
            return currentValue !== undefined ? formatSliderValue(currentValue, String(bounds.step), p.precision, p.key) : ".."
          }}</span>` : ""}
      </div>

      ${rowControl}
    </div>
  `
}

function hasChildParams(paramsList, key) {
  return paramsList.some(param => param.parent_key === key)
}

function renderSettingTree(paramsList, parentKey = null) {
  const directChildren = paramsList.filter(param => (param.parent_key || null) === parentKey)
  const rendered = []

  for (const param of directChildren) {
    const row = renderSettingRow(param)
    if (row) rendered.push(row)

    if (!hasChildParams(paramsList, param.key)) continue
    if (!isParamEnabledForChildren(param) || !state.expanded[param.key]) continue

    rendered.push(...renderSettingTree(paramsList, param.key))
  }

  return rendered
}

// Resolve the active section slug imperatively — NEVER inside a reactive expression
function resolveActiveSectionSlug(params) {
  if (state.layout.length === 0) return

  const sections = getSectionsWithSlug()
  const validSlugs = new Set(sections.map(s => s.slug))
  const requestedSlug = String(params?.section || "").toLowerCase()
  const fallbackSlug = sections[0].slug
  const nextSlug = validSlugs.has(requestedSlug)
    ? requestedSlug
    : (validSlugs.has(state.activeSectionSlug) ? state.activeSectionSlug : fallbackSlug)

  if (state.activeSectionSlug !== nextSlug) {
    state.activeSectionSlug = nextSlug
  }
}

export function DeviceSettings({ params }) {
  lastParams = params

  fetchFlmWorkspace()
  ensureFavoriteValuePolling()

  if (!state.fetched) {
    state.fetched = true
    fetchLayoutAndParams()
  }

  // Resolve slug imperatively (safe: runs in function body, not reactive context)
  resolveActiveSectionSlug(params)

  return html`
    <div class="ds-wrapper">
      <h2>Toggles</h2>

      <div class="ds-search-row">
        <input
          class="ds-search"
          type="text"
          placeholder="Search settings..."
          value="${() => state.filter}"
          @keydown="${(e) => {
            if (e.key === "Escape") clearSearchFilter()
          }}"
          @input="${updateSearchFilter}"
          @change="${updateSearchFilter}" />
        ${() => state.filter ? html`
          <button
            class="ds-search-clear"
            @click="${() => clearSearchFilter()}">
            Clear
          </button>
        ` : ""}
      </div>

      ${() => {
      if (state.loadingLayout || state.loadingValues) {
        return html`<div class="ds-loading">Loading configuration...</div>`
      }

      const sections = getSectionsWithSlug()
      if (sections.length === 0) {
        return html`<div class="ds-empty">No settings available.</div>`
      }

      // Sync DOM inputs after ArrowJS renders (safe: syncScheduled is non-reactive)
      scheduleSyncInputs()

      // Search active → show matching results from ALL sections
      if (state.filter) {
        const MAX_PER_SECTION = 25
        const searchResults = sections
          .map(s => ({ ...s, matches: s.params.filter(p => matchesFilter(p)) }))
          .filter(s => s.matches.length > 0)

        const totalMatches = searchResults.reduce((n, s) => n + s.matches.length, 0)

        return html`
          <div class="ds-status-bar">
            <span>${totalMatches} result${totalMatches !== 1 ? "s" : ""} across ${searchResults.length} section${searchResults.length !== 1 ? "s" : ""}</span>
            <span>${state.allKeys.length} total mapped</span>
          </div>

          ${searchResults.map(section => html`
            <div class="ds-section">
              <div class="ds-section-header ds-static-header">
                <i class="bi ${section.icon}"></i>
                <span class="ds-section-title">${section.name} (${section.matches.length})</span>
              </div>
              <div class="ds-section-body">
                ${section.matches.slice(0, MAX_PER_SECTION).map(p => renderSettingRow(p))}
                ${section.matches.length > MAX_PER_SECTION ? html`<div class="ds-row"><span class="ds-row-label" style="opacity:0.5">+${section.matches.length - MAX_PER_SECTION} more — refine your search</span></div>` : ""}
              </div>
            </div>
          `)}

          ${totalMatches === 0 ? html`<div class="ds-empty">No settings match your search.</div>` : ""}
        `
      }

      // No search → normal tab-based single-section view
      const activeSection = sections.find(s => s.slug === state.activeSectionSlug) || sections[0]
      const visibleParams = activeSection.params.filter(p => matchesFilter(p))

      return html`
          <div class="ds-tabs" id="ds-tabs">
            ${sections.map(section => html`
              <button
                class="ds-tab ${section.slug === state.activeSectionSlug ? "active" : ""}"
                @click="${(e) => {
          handleSectionTabClick(section.slug, e)
        }}">
                <i class="bi ${section.icon}"></i>
                <span>${section.name}</span>
              </button>
            `)}
          </div>

          <div class="ds-status-bar">
            <span>${activeSection.params.length} settings in ${activeSection.name}</span>
            <span>${state.allKeys.length} total mapped</span>
          </div>

          <div class="ds-section">
            <div class="ds-section-header ds-static-header">
              <i class="bi ${activeSection.icon}"></i>
              <span class="ds-section-title">${activeSection.name} (${visibleParams.length})</span>
            </div>
            <div class="ds-section-body">
              ${renderSettingTree(visibleParams)}
            </div>
          </div>

          ${visibleParams.length === 0 ? html`<div class="ds-empty">No settings match your search.</div>` : ""}
        `
    }}
    </div>
  `
}
