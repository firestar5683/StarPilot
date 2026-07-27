import { html, reactive } from "/assets/vendor/arrow-core.js"

export function TailscaleControl() {
  const state = reactive({
    busy: false,
    enabled: false,
    installed: false,
    ownerURL: "",
    publicURL: "",
    relayState: "disabled",
  })

  async function requestJSON(url, options) {
    const response = await fetch(url, { ...(options || {}), credentials: "same-origin" })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.error || "Tailscale request failed.")
    }
    return data
  }

  async function refresh() {
    try {
      const data = await requestJSON("/api/tailscale/installed")
      state.installed = !!data.installed
      state.enabled = !!data.enabled
      state.relayState = data.state || "disabled"
      state.publicURL = data.publicURL || ""
      state.ownerURL = data.ownerURL || ""
    } catch (error) {
      showSnackbar(error.message)
    }
  }

  function openOwnerURL(ownerURL) {
    try {
      const parsed = new URL(ownerURL)
      if (parsed.protocol !== "https:" || parsed.hostname !== "login.tailscale.com") {
        throw new Error("Unexpected owner URL")
      }
      window.location.href = parsed.href
    } catch (error) {
      showSnackbar("Tailscale returned an invalid owner URL.")
    }
  }

  async function enableRelay() {
    if (state.busy) return
    state.busy = true
    try {
      const data = await requestJSON("/api/tailscale/setup", { method: "POST" })
      showSnackbar(data.message || "Personal relay enabled.")
      await refresh()
      setTimeout(refresh, 1500)
      setTimeout(refresh, 5500)
    } catch (error) {
      showSnackbar(error.message)
    } finally {
      state.busy = false
    }
  }

  async function ownerLogin() {
    if (state.busy) return
    if (state.ownerURL) {
      openOwnerURL(state.ownerURL)
      return
    }
    state.busy = true
    try {
      const data = await requestJSON("/api/tailscale/login", { method: "POST" })
      openOwnerURL(data.ownerURL || "")
    } catch (error) {
      showSnackbar(error.message)
    } finally {
      state.busy = false
    }
  }

  async function disableRelay() {
    if (state.busy) return
    state.busy = true
    try {
      const data = await requestJSON("/api/tailscale/uninstall", { method: "POST" })
      showSnackbar(data.message || "Personal relay disabled.")
      await refresh()
    } catch (error) {
      showSnackbar(error.message)
    } finally {
      state.busy = false
    }
  }

  refresh()

  return html`
    <div class="toggle-control-widget" style="margin-top: 1.5rem">
      <section class="tailscale-widget">
        <div class="toggle-control-title">Personal Tailscale Relay</div>
        <p class="tailscale-text">
          Give this comma a public, bearer-token-protected telemetry URL through your own free Tailscale account. Setup is outbound-only and needs one owner login plus one Funnel approval. No router changes, custom DNS, shared relay, or StarPilot-managed account are required.
          <br><br>Status: <strong>${() => state.relayState}</strong>
        </p>
        ${() => state.publicURL ? html`<p class="tailscale-text">${state.publicURL}</p>` : ""}
        <div class="tailscale-button-wrapper">
          <button class="tailscale-button" @click="${enableRelay}" disabled="${() => state.busy}">
            ${() => state.busy ? "Working..." : state.enabled ? "Re-enable / Repair" : state.installed ? "Enable Relay" : "Install / Enable"}
          </button>
          ${() => state.enabled && state.relayState !== "running" ? html`
            <button class="tailscale-button" @click="${ownerLogin}" disabled="${() => state.busy}">
              ${() => state.relayState === "needs-funnel-approval" ? "Approve Funnel" : "Owner Login"}
            </button>
          ` : ""}
          ${() => state.enabled ? html`
            <button class="tailscale-button" @click="${disableRelay}" disabled="${() => state.busy}">Disable Relay</button>
          ` : ""}
          <a class="tailscale-link" href="https://tailscale.com/download" rel="noopener noreferrer" target="_blank">
            Download Tailscale on your other devices
          </a>
        </div>
      </section>
    </div>
  `
}
