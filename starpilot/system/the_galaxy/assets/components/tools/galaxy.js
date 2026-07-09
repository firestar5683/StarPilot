import { html, reactive } from "/assets/vendor/arrow-core.js"
import { isGalaxyTunnel } from "/assets/js/utils.js"
import { Modal } from "/assets/components/modal.js"

const state = reactive({
  paired: false,
  url: "",
  iosConnectUrl: "",
  iosPairingCode: "",
  iosShortPairingCode: "",
  iosShortPairingUrl: "",
  iosPairingQRCodeUrl: "",
  portalURL: "",
  localBaseURL: "",
  cookieName: "galaxy_session",
  telemetryPath: "/api/galaxy/telemetry",
  vehicleTelemetryUrl: "",
  password: "",
  loading: true,
  submitting: false,
  showUnpairModal: false,
  fetched: false,
})

async function fetchStatus() {
  state.loading = true
  try {
    const res = await fetch("/api/galaxy/status")
    const data = await res.json()
    state.paired = data.paired
    state.url = data.url
    state.iosConnectUrl = data.iosConnectUrl || ""
    state.iosPairingCode = data.iosPairingCode || ""
    state.iosShortPairingCode = data.iosShortPairingCode || ""
    state.iosShortPairingUrl = data.iosShortPairingUrl || ""
    state.iosPairingQRCodeUrl = data.iosPairingQRCodeUrl || ""
    state.portalURL = data.portalURL || data.url || ""
    state.localBaseURL = data.localBaseURL || ""
    state.cookieName = data.cookieName || "galaxy_session"
    state.telemetryPath = data.telemetryPath || "/api/galaxy/telemetry"
    state.vehicleTelemetryUrl = data.vehicleTelemetryUrl || ""
  } catch (e) {
    console.error("Failed to fetch Galaxy status:", e)
  }
  state.loading = false
}

async function pair() {
  if (state.submitting) return
  const pw = state.password.trim()
  if (pw.length < 6) {
    showSnackbar("Password must be at least 6 characters.")
    return
  }

  state.submitting = true
  try {
    const res = await fetch("/api/galaxy/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pw }),
    })
    const data = await res.json()
    if (res.ok) {
      state.paired = true
      state.url = data.url
      state.iosConnectUrl = data.iosConnectUrl || state.iosConnectUrl
      state.iosPairingCode = data.iosPairingCode || state.iosPairingCode
      state.iosShortPairingCode = data.iosShortPairingCode || state.iosShortPairingCode
      state.iosShortPairingUrl = data.iosShortPairingUrl || state.iosShortPairingUrl
      state.iosPairingQRCodeUrl = data.iosPairingQRCodeUrl || state.iosPairingQRCodeUrl
      state.portalURL = data.portalURL || data.url || state.portalURL
      state.localBaseURL = data.localBaseURL || state.localBaseURL
      state.cookieName = data.cookieName || state.cookieName
      state.telemetryPath = data.telemetryPath || state.telemetryPath
      state.vehicleTelemetryUrl = data.vehicleTelemetryUrl || state.vehicleTelemetryUrl
      state.password = ""
      // Clear the DOM input value directly (Arrow.js doesn't two-way bind)
      const input = document.querySelector(".galaxy-input")
      if (input) input.value = ""
      showSnackbar(data.message || "Paired!")
    } else {
      showSnackbar(data.error || "Pairing failed.")
    }
  } catch (e) {
    showSnackbar("Network error — is the device reachable?")
  }
  state.submitting = false
}

async function unpair() {
  state.showUnpairModal = false
  state.submitting = true
  try {
    const res = await fetch("/api/galaxy/unpair", { method: "POST" })
    const data = await res.json()
    if (res.ok) {
      state.paired = false
      state.url = ""
      state.iosConnectUrl = ""
      state.iosPairingCode = ""
      state.iosShortPairingCode = ""
      state.iosShortPairingUrl = ""
      state.iosPairingQRCodeUrl = ""
      state.portalURL = ""
      state.localBaseURL = ""
      state.cookieName = "galaxy_session"
      state.telemetryPath = "/api/galaxy/telemetry"
      state.vehicleTelemetryUrl = ""
      showSnackbar(data.message || "Unpaired!")
    } else {
      showSnackbar(data.error || "Unpairing failed.")
    }
  } catch (e) {
    showSnackbar("Network error — is the device reachable?")
  }
  state.submitting = false
}

