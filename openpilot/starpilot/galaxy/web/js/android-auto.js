import { BluetoothDeviceList } from "./bluetooth-devices.js"

export function uploadPackage(path, options, progress, makeRequest = () => new XMLHttpRequest()) {
  return new Promise((resolve, reject) => {
    const xhr = makeRequest()
    let settled = false
    const abort = () => xhr.abort()
    const finish = (callback, value) => {
      if (settled) return
      settled = true
      options.signal?.removeEventListener("abort", abort)
      callback(value)
    }
    xhr.open("POST", path)
    xhr.withCredentials = true
    xhr.timeout = 180000
    xhr.setRequestHeader("Content-Type", "application/octet-stream")
    xhr.upload.onprogress = (event) => {
      if (!settled && event.lengthComputable) progress({ loaded: event.loaded, total: event.total })
    }
    xhr.onload = () => finish(resolve, { status: xhr.status, ok: xhr.status >= 200 && xhr.status < 300,
      json: async () => JSON.parse(xhr.responseText) })
    xhr.onerror = () => finish(reject, new Error("Upload interrupted. Check your connection and retry."))
    xhr.ontimeout = () => finish(reject, new Error("Upload timed out. Check your connection and retry."))
    xhr.onabort = () => finish(reject, new Error("Upload canceled."))
    options.signal?.addEventListener("abort", abort, { once: true })
    if (options.signal?.aborted) { finish(reject, new Error("Upload canceled.")); return }
    xhr.send(options.body)
  })
}

const ADDRESS = /^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$/
const PROMPT = new Set(["pin", "passkey", "confirmation", "authorization", "display_pin", "display_passkey"])

export function validPromptInput(prompt, value) {
  if (prompt?.kind === "pin") return /^[\x20-\x7E]{1,16}$/.test(value)
  if (prompt?.kind === "passkey") return /^[0-9]{1,6}$/.test(value)
  return ["confirmation", "authorization"].includes(prompt?.kind) && value === ""
}

export function validPairingStatus(value) {
  if (!value || typeof value.active !== "boolean" || typeof value.approved !== "boolean") return false
  if (value.devices !== undefined && (!Array.isArray(value.devices) || !value.devices.every(validDiscoveredDevice))) return false
  if (value.discovering !== undefined && typeof value.discovering !== "boolean") return false
  if (value.state !== undefined && !["idle", "pairing", "paired", "failed", "connecting", "connected"].includes(value.state)) return false
  if (value.error !== undefined && typeof value.error !== "string") return false
  const receiver = value.receiver
  if (receiver !== null && (!ADDRESS.test(receiver?.address) || typeof receiver.name !== "string" || receiver.name.length > 80)) return false
  const prompt = value.prompt
  return prompt === null || (receiver !== null && /^[0-9a-f]{32}$/.test(prompt?.id) && PROMPT.has(prompt.kind) &&
    typeof prompt.value === "string" && prompt.value.length <= 16 && typeof prompt.displayOnly === "boolean")
}

export function validDiscoveredDevice(value) {
  return value !== null && ADDRESS.test(value?.address) && typeof value.name === "string" && value.name.length <= 80 &&
    ["paired", "connected", "android_auto"].every((key) => typeof value[key] === "boolean")
}

function validSelected(value) {
  return value === null || (ADDRESS.test(value?.address) && typeof value.name === "string" && value.name.length <= 80)
}

function validSetup(value) {
  return value && typeof value.enabled === "boolean" && typeof value.bluetoothEnabled === "boolean" &&
    typeof value.parked === "boolean" && typeof value.installReady === "boolean" && typeof value.serviceReady === "boolean" &&
    value.identity && typeof value.identity.installed === "boolean" && value.import &&
    Number.isSafeInteger(value.maxUploadBytes) && value.maxUploadBytes > 0
}

