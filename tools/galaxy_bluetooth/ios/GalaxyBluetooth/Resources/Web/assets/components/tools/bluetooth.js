import { html, reactive } from "/assets/vendor/arrow-core.js"
import { escapeHtml, galaxyPath } from "/assets/js/utils.js"

const state = reactive({
  loading: true,
  busy: "",
  powerTarget: null,
  available: false,
  enabled: false,
  powered: false,
  discovering: false,
  offroad: false,
  selectedAudio: "",
  pairingAddress: "",
  devices: [],
  revision: 0,
  deviceSignature: "",
  refreshing: false,
  lastUpdated: 0,
  prompt: null,
  audioTestAddress: "",
  audioTestLabel: "",
  error: "",
})

let initialized = false
let audioTestTimer = null
let pollTimer = null
let refreshRequested = false
let refreshPromise = null
const POLL_INTERVAL_MS = 750
const ACTIVE_POLL_INTERVAL_MS = 250

function bluetoothPageActive() {
  const currentPath = window.location.pathname.replace(/\/+$/, "")
  const bluetoothPath = galaxyPath("/bluetooth").replace(/\/+$/, "")
  return document.querySelector(".bluetoothPage") !== null || currentPath === bluetoothPath
}

function pollDelay() {
  return state.busy || state.discovering || state.pairingAddress ? ACTIVE_POLL_INTERVAL_MS : POLL_INTERVAL_MS
}

function schedulePoll(delay = pollDelay()) {
  if (pollTimer !== null) clearTimeout(pollTimer)
  pollTimer = setTimeout(async () => {
    pollTimer = null
    try {
      if (bluetoothPageActive() && document.visibilityState !== "hidden" && state.busy !== "power") {
        await refresh()
      }
    } finally {
      schedulePoll()
    }
  }, delay)
}

function startAudioTestCountdown(address, delayMs, requestStartedAt) {
  if (audioTestTimer !== null) clearInterval(audioTestTimer)
  const halfRoundTripMs = Math.max(0, (performance.now() - requestStartedAt) / 2)
  const deadline = performance.now() + Math.max(0, delayMs - halfRoundTripMs)
  state.audioTestAddress = address

  const update = () => {
    const remaining = deadline - performance.now()
    if (remaining > 0) {
      state.audioTestLabel = String(Math.max(1, Math.ceil(remaining / 1000)))
    } else if (remaining > -3000) {
      state.audioTestLabel = "NOW"
    } else {
      state.audioTestLabel = ""
      state.audioTestAddress = ""
      clearInterval(audioTestTimer)
      audioTestTimer = null
    }
  }
  update()
  audioTestTimer = setInterval(update, 50)
}

