import { html, reactive } from "/assets/vendor/arrow-core.js"
import { Modal } from "/assets/components/modal.js";

const DEFAULT_PLAY_STORE_URL = "https://play.google.com/store/apps/details?id=com.embaucha.galaxynav&hl=en-US&ah=9FldHJ99kxL8oNbSlO5F4sQqwC4"

export function NavKeys() {
  const state = reactive({
    initialMapboxComplete: false,
    showMapboxHelp: false,
    visible: false,

    imageVersion: 0,

    error: "",
    lastGroup: "",
    message: "",

    amap1Key: "", amap2Key: "",
    editA1: false, editA2: false,
    savedA1: false, savedA2: false,

    publicKey: "", secretKey: "",
    editPublic: false, editSecret: false,
    savedPublic: false, savedSecret: false,

    galaxyAppUrl: DEFAULT_PLAY_STORE_URL,
    galaxyPaired: false,
    externalPairingQrData: "",
    externalPairingQrImage: "",
    externalPairingCode: "",
    externalPairingExpiresAt: 0,
    externalPairingLoading: false,

    telemetryMode: "off",
    telemetryFetchEnabled: false,
    telemetryFetchPort: 7766,
    telemetryFetchHasToken: false,
    telemetryGeneratedFetchToken: "",
    telemetryPushEnabled: false,
    telemetryPushUrl: "",
    telemetryPushToken: "",
    telemetryVehicleId: "",
    telemetryVehicleName: "",
    telemetryBatteryCapacity: "",
    telemetryDrivingInterval: 60,
    telemetryChargingInterval: 120,
    telemetryParkedInterval: 900,
    telemetryTunnelBinary: "/data/vehicle_telemetry/bin/frpc",
    telemetryTunnelServer: "",
    telemetryTunnelPort: 7000,
    telemetryTunnelToken: "",
    telemetryTunnelDomain: "",
    telemetryTunnelSubdomain: "auto",
    telemetryTunnelCa: "",
    telemetryTunnelServerName: "",
    telemetryTunnelState: "disabled",
    telemetryPublicUrl: "",
    telemetryOwnerUrl: "",
    telemetrySaving: false,

    showDeleteModal: false,
    keyToDelete: null,
  })

  const bumpImageVersion = () => state.imageVersion++

  let clearTimer = null
  let fadeTimer = null

  function showMessage(type, text, group) {
    clearTimer && clearTimeout(clearTimer)
    fadeTimer && clearTimeout(fadeTimer)

    state.error = type === "error" ? text : ""
    state.message = type === "message" ? text : ""

    state.lastGroup = group

    state.visible = true

    clearTimer = setTimeout(() => { state.message = "", state.error = "" }, 5000)
    fadeTimer = setTimeout(() => state.visible = false, 5000)
  }

  const util = {
    prefix: (key, prefix) => key.startsWith(prefix) ? key : prefix ? prefix + key : key,

    mask: (key) => {
      if (!key) {
        return ""
      }

      const prefix = ["pk.", "sk."].find(p => key.startsWith(p)) || ""
      return prefix + "x".repeat(key.length - prefix.length)
    },

    req: async (url, opts) => {
      const response = await fetch(url, { ...(opts || {}), credentials: "same-origin" })
      return { ok: response.ok, data: await response.json().catch(() => ({})) }
    },

    copyText: async (text) => {
      if (!text) {
        throw new Error("Nothing to copy")
      }

      if (navigator.clipboard?.writeText && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
        return
      }

      const textarea = document.createElement("textarea")
      textarea.value = text
      textarea.setAttribute("readonly", "")
      textarea.style.position = "fixed"
      textarea.style.left = "-9999px"
      textarea.style.opacity = "0"
      document.body.appendChild(textarea)
      textarea.select()

      try {
        if (!document.execCommand("copy")) {
          throw new Error("Copy command failed")
        }
      } finally {
        textarea.remove()
      }
    }
  }

  const meta = {
    amap1:  { prop: "amap1Key",  saved: "savedA1",     edit: "editA1",     prefix: "",    body: "amap1", minLength: 39  },
    amap2:  { prop: "amap2Key",  saved: "savedA2",     edit: "editA2",     prefix: "",    body: "amap2", minLength: 39  },
    public: { prop: "publicKey", saved: "savedPublic", edit: "editPublic", prefix: "pk.", body: "public", minLength: 80 },
    secret: { prop: "secretKey", saved: "savedSecret", edit: "editSecret", prefix: "sk.", body: "secret", minLength: 80 }
  }

  const canSave = (kind) => {
    const keyMeta = meta[kind];
    if (!keyMeta) return false;

    const value = state[keyMeta.prop]?.trim() || "";
    if (!value) return false;

    if (!state[keyMeta.saved]) {
      const fullValue = util.prefix(value, keyMeta.prefix);
      return fullValue.length >= keyMeta.minLength;
    }
    return false;
  }

  const getDeleteLabel = (kind) => {
    switch (kind) {
      case "amap1": return "AMap / Gaode 1"
      case "amap2": return "AMap / Gaode 2"
      case "public": return "Public Mapbox"
      case "secret": return "Secret Mapbox"
      default: return kind
    }
  }

  const api = {
    path: {
      galaxy: "/api/galaxy/session",
      externalPairing: "/api/external-app/pairing",
      telemetryConfig: "/api/vehicle/telemetry/config",
      key: "/api/navigation_key",
      nav: "/api/navigation"
    },

    load: async () => {
      const { ok, data } = await util.req(api.path.nav)
      if (!ok) {
        showMessage("error", "Failed to load keys...", "")
        await Promise.all([api.loadGalaxySession(), api.loadTelemetry()])
        return
      }

      state.amap1Key = data.amap1Key ?? ""
      state.amap2Key = data.amap2Key ?? ""
      state.savedA1 = !!state.amap1Key
      state.savedA2 = !!state.amap2Key

      state.publicKey = data.mapboxPublic ?? ""
      state.secretKey = data.mapboxSecret ?? ""
      state.savedPublic = !!state.publicKey
      state.savedSecret = !!state.secretKey

      state.initialMapboxComplete = state.savedPublic && state.savedSecret

      bumpImageVersion()
      await Promise.all([api.loadGalaxySession(), api.loadTelemetry()])
    },

    loadGalaxySession: async () => {
      const { ok, data } = await util.req(api.path.galaxy)
      if (!ok) {
        return showMessage("error", "Failed to load Galaxy session...", "app")
      }

      state.galaxyAppUrl = data.appUrl || DEFAULT_PLAY_STORE_URL
      state.galaxyPaired = !!data.paired
    },

    applyTelemetry: (data) => {
      const config = data.config || {}
      const fetchConfig = config.fetch || {}
      const push = config.push || {}
      const tunnel = config.tunnel || {}
      state.telemetryMode = config.mode || "off"
      state.telemetryFetchEnabled = !!fetchConfig.enabled
      state.telemetryFetchPort = Number(fetchConfig.port || 7766)
      state.telemetryFetchHasToken = !!fetchConfig.hasToken
      state.telemetryPushEnabled = !!push.enabled
      state.telemetryPushUrl = push.url || ""
      state.telemetryVehicleId = push.vehicleId || ""
      state.telemetryVehicleName = push.vehicleName || ""
      state.telemetryBatteryCapacity = push.maximumBatteryCapacityKilowattHours ?? ""
      state.telemetryDrivingInterval = Number(push.drivingIntervalSeconds || 60)
      state.telemetryChargingInterval = Number(push.chargingIntervalSeconds || 120)
      state.telemetryParkedInterval = Number(push.parkedIntervalSeconds || 900)
      state.telemetryTunnelBinary = tunnel.binaryPath || "/data/vehicle_telemetry/bin/frpc"
      state.telemetryTunnelServer = tunnel.serverAddress || ""
      state.telemetryTunnelPort = Number(tunnel.serverPort || 7000)
      state.telemetryTunnelDomain = tunnel.subdomainHost || ""
      state.telemetryTunnelSubdomain = tunnel.subdomain || "auto"
      state.telemetryTunnelCa = tunnel.trustedCaFile || ""
      state.telemetryTunnelServerName = tunnel.serverName || ""
      state.telemetryTunnelState = data.tunnel?.state || "disabled"
      state.telemetryPublicUrl = data.tunnel?.publicURL || ""
      state.telemetryOwnerUrl = data.tunnel?.ownerURL || ""
      if (data.generatedFetchToken) {
        state.telemetryGeneratedFetchToken = data.generatedFetchToken
      }
    },

    loadTelemetry: async () => {
      const { ok, data } = await util.req(api.path.telemetryConfig)
      if (!ok) {
        return showMessage("error", data.error || "Failed to load EV Vehicle Telemetry...", "telemetry")
      }
      api.applyTelemetry(data)
    },

    saveTelemetry: async ({ rotateFetchToken = false } = {}) => {
      state.telemetrySaving = true
      const payload = {
        mode: state.telemetryMode,
        rotateFetchToken,
        fetchToken: "",
        fetch: {
          enabled: ["local", "tailscale", "frp", "galaxy"].includes(state.telemetryMode),
          port: Number(state.telemetryFetchPort || 7766),
          bindAddress: state.telemetryMode === "local" ? "0.0.0.0" : "127.0.0.1",
        },
        pushToken: state.telemetryPushToken,
        push: {
          enabled: state.telemetryMode === "send" || state.telemetryPushEnabled,
          url: state.telemetryPushUrl,
          vehicleId: state.telemetryVehicleId,
          vehicleName: state.telemetryVehicleName,
          maximumBatteryCapacityKilowattHours: state.telemetryBatteryCapacity || null,
          drivingIntervalSeconds: Number(state.telemetryDrivingInterval || 60),
          chargingIntervalSeconds: Number(state.telemetryChargingInterval || 120),
          parkedIntervalSeconds: Number(state.telemetryParkedInterval || 900),
        },
        tunnelToken: state.telemetryTunnelToken,
        tunnel: {
          binaryPath: state.telemetryTunnelBinary,
          serverAddress: state.telemetryTunnelServer,
          serverPort: Number(state.telemetryTunnelPort || 7000),
          subdomainHost: state.telemetryTunnelDomain,
          subdomain: state.telemetryTunnelSubdomain,
          trustedCaFile: state.telemetryTunnelCa,
          serverName: state.telemetryTunnelServerName,
        },
      }
      const { ok, data } = await util.req(api.path.telemetryConfig, {
        body: JSON.stringify(payload),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      })
      state.telemetrySaving = false
      if (!ok) {
        return showMessage("error", data.error || "Could not save EV Vehicle Telemetry...", "telemetry")
      }
      state.telemetryPushToken = ""
      state.telemetryTunnelToken = ""
      api.applyTelemetry(data)
      showMessage("message", rotateFetchToken ? "New fetch token generated." : "EV Vehicle Telemetry saved.", "telemetry")
    },

    setupTailscale: async () => {
      state.telemetrySaving = true
      const { ok, data } = await util.req("/api/tailscale/setup", { method: "POST" })
      state.telemetrySaving = false
      if (!ok) {
        return showMessage("error", data.error || "Could not enable the personal relay...", "telemetry")
      }
      if (data.generatedFetchToken) {
        state.telemetryGeneratedFetchToken = data.generatedFetchToken
      }
      showMessage("message", data.message || "Personal relay enabled.", "telemetry")
      await api.loadTelemetry()
      setTimeout(api.loadTelemetry, 1500)
      setTimeout(api.loadTelemetry, 5500)
    },

    openTailscaleOwner: async () => {
      let ownerURL = state.telemetryOwnerUrl
      if (!ownerURL) {
        const { ok, data } = await util.req("/api/tailscale/login", { method: "POST" })
        if (!ok) {
          return showMessage("error", data.error || "Tailscale is not ready yet...", "telemetry")
        }
        ownerURL = data.ownerURL || ""
      }
      try {
        const parsed = new URL(ownerURL)
        if (parsed.protocol !== "https:" || parsed.hostname !== "login.tailscale.com") {
          throw new Error("Unexpected owner URL")
        }
        window.location.href = parsed.href
      } catch (error) {
        showMessage("error", "Tailscale returned an invalid owner URL.", "telemetry")
      }
    },

    disableTailscale: async () => {
      state.telemetrySaving = true
      const { ok, data } = await util.req("/api/tailscale/uninstall", { method: "POST" })
      state.telemetrySaving = false
      if (!ok) {
        return showMessage("error", data.error || "Could not disable the personal relay...", "telemetry")
      }
      await api.loadTelemetry()
      showMessage("message", data.message || "Personal relay disabled.", "telemetry")
    },

    copyTelemetryValue: async (value, label) => {
      try {
        await util.copyText(value)
        showMessage("message", `${label} copied!`, "telemetry")
      } catch (e) {
        showMessage("error", "Copy failed...", "telemetry")
      }
    },

    createExternalPairing: async () => {
      state.externalPairingLoading = true
      const { ok, data } = await util.req(api.path.externalPairing, { method: "POST" })
      state.externalPairingLoading = false
      if (!ok) {
        return showMessage("error", data.error || "Could not create pairing...", "app")
      }
      state.externalPairingQrData = data.qrData || ""
      state.externalPairingQrImage = data.qrImageDataURL || ""
      state.externalPairingCode = data.pairingCode || ""
      state.externalPairingExpiresAt = Number(data.expiresAt || 0)
      showMessage("message", "One-time pairing is ready for 10 minutes.", "app")
    },

    copyExternalPairing: async () => {
      try {
        await util.copyText(state.externalPairingQrData)
        showMessage("message", "One-time pairing package copied!", "app")
      } catch (e) {
        showMessage("error", "Copy failed...", "app")
      }
    },

    save: (kind) => async () => {
      const group = kind.startsWith("amap") ? "amap" : "mapbox"
      const keyMeta = meta[kind]
      const value = util.prefix(state[keyMeta.prop].trim(), keyMeta.prefix)

      const { ok, data } = await util.req(api.path.key, {
        body: JSON.stringify({ [keyMeta.body]: value }),
        headers: { "Content-Type": "application/json" },
        method: "POST"
      })

      if (!ok) {
        const input = document.getElementById(`${kind}-key`)
        if (input) {
          input.value = ""
          state[keyMeta.edit] = true
          state[keyMeta.saved] = false
          state[keyMeta.prop] = ""
          input.focus()
        }
        return showMessage("error", data.error || "Save failed...", group)
      }

      Object.assign(state, {
        [keyMeta.edit]: false,
        [keyMeta.saved]: true,
        [keyMeta.prop]: value
      })

      const input = document.getElementById(`${kind}-key`)
      if (input) {
        input.blur()
        input.value = ""
        requestAnimationFrame(() => { input.value = util.mask(state[keyMeta.prop]) })
      }

      if (group === "mapbox") {
        bumpImageVersion()
      }

      showMessage("message", data.message || "Saved!", group)
    },

    confirmDelete: (kind) => {
      state.keyToDelete = kind;
      state.showDeleteModal = true;
    },

    delete: async () => {
      const kind = state.keyToDelete;
      if (!kind) return;

      const group = kind.startsWith("amap") ? "amap" : "mapbox"
      const keyMeta = meta[kind]

      const { ok, data } = await util.req(`${api.path.key}?type=${kind}`, {
        method: "DELETE"
      })

      state.showDeleteModal = false;

      if (!ok) {
        return showMessage("error", data.error || "Delete failed...", group)
      }

      Object.assign(state, {
        [keyMeta.saved]: false,
        [keyMeta.prop]: ""
      })

      if (group === "mapbox") {
        state.initialMapboxComplete = false
        bumpImageVersion()
      }

      showMessage("message", data.message || "Deleted!", group)
    }
  }

  queueMicrotask(api.load)

  function renderGroup(title, kinds) {
    const isMapbox = title === "Mapbox Keys"
    const isAMap = title === "AMap / Gaode Keys"

    return html`
      <div class="navkeys-group">
        <div class="navkeys-title">
          ${title}
          ${isMapbox ? html`
            <span class="navkeys-help-icon" @click="${() => state.showMapboxHelp = !state.showMapboxHelp}">
              <i class="bi bi-question-circle-fill"></i>
            </span>
          ` : ""}
        </div>
        ${isAMap ? html`<div class="navkeys-subtitle">AMap is the Gaode provider, not Google Maps.</div>` : ""}

        ${kinds.map(kind => {
          const keyMeta = meta[kind]
          const label = kind[0].toUpperCase() + kind.slice(1).replace(/[0-9]/, d => " " + d)

          return html`
            <label class="navkeys-label" for="${kind}-key">${label} Key</label>
            <div class="navkeys-row">
              <input
                autocomplete="off"
                class="navkeys-input"
                id="${kind}-key"
                placeholder="${keyMeta.prefix || ""}xxxxxx..."
                value="${() => state[keyMeta.saved] ? util.mask(state[keyMeta.prop]) : state[keyMeta.prop]}"
                @keydown="${(e) => {
                  if (state[keyMeta.saved] && !state[keyMeta.edit]) {
                    state[keyMeta.edit] = true
                    state[keyMeta.saved] = false
                    state[keyMeta.prop] = ""
                    e.target.value = ""
                  }
                }}"
                @input="${(e) => state[keyMeta.prop] = e.target.value}"
              />
              <button
                class="${() => `navkeys-btn ${state[keyMeta.saved] ? "delete" : ""}`}"
                @click="${() => state[keyMeta.saved] ? api.confirmDelete(kind) : api.save(kind)()}"
                disabled="${() => !state[keyMeta.saved] && !canSave(kind)}">
                ${() => state[keyMeta.saved] ? "🗑️" : "💾"}
              </button>
            </div>
          `
        })}

        ${() => {
          if (isMapbox && state.showMapboxHelp) {
            return html`
              <div class="navkeys-help-img">
                <img
                  alt="Mapbox key setup guide"
                  src="${() => {
                    const bothKeysSet = state.savedPublic && state.savedSecret

                    let imageSource = "/mapbox-help/no_keys_set.png"
                    if (bothKeysSet) {
                      imageSource = state.initialMapboxComplete ? "/mapbox-help/setup_completed.png" : "/mapbox-help/both_keys_set.png"
                    } else if (state.savedPublic) {
                      imageSource = "/mapbox-help/public_key_set.png"
                    }
                    return `${imageSource}?v=${state.imageVersion}`
                  }}"
                />
              </div>
            `
          }
          return ""
        }}
      </div>
    `
  }

  function renderStatus(group) {
    return html`
      <div class="navkeys-status">
        <div
          class="navkeys-message"
          style="${() => state.lastGroup === group && state.message ? `opacity: ${state.visible ? 1 : 0}` : "opacity: 0"}">
          ${() => state.message}
        </div>
        <div
          class="navkeys-error"
          style="${() => state.lastGroup === group && state.error ? `opacity: ${state.visible ? 1 : 0}` : "opacity: 0"}">
          ${() => state.error}
        </div>
      </div>
    `
  }

  function renderAppKeys() {
    return html`
      <div class="navkeys-title">App Keys</div>

      <div class="navkeys-app-actions">
        <a
          class="navkeys-btn navkeys-link-btn"
          href="${() => state.galaxyAppUrl}"
          rel="noopener noreferrer"
          target="_blank">
          <i class="bi bi-google-play"></i>
          <span>Install The App</span>
        </a>
      </div>

      <div class="navkeys-subtitle">
        Pair RangeBridge, Galaxy Nav, or another external app without copying URLs or reusable secrets.
      </div>

      <div class="navkeys-app-actions navkeys-pair-actions">
        <button
          class="navkeys-btn navkeys-copy-btn"
          @click="${api.createExternalPairing}"
          disabled="${() => state.externalPairingLoading || state.telemetryMode === "off"}">
          <i class="bi bi-qr-code"></i>
          <span>${() => state.externalPairingLoading ? "Creating..." : "Create Pairing QR"}</span>
        </button>
      </div>

      ${() => state.externalPairingQrData ? html`
        <div class="navkeys-pairing-card">
          ${state.externalPairingQrImage ? html`
            <img class="navkeys-pairing-qr" alt="One-time external app pairing QR code" src="${state.externalPairingQrImage}" />
          ` : ""}
          <div class="navkeys-pairing-details">
            <div class="navkeys-label">One-time connection package</div>
            <div class="navkeys-pairing-code" aria-label="Six digit pairing code">
              ${state.externalPairingCode}
            </div>
            <div class="navkeys-subtitle navkeys-pairing-subtitle">
              Scan the QR or enter this six-digit code in an app on the same LAN. It expires at ${new Date(state.externalPairingExpiresAt * 1000).toLocaleTimeString()} and can be used once.
            </div>
            <button class="navkeys-btn navkeys-copy-btn" @click="${api.copyExternalPairing}">
              <i class="bi bi-copy"></i>
              <span>Copy Pairing Package</span>
            </button>
          </div>
        </div>
      ` : ""}
    `
  }

  function telemetryInput(label, property, { type = "text", placeholder = "", secret = false } = {}) {
    return html`
      <label class="navkeys-label">${label}</label>
      <input
        autocomplete="${secret ? "new-password" : "off"}"
        class="navkeys-input ${secret ? "navkeys-token-input" : ""}"
        type="${type}"
        placeholder="${placeholder}"
        value="${() => state[property]}"
        @input="${(event) => state[property] = event.target.value}" />
    `
  }

  function renderTelemetryConfig() {
    return html`
      <div class="navkeys-title">EV Vehicle Telemetry</div>
      <div class="navkeys-subtitle">
        Cache only, send to your custom backend, serve on your LAN, use a personal Tailscale Funnel, publish through your own FRP gateway, or use the hosted Galaxy route. Custom HTTPS sending can also run with any access mode.
      </div>

      <div class="navkeys-telemetry-grid">
        <div>
          <label class="navkeys-label">Operating mode</label>
          <select
            class="navkeys-input navkeys-select"
            value="${() => state.telemetryMode}"
            @change="${(event) => {
              state.telemetryMode = event.target.value
              if (state.telemetryMode === "send") state.telemetryPushEnabled = true
            }}">
            <option value="off">Off / cache only</option>
            <option value="send">Custom backend (send only)</option>
            <option value="local">Local network</option>
            <option value="tailscale">Personal public relay (Tailscale)</option>
            <option value="frp">Self-hosted FRP</option>
            <option value="galaxy">Galaxy portal</option>
          </select>
        </div>
        ${() => state.telemetryMode === "local" || state.telemetryMode === "frp" ? html`
          <div>${telemetryInput("Local API port", "telemetryFetchPort", { type: "number", placeholder: "7766" })}</div>
        ` : ""}
      </div>

      ${() => state.telemetryMode === "tailscale" ? html`
        <div class="navkeys-telemetry-section">
          <div class="navkeys-label">Personal public relay</div>
          <div class="navkeys-subtitle">
            Your comma makes an outbound connection to your own free Tailscale account. One owner login and one Funnel approval are required; afterward the public HTTPS URL is restored automatically without port forwarding or custom DNS.
          </div>
          <div class="navkeys-telemetry-status">
            Relay: <strong>${() => state.telemetryTunnelState}</strong>
            ${() => state.telemetryPublicUrl ? html`
              <button class="navkeys-inline-copy" @click="${() => api.copyTelemetryValue(state.telemetryPublicUrl, "Public URL")}">
                ${state.telemetryPublicUrl}
              </button>
            ` : ""}
          </div>
          <div class="navkeys-app-actions navkeys-telemetry-actions">
            <button class="navkeys-btn navkeys-copy-btn" @click="${api.setupTailscale}" disabled="${() => state.telemetrySaving}">
              <i class="bi bi-cloud-arrow-up-fill"></i><span>Install / Enable Relay</span>
            </button>
            <button class="navkeys-btn navkeys-copy-btn" @click="${api.openTailscaleOwner}" disabled="${() => state.telemetrySaving || state.telemetryTunnelState === "running"}">
              <i class="bi bi-box-arrow-up-right"></i><span>${() => state.telemetryTunnelState === "needs-funnel-approval" ? "Approve Funnel" : "Owner Login"}</span>
            </button>
            <button class="navkeys-btn navkeys-copy-btn delete" @click="${api.disableTailscale}" disabled="${() => state.telemetrySaving}">
              <i class="bi bi-stop-circle"></i><span>Disable Relay</span>
            </button>
          </div>
        </div>
      ` : ""}

      ${() => state.telemetryMode === "frp" ? html`
        <div class="navkeys-telemetry-section">
          <div class="navkeys-label">FRP client</div>
          <div class="navkeys-telemetry-grid">
            <div>${telemetryInput("Gateway address", "telemetryTunnelServer", { placeholder: "example.com" })}</div>
            <div>${telemetryInput("Gateway port", "telemetryTunnelPort", { type: "number", placeholder: "7000" })}</div>
            <div>${telemetryInput("Public wildcard domain", "telemetryTunnelDomain", { placeholder: "example.com" })}</div>
            <div>${telemetryInput("Subdomain", "telemetryTunnelSubdomain", { placeholder: "auto" })}</div>
            <div>${telemetryInput("frpc binary path", "telemetryTunnelBinary", { placeholder: "/data/vehicle_telemetry/bin/frpc" })}</div>
            <div>${telemetryInput("Gateway token (leave blank to keep)", "telemetryTunnelToken", { secret: true, placeholder: "••••••••" })}</div>
            <div>${telemetryInput("Trusted CA file", "telemetryTunnelCa", { placeholder: "/data/galaxy/gateway-ca.crt" })}</div>
            <div>${telemetryInput("TLS server name", "telemetryTunnelServerName", { placeholder: "example.com" })}</div>
          </div>
          <div class="navkeys-telemetry-status">
            Tunnel: <strong>${() => state.telemetryTunnelState}</strong>
            ${() => state.telemetryPublicUrl ? html`
              <button class="navkeys-inline-copy" @click="${() => api.copyTelemetryValue(state.telemetryPublicUrl, "Proxy URL")}">
                ${state.telemetryPublicUrl}
              </button>
            ` : ""}
          </div>
        </div>
      ` : ""}

      <div class="navkeys-telemetry-section">
        <label class="navkeys-checkbox-row">
          <input
            type="checkbox"
            :checked="${() => state.telemetryMode === "send" || state.telemetryPushEnabled}"
            @change="${(event) => state.telemetryPushEnabled = !!event.target.checked}"
            disabled="${() => state.telemetryMode === "send"}" />
          <span>Send snapshots to a custom HTTPS backend</span>
        </label>
        ${() => state.telemetryMode === "send" || state.telemetryPushEnabled ? html`
          <div class="navkeys-telemetry-grid">
            <div>${telemetryInput("Backend URL", "telemetryPushUrl", { placeholder: "https://telemetry.example/ingest" })}</div>
            <div>${telemetryInput("Backend bearer token (leave blank to keep)", "telemetryPushToken", { secret: true, placeholder: "••••••••" })}</div>
            <div>${telemetryInput("Vehicle ID or VIN", "telemetryVehicleId")}</div>
            <div>${telemetryInput("Vehicle name", "telemetryVehicleName")}</div>
            <div>${telemetryInput("Battery capacity (kWh)", "telemetryBatteryCapacity", { type: "number" })}</div>
            <div>${telemetryInput("Driving interval (seconds)", "telemetryDrivingInterval", { type: "number" })}</div>
            <div>${telemetryInput("Charging interval (seconds)", "telemetryChargingInterval", { type: "number" })}</div>
            <div>${telemetryInput("Parked interval (seconds)", "telemetryParkedInterval", { type: "number" })}</div>
          </div>
        ` : ""}
      </div>

      <div class="navkeys-app-actions navkeys-telemetry-actions">
        <button
          class="navkeys-btn navkeys-copy-btn"
          @click="${() => api.saveTelemetry({ rotateFetchToken: true })}"
          disabled="${() => state.telemetrySaving || state.telemetryMode === "off" || state.telemetryMode === "send"}">
          <i class="bi bi-arrow-clockwise"></i>
          <span>Rotate Fetch Token</span>
        </button>
        <button
          class="navkeys-btn navkeys-copy-btn"
          @click="${() => api.saveTelemetry()}"
          disabled="${() => state.telemetrySaving}">
          <i class="bi bi-floppy-fill"></i>
          <span>${() => state.telemetrySaving ? "Saving..." : "Save Telemetry"}</span>
        </button>
      </div>

      ${() => state.telemetryGeneratedFetchToken ? html`
        <div class="navkeys-pairing-card navkeys-token-card">
          <div class="navkeys-pairing-details">
            <div class="navkeys-label">New fetch token — copy it now</div>
            <div class="navkeys-generated-token">${state.telemetryGeneratedFetchToken}</div>
            <button class="navkeys-btn navkeys-copy-btn" @click="${() => api.copyTelemetryValue(state.telemetryGeneratedFetchToken, "Fetch token")}">
              <i class="bi bi-copy"></i><span>Copy Token</span>
            </button>
          </div>
        </div>
      ` : ""}
    `
  }

  return html`
    <div class="navkeys-wrapper navkeys-offset-top">
      <div class="navkeys-container">
          ${renderGroup("AMap / Gaode Keys", ["amap1", "amap2"])}
        ${renderStatus("amap")}
      </div>
      <div class="navkeys-container">
        ${renderGroup("Mapbox Keys", ["public", "secret"])}
        ${renderStatus("mapbox")}
      </div>
      <div class="navkeys-container navkeys-app-container">
        ${renderAppKeys()}
        ${renderStatus("app")}
      </div>
      <div class="navkeys-container navkeys-app-container">
        ${renderTelemetryConfig()}
        ${renderStatus("telemetry")}
      </div>
    </div>
    ${() => state.showDeleteModal ? Modal({
      title: "Confirm Delete",
      message: `Are you sure you want to delete your <strong>${getDeleteLabel(state.keyToDelete)}</strong> key?`,
      onConfirm: api.delete,
      onCancel: () => { state.showDeleteModal = false },
      confirmText: "Yes, Delete"
    }) : ""}
  `
}