export class AndroidAutoFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                uploader = uploadPackage, later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, uploader, later, cancelTimer })
    this.active = false
    this.generation = 0
    this.controller = null
    this.timer = null
    this.pollTimer = null
    this.setup = null
    this.pairing = null
    this.selected = null
    this.runtime = null
    this.receivers = []
    this.endReason = ""
    this.busy = false
    this.refreshing = false
    this.deviceList = new BluetoothDeviceList()
    this.receiverList = new BluetoothDeviceList()
    this.uploadProgress = null
    this.error = ""
  }

  emit() { this.publish({ setup: this.setup, pairing: this.pairing, selected: this.selected, runtime: this.runtime,
    receivers: this.receivers,
    endReason: this.endReason, busy: this.busy, uploadProgress: this.uploadProgress, error: this.error }) }

  stop(cancelPair = false) {
    if (cancelPair && this.active && this.pairing?.active) {
      this.fetcher("./api/android-auto/pairing/cancel", { method: "POST", credentials: "same-origin", keepalive: true,
        headers: { "Content-Type": "application/json" }, body: "{}" }).catch(() => {})
    }
    this.active = false
    this.generation++
    this.controller?.abort()
    if (this.timer !== null) this.cancelTimer(this.timer)
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    this.controller = this.timer = this.pollTimer = null
    this.busy = false
    this.refreshing = false
    this.deviceList.reset()
    this.receiverList.reset()
    this.uploadProgress = null
    this.pairing = null
    this.emit()
  }

  start() {
    this.stop()
    this.active = true
    return this.refresh()
  }

  async request(path, options = {}, timeout = 8000, transport = this.fetcher, background = false) {
    if (!background) {
      // A user action supersedes a pending poll, including a delayed JSON body.
      this.generation++
      this.controller?.abort()
      if (this.timer !== null) this.cancelTimer(this.timer)
      if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
      this.pollTimer = null
      this.refreshing = false
    }
    const generation = this.generation
    const controller = new AbortController()
    this.controller = controller
    if (!background) { this.busy = true; this.emit() }
    let timedOut = false
    this.timer = this.later(() => { timedOut = true; controller.abort() }, timeout)
    try {
      const response = await transport(path, { ...options, credentials: "same-origin", cache: "no-store", signal: controller.signal })
      if (!this.active || this.generation !== generation || controller.signal.aborted) return null
      if (response.status === 401) { this.stop(); this.unauthorized(); return null }
      const data = await response.json()
      if (!this.active || this.generation !== generation || controller.signal.aborted) return null
      if (!response.ok) throw new Error(data?.error || "Android Auto setup is unavailable")
      this.error = ""
      return data
    } catch (error) {
      if (this.active && this.generation === generation) {
        this.error = timedOut ? "Android Auto took too long to respond. Try again." :
          error instanceof Error ? error.message : "Android Auto setup is unavailable"
      }
      return null
    } finally {
      if (this.controller === controller) {
        this.cancelTimer(this.timer)
        this.controller = this.timer = null
        if (!background) {
          this.busy = false
          if (this.active && this.generation === generation && this.pollTimer === null) {
            this.pollTimer = this.later(() => this.refresh(), this.pairing?.active ? 1000 : 5000)
          }
        }
        this.emit()
      }
    }
  }

  async refresh() {
    if (!this.active || this.busy || this.refreshing) return
    this.refreshing = true
    if (this.pollTimer !== null) { this.cancelTimer(this.pollTimer); this.pollTimer = null }
    const generation = this.generation
    const setup = await this.request("./api/android-auto/setup", {}, 8000, this.fetcher, true)
    if (!this.active || this.generation !== generation) return
    const setupValid = setup && validSetup(setup)
    if (setupValid) this.setup = setup
    else if (setup) this.error = "Android Auto setup response changed"
    if (setupValid && !setup.enabled) {
      this.pairing = this.selected = this.runtime = null
      this.receivers = []
      this.deviceList.reset()
      this.receiverList.reset()
      this.emit()
    }
    if (this.active && this.generation === generation && setupValid && setup.enabled) {
      const result = await this.request("./api/android-auto/pairing/status", {}, 8000, this.fetcher, true)
      if (!this.active || this.generation !== generation) return
      if (result && validPairingStatus(result.pairing) && validSelected(result.selectedReceiver)) {
        const wasActive = this.pairing?.active
        if (!result.pairing.active) this.deviceList.reset()
        this.pairing = { ...result.pairing, devices: this.deviceList.update(result.pairing.devices || []) }
        this.selected = result.selectedReceiver
        this.runtime = result.runtime && typeof result.runtime === "object" ? result.runtime : null
        if (wasActive && !this.pairing.active && !this.selected && !this.endReason) this.endReason = "ended"
      }
      else if (result) this.error = "Pairing status response changed"
    }
    this.refreshing = false
    this.emit()
    if (this.active && this.generation === generation) {
      const delay = this.pairing?.active || this.setup?.import?.state === "running" ? 1000 : 5000
      this.pollTimer = this.later(() => this.refresh(), delay)
    }
  }

  async action(path, body = {}, timeout = 12000) {
    if (!this.active || this.busy || !this.setup?.parked || !this.setup?.enabled) return false
    const result = await this.request(path, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) }, timeout)
    if (result === null) return false
    if (path.endsWith('/pairing')) this.endReason = ""
    if (path.endsWith('/cancel')) this.endReason = "canceled"
    await this.refresh()
    return true
  }

  async selectDevice(address) {
    if (!ADDRESS.test(address) || !this.pairing?.active || this.pairing?.prompt ||
        ["pairing", "connecting"].includes(this.pairing?.state) || this.runtime?.running ||
        !this.pairing?.devices?.some((device) => device.address === address)) return false
    return this.action("./api/android-auto/pairing/select", { address })
  }

  async loadReceivers() {
    if (!this.active || this.busy || !this.setup?.enabled || this.pairing?.active) return false
    const result = await this.request("./api/android-auto/receivers")
    if (result === null) return false
    if (!Array.isArray(result.receivers) || !result.receivers.every((car) => car !== null && validSelected(car))) {
      this.error = "Paired car list changed"
      this.emit()
      return false
    }
    this.receivers = this.receiverList.update(result.receivers)
    this.emit()
    return true
  }

  async control(action, extra = {}) {
    if (!this.active || this.busy || !this.setup?.enabled || this.pairing?.active ||
        !["start", "stop", "select_receiver", "auto_connect"].includes(action)) return false
    const result = await this.request("./api/android-auto/control", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, ...extra }) })
    if (result === null) return false
    await this.refresh()
    return true
  }

  async setEnabled(enabled) {
    if (!this.active || this.busy || typeof enabled !== "boolean" ||
        enabled && (!this.setup?.parked || !this.setup?.installReady)) return false
    const result = await this.request("./api/android-auto/enable", { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled }) })
    if (result === null) return false
    await this.refresh()
    return true
  }

  async upload(file) {
    if (!this.active || this.busy || !this.setup?.parked || !this.setup?.enabled ||
        !file || !Number.isSafeInteger(file.size) || file.size <= 0 || file.size > this.setup.maxUploadBytes) {
      this.error = "Choose an APK, XAPK, or APKM within the shown size limit."
      this.emit()
      return false
    }
    this.uploadProgress = { loaded: 0, total: file.size }
    const generation = this.generation + 1
    const transport = (path, options) => this.uploader(path, options, (progress) => {
      if (this.active && generation === this.generation) { this.uploadProgress = progress; this.emit() }
    })
    const result = await this.request("./api/android-auto/upload", { method: "POST",
      headers: { "Content-Type": "application/octet-stream" }, body: file }, 180000, transport)
    this.uploadProgress = null
    this.emit()
    if (result === null) return false
    await this.refresh()
    return true
  }

  async removePackage() {
    if (!this.active || this.busy || !this.setup?.parked || !this.setup?.enabled ||
        this.setup.import?.state === "running" || this.runtime?.running) return false
    const result = await this.request("./api/android-auto/identity", { method: "DELETE" })
    if (result === null) return false
    await this.refresh()
    return true
  }
}

