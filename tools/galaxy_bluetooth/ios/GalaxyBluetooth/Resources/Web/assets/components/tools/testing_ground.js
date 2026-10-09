import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  error: "",
  busy: false,
  data: null,
  selectedSlot: "",
})

let initialized = false

function getApiUrl(path) {
  const normalizedPath = String(path || "").replace(/^\/+/, "")
  const currentUrl = new URL(window.location.href)
  currentUrl.hash = ""
  currentUrl.search = ""
  currentUrl.pathname = currentUrl.pathname.replace(/\/+$/, "") || "/"
  return new URL(normalizedPath, currentUrl).toString()
}

async function parseApiPayload(response, fallbackMessage) {
  const contentType = String(response.headers.get("content-type") || "").toLowerCase()

  if (contentType.includes("application/json")) {
    const payload = await response.json()
    return {
      payload,
      message: payload?.error || payload?.message || fallbackMessage,
    }
  }

  const text = (await response.text()).trim()
  const cleaned = text.replace(/\s+/g, " ").slice(0, 200)
  return {
    payload: null,
    message: cleaned || fallbackMessage,
  }
}

function slotId(slot) {
  return String(slot?.id || "").trim()
}

function isUnusedSlot(slot) {
  const name = String(slot?.name || "").trim().toLowerCase()
  return name === "unused" || name.startsWith("unused ")
}

function getSelectableSlots() {
  const selectable = Array.isArray(state.data?.selectableSlots) ? state.data.selectableSlots : []
  if (selectable.length) return selectable

  const slots = Array.isArray(state.data?.slots) ? state.data.slots : []
  return slots.filter((slot) => !isUnusedSlot(slot))
}

function getVisibleSlotLines() {
  return getSelectableSlots().map((slot) => `${slot.id}. ${slot.name}`)
}

function getSelectedSlot() {
  const slots = Array.isArray(state.data?.slots) ? state.data.slots : []
  const selectedId = String(state.selectedSlot || "").trim()
  if (!selectedId) return null
  return slots.find((slot) => slotId(slot) === selectedId) || null
}

function getActiveSlot() {
  const slots = Array.isArray(state.data?.slots) ? state.data.slots : []
  const activeId = String(state.data?.activeSlot || "").trim()
  if (!activeId) return null
  return slots.find((slot) => slotId(slot) === activeId) || null
}

function getVariantLabels(slot) {
  if (!slot || typeof slot !== "object") {
    return { A: "A" }
  }

  const labels = {}
  const rawVariantLabels = slot.variantLabels
  if (rawVariantLabels && typeof rawVariantLabels === "object") {
    Object.entries(rawVariantLabels).forEach(([rawMode, rawLabel]) => {
      const mode = String(rawMode || "").trim().toUpperCase()
      const label = String(rawLabel || "").trim()
      if (mode.length === 1 && /^[A-Z]$/.test(mode) && label) {
        labels[mode] = label
      }
    })
  }

  const aLabel = String(slot.aLabel || "").trim()
  const bLabel = String(slot.bLabel || "").trim()
  if (aLabel) labels.A = labels.A || aLabel
  if (bLabel) labels.B = labels.B || bLabel
  if (!labels.A) labels.A = "A"

  return Object.keys(labels).sort().reduce((acc, key) => {
    acc[key] = labels[key]
    return acc
  }, {})
}

function getVariantModes(slot) {
  return Object.keys(getVariantLabels(slot))
}

function getDefaultMode(slot) {
  const modes = getVariantModes(slot)
  if (modes.includes("A")) return "A"
  return modes[0] || "A"
}

function toModeLabel(slot, mode) {
  const labels = getVariantLabels(slot)
  return labels[String(mode || "").trim().toUpperCase()] || String(mode || "").trim().toUpperCase() || "A"
}

function isModeActive(mode) {
  const normalizedMode = String(mode || "").trim().toUpperCase()
  return String(state.data?.activeSlot || "").trim() === String(state.selectedSlot || "").trim() && String(state.data?.activeVariant || "").trim().toUpperCase() === normalizedMode
}

function getSelectedMode() {
  const selectedSlot = getSelectedSlot()
  if (!selectedSlot) return "Not active"
  if (String(state.data?.activeSlot || "").trim() === String(state.selectedSlot || "").trim()) {
    const activeMode = String(state.data?.activeVariant || "").trim().toUpperCase() || getDefaultMode(selectedSlot)
    return String(state.data?.activeVariantLabel || "").trim() || toModeLabel(selectedSlot, activeMode)
  }
  return "Not active"
}

function modeButtonClass(mode) {
  const normalizedMode = String(mode || "").trim().toUpperCase()
  return [
    "testingGroundModeButton",
    `testingGroundModeButton${normalizedMode}`,
    isModeActive(normalizedMode) ? "active" : "",
  ].filter(Boolean).join(" ")
}

async function fetchTestingGrounds() {
  try {
    const response = await fetch(getApiUrl("api/testing_grounds"))
    const { payload, message } = await parseApiPayload(response, "Failed to load testing grounds")
    if (!response.ok) {
      throw new Error(message || response.statusText || "Failed to load testing grounds")
    }
    if (!payload || typeof payload !== "object") {
      throw new Error(message || "Failed to load testing grounds")
    }

    state.data = payload
    state.error = ""

    const selectable = Array.isArray(payload.selectableSlots) ? payload.selectableSlots : []
    const hasCurrentSelection = selectable.some((slot) => slotId(slot) === String(state.selectedSlot || "").trim())
    if (!hasCurrentSelection) {
      const activeSlot = String(payload.activeSlot || "").trim()
      const activeSelectable = selectable.some((slot) => slotId(slot) === activeSlot)
      state.selectedSlot = activeSelectable ? activeSlot : slotId(selectable[0] || {})
    }

  } catch (error) {
    const message = error?.message || "Failed to load testing grounds"
    state.error = message
  }
}