async function request(operation, body = {}) {
  const requestStartedAt = performance.now()
  state.busy = operation
  if (operation === "power") state.powerTarget = !!body.enabled
  schedulePoll(250)
  try {
    const response = await fetch(galaxyPath(`/api/bluetooth/${operation}`), {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Bluetooth operation failed")
    if (operation === "test_audio") {
      startAudioTestCountdown(String(body.address || ""), Number(payload.audio_test_delay_ms || 3000), requestStartedAt)
    }
    state.error = ""
    await refresh()
  } catch (error) {
    state.error = error?.message || "Bluetooth operation failed"
  } finally {
    state.busy = ""
    if (operation === "power") state.powerTarget = null
    schedulePoll(250)
  }
}

async function refreshOnce() {
  const statusUrl = `${galaxyPath("/api/bluetooth/status")}?_=${Date.now()}`
  const response = await fetch(statusUrl, { cache: "no-store" })
  const payload = await response.json()
  state.available = !!payload.available
  state.enabled = !!payload.enabled
  state.powered = !!payload.powered
  state.discovering = !!payload.discovering
  state.offroad = !!payload.offroad
  state.selectedAudio = String(payload.selected_audio || "")
  state.pairingAddress = String(payload.pairing_address || "")
  const devices = Array.isArray(payload.devices) ? payload.devices : []
  const deviceSignature = JSON.stringify({
    enabled: state.enabled,
    discovering: state.discovering,
    selectedAudio: state.selectedAudio,
    pairingAddress: state.pairingAddress,
    devices,
  })
  state.devices = devices
  if (state.deviceSignature !== deviceSignature) {
    state.deviceSignature = deviceSignature
    state.revision++
  }
  state.lastUpdated = Date.now()
  state.prompt = payload.prompt || null
  state.error = payload.error || (response.ok ? "" : "Bluetooth service unavailable")
}

function pairingPromptNeedsValue() {
  return state.prompt && (state.prompt.kind === "pin" || state.prompt.kind === "passkey")
}

function respondToPairingPrompt(accepted) {
  const prompt = state.prompt
  if (!prompt || state.busy === "pairing_response") return
  const input = document.getElementById("bluetoothPairingValue")
  const value = input?.value.trim() || ""
  if (accepted && prompt.kind === "pin" && !value) {
    state.error = "Enter the PIN to continue pairing."
    input?.focus()
    return
  }
  if (accepted && prompt.kind === "passkey" && !/^\d{1,6}$/.test(value)) {
    state.error = "Enter the numeric passkey to continue pairing."
    input?.focus()
    return
  }
  request("pairing_response", { prompt_id: prompt.id, accepted, value })
}

function pairingPrompt() {
  const prompt = state.prompt
  if (!prompt) return ""
  const name = prompt.name || "Bluetooth device"
  const valuePrompt = pairingPromptNeedsValue()
  const message = prompt.kind === "confirmation"
    ? "Confirm the pairing request on this device."
    : prompt.kind === "authorization"
      ? "Allow this device to connect?"
      : prompt.kind === "pin"
        ? "Enter the PIN supplied by the device."
        : prompt.kind === "passkey"
          ? "Enter the device passkey."
          : "Follow the instructions on the device."
  return html`
    <div class="bluetoothPrompt">
      <div class="bluetoothPromptHeader"><i class="bi bi-shield-check" aria-hidden="true"></i><strong>Bluetooth pairing request</strong></div>
      <p><strong>${name}</strong> — ${message}</p>
      ${prompt.value ? html`<p class="bluetoothPromptPasskey">Passkey: <strong>${prompt.value}</strong></p>` : ""}
      ${() => valuePrompt ? html`
        <input id="bluetoothPairingValue" class="bluetoothPromptInput" inputmode="numeric" autocomplete="one-time-code"
               placeholder="${() => prompt.kind === "pin" ? "PIN" : "Passkey"}" disabled="${() => state.busy === "pairing_response"}" />
      ` : ""}
      ${prompt.display_only ? "" : html`
        <div class="bluetoothPromptActions">
          <button class="bluetoothPromptReject" disabled="${() => state.busy === "pairing_response"}" @click="${() => respondToPairingPrompt(false)}">Cancel</button>
          <button disabled="${() => state.busy === "pairing_response"}" @click="${() => respondToPairingPrompt(true)}">Allow</button>
        </div>
      `}
    </div>
  `
}

async function refresh() {
  refreshRequested = true
  if (refreshPromise !== null) return refreshPromise

  state.refreshing = true
  refreshPromise = (async () => {
    while (refreshRequested) {
      refreshRequested = false
      try {
        await refreshOnce()
      } catch (error) {
        state.available = false
        state.error = error?.message || "Bluetooth service unavailable"
      } finally {
        state.loading = false
      }
    }
  })()

  try {
    await refreshPromise
  } finally {
    refreshPromise = null
    state.refreshing = false
  }
}

function initialize() {
  if (initialized) return
  initialized = true
  window.addEventListener("focus", refresh)
  window.addEventListener("pageshow", refresh)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "hidden" && bluetoothPageActive()) refresh()
  })
  refresh()
  schedulePoll(0)
}

function normalizedAddress(device) {
  return String(device.address || "").toUpperCase()
}

function isPairing(device) {
  return !!state.pairingAddress && state.pairingAddress.toUpperCase() === normalizedAddress(device)
}