export const AndroidAutoPage = {
  props: { mode: { type: String, required: true }, localAccess: { type: Boolean, required: true },
    unauthorized: { type: Function, required: true } },
  data: () => ({ setup: null, pairing: null, selected: null, runtime: null, receivers: [], endReason: "", busy: false, error: "",
    pairValue: "", packageFile: null, uploadProgress: null }),
  mounted() {
    this.feed = new AndroidAutoFeed({ publish: (value) => Object.assign(this, value), unauthorized: this.unauthorized })
    this.visibility = () => document.hidden ? this.feed.stop(true) : this.feed.start()
    document.addEventListener("visibilitychange", this.visibility)
    if (!document.hidden) this.feed.start()
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibility); this.feed?.stop(true) },
  watch: {
    mode() { if (!document.hidden) this.feed?.start(); else this.feed?.stop(true) },
    localAccess() { if (!document.hidden) this.feed?.start(); else this.feed?.stop(true) },
    'pairing.prompt.id'() { this.pairValue = "" },
  },
  computed: {
    canRespond() { return validPromptInput(this.pairing?.prompt, this.pairValue) },
    packageError() {
      if (!this.packageFile) return ""
      if (!Number.isSafeInteger(this.packageFile.size) || this.packageFile.size <= 0) return "The selected file is empty or its size cannot be read."
      if (this.setup && this.packageFile.size > this.setup.maxUploadBytes) return "The selected package exceeds the maximum size shown below."
      return ""
    },
    uploadReason() {
      if (!this.packageFile) return "Choose your Android Auto package."
      if (this.packageError) return this.packageError
      if (!this.setup?.parked) return "Use offroad mode or Park to upload your package."
      if (!this.setup.enabled && !this.setup.installReady) return "The Android Auto display and encoder must be installed before uploading."
      if (this.setup.import?.state === "running") return "Wait for the current package verification to finish."
      if (this.busy) return "Waiting for Android Auto setup to respond…"
      return ""
    },
    hasPackage() { return !!(this.setup?.identity.installed || this.setup?.identity.expired || this.setup?.identity.error) },
    removeReason() {
      if (!this.setup?.parked) return "Use offroad mode or Park to delete the package."
      if (!this.setup.enabled) return "Enable Android Auto to delete the package."
      if (this.setup.import?.state === "running") return "Wait for the current package verification to finish."
      if (this.runtime?.running) return "Stop projection before deleting the package."
      return ""
    },
    pairingReason() {
      if (!this.setup) return "Load setup status first."
      if (!this.setup.installReady) return "This build is missing the Android Auto display or encoder."
      if (!this.setup.enabled) return "Enable Android Auto in Prepare."
      if (!this.setup.serviceReady) return "Waiting for the Android Auto service to start."
      if (!this.setup.bluetoothEnabled) return "Turn on Bluetooth on the Bluetooth page."
      if (!this.setup.parked) return "Use offroad mode or Park before starting pairing."
      if (!this.setup.identity.installed) return "Upload and verify your Android Auto package in Prepare."
      if (this.runtime?.running) return "Stop projection before searching or pairing."
      return ""
    },
    waitingForCar() { return this.pairing?.active && !this.pairing?.receiver && !this.pairing?.prompt && !this.pairing?.approved &&
      !["pairing", "connecting", "paired", "connected", "failed"].includes(this.pairing?.state) },
    deviceSelectionBlocked() { return this.busy || !!this.pairingReason || !this.pairing?.active ||
      !!this.pairing?.prompt || ["pairing", "connecting"].includes(this.pairing?.state) || !!this.runtime?.running },
  },
  methods: {
    refresh() { return this.feed.refresh() },
    setEnabled(enabled) { return this.feed.setEnabled(enabled) },
    startPairing() {
      if (this.pairingReason || this.runtime?.running) return false
      return this.feed.action("./api/android-auto/pairing")
    },
    selectDevice(address) { return this.feed.selectDevice(address) },
    cancelPairing() { return this.feed.action("./api/android-auto/pairing/cancel") },
    respond(accepted) {
      const prompt = this.pairing?.prompt
      if (!prompt || prompt.displayOnly || accepted && !this.canRespond) return
      const value = accepted && ["pin", "passkey"].includes(prompt.kind) ? this.pairValue : ""
      return this.feed.action("./api/android-auto/pairing/response", { prompt_id: prompt.id, accepted, value })
    },
    choosePackage(event) { this.packageFile = event.target.files?.[0] || null },
    async upload() {
      if (this.uploadReason) return false
      const file = this.packageFile
      if (!this.setup.enabled && !await this.feed.setEnabled(true)) return false
      return this.feed.upload(file)
    },
    removePackage() {
      if (this.removeReason) return false
      if (!window.confirm("Delete the Android Auto package and its certificate from this device? Projection will not start until you upload a package again.")) return false
      return this.feed.removePackage()
    },
    loadReceivers() { return this.feed.loadReceivers() },
    control(action, extra = {}) { return this.feed.control(action, extra) },
  },
  template: `
    <section class="gx-driving" aria-label="Android Auto setup">
      <div class="gx-card gx-driving__intro"><h2>Android Auto</h2>
        <p>Show StarPilot on your car’s wireless Android Auto display. Enable projection, upload your Android Auto package, then find your car or wireless adapter. Setup works here over local or remote Galaxy.</p></div>
      <div class="gx-android-auto-setup">
        <p v-if="error" class="gx-card gx-message" role="alert">{{ error }}</p>
        <div v-if="!setup" class="gx-card gx-message" role="status">{{ error ? "Setup could not be loaded." : "Checking Android Auto setup…" }} <button class="gx-btn gx-btn--tonal" :disabled="busy" @click="refresh">Retry</button></div>
        <template v-else>
          <div class="gx-card gx-driving__intro"><h3>1. Prepare</h3>
            <p v-if="!setup.installReady" role="status">Android Auto display and encoder are not installed on this build. Projection setup is unavailable.</p>
            <p v-else-if="setup.enabled && !setup.serviceReady" role="status">Starting the Android Auto service. Pairing is unavailable until it is ready.</p>
            <div class="gx-driving__actions"><button class="gx-btn" :disabled="busy || !setup.parked || !setup.installReady" v-if="!setup.enabled" @click="setEnabled(true)">Enable Android Auto</button>
              <button class="gx-btn gx-btn--tonal" :disabled="busy" v-else @click="setEnabled(false)">Turn Off Android Auto</button></div>
            <p v-if="!setup.bluetoothEnabled">Open <a href="/bluetooth">Bluetooth</a> and turn it on before pairing.</p>
            <p v-if="!setup.parked">Use offroad mode or Park to upload a package or pair your car.</p>
            <p>{{ setup.identity.message || (setup.identity.installed ? 'Your Android Auto package is ready.' : 'Upload your Android Auto APK, XAPK, or APKM.') }}</p>
            <details><summary>Where do I get the Android Auto package?</summary>
              <ol>
                <li>Open <a href="https://www.apkmirror.com/apk/google-inc/android-auto/" target="_blank" rel="noopener noreferrer">Android Auto by Google LLC on APKMirror</a>, a third-party download site.</li>
                <li>Download the Android Auto app package to this phone or computer. Choose the app's APK or bundle download; you do not need the APKMirror Installer app.</li>
                <li>Return here, choose the downloaded APK, XAPK, or APKM file, and press Upload Package. Leave bundles zipped.</li>
              </ol>
              <p>You do not install an Android app on the comma. Galaxy imports the information needed to connect to your car and checks that it is usable.</p>
            </details>
            <p v-if="setup.identity.warning" role="status">{{ setup.identity.warning }}</p>
            <p v-if="setup.import?.state === 'running'" role="status">Checking your package…</p>
            <p v-if="setup.import?.state === 'failed'" role="alert">Package verification failed: {{ setup.import.error || 'Try another package.' }}</p>
            <p v-if="setup.import?.state === 'done' && setup.identity.installed" role="status">Package verified and ready.</p>
            <div v-if="hasPackage" class="gx-driving__actions"><button class="gx-btn gx-btn--tonal" :disabled="busy || !!removeReason" :title="removeReason" @click="removePackage">Delete Package</button></div>
            <p v-if="hasPackage && removeReason && setup.import?.state !== 'running'" class="gx-muted">{{ removeReason }}</p>
            <div class="gx-driving__actions"><input type="file" accept=".apk,.xapk,.apkm" style="max-width:100%;min-width:0" aria-label="Android Auto APK, XAPK, or APKM" @change="choosePackage" />
              <button class="gx-btn" :disabled="!!uploadReason" @click="upload">{{ setup.enabled ? 'Upload Package' : 'Enable and Upload Package' }}</button></div>
            <p v-if="packageFile" role="status">Selected: {{ packageFile.name }} ({{ Math.ceil(packageFile.size / 1048576) }} MB).</p>
            <div v-if="uploadProgress" role="status" aria-live="polite">
              <progress :value="uploadProgress.loaded" :max="uploadProgress.total"></progress>
              Uploading {{ Math.round(100 * uploadProgress.loaded / uploadProgress.total) }}%
            </div>
            <p v-if="uploadReason" :role="packageError ? 'alert' : 'status'">{{ uploadReason }}</p>
            <small>Maximum package size: {{ Math.floor(setup.maxUploadBytes / 1048576) }} MB. Your package stays on this device.</small>
          </div>
          <div class="gx-card gx-driving__intro"><h3>2. Find and Pair</h3>
            <p>Using a wireless Android Auto adapter? Pair with your vehicle first, then pair with the adapter. Select the adapter to start projection.</p>
            <p>Look for an adapter name such as AndroidAuto-XXXX. Keep your vehicle paired for calls.</p>
            <p v-if="!setup.identity.installed">Finish package verification before pairing.</p>
            <p v-else-if="!pairing?.active && selected">Saved Android Auto receiver: {{ selected.name }}. Find a car or wireless adapter in offroad mode or Park.</p>
            <p v-else-if="!pairing?.active && endReason === 'canceled'">Pairing canceled. Start again when your car is ready.</p>
            <p v-else-if="!pairing?.active && endReason">The pairing window ended without selecting a car. Try again in offroad mode or Park.</p>
            <p v-else-if="!pairing?.active">Open your car’s phone pairing screen or put your wireless adapter in pairing mode, then find it here.</p>
            <p v-else-if="waitingForCar" role="status">{{ pairing.discovering ? "Searching nearby Bluetooth devices…" : "Search is open. Choose your car or wireless adapter below." }}</p>
            <p v-else-if="pairing.approved && (!pairing.state || pairing.state === 'idle')" role="status">Approved {{ pairing.receiver?.name }}. Waiting for Bluetooth pairing to finish…</p>
            <p v-if="pairing?.state === 'pairing' && !pairing.prompt && !pairing.approved" role="status">Pairing with {{ pairing.receiver?.name || 'the selected device' }}…</p>
            <p v-if="pairing?.state === 'connecting'" role="status">Connecting to {{ pairing.receiver?.name || 'the selected device' }}…</p>
            <p v-if="['paired', 'connected'].includes(pairing?.state)" role="status">{{ pairing.receiver?.name || 'Device' }} {{ pairing.state === 'connected' ? 'connected' : 'paired' }} over Bluetooth.</p>
            <p v-if="pairing?.error" role="alert">{{ pairing.error }}</p>
            <div v-if="pairing?.active" style="display:grid;gap:10px;margin:16px 0;min-width:0">
              <p v-if="!pairing.devices?.length && waitingForCar" role="status">No devices found yet. Keep the car or adapter’s pairing screen open.</p>
              <div v-for="device in pairing.devices || []" :key="device.address" style="display:flex;flex-wrap:wrap;align-items:center;gap:10px">
                <span><strong>{{ device.name }}</strong><br />{{ device.android_auto ? 'Wireless Android Auto advertised' : 'Bluetooth device; Android Auto capability not yet advertised' }}<br />{{ device.connected ? 'Connected' : device.paired ? 'Saved Bluetooth pairing' : 'Nearby' }}</span>
                <button class="gx-btn gx-btn--tonal" :disabled="deviceSelectionBlocked" @click="selectDevice(device.address)">{{ device.paired ? 'Connect' : 'Pair' }}</button>
              </div>
              <small>Bluetooth pairing alone does not confirm Android Auto support.</small>
            </div>
            <div v-if="pairing?.prompt" role="status" style="display:grid;gap:10px;margin:16px 0;min-width:0"><strong>{{ pairing.receiver.name }}</strong>
              <p>{{ pairing.prompt.kind === 'confirmation' ? 'Check that this code matches your car, then confirm.' :
                pairing.prompt.kind === 'pin' ? 'Enter the PIN shown by your car.' :
                pairing.prompt.kind === 'passkey' ? 'Enter your car’s passkey.' :
                pairing.prompt.kind === 'authorization' ? 'Allow this car to pair?' : 'Enter this code in your car.' }}</p>
              <strong v-if="pairing.prompt.value" style="font-size:1.3rem;letter-spacing:.1em">{{ pairing.prompt.value }}</strong>
              <input v-if="['pin','passkey'].includes(pairing.prompt.kind)" class="gx-field" type="text" maxlength="16" autocomplete="off"
                :inputmode="pairing.prompt.kind === 'passkey' ? 'numeric' : 'text'" :aria-label="pairing.prompt.kind === 'pin' ? 'Car PIN' : 'Car passkey'" v-model="pairValue" />
              <div v-if="!pairing.prompt.displayOnly" class="gx-driving__actions">
                <button class="gx-btn gx-btn--tonal" :disabled="busy" @click="respond(false)">Reject</button>
                <button class="gx-btn" :disabled="busy || !canRespond" @click="respond(true)">{{ pairing.prompt.kind === 'pin' ? 'Send PIN' : pairing.prompt.kind === 'passkey' ? 'Send Passkey' : 'Confirm' }}</button></div>
            </div>
            <p v-if="!pairing?.active && pairingReason" role="status">{{ pairingReason }}</p>
            <p v-if="selected && !pairing?.active" class="gx-muted">For a wireless adapter, connect your paired car in Galaxy Bluetooth first. That car is saved for automatic reconnection before the adapter starts.</p>
            <p v-if="runtime?.companion_name" class="gx-muted">Car: {{ runtime.companion_name }}</p>
            <div class="gx-driving__actions"><button v-if="!pairing?.active" class="gx-btn" :disabled="busy || !!pairingReason" @click="startPairing">Find Car or Adapter</button>
              <button v-else class="gx-btn gx-btn--tonal" :disabled="busy" @click="cancelPairing">Cancel Search / Pairing</button>
              <button class="gx-btn gx-btn--tonal" :disabled="busy" @click="refresh">Refresh</button></div>
          </div>
          <div class="gx-card gx-driving__intro"><h3>3. Connect</h3>
            <p v-if="selected">Selected Android Auto receiver: {{ selected.name }}.</p>
            <p v-else>Select a paired Android Auto car before connecting.</p>
            <p v-if="runtime?.state">Projection: {{ runtime.state }}<span v-if="runtime.detail"> — {{ runtime.detail }}</span>.</p>
            <div class="gx-driving__actions">
              <button class="gx-btn gx-btn--tonal" :disabled="busy || !setup.enabled || !setup.serviceReady || !setup.parked || pairing?.active" @click="loadReceivers">Find Paired Cars</button>
              <button v-for="car in receivers" :key="car.address" class="gx-btn gx-btn--tonal"
                :disabled="busy || !setup.parked || pairing?.active || runtime?.running || selected?.address === car.address"
                @click="control('select_receiver', { address: car.address })">Select {{ car.name }}</button>
            </div>
            <div class="gx-driving__actions">
              <button v-if="!runtime?.running" class="gx-btn" :disabled="busy || !selected || !setup.enabled || !setup.serviceReady || !setup.identity.installed || pairing?.active" @click="control('start')">Start Projection</button>
              <button v-else class="gx-btn gx-btn--tonal" :disabled="busy" @click="control('stop')">Stop Projection</button>
              <button class="gx-btn gx-btn--tonal" :disabled="busy || !setup.parked || pairing?.active"
                @click="control('auto_connect', { enabled: !runtime?.auto_connect })">Automatic Connection: {{ runtime?.auto_connect ? 'On' : 'Off' }}</button>
            </div>
            <p>Wired USB setup is unavailable.</p>
            <p>If this device's video encoder cannot start, projection stops and reports the error here.</p>
            <p>Projection support still needs validation with your car and this device.</p></div>
        </template>
      </div>
    </section>`,
}
