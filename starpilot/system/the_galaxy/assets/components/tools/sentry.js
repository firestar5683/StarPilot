import { html, reactive } from "/assets/vendor/arrow-core.js"
import { galaxyPath, isGalaxyTunnel } from "/assets/js/utils.js"
import {
  enableSentryPush,
  sendSentryTestNotification,
} from "/assets/components/sentry_notifications.js"

const state = reactive({
  loading: true,
  savingKey: "",
  params: {},
  status: {},
  event: {},
  history: [],
  historyVisible: false,
  historyBusy: false,
  liveCapture: {},
  testBusy: false,
  liveBusy: false,
  deleteBusy: false,
  pushBusy: false,
})

let pollTimer = null

async function fetchParams() {
  try {
    const response = await fetch(galaxyPath("/api/params/all"), { cache: "no-store" })
    if (response.ok) state.params = await response.json()
  } catch (error) {
    console.error("Failed to fetch Sentry settings:", error)
  } finally {
    state.loading = false
  }
}

async function fetchStatus() {
  try {
    const response = await fetch(galaxyPath("/api/sentry/status"), { cache: "no-store" })
    if (!response.ok) return
    const payload = await response.json()
    state.status = payload.status || {}
    state.event = payload.lastEvent || {}
    if (state.historyVisible && !state.historyBusy) fetchHistory()
  } catch (error) {
    console.error("Failed to fetch Sentry status:", error)
  }
}

async function fetchHistory() {
  state.historyBusy = true
  try {
    const response = await fetch(galaxyPath("/api/sentry/events"), { cache: "no-store" })
    const payload = await readJsonResponse(response)
    if (!response.ok) {
      showSnackbar(payload.error || "Failed to load Sentry history.")
      return
    }
    state.history = Array.isArray(payload.events) ? payload.events : []
  } catch (error) {
    showSnackbar(error.message || "Failed to load Sentry history.")
  } finally {
    state.historyBusy = false
  }
}

function startPolling() {
  if (pollTimer !== null) return
  fetchParams()
  fetchStatus()
  pollTimer = window.setInterval(fetchStatus, 5000)
}

async function toggleHistory() {
  state.historyVisible = !state.historyVisible
  if (state.historyVisible) await fetchHistory()
}

function numericParam(key, fallback) {
  const value = Number(state.params[key])
  return Number.isFinite(value) ? value : fallback
}

async function saveParam(key, value) {
  state.savingKey = key
  try {
    const response = await fetch(galaxyPath("/api/params"), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value }),
    })
    const payload = await response.json()
    if (!response.ok) {
      showSnackbar(payload.error || `Failed to update ${key}.`)
      return
    }
    state.params = { ...state.params, ...(payload.updated || {}), [key]: value }
    showSnackbar(payload.message || "Sentry setting saved.")
  } catch (error) {
    showSnackbar("Network error — is the device reachable?")
  } finally {
    state.savingKey = ""
  }
}

async function sendTestEvent() {
  if (state.testBusy) return
  state.testBusy = true
  try {
    const response = await fetch(galaxyPath("/api/sentry/test"), { method: "POST" })
    const payload = await readJsonResponse(response)
    if (!response.ok) {
      showSnackbar(payload.error || "Sentry test failed.")
      return
    }
    showSnackbar("Test capture started. The images will appear here shortly.")
  } catch (error) {
    showSnackbar(error.message || "Network error — is the device reachable?")
  } finally {
    state.testBusy = false
  }
}

async function readJsonResponse(response) {
  const body = await response.text()
  if (!body) return {}

  try {
    return JSON.parse(body)
  } catch {
    const contentType = response.headers?.get("content-type") || ""
    if (contentType.includes("text/html") || body.trim().startsWith("<")) {
      if (response.status === 200) {
        throw new Error("Galaxy returned an HTML page instead of JSON data. Check your session or connection.")
      }
      throw new Error(`Galaxy returned an HTML error page (${response.status}). Check the device connection or Galaxy tunnel.`)
    }
    throw new Error(`Galaxy returned an unexpected ${response.status} response. Check the device connection or Galaxy tunnel.`)
  }
}