function deviceIcon(device) {
  if (device.audio && device.controller) return "bi-headset"
  if (device.audio) return "bi-headphones"
  if (device.controller) return "bi-controller"
  return "bi-bluetooth"
}

function deviceCapabilities(device) {
  const capabilities = []
  if (device.audio) capabilities.push("Audio")
  if (device.controller) capabilities.push("Controller")
  return capabilities.join(" · ") || "Bluetooth device"
}

function deviceStatus(device) {
  if (isPairing(device)) return "Pairing…"
  if (device.connected) {
    const audioSelected = state.selectedAudio.toUpperCase() === normalizedAddress(device)
    if (!device.paired) return audioSelected ? "Connected · Ready to pair · Audio output" : "Connected · Ready to pair"
    return audioSelected ? "Connected · Audio output" : "Connected"
  }
  return device.paired ? "Saved" : "Ready to pair"
}

function knownDevices() {
  return state.devices.filter((device) => device.paired || device.trusted || device.connected)
}

function availableDevices() {
  return state.devices.filter((device) => !device.paired && !device.trusted && !device.connected)
}

function deviceActions(device) {
  const audioSelected = () => state.selectedAudio.toUpperCase() === device.address.toUpperCase()
  const pairing = () => isPairing(device)
  return html`
    <div class="bluetoothActions">
      ${!device.paired ? html`
        <button disabled="${() => !state.offroad || !!state.busy || pairing()}" @click="${() => request("pair", { address: device.address })}">
          ${() => pairing() ? "Pairing…" : "Pair"}
        </button>
      ` : ""}
      ${device.paired || device.connected ? html`
        <button disabled="${() => !!state.busy}" @click="${() => request(device.connected ? "disconnect" : "connect", { address: device.address })}">
          ${device.connected ? "Disconnect" : "Connect"}
        </button>
      ` : ""}
      ${device.paired || device.connected ? html`
        ${device.audio ? html`
          <button class="${() => audioSelected() ? "selected" : ""}"
                  disabled="${() => !!state.busy}" @click="${() => request("select_audio", { address: audioSelected() ? "" : device.address })}">
            ${() => audioSelected() ? "Stop Using for Audio" : "Use for Audio"}
          </button>
          ${device.connected ? html`
            <button disabled="${() => !state.offroad || !!state.busy || !!state.audioTestLabel}" @click="${() => request("test_audio", { address: device.address })}">
              ${() => state.audioTestAddress === device.address && state.audioTestLabel ? `Test Audio: ${state.audioTestLabel}` : "Test Audio"}
            </button>
          ` : ""}
        ` : ""}
        ${device.paired ? html`<button class="bluetoothIconButton bluetoothForgetButton" title="Forget device" aria-label="Forget ${device.name}"
                disabled="${() => !state.offroad || !!state.busy}" @click="${() => {
          if (window.confirm(`Forget ${device.name}?`)) request("forget", { address: device.address })
        }}"><i class="bi bi-trash3" aria-hidden="true"></i></button>` : ""}
      ` : ""}
    </div>
  `
}

function deviceRow(device) {
  return html`
    <div class="${() => `bluetoothDeviceRow ${device.connected ? "connected" : ""}`}">
      <div class="bluetoothDeviceIcon"><i class="bi ${deviceIcon(device)}" aria-hidden="true"></i></div>
      <div class="bluetoothDeviceDetails">
        <div class="bluetoothDeviceName">
          <h3>${device.name}</h3>
          ${device.connected ? html`<span class="bluetoothConnectedDot" title="Connected"></span>` : ""}
        </div>
        <p>${deviceCapabilities(device)}</p>
        <span class="bluetoothDeviceStatus">${() => deviceStatus(device)}</span>
      </div>
      ${deviceActions(device)}
    </div>
  `
}

