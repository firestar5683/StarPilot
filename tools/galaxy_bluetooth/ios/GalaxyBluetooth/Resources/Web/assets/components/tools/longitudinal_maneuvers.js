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

function isLongitudinalManeuversRouteActive() {
  return window.location.pathname === "/longitudinal_maneuvers"
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
  normalized.support = normalized.support && typeof normalized.support === "object" ? normalized.support : {}
  normalized.caveats = Array.isArray(normalized.caveats) ? normalized.caveats : []
  normalized.skippedManeuvers = Array.isArray(normalized.skippedManeuvers) ? normalized.skippedManeuvers : []
  normalized.history = Array.isArray(normalized.history) ? normalized.history : []
  return normalized
}

function getSupportValue(key) {
  const data = state.data && typeof state.data === "object" ? state.data : {}
  const support = data.support && typeof data.support === "object" ? data.support : {}
  return support[key]
}

function formatSupportBool(key) {
  return getSupportValue(key) ? "Yes" : "No"
}

function formatSupportNumber(key, unit) {
  const value = Number(getSupportValue(key))
  return Number.isFinite(value) ? `${value.toFixed(2)} ${unit}` : "n/a"
}

async function fetchStatus() {
  try {
    const response = await fetch("/api/longitudinal_maneuvers/status")
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
    if (!isLongitudinalManeuversRouteActive()) {
      pollHandle = null
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
    const response = await fetch(`/api/longitudinal_maneuvers/${action}`, { method: "POST" })
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

export function LongitudinalManeuvers() {
  initialize()

  return html`
    <div class="longManeuverPage">
      <h2>Long Maneuvers</h2>

      <div class="longManeuverCard">
        <p class="longManeuverIntro">
          Run the longitudinal maneuver suite from your phone and monitor progress live.
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
            @click="${() => runAction("stop")}">            Stop
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
            ${statusLine("Paddle Mode", state.data.paddleMode || "auto")}
            ${statusLine("Step", `${safeNumber(state.data.stepIndex, 0)}/${safeNumber(state.data.stepTotal, 0)}`)}
            ${statusLine("Run", `${safeNumber(state.data.runIndex, 0)}/${safeNumber(state.data.runTotal, 0)}`)}
            ${statusLine("Updated", formatAgeSeconds(state.data.updatedAgeSec))}
          </div>

          <div class="longManeuverCurrent">
            <p><strong>Current Maneuver:</strong> ${state.data.maneuver || "n/a"}</p>
            <p><strong>Popup Text:</strong> ${state.data.uiText1 || ""} ${state.data.uiText2 ? `| ${state.data.uiText2}` : ""}</p>
          </div>

          <div class="longManeuverStatusGrid">
            ${statusLine("openpilot Long", formatSupportBool("openpilotLongitudinalControl"))}
            ${statusLine("Full Stop + Go", formatSupportBool("fullStopAndGo"))}
            ${statusLine("Auto Resume", formatSupportBool("autoResumeFromStop"))}
            ${statusLine("Resume Assist", formatSupportBool("requiresResumeAssist"))}
            ${statusLine("Expected Zero", formatSupportBool("expectedToReachZero"))}
            ${statusLine("Min Enable", formatSupportNumber("minEnableSpeed", "m/s"))}
            ${statusLine("Stop Accel", formatSupportNumber("stopAccel", "m/s^2"))}
          </div>

          ${(state.data.caveats || []).length ? html`
            <div class="longManeuverInstructions">
              <h3>Platform Caveats</h3>
              <ul>
                ${(state.data.caveats || []).map((line) => html`<li>${line}</li>`)}
              </ul>
            </div>
          ` : ""}

          ${(state.data.skippedManeuvers || []).length ? html`
            <div class="longManeuverInstructions">
              <h3>Expected Skips</h3>
              <ul>
                ${(state.data.skippedManeuvers || []).map((line) => html`<li>${line}</li>`)}
              </ul>
            </div>
          ` : ""}

          <div class="longManeuverInstructions">
            <h3>Quick Guide</h3>
            <ol>
              <li>Find a large, empty, straight road or lot with no traffic.</li>
              <li>Press <strong>Start / Arm</strong> here, then engage openpilot with SET.</li>
              <li>Keep full supervision and be ready to disengage at all times.</li>
              <li>Review the platform caveats before starting. Low-speed maneuvers can be skipped automatically on cars that do not fully stop.</li>
              <li>When the status says complete, collect logs and generate your HTML report.</li>
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