async function viewLive() {
  if (state.liveBusy) return
  state.liveBusy = true
  try {
    const response = await fetch(galaxyPath("/api/sentry/live"), { cache: "no-store" })
    const payload = await readJsonResponse(response)
    if (!response.ok) {
      showSnackbar(payload.error || "Live camera capture failed.")
      return
    }
    state.liveCapture = payload
    showSnackbar("Live camera snapshot captured.")
  } catch (error) {
    showSnackbar(error.message || "Network error — is the device reachable?")
  } finally {
    state.liveBusy = false
  }
}

async function enablePush() {
  if (state.pushBusy) return
  state.pushBusy = true
  try {
    const result = await enableSentryPush()
    showSnackbar(result.message)
  } catch (error) {
    showSnackbar(error.message || "Could not enable browser notifications.")
  } finally {
    state.pushBusy = false
  }
}

async function sendTestNotification() {
  if (state.pushBusy) return
  state.pushBusy = true
  try {
    const payload = await sendSentryTestNotification()
    const channels = Object.entries(payload.channels || {})
      .filter(([, configured]) => configured)
      .map(([channel]) => channel === "webPush" ? "browser" : channel)
    showSnackbar(`Test notification sent through ${channels.join(", ")}.`)
  } catch (error) {
    showSnackbar(error.message || "Could not send the test notification.")
  } finally {
    state.pushBusy = false
  }
}

async function deleteEvent(eventId) {
  eventId = String(eventId || "")
  if (!eventId || state.deleteBusy) return
  if (!window.confirm("Delete this Sentry event and its camera images? This cannot be undone.")) return

  state.deleteBusy = true
  try {
    const response = await fetch(galaxyPath(`/api/sentry/events/${encodeURIComponent(eventId)}`), {
      method: "DELETE",
    })
    const payload = await readJsonResponse(response)
    if (!response.ok) {
      showSnackbar(payload.error || "Sentry event deletion failed.")
      return
    }
    state.history = state.history.filter((event) => String(event.eventId || "") !== eventId)
    if (String(state.event?.eventId || "") === eventId) {
      state.event = {}
      await fetchStatus()
    }
    showSnackbar("Sentry event deleted.")
  } catch (error) {
    showSnackbar(error.message || "Network error — is the device reachable?")
  } finally {
    state.deleteBusy = false
  }
}

function renderEvent(event = state.event) {
  event = event || {}
  if (!event.eventId) return html`<p class="sentry-empty">No Sentry events recorded yet.</p>`

  return html`
    <div class="sentry-event-meta">
      <span class="sentry-event-kind">${String(event.kind || "event").toUpperCase()}</span>
      <span>${event.detectedAt || ""}</span>
    </div>
    <p class="sentry-event-message">${event.message || "Movement detected while parked."}</p>
    ${Array.isArray(event.imageUrls) && event.imageUrls.length > 0 ? html`
      <div class="sentry-image-grid">
        ${event.imageUrls.map((url, index) => html`
          <a href="${galaxyPath(url)}" target="_blank" rel="noopener">
            <img src="${galaxyPath(url)}" alt="Sentry capture ${index + 1}" loading="lazy" />
          </a>
        `)}
      </div>
    ` : event.kind === "power_off"
      ? html`<p class="sentry-empty">Power-off alerts do not include camera captures because the device is shutting down.</p>`
      : html`<p class="sentry-empty">No camera images were available for this event.</p>`}
  `
}

function renderHistory() {
  if (!state.historyVisible) return ""
  if (state.historyBusy) return html`<p class="sentry-loading">Loading Sentry history…</p>`
  if (state.history.length === 0) return html`<p class="sentry-empty">No retained Sentry events.</p>`

  return html`
    <div class="sentry-history-list">
      <p class="sentry-muted">${state.history.length} event${state.history.length === 1 ? "" : "s"} retained. Events stay here until you delete them.</p>
      ${state.history.map((event) => html`
        <article class="sentry-history-event">
          <div class="sentry-history-heading">
            <strong>${event.detectedAt || "Sentry event"}</strong>
            <button class="sentry-button sentry-button-danger" @click="${() => deleteEvent(event.eventId)}" disabled="${() => state.deleteBusy}">
              ${() => state.deleteBusy ? "Deleting…" : "Delete event"}
            </button>
          </div>
          ${renderEvent(event)}
        </article>
      `)}
    </div>
  `
}