async function applySelection(slotValue, mode, showToast = true) {
  const normalizedSlot = String(slotValue || "").trim()
  const normalizedMode = String(mode || "").trim().toUpperCase()
  if (!normalizedSlot || !normalizedMode) return false

  state.busy = true
  try {
    const response = await fetch(getApiUrl("api/testing_grounds/select"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slotId: normalizedSlot, variant: normalizedMode }),
    })
    const { payload, message } = await parseApiPayload(response, "Failed to update testing ground mode")
    if (!response.ok) {
      throw new Error(message || response.statusText || "Failed to update testing ground mode")
    }
    if (!payload || typeof payload !== "object") {
      throw new Error(message || "Failed to update testing ground mode")
    }

    state.data = payload
    state.error = ""
    state.selectedSlot = normalizedSlot
    if (showToast) {
      const selectedSlot = Array.isArray(payload.slots)
        ? payload.slots.find((slot) => slotId(slot) === normalizedSlot)
        : null
      const selectedLabel = String(payload.activeVariantLabel || "").trim() || toModeLabel(selectedSlot, normalizedMode)
      showSnackbar(payload.message || `Testing Ground ${normalizedSlot} set to ${selectedLabel}.`)
    }
    return true
  } catch (error) {
    const message = error?.message || "Failed to update testing ground mode"
    state.error = message
    if (showToast) {
      showSnackbar(message, "error")
    }
    return false
  } finally {
    state.busy = false
  }
}

async function selectMode(mode) {
  if (state.busy) return

  const slot = getSelectedSlot()
  const slotValue = slotId(slot)
  if (!slotValue) {
    showSnackbar("Select a testing ground first.", "error")
    return
  }

  await applySelection(slotValue, mode, true)
}

async function selectSlot(slotValue) {
  const normalizedSlot = String(slotValue || "").trim()
  if (!normalizedSlot || state.busy) return
  state.selectedSlot = normalizedSlot
}

function initialize() {
  if (initialized) return
  initialized = true

  fetchTestingGrounds().finally(() => {
    state.loading = false
  })
}

export function TestingGround() {
  initialize()

  return html`
    <div class="testingGroundPage">
      <h2>Testing Ground</h2>
      ${() => state.loading ? html`<div class="testingGroundCard">Loading testing ground state...</div>` : ""}
      ${() => !state.loading ? html`
        <div class="testingGroundCard">
          <p class="testingGroundIntro">
            A/B Tuning Sandbox. If you don't know what this is, you probably shouldn't be here ;)
          </p>

          <div class="testingGroundTopList">
            <strong>Current Test Slots</strong>
            <ol>
              ${getVisibleSlotLines().map((line) => html`<li>${line}</li>`)}
            </ol>
          </div>

          <div class="testingGroundStatusGrid">
            <p><strong>Selected Slot:</strong> ${getSelectedSlot()?.name || "Unknown"}</p>
            <p><strong>Selected Mode:</strong> ${getSelectedMode()}</p>
            <p><strong>Onroad:</strong> ${state.data?.isOnroad ? "Yes" : "No"}</p>
            <p><strong>Selectable Slots:</strong> ${getSelectableSlots().length}</p>
          </div>

          <div class="testingGroundSelectionRow">
            <select
              class="testingGroundSelect"
              disabled="${() => state.busy || getSelectableSlots().length === 0 || false}"
              @change="${(event) => {
                selectSlot(String(event.target.value || ""))
              }}">
              ${() => getSelectableSlots().length
                ? getSelectableSlots().map((slot) => html`<option value="${slotId(slot)}" selected="${() => slotId(slot) === state.selectedSlot || false}">${slot.id}. ${slot.name}</option>`)
                : html`<option value="">No active test slots</option>`
              }
            </select>
          </div>

          <p class="testingGroundHint">
            Only one Testing Ground can be active at a time. Switching slots only changes what you're viewing, and the active test stays enabled until you explicitly choose another mode.
          </p>

          ${() => getSelectedSlot() ? html`
            <div class="testingGroundDetails">
              <h3>${getSelectedSlot().name}</h3>
              ${() => getSelectedSlot().description ? html`<p>${getSelectedSlot().description}</p>` : ""}
            </div>
          ` : ""}

          ${() => getSelectedSlot() ? html`
            <div class="testingGroundActionGrid">
              ${() => getVariantModes(getSelectedSlot()).map((mode) => html`
                <button
                  class="${modeButtonClass(mode)}"
                  disabled="${() => state.busy || false}"
                  @click="${() => selectMode(mode)}">
                  <span class="testingGroundModeLetter">${mode}</span>
                  <span class="testingGroundModeLabel">${toModeLabel(getSelectedSlot(), mode)}</span>
                </button>
              `)}
            </div>
          ` : ""}

          ${() => state.error ? html`<p class="testingGroundError"><strong>Error:</strong> ${state.error}</p>` : ""}

          ${() => getActiveSlot() ? html`
            <p class="testingGroundActiveSummary">
              Currently active: <strong>${getActiveSlot().id}. ${getActiveSlot().name}</strong> in mode <strong>${state.data?.activeVariantLabel || toModeLabel(getActiveSlot(), state.data?.activeVariant || "A")}</strong>.
            </p>
          ` : ""}
        </div>
      ` : ""}
    </div>
  `
}