async function copyText(text, label) {
  if (!text) return
  try {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement("textarea")
      textarea.value = text
      textarea.setAttribute("readonly", "")
      textarea.style.position = "fixed"
      textarea.style.left = "-9999px"
      textarea.style.opacity = "0"
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand("copy")
      textarea.remove()
    }
    showSnackbar(`${label} copied!`)
  } catch (e) {
    showSnackbar(`Failed to copy ${label.toLowerCase()}.`)
  }
}

export function GalaxyPairing() {
  if (isGalaxyTunnel()) {
    return html`
      <div class="tunnel-notice">
        <div class="tunnel-notice-icon">🛰️</div>
        <h3 class="tunnel-notice-title">Galaxy Pairing Unavailable via Galaxy</h3>
        <p class="tunnel-notice-body">Galaxy pairing requires a direct connection.<br>Connect to your device's local network to use this feature.</p>
      </div>
    `;
  }

  if (!state.fetched) {
    state.fetched = true
    fetchStatus()
  }

  return html`
    <div class="galaxy-wrapper">
      <h2>Galaxy</h2>

      ${() => {
      if (state.loading) {
        return html`<div class="galaxy-loading">Checking pairing status…</div>`
      }

      if (state.paired) {
        return html`
            <section class="galaxy-widget">
              <div class="galaxy-status-badge galaxy-paired">
                <i class="bi bi-check-circle-fill"></i> Paired
              </div>
              <p class="galaxy-text">
                Your device is paired with Galaxy. Access it remotely at:
              </p>
              <a class="galaxy-url" href="${state.url}" target="_blank" rel="noopener">
                ${state.url}
              </a>
              ${() => state.iosConnectUrl ? html`
                <div class="galaxy-ios-box">
                  <a class="galaxy-button galaxy-button-primary" href="${state.iosConnectUrl}">
                    Pair with Galaxy Nav
                  </a>
                  <details class="galaxy-help">
                    <summary>Where to find setup details</summary>
                    <dl>
                      <dt>Portal URL</dt>
                      <dd>${() => state.portalURL || state.url || "Shown here after pairing."}</dd>
                      <dt>LAN URL</dt>
                      <dd>${() => state.localBaseURL || "Use Find Galaxy in the iPhone app while on the same Wi-Fi."}</dd>
                      <dt>Galaxy Token</dt>
                      <dd>Open App Keys and copy the session token.</dd>
                    </dl>
                  </details>
                </div>
              ` : ""}
              <button
                class="galaxy-button galaxy-button-danger"
                @click="${() => { state.showUnpairModal = true }}"
                disabled="${() => state.submitting}"
              >
                ${() => state.submitting ? "Unpairing…" : "Unpair"}
              </button>
            </section>

            ${() => state.showUnpairModal ? Modal({
          title: "Confirm Unpair",
          message: "Are you sure you want to unpair from Galaxy? You will lose remote access until you pair again.",
          onConfirm: unpair,
          onCancel: () => { state.showUnpairModal = false },
          confirmText: "Unpair",
        }) : ""}
          `
      }

      return html`
          <section class="galaxy-widget">
            <p class="galaxy-text">
              Pair your device with Galaxy to access The Galaxy remotely from anywhere.
              Set a password to secure your connection.
            </p>
            <div class="galaxy-input-group">
              <input
                class="galaxy-input"
                type="password"
                placeholder="Password (min 6 characters)"
                @input="${(e) => { state.password = e.target.value }}"
                @keydown="${(e) => { if (e.key === 'Enter') pair() }}"
              />
              <button
                class="galaxy-button"
                @click="${pair}"
                disabled="${() => state.submitting || state.password.trim().length < 6}"
              >
                ${() => state.submitting ? "Pairing…" : "Pair"}
              </button>
            </div>
          </section>
        `
    }}
    </div>
  `
}