function deviceSection(title, icon, devices, emptyText = "", revision = null) {
  const revisionAttribute = revision === null ? "" : ` data-revision="${revision}"`
  return html`
    <section class="bluetoothSection"${revisionAttribute}>
      <div class="bluetoothSectionHeader">
        <div><i class="bi ${icon}" aria-hidden="true"></i><h3>${title}</h3></div>
        <span>${devices.length}</span>
      </div>
      <div class="bluetoothSectionBody">
        ${devices.length ? devices.map(deviceRow) : html`
          <div class="bluetoothEmptyState">${emptyText}</div>
        `}
      </div>
    </section>
  `
}

function renderDisabledAttribute(disabled) {
  return disabled ? " disabled" : ""
}

function renderDeviceActions(device) {
  const selected = state.selectedAudio.toUpperCase() === device.address.toUpperCase()
  const pairing = isPairing(device)
  const address = escapeHtml(device.address)
  const name = escapeHtml(device.name)
  const actions = []
  if (!device.paired) {
    actions.push("<button data-bluetooth-operation=\"pair\" data-address=\"" + address + "\"" +
      renderDisabledAttribute(!state.offroad || !!state.busy || pairing) + ">" + (pairing ? "Pairing…" : "Pair") + "</button>")
  }
  if (device.paired || device.connected) {
    const operation = device.connected ? "disconnect" : "connect"
    actions.push("<button data-bluetooth-operation=\"" + operation + "\" data-address=\"" + address + "\"" +
      renderDisabledAttribute(!!state.busy) + ">" + (device.connected ? "Disconnect" : "Connect") + "</button>")
    if (device.audio) {
      actions.push("<button class=\"" + (selected ? "selected" : "") + "\" data-bluetooth-operation=\"select_audio\" data-address=\"" +
        (selected ? "" : address) + "\"" + renderDisabledAttribute(!!state.busy) + ">" +
        (selected ? "Stop Using for Audio" : "Use for Audio") + "</button>")
      if (device.connected) {
        const testing = state.audioTestAddress.toUpperCase() === device.address.toUpperCase() && !!state.audioTestLabel
        actions.push("<button data-bluetooth-operation=\"test_audio\" data-address=\"" + address + "\"" +
          renderDisabledAttribute(!state.offroad || !!state.busy || !!state.audioTestLabel) + ">" +
          (testing ? "Test Audio: " + escapeHtml(state.audioTestLabel) : "Test Audio") + "</button>")
      }
    }
    if (device.paired) {
      actions.push("<button class=\"bluetoothIconButton bluetoothForgetButton\" data-bluetooth-operation=\"forget\" data-address=\"" +
        address + "\" data-device-name=\"" + name + "\" title=\"Forget device\" aria-label=\"Forget " + name + "\"" +
        renderDisabledAttribute(!state.offroad || !!state.busy) + "><i class=\"bi bi-trash3\" aria-hidden=\"true\"></i></button>")
    }
  }
  return "<div class=\"bluetoothActions\">" + actions.join("") + "</div>"
}

function renderDeviceRow(device) {
  const name = escapeHtml(device.name)
  return "<div class=\"bluetoothDeviceRow " + (device.connected ? "connected" : "") + "\">" +
    "<div class=\"bluetoothDeviceIcon\"><i class=\"bi " + deviceIcon(device) + "\" aria-hidden=\"true\"></i></div>" +
    "<div class=\"bluetoothDeviceDetails\"><div class=\"bluetoothDeviceName\"><h3>" + name +
    "</h3>" + (device.connected ? "<span class=\"bluetoothConnectedDot\" title=\"Connected\"></span>" : "") +
    "</div><p>" + deviceCapabilities(device) + "</p><span class=\"bluetoothDeviceStatus\">" +
    escapeHtml(deviceStatus(device)) + "</span></div>" + renderDeviceActions(device) + "</div>"
}

function renderDeviceSection(title, icon, devices, emptyText = "", revision = null) {
  const revisionAttribute = revision === null ? "" : " data-revision=\"" + revision + "\""
  const rows = devices.length
    ? devices.map(renderDeviceRow).join("")
    : "<div class=\"bluetoothEmptyState\">" + escapeHtml(emptyText) + "</div>"
  return html(["<section class=\"bluetoothSection\"" + revisionAttribute + ">" +
    "<div class=\"bluetoothSectionHeader\"><div><i class=\"bi " + icon + "\" aria-hidden=\"true\"></i><h3>" + title +
    "</h3></div><span>" + devices.length + "</span></div><div class=\"bluetoothSectionBody\">" + rows +
    "</div></section>"])
}

