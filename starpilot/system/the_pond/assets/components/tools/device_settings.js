import { html, reactive } from "/assets/vendor/arrow-core.js"

const endpointOptionsCache = {}
const endpointOptionsInflight = {}

// Plain variables — scheduling/routing flags that must NOT be reactive
let syncScheduled = false
let lastParams = null
const DYNAMIC_DEFAULT_DEP_KEYS = new Set(["AccelerationProfile", "EVTuning", "TruckTuning"])

// Module-level state (persists across route changes)
const state = reactive({
  layout: [],
  allKeys: [],
  paramMetaByKey: {},
  values: {},
  defaultValues: {},
  loadingLayout: true,
  loadingValues: true,
  filter: "",
  expanded: {},
  fetched: false,
  activeSectionSlug: "",
  numericUpdating: {},
})

function slugifySectionName(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

function getSectionsWithSlug() {
  return state.layout.map(section => ({
    ...section,
    slug: slugifySectionName(section.name),
  }))
}

function toSelectValue(value) {
  return value === null || value === undefined ? "" : String(value)
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
    const o = document.createElement("option")
    o.value = String(opt.value)
    o.textContent = opt.label
    el.appendChild(o)
  }
}

async function hydrateEndpointOptions(el, key, endpoint) {
  if (endpointOptionsCache[endpoint]) {
    applySelectOptions(el, endpointOptionsCache[endpoint])
    el.dataset.hydrated = "1"
    el.value = toSelectValue(state.values[key])
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
  el.value = toSelectValue(state.values[key])
}

function syncInputs() {
  // Sync checkboxes — set DOM property directly (attribute alone is unreliable)
  for (const el of document.querySelectorAll("input[type='checkbox'].ds-toggle[id^='ds-']")) {
    el.checked = !!state.values[el.id.slice(3)]
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
        el.value = toSelectValue(state.values[key])
      }
      continue
    }

    if (Array.isArray(inlineOptions) && inlineOptions.length > 0) {
      if (!el.dataset.hydrated) {
        applySelectOptions(el, inlineOptions)
        el.dataset.hydrated = "1"
      }
      el.value = toSelectValue(state.values[key])
    }
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

async function refreshParamsAndDefaults() {
  await fetchDefaultValues()

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
    const layoutRes = await fetch("/assets/components/tools/device_settings_layout.json")
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
    if (!(await fetchDefaultValues())) {
      state.defaultValues = {}
    }

    const valuesRes = await fetch("/api/params/all")
    const data = await valuesRes.json()
    state.values = data
  } catch (e) {
    console.error("Failed to fetch param values:", e)
    state.defaultValues = {}
  }
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
  const current = state.values[key]
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

async function updateParam(key, elType) {
  const current = state.values[key]
  const el = document.getElementById(`ds-${key}`)
  if (!el) return

  const param = state.paramMetaByKey[key] || {}

  let formattedVal
  if (elType === "checkbox") {
    formattedVal = !!el.checked
  } else if (elType === "dropdown") {
    formattedVal = coerceValueByType(el.value, param.data_type)
  } else {
    formattedVal = coerceValueByType(el.value, param.data_type)
  }

  try {
    const res = await fetch("/api/params", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value: formattedVal }),
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

  el.value = current
}

function toggleManage(key) {
  state.expanded = { ...state.expanded, [key]: !state.expanded[key] }
  scheduleSyncInputs()
}

function matchesFilter(p) {
  if (!state.filter) return true
  const q = state.filter.toLowerCase()
  return p.label.toLowerCase().includes(q) || p.key.toLowerCase().includes(q)
}

function clearSearchFilter() {
  if (!state.filter) return
  state.filter = ""
  scheduleSyncInputs()
}

function getSettingLockReason(param) {
  if (param?.key === "LKASButtonControl" && !!state.values.RemapCancelToDistance) {
    return "Cancel remap requires the LKAS button to stay on No Action."
  }
  return ""
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

function renderSettingRow(p) {
  if (p.parent_key && !state.filter) {
    if (!state.values[p.parent_key]) return ""
    if (!state.expanded[p.parent_key]) return ""
  }

  const isNumeric = p.ui_type === "numeric"
  const isChild = p.parent_key ? "ds-child-modifier" : ""
  const lockReason = getSettingLockReason(p)
  const isLocked = lockReason !== ""

  return html`
    <div class="ds-row ${isNumeric ? "ds-row-numeric" : ""} ${isChild}">
      <div class="ds-row-info">
        <div class="ds-row-text">
          <span class="ds-row-label">${p.label}</span>
          ${p.description ? html`<div class="ds-row-desc">${p.description}</div>` : ""}
          ${lockReason ? html`<div class="ds-row-desc"><strong>Locked:</strong> ${lockReason}</div>` : ""}

          ${() => p.is_parent_toggle && state.values[p.key] ? html`
            <div class="ds-manage-btn" @click="${() => toggleManage(p.key)}">
              ${state.expanded[p.key] ? "Close" : "Manage"}
              <i class="bi bi-chevron-${state.expanded[p.key] ? "up" : "down"}"></i>
            </div>
          ` : ""}
        </div>
        ${isNumeric ? html`<span class="ds-row-value" id="ds-display-${p.key}">${() => {
            const currentValue = state.values[p.key]
            const bounds = numericBounds(p)
            return currentValue !== undefined ? formatSliderValue(currentValue, String(bounds.step), p.precision, p.key) : ".."
          }}</span>` : ""}
      </div>

      ${isNumeric ? html`
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
        const stepLabel = formatStepValue(bounds.step, precision)
        return html`
              <div class="ds-stepper">
                <button
                  class="ds-stepper-btn"
                  disabled="${() => !canDecrease || false}"
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
                      ?disabled="${updating}"
                      value="${() => formatNumericForInput(resolveCurrentNumericValue(p, numericBounds(p)), precision)}"
                      @keydown="${(e) => {
                        if (e.key !== "Enter") return
                        e.preventDefault()
                        applyManualNumericParam(p)
                      }}" />
                    <button
                      class="ds-apply-btn"
                      ?disabled="${updating}"
                      @click="${() => applyManualNumericParam(p)}">Apply</button>
                  </div>
                  <button
                    class="ds-reset-btn"
                    disabled="${() => !canReset || false}"
                    @click="${() => resetNumericParam(p)}">Reset to Default</button>
                </div>
                <button
                  class="ds-stepper-btn"
                  disabled="${() => !canIncrease || false}"
                  @click="${() => stepNumericParam(p, 1)}">+</button>              </div>
            `
      })()}
        </div>
      ` : p.ui_type === "dropdown" ? html`
        <select
          class="ds-select"
          id="ds-${p.key}"
          data-endpoint="${p.options_endpoint || ""}"
          ?disabled="${isLocked}"
          @change="${() => updateParam(p.key, "dropdown")}">
          <option value="">Loading...</option>
        </select>
      ` : html`
        <input
          type="checkbox"
          class="ds-toggle"
          id="ds-${p.key}"
          @change="${() => updateParam(p.key, "checkbox")}" />
      `}
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
    if (!state.values[param.key] || !state.expanded[param.key]) continue

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
          @input="${(e) => {
            state.filter = e.target.value
            scheduleSyncInputs()
          }}" />
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