function renderLiveCapture() {
  const capture = state.liveCapture || {}
  const imageUrls = Array.isArray(capture.imageUrls) ? capture.imageUrls : []
  if (imageUrls.length === 0) return html`<p class="sentry-empty">No live snapshot captured yet.</p>`

  const cacheKey = encodeURIComponent(capture.capturedAt || "")
  return html`
    <p class="sentry-muted">Captured ${capture.capturedAt || "just now"}.</p>
    <div class="sentry-image-grid">
      ${imageUrls.map((url, index) => html`
        <a href="${galaxyPath(`${url}?t=${cacheKey}`)}" target="_blank" rel="noopener">
          <img src="${galaxyPath(`${url}?t=${cacheKey}`)}" alt="Live Sentry camera ${index + 1}" />
        </a>
      `)}
    </div>
  `
}

export function SentryMode() {
  startPolling()
  const remote = isGalaxyTunnel()

  return html`
    <div class="sentry-page">
      <div class="sentry-page-header">
        <div>
          <h2>Sentry Mode</h2>
          <p>Monitor the parked vehicle and review movement captures directly in Galaxy.</p>
        </div>
        <span class="sentry-status-pill">${() => state.status.state || "unknown"}</span>
      </div>

      <section class="sentry-card">
        <h3>Configuration</h3>
        <p class="sentry-muted">Galaxy is the built-in notification and image viewer. Sentry detects accelerometer movement. Webhook and ntfy delivery are optional.</p>

        ${() => state.loading ? html`<div class="sentry-loading">Loading Sentry settings…</div>` : html`
          <label class="sentry-setting-row">
            <span>
              <strong>Enable Sentry Mode</strong>
              <small>Detect sustained movement while the vehicle is parked.</small>
            </span>
            <input
              type="checkbox"
              class="sentry-toggle"
              checked="${() => !!state.params.SentryModeEnabled}"
              disabled="${() => state.savingKey === "SentryModeEnabled"}"
              @change="${(event) => saveParam("SentryModeEnabled", !!event.currentTarget.checked)}" />
          </label>

          <label class="sentry-field">
            <span><strong>Webhook URL</strong><small>Optional Discord-compatible or custom webhook.</small></span>
            <input
              class="sentry-input"
              type="url"
              value="${() => state.params.SentryModeWebhook || ""}"
              placeholder="https://…"
              disabled="${() => state.savingKey === "SentryModeWebhook"}"
              @change="${(event) => saveParam("SentryModeWebhook", event.currentTarget.value.trim())}" />
          </label>

          <label class="sentry-field">
            <span><strong>ntfy URL</strong><small>Optional ntfy topic URL for phone notifications.</small></span>
            <input
              class="sentry-input"
              type="url"
              value="${() => state.params.SentryModeNtfyUrl || ""}"
              placeholder="https://ntfy.sh/…"
              disabled="${() => state.savingKey === "SentryModeNtfyUrl"}"
              @change="${(event) => saveParam("SentryModeNtfyUrl", event.currentTarget.value.trim())}" />
          </label>

          <label class="sentry-field sentry-range-field">
            <span><strong>Motion sensitivity</strong><small>Lower values detect smaller acceleration changes. Default: 0.04.</small></span>
            <div class="sentry-range-control">
              <input
                class="sentry-range"
                type="range"
                min="0.005"
                max="1"
                step="0.001"
                value="${() => numericParam("SentryModeSensitivity", 0.04)}"
                disabled="${() => state.savingKey === "SentryModeSensitivity"}"
                aria-label="Motion sensitivity"
                @change="${(event) => saveParam("SentryModeSensitivity", Number(event.currentTarget.value))}" />
              <input
                class="sentry-number-input"
                type="number"
                min="0.005"
                max="1"
                step="0.001"
                value="${() => numericParam("SentryModeSensitivity", 0.04)}"
                disabled="${() => state.savingKey === "SentryModeSensitivity"}"
                aria-label="Exact motion sensitivity"
                @change="${(event) => saveParam("SentryModeSensitivity", Number(event.currentTarget.value))}" />
            </div>
          </label>

          <label class="sentry-field sentry-range-field">
            <span><strong>Warning persistence</strong><small>How long movement must continue before the first alert. Default: 1 second.</small></span>
            <div class="sentry-range-control">
              <input
                class="sentry-range"
                type="range"
                min="0.1"
                max="10"
                step="0.1"
                value="${() => numericParam("SentryModeWarningTime", 1)}"
                disabled="${() => state.savingKey === "SentryModeWarningTime"}"
                aria-label="Warning persistence"
                @change="${(event) => saveParam("SentryModeWarningTime", Number(event.currentTarget.value))}" />
              <input
                class="sentry-number-input"
                type="number"
                min="0.1"
                max="10"
                step="0.1"
                value="${() => numericParam("SentryModeWarningTime", 1)}"
                disabled="${() => state.savingKey === "SentryModeWarningTime"}"
                aria-label="Exact warning persistence"
                @change="${(event) => saveParam("SentryModeWarningTime", Number(event.currentTarget.value))}" />
              <span class="sentry-range-unit">seconds</span>
            </div>
          </label>

          <div class="sentry-action-row">
            <button class="sentry-button" @click="${enablePush}" disabled="${() => state.pushBusy}">
              ${() => state.pushBusy ? "Enabling…" : "Enable browser notifications"}
            </button>
            <button class="sentry-button sentry-button-secondary" @click="${sendTestNotification}" disabled="${() => state.pushBusy}">
              ${() => state.pushBusy ? "Sending…" : "Send test notification"}
            </button>
          </div>
          <p class="sentry-muted">The test notification uses every configured channel: browser Web Push, ntfy, and webhook.</p>
          <p class="sentry-muted">iPhone users: add Galaxy to your Home Screen as a web app before enabling notifications. iOS web push requires the Home Screen web app.</p>
        `}
      </section>

      <section class="sentry-card">
        <div class="sentry-card-heading">
          <div>
            <h3>Live view</h3>
            <p class="sentry-muted">Capture one still from both cameras while parked.</p>
          </div>
          <button class="sentry-button sentry-button-secondary" @click="${viewLive}" disabled="${() => state.liveBusy}">
            ${() => state.liveBusy ? "Capturing…" : "View live"}
          </button>
        </div>
        ${() => renderLiveCapture()}
      </section>

      <section class="sentry-card">
        <div class="sentry-card-heading">
          <div>
            <h3>Latest Event</h3>
            <p class="sentry-muted">Events refresh automatically every five seconds.</p>
          </div>
          <div class="sentry-action-row">
            <button class="sentry-button sentry-button-secondary" @click="${toggleHistory}" disabled="${() => state.historyBusy}">
              ${() => state.historyBusy ? "Loading…" : state.historyVisible ? "Hide history" : "View history"}
            </button>
            ${remote ? "" : html`
              <button class="sentry-button sentry-button-secondary" @click="${sendTestEvent}" disabled="${() => state.testBusy}">
                ${() => state.testBusy ? "Capturing…" : "Send test capture"}
              </button>
            `}
            ${() => state.event?.eventId ? html`
              <button class="sentry-button sentry-button-danger" @click="${() => deleteEvent(state.event.eventId)}" disabled="${() => state.deleteBusy}">
                ${() => state.deleteBusy ? "Deleting…" : "Delete event"}
              </button>
            ` : ""}
          </div>
        </div>
        ${() => renderEvent()}
        ${() => renderHistory()}
      </section>
    </div>
  `
}