function handleDeviceListClick(event) {
  const target = event.target
  const button = target && typeof target.closest === "function"
    ? target.closest("button[data-bluetooth-operation]")
    : null
  if (!button) return
  const operation = button.dataset.bluetoothOperation
  const address = button.dataset.address || ""
  if (operation === "forget" && !window.confirm("Forget " + (button.dataset.deviceName || "this device") + "?")) return
  request(operation, { address })
}

export function Bluetooth() {
  initialize()
  return html`
    <div class="bluetoothPage">
      <div class="bluetoothHeader">
        <div class="bluetoothTitle">
          <i class="bi bi-bluetooth" aria-hidden="true"></i>
          <div>
          <h2>Bluetooth</h2>
          <p>Connect speakers, headphones, media controls, and controllers.</p>
          </div>
        </div>
        <label class="bluetoothSwitch">
          <input type="checkbox" checked="${() => state.enabled}" disabled="${() => !state.available || !state.offroad || !!state.busy}"
                 @change="${(event) => request("power", { enabled: event.target.checked })}" />
          <span>${() => state.busy === "power"
            ? `Turning Bluetooth ${state.powerTarget ? "on" : "off"}…`
            : state.enabled ? "On" : "Off"}</span>
        </label>
      </div>

      ${() => !state.offroad ? html`<div class="bluetoothNotice">Scanning, pairing, and forgetting devices are available offroad only.</div>` : ""}
      ${() => state.error ? html`<div class="bluetoothError">${state.error}</div>` : ""}
      ${pairingPrompt}
      ${() => state.audioTestLabel ? html`
        <div class="bluetoothAudioCountdown">
          <strong>${state.audioTestLabel}</strong>
          <span>The test sound is sent at NOW. The audible gap is Bluetooth latency.</span>
        </div>
      ` : ""}

      <div class="bluetoothToolbar">
        <button disabled="${() => !state.offroad || !state.enabled || !!state.busy}"
                class="${() => state.discovering ? "scanning" : ""}"
                @click="${() => request(state.discovering ? "stop_scan" : "scan")}">
          <i class="${() => `bi ${state.discovering ? "bi-arrow-repeat" : "bi-search"}`}" aria-hidden="true"></i>
          ${() => state.discovering ? "Searching…" : "Search for Devices"}
        </button>
        <button class="bluetoothSecondaryButton" disabled="${() => !!state.busy}" @click="${refresh}">
          <i class="bi bi-arrow-clockwise" aria-hidden="true"></i> Refresh
        </button>
        <span class="bluetoothLiveStatus" aria-live="polite">${() => state.busy ? "Updating…" : state.lastUpdated ? "Live" : ""}</span>
        <span class="bluetoothScanHint">Put a device in pairing mode before searching.</span>
      </div>

      <div class="bluetoothDeviceList" @click="${handleDeviceListClick}">
        ${() => state.loading ? html`<div class="bluetoothLoading"><span></span><span></span><span></span></div>` : ""}
        ${() => !state.loading && !state.enabled ? html`
          <div class="bluetoothEmptyPage">
            <i class="bi bi-bluetooth" aria-hidden="true"></i>
            <h3>Bluetooth is off</h3>
            <p>Turn it on to reconnect saved devices or find something new.</p>
          </div>
        ` : ""}
        ${() => !state.loading && state.enabled
          ? renderDeviceSection("My Devices", "bi-check2-circle", knownDevices(), "No saved devices yet.", state.revision)
          : ""}
        ${() => !state.loading && state.enabled
          ? renderDeviceSection("Available Devices", "bi-radar", availableDevices(), state.discovering ? "Searching for nearby devices…" : "No nearby devices found. Start a search to try again.")
          : ""}
      </div>
    </div>
  `
}
