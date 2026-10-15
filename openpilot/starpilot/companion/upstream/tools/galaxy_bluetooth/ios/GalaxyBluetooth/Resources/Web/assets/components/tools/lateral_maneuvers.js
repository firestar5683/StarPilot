import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  busy: false,
  error: "",
  data: null,
})

let initialized = false
let pollHandle = null
const POLL_INTERVAL_MS = 3000

function isLateralManeuversRouteActive() {
  return window.location.pathname === "/lateral_maneuvers"
}

function safeNumber(value, fallback = 0) {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function formatAgeSeconds(value) {
  const sec = safeNumber(value, -1)
  if (sec < 0) return "unknown"
  if (sec < 1) return "just now"
  if (sec < 60) return `${Math.round(sec)}s ago`
  const min = sec / 60
  if (min < 60) return `${Math.round(min)}m ago`
  const hr = min / 60
  return `${Math.round(hr)}h ago`
}

function normalizeStatusPayload(payload) {
  const normalized = payload && typeof payload === "object" ? { ...payload } : {}
  normalized.history = Array.isArray(normalized.history) ? normalized.history : []
  return normalized
}

async function fetchStatus() {
  try {
    const response = await fetch("/api/lateral_maneuvers/status")
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Failed to load maneuver status")
    }

    state.data = normalizeStatusPayload(payload)
    state.error = ""
  } catch (error) {
    state.error = error?.message || "Failed to load maneuver status"
  } finally {
    state.loading = false
  }
}

function stopPolling() {
  if (!pollHandle) return
  clearTimeout(pollHandle)
  pollHandle = null
}

function ensurePolling() {
  if (pollHandle) return

  const poll = async () => {
    if (!isLateralManeuversRouteActive()) {
      stopPolling()
      return
    }

    if (document.visibilityState !== "visible") {
      pollHandle = setTimeout(poll, POLL_INTERVAL_MS)
      return
    }

    await fetchStatus()
    pollHandle = setTimeout(poll, POLL_INTERVAL_MS)
  }

  pollHandle = setTimeout(poll, POLL_INTERVAL_MS)
}

async function runAction(action) {
  if (state.busy) return
  state.busy = true

  try {
    const response = await fetch(`/api/lateral_maneuvers/${action}`, { method: "POST" })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || `Failed to ${action} maneuvers`)
    }

    state.data = normalizeStatusPayload(payload)
    state.error = ""
    showSnackbar(payload.message || "Action complete.")
  } catch (error) {
    const message = error?.message || `Failed to ${action} maneuvers`
    state.error = message
    showSnackbar(message, "error")
  } finally {
    state.busy = false
  }
}

function initialize() {
  if (initialized) return
  initialized = true
  fetchStatus()
  ensurePolling()
}

function statusLine(label, value) {
  return html`<p><strong>${label}:</strong> ${value}</p>`
}

export function LateralManeuvers() {
  initialize()

  return html`
    <div class="longManeuverPage">
      <h2>Lateral Maneuvers</h2>

      <div class="longManeuverCard">
        <p class="longManeuverIntro">
          Arm the lateral maneuver suite from your phone and monitor progress live.
        </p>

        <div class="longManeuverActions">
          <button
            class="longManeuverButton"
            disabled="${() => state.busy || false}"
            @click="${() => runAction("start")}">
            Start / Arm
          </button>
          <button
            class="longManeuverButton danger"
            disabled="${() => state.busy || false}"
            @click="${() => runAction("stop")}">
            Stop
          </button>
        </div>

        ${() => state.loading ? html`<p class="longManeuverMuted">Loading status...</p>` : ""}
        ${() => state.error ? html`<p class="longManeuverError">${state.error}</p>` : ""}

        ${() => state.data ? html`
          <div class="longManeuverStatusGrid">
            ${statusLine("Mode Enabled", state.data.modeEnabled ? "Yes" : "No")}
            ${statusLine("State", state.data.state || "idle")}
            ${statusLine("Onroad", state.data.isOnroad ? "Yes" : "No")}
            ${statusLine("Engaged", state.data.isEngaged ? "Yes" : "No")}
            ${statusLine("Phase", state.data.phase || "n/a")}
            ${statusLine("Step", `${safeNumber(state.data.stepIndex, 0)}/${safeNumber(state.data.stepTotal, 0)}`)}
            ${statusLine("Run", `${safeNumber(state.data.runIndex, 0)}/${safeNumber(state.data.runTotal, 0)}`)}
            ${statusLine("Updated", formatAgeSeconds(state.data.updatedAgeSec))}
          </div>

          <div class="longManeuverCurrent">
            <p><strong>Current Maneuver:</strong> ${state.data.maneuver || "n/a"}</p>
            <p><strong>Popup Text:</strong> ${state.data.uiText1 || ""} ${state.data.uiText2 ? `| ${state.data.uiText2}` : ""}</p>
          </div>

          <div class="longManeuverInstructions">
            <h3>Quick Guide</h3>
            <ol>
              <li>Find a large, empty, straight, flat road or lot with no traffic.</li>
              <li>Press <strong>Start / Arm</strong> here, then engage openpilot and set the requested speed manually.</li>
              <li>Keep full supervision and be ready to steer or disengage immediately at all times.</li>
              <li>Do not touch the wheel during a run. Steering input or speed drift can reset the current maneuver.</li>
              <li>When the status says complete, collect logs and generate the HTML report if needed.</li>
            </ol>
          </div>

          <div class="longManeuverHistory">
            <h3>Progress Chain</h3>
            ${() => (state.data.history || []).length ? html`
              <ol>
                ${(state.data.history || []).slice().reverse().map((line) => html`<li>${line}</li>`)}
              </ol>
            ` : html`<p class="longManeuverMuted">No steps logged yet.</p>`}
          </div>
        ` : ""}
      </div>
    </div>
  `
}
