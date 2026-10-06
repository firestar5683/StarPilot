import { GxIconButton } from "./icon-button.js"
import { requestJson } from "./startup.js"
import { GxNotice } from "./notice.js"
import { connectionError } from "./polling.js"
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
    xhr.onload = () => finish(resolve, {
      status: xhr.status, ok: xhr.status >= 200 && xhr.status < 300,
      json: async () => JSON.parse(xhr.responseText)
    })
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
  constructor({ publish, unauthorized = () => { }, fetcher = (...args) => fetch(...args),
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

  emit() {
    this.publish({
      setup: this.setup, pairing: this.pairing, selected: this.selected, runtime: this.runtime,
      receivers: this.receivers,
      endReason: this.endReason, busy: this.busy, uploadProgress: this.uploadProgress, error: this.error
    })
  }

  stop(cancelPair = false) {
    if (cancelPair && this.active && this.pairing?.active) {
      this.fetcher("./api/android-auto/pairing/cancel", {
        method: "POST", credentials: "same-origin", keepalive: true,
        headers: { "Content-Type": "application/json" }, body: "{}"
      }).catch(() => { })
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
    try {
      const { response, data } = await requestJson(path, {
        fetcher: transport, timeout, later: this.later, cancel: this.cancelTimer,
        request: { ...options, signal: controller.signal }, withResponse: true
      })
      if (!this.active || this.generation !== generation || controller.signal.aborted) return null
      if (response.status === 401) { this.stop(); this.unauthorized(); return null }
      if (!this.active || this.generation !== generation || controller.signal.aborted) return null
      if (!response.ok) throw new Error(data?.error || "Android Auto setup is unavailable")
      if (!background) this.error = ""
      return data
    } catch (error) {
      if (this.active && this.generation === generation) {
        this.error = error.name === "TimeoutError" ? "Android Auto took too long to respond. Reconnecting automatically…" : connectionError(error)
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
    let healthy = !!setupValid
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
      else { healthy = false; if (result) this.error = "Pairing status response changed" }
    }
    this.refreshing = false
    if (healthy) this.error = ""
    this.emit()
    if (this.active && this.generation === generation) {
      const delay = this.pairing?.active || this.setup?.import?.state === "running" ? 1000 : 5000
      this.pollTimer = this.later(() => this.refresh(), delay)
    }
  }

  async action(path, body = {}, timeout = 12000) {
    if (!this.active || this.busy || !this.setup?.parked || !this.setup?.enabled) return false
    const result = await this.request(path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }, timeout)
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
    const result = await this.request("./api/android-auto/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, ...extra })
    })
    if (result === null) return false
    await this.refresh()
    return true
  }

  async setEnabled(enabled) {
    if (!this.active || this.busy || typeof enabled !== "boolean" ||
      enabled && (!this.setup?.parked || !this.setup?.installReady)) return false
    const result = await this.request("./api/android-auto/enable", {
      method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ enabled })
    })
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
    const result = await this.request("./api/android-auto/upload", {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" }, body: file
    }, 180000, transport)
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

export const APKMIRROR_URL = "https://www.apkmirror.com/apk/google-inc/android-auto/"
const KNOWN_GOOD_VERSION = "17.6.663454-release"
const STAGES = ["reading", "searching", "decrypting", "verifying", "installing", "done"]
const CHECKS = [
  { stage: "reading", codes: ["NOT_PACKAGE", "CORRUPT", "NO_CODE", "TOO_LARGE"], label: "Android package opened" },
  { stage: "searching", codes: ["WRONG_APP", "UNVERIFIED"], label: "Google Automotive Link certificate found" },
  { stage: "decrypting", codes: ["UNSUPPORTED_VERSION"], label: "Security key unlocked" },
  { stage: "verifying", codes: ["EXPIRED", "NOT_YET_VALID"], label: "Certificate is valid" },
]

// Certificate dates are UTC instants; showing them in UTC keeps "valid until" on the day the car checks.
export function formatDate(iso, options = { month: "short", day: "numeric", year: "numeric" }, locale = undefined) {
  const date = new Date(iso)
  return typeof iso !== "string" || Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString(locale, { timeZone: "UTC", ...options })
}

export function expiryInfo(identity, locale = undefined) {
  if (identity?.installed) {
    const days = Number.isSafeInteger(identity.days_left) ? identity.days_left : null
    if (days !== null && days <= 14) {
      const day = formatDate(identity.expires, { month: "short", day: "numeric" }, locale)
      const left = days <= 0 ? "Expires within a day" : `Expires in ${days} day${days === 1 ? "" : "s"}`
      return { level: "soon", label: day ? `${left} (${day})` : left }
    }
    const until = formatDate(identity.expires, undefined, locale)
    return { level: "ready", label: until ? `Ready · Valid until ${until}` : "Ready" }
  }
  if (identity?.expired) {
    const on = formatDate(identity.expires, undefined, locale)
    return { level: "expired", label: on ? `Expired on ${on}` : "Expired" }
  }
  if (identity?.error) return { level: "broken", label: "Needs reinstalling" }
  return { level: "none", label: "Not set up" }
}

// Name-only checks that catch the common wrong downloads before a long upload.
// APKMirror names the real app "…-apkmirror.com.apk", so "apkmirror" alone is fine.
export function packagePreflight(file) {
  const name = typeof file?.name === "string" ? file.name : ""
  if (/installer|apkmirror\.helper/i.test(name)) {
    return "This is the APKMirror Installer app, not Android Auto. Go back and tap Download APK on the Android Auto page itself."
  }
  if (/com\.google\.android\.gms|play[ ._-]?services/i.test(name)) {
    return "This is Google Play Services, not Android Auto. Go back and download Android Auto by Google LLC."
  }
  if (name && !/\.(apk|xapk|apkm)$/i.test(name)) return "That’s not an Android package. Choose the .apk, .xapk, or .apkm file you downloaded."
  return ""
}

export function importProblem(job, fileName = "", locale = undefined) {
  if (job?.state !== "failed") return ""
  switch (job.code) {
    case "NOT_PACKAGE": case "CORRUPT":
      return "This file looks incomplete or damaged. Download it again and wait for the download to finish."
    case "NO_CODE": return "This file is only part of the app. Download the full Android Auto APK, or the XAPK/APKM bundle."
    case "WRONG_APP":
      return packagePreflight({ name: fileName }) ||
        `Wrong app selected${fileName ? ` (${fileName})` : ""}. Choose Android Auto by Google LLC.`
    case "UNVERIFIED": return "This package isn’t signed for Android Auto. The file must be the official Android Auto app from Google."
    case "EXPIRED": {
      const on = formatDate(job.expires, undefined, locale)
      return `This Android Auto version expired${on ? ` on ${on}` : ""}. Download a newer stable release.`
    }
    case "NOT_YET_VALID": return "This version isn’t valid yet. Check that the comma’s date and time are correct."
    case "UNSUPPORTED_VERSION":
      return `This version stores its key differently. Download version ${KNOWN_GOOD_VERSION}, or another release known to work.`
    case "TOO_LARGE": return "This file is too large to be the Android Auto app."
    case "CANCELLED": return "Setup stopped because Android Auto was turned off. Try again."
    default: return job.error || "Something went wrong. Try again."
  }
}

export function installChecks(job, locale = undefined) {
  const at = job?.state === "done" ? STAGES.length : STAGES.indexOf(job?.stage)
  const ends = CHECKS.map((_, index) => STAGES.indexOf(index + 1 < CHECKS.length ? CHECKS[index + 1].stage : "done"))
  let failed = -1
  if (job?.state === "failed") {
    failed = CHECKS.findIndex((check) => check.codes.includes(job.code))
    if (failed < 0) failed = Math.max(0, ends.findIndex((end) => at < end))
  }
  return CHECKS.map((check, index) => {
    const label = index === CHECKS.length - 1 && job?.state === "done" && formatDate(job.expires, undefined, locale) ?
      `Certificate valid until ${formatDate(job.expires, { month: "long", day: "numeric", year: "numeric" }, locale)}` : check.label
    const status = failed >= 0 ? (index < failed ? "done" : index === failed ? "failed" : "pending") :
      at >= ends[index] ? "done" : at >= STAGES.indexOf(check.stage) ? "active" : "pending"
    return { label, status }
  })
}

export const AndroidAutoPage = {
  components: { GxIconButton, GxNotice },
  props: {
    mode: { type: String, required: true }, localAccess: { type: Boolean, required: true },
    unauthorized: { type: Function, required: true }
  },
  data: () => ({
    setup: null, pairing: null, selected: null, runtime: null, receivers: [], endReason: "", busy: false, error: "",
    pairValue: "", packageFile: null, uploadProgress: null, installOpen: false, removeOpen: false, installAttempted: false, installBaseline: null,
    installFileName: "", apkmirror: APKMIRROR_URL, pairWhenReady: false
  }),
  mounted() {
    this.feed = new AndroidAutoFeed({ publish: (value) => Object.assign(this, value), unauthorized: this.unauthorized })
    this.visibility = () => document.hidden ? this.feed.stop(true) : this.begin()
    document.addEventListener("visibilitychange", this.visibility)
    if (!document.hidden) this.begin()
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibility); this.feed?.stop(true) },
  watch: {
    mode() { if (!document.hidden) this.begin(); else this.feed?.stop(true) },
    localAccess() { if (!document.hidden) this.begin(); else this.feed?.stop(true) },
    'pairing.prompt.id'() { this.pairValue = "" },
    'pairing.active'(active, was) { if (was && !active) this.loadReceivers() },
    // Find My Car on a fresh device turns Android Auto on first, then searches once the service is up.
    'setup.serviceReady'(ready) { if (ready && this.pairWhenReady) { this.pairWhenReady = false; this.startPairing() } },
  },
  computed: {
    canRespond() { return validPromptInput(this.pairing?.prompt, this.pairValue) },
    expiry() { return expiryInfo(this.setup?.identity) },
    supportReady() { return !!(this.setup?.enabled && this.setup.identity.installed) },
    packageError() {
      if (!this.packageFile) return ""
      const preflight = packagePreflight(this.packageFile)
      if (preflight) return preflight
      if (!Number.isSafeInteger(this.packageFile.size) || this.packageFile.size <= 0) return "The selected file is empty or its size cannot be read."
      if (this.setup && this.packageFile.size > this.setup.maxUploadBytes) return "The selected package exceeds the maximum size shown below."
      return ""
    },
    uploadReason() {
      if (!this.packageFile) return "Choose your Android Auto package."
      if (this.packageError) return this.packageError
      if (!this.setup?.parked) return "Use offroad mode or Park to install Android Auto support."
      if (!this.setup.enabled && !this.setup.installReady) return "The Android Auto display and encoder must be installed before uploading."
      if (this.setup.import?.state === "running") return "Wait for the current package check to finish."
      if (this.busy) return "Waiting for Android Auto setup to respond…"
      return ""
    },
    installState() {
      const job = this.setup?.import
      const current = this.installAttempted && job && job.started !== this.installBaseline
      if (this.uploadProgress || this.installAttempted && this.busy && !current) return "uploading"
      if (job?.state === "running") return "checking"
      if (!current) return "choose"
      if (job.state === "done" && this.setup.identity.installed) return "done"
      return job.state === "failed" ? "failed" : "choose"
    },
    checks() { return installChecks(this.setup?.import) },
    problem() { return importProblem(this.setup?.import, this.installFileName) },
    hasPackage() { return !!(this.setup?.identity.installed || this.setup?.identity.expired || this.setup?.identity.error) },
    removeReason() {
      if (!this.setup?.parked) return "Use offroad mode or Park to delete the package."
      if (!this.setup.enabled) return "Enable Android Auto to delete the package."
      if (this.setup.import?.state === "running") return "Wait for the current package check to finish."
      if (this.runtime?.running) return "Disconnect from your car before deleting the package."
      return ""
    },
    // Bluetooth pairing and the car's Wi-Fi handoff need no Android Auto package; only projection does.
    pairingReason() {
      if (!this.setup) return "Load setup status first."
      if (!this.setup.installReady) return "This build is missing the Android Auto display or encoder."
      if (this.setup.enabled && !this.setup.serviceReady) return "Waiting for the Android Auto service to start."
      if (!this.setup.bluetoothEnabled) return "Turn on Bluetooth on the Bluetooth page."
      if (!this.setup.parked) return "Use offroad mode or Park before starting pairing."
      if (this.runtime?.running) return "Disconnect from your car before pairing."
      return ""
    },
    connectReason() {
      if (!this.selected) return "Pair your car in step 2 first."
      if (!this.setup?.enabled) return "Turn on Android Auto Support in step 1."
      if (!this.setup.serviceReady) return "Waiting for the Android Auto service to start."
      if (this.pairing?.active) return "Finish or cancel pairing first."
      return ""
    },
    waitingForCar() {
      return this.pairing?.active && !this.pairing?.receiver && !this.pairing?.prompt && !this.pairing?.approved &&
        !["pairing", "connecting", "paired", "connected", "failed"].includes(this.pairing?.state)
    },
    deviceSelectionBlocked() {
      return this.busy || !!this.pairingReason || !this.pairing?.active ||
        !!this.pairing?.prompt || ["pairing", "connecting"].includes(this.pairing?.state) || !!this.runtime?.running
    },
  },
  methods: {
    async begin() {
      await this.feed.start()
      if (this.setup?.enabled && this.setup.serviceReady && !this.pairing?.active) this.loadReceivers()
    },
    refresh() { return this.feed.refresh() },
    setEnabled(enabled) { return this.feed.setEnabled(enabled) },
    startPairing() {
      if (this.pairingReason || this.runtime?.running) return false
      if (!this.setup.enabled) return this.feed.setEnabled(true).then((enabled) => { this.pairWhenReady = enabled; return false })
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
    openInstall() {
      Object.assign(this, { installOpen: true, installAttempted: false, packageFile: null })
      this.$nextTick?.(() => this.$refs.installDialog?.focus())
    },
    closeInstall() { this.installOpen = false },
    chooseAgain() { Object.assign(this, { installAttempted: false, packageFile: null }) },
    choosePackage(event) { this.packageFile = event.target.files?.[0] || null },
    async upload() {
      if (this.uploadReason) return false
      const file = this.packageFile
      Object.assign(this, { installAttempted: true, installBaseline: this.setup.import?.started ?? null, installFileName: file.name || "" })
      if (!this.setup.enabled && !await this.feed.setEnabled(true)) { this.installAttempted = false; return false }
      return this.feed.upload(file)
    },
    openRemove() { if (!this.removeReason) this.removeOpen = true },
    closeRemove() { this.removeOpen = false },
    async removePackage() {
      if (this.removeReason) { this.removeOpen = false; return false }
      this.removeOpen = false
      return this.feed.removePackage()
    },
    connect() {
      if (this.connectReason) return false
      if (!this.setup.identity.installed) { this.openInstall(); return false }
      return this.control("start")
    },
    formatDate(iso) { return formatDate(iso) },
    loadReceivers() { return this.feed.loadReceivers() },
    control(action, extra = {}) { return this.feed.control(action, extra) },
  },
  template: `
    <section class="gx-driving gx-aa" aria-label="Android Auto setup">
      <header class="gx-card gx-driving__intro gx-aa__hero">
        <h2>Android Auto</h2>
        <p>Stream navigation and media from StarPilot to your car’s screen. Three steps, about five minutes.</p>
      </header>
      <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
      <div v-if="!setup" class="gx-card gx-message" role="status">{{ error ? "Setup could not be loaded." : "Checking Android Auto setup…" }} <button class="gx-btn gx-btn--tonal" :disabled="busy" @click="refresh">Retry</button></div>
      <ol v-else class="gx-aa__steps">
        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': supportReady }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="supportReady" class="bi bi-check-lg"></i><template v-else>1</template></span>
            <div><h3>Android Auto Support</h3><p>The one-time setup that lets your comma talk to your car.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <p v-if="!setup.installReady" class="gx-aa-pill gx-aa-pill--expired" role="status">Not available on this build — the Android Auto display and encoder are missing.</p>
            <template v-else>
              <div class="gx-aa-status">
                <span class="gx-aa-pill" :class="'gx-aa-pill--' + expiry.level" role="status">{{ expiry.label }}<template v-if="hasPackage && !setup.enabled"> · Off</template></span>
                <button v-if="hasPackage" type="button" class="gx-aa-trash" aria-label="Delete Package" :disabled="busy || !!removeReason" :title="removeReason || 'Delete Package'" @click="openRemove"><i class="bi bi-trash3"></i></button>
                <span v-if="setup.enabled && !setup.serviceReady" class="gx-muted" role="status">Starting…</span>
                <div class="gx-aa-status__actions">
                  <button v-if="!setup.identity.installed" class="gx-btn" :disabled="busy || !setup.parked" @click="openInstall">{{ setup.identity.expired || setup.identity.error ? 'Reinstall' : 'Install Android Auto Support' }}</button>
                  <button v-else-if="expiry.level === 'soon'" class="gx-btn" :disabled="busy || !setup.parked" @click="openInstall">Update</button>
                  <button v-if="setup.identity.installed && !setup.enabled" class="gx-btn" :disabled="busy || !setup.parked" @click="setEnabled(true)">Turn On</button>
                  <button v-else-if="setup.enabled && setup.identity.installed" class="gx-btn gx-btn--tonal" :disabled="busy" @click="setEnabled(false)">Turn Off</button>
                </div>
              </div>
              <p v-if="setup.import?.state === 'running' && !installOpen" class="gx-muted" role="status">Checking your package…</p>
              <p v-if="!setup.parked" class="gx-muted">Use offroad mode or Park to make changes.</p>
            </template>
            <details class="gx-aa-wiki"><summary>Stuck installing? Common problems</summary>
              <ul>
                <li><strong>“This is the APKMirror Installer app”:</strong> you downloaded the helper app. Go back to the Android Auto release page and use <strong>Download APK Bundle</strong> there.</li>
                <li><strong>“Not Android Auto” or an unverified file:</strong> make sure the app is <strong>Android Auto</strong> by <strong>Google LLC</strong>, and that the variant name ends in <strong>‑release</strong> (not beta or alpha).</li>
                <li><strong>Certificate expired:</strong> that release is too old. Go back to All versions and download the one with the newest date.</li>
                <li><strong>Can’t find the right file:</strong> only the release’s <strong>Variant</strong> entries are the app. Skip the ones named beta or any other app.</li>
                <li><strong>The file won’t pick or was rejected:</strong> don’t unzip it. Use the .apk, .xapk or .apkm file exactly as downloaded.</li>
                <li><strong>Upload is slow or stops:</strong> stay on this page and keep the comma awake and on the same Wi-Fi until it finishes.</li>
              </ul>
              <p><strong>Why is this needed?</strong> Car screens only talk to devices that present Google’s Android Auto certificate. Your comma reads it from your own copy of the app, on the device. Nothing is sent anywhere, and no Android app is installed on the comma.</p>
            </details>
          </div>
        </li>

        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': !!selected && !pairing?.active }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="selected && !pairing?.active" class="bi bi-check-lg"></i><template v-else>2</template></span>
            <div><h3>Pair Your Car</h3><p>Open your car’s phone pairing screen, then tap Find My Car. You can do this before step 1 is finished.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <ul v-if="!pairing?.active && receivers.length" class="gx-aa-list" aria-label="Paired cars">
              <li v-for="car in receivers" :key="car.address" class="gx-aa-row">
                <i class="bi bi-car-front" aria-hidden="true"></i>
                <span class="gx-aa-row__text"><strong>{{ car.name }}</strong><small>{{ selected?.address === car.address ? 'Used for Android Auto' : 'Paired' }}</small></span>
                <span v-if="selected?.address === car.address" class="gx-aa-pill gx-aa-pill--ready"><i class="bi bi-check-lg"></i> Selected</span>
                <button v-else class="gx-btn gx-btn--tonal" :disabled="busy || !setup.parked || runtime?.running" @click="control('select_receiver', { address: car.address })">Use</button>
              </li>
            </ul>
            <p v-else-if="!pairing?.active && selected" class="gx-aa-row"><i class="bi bi-car-front" aria-hidden="true"></i><span class="gx-aa-row__text"><strong>{{ selected.name }}</strong><small>Used for Android Auto</small></span></p>
            <p v-if="!pairing?.active && endReason === 'canceled'" class="gx-muted" role="status">Pairing canceled. Start again when your car is ready.</p>
            <p v-else-if="!pairing?.active && endReason" class="gx-muted" role="status">The pairing window ended without choosing a car. Try again when your car’s pairing screen is open.</p>
            <p v-if="waitingForCar" role="status">{{ pairing.discovering ? "Searching for nearby cars and adapters…" : "Choose your car or wireless adapter below." }}</p>
            <p v-else-if="pairing?.active && pairing.approved && (!pairing.state || pairing.state === 'idle')" role="status">Approved {{ pairing.receiver?.name }}. Finishing Bluetooth pairing…</p>
            <p v-if="pairing?.state === 'pairing' && !pairing.prompt && !pairing.approved" role="status">Pairing with {{ pairing.receiver?.name || 'the selected device' }}…</p>
            <p v-if="pairing?.state === 'connecting'" role="status">Connecting to {{ pairing.receiver?.name || 'the selected device' }}…</p>
            <p v-if="['paired', 'connected'].includes(pairing?.state)" role="status"><i class="bi bi-check-circle-fill gx-aa-ok"></i> {{ pairing.receiver?.name || 'Device' }} {{ pairing.state === 'connected' ? 'connected' : 'paired' }}.</p>
            <GxNotice tone="danger" v-if="pairing?.error">{{ pairing.error }}</GxNotice>
            <ul v-if="pairing?.active" class="gx-aa-list" aria-label="Nearby devices">
              <li v-if="!pairing.devices?.length && waitingForCar" class="gx-aa-row gx-muted" role="status"><span class="gx-aa-spinner" aria-hidden="true"></span>Nothing found yet. Keep your car’s pairing screen open.</li>
              <li v-for="device in pairing.devices || []" :key="device.address" class="gx-aa-row">
                <i :class="device.android_auto ? 'bi bi-car-front' : 'bi bi-bluetooth'" aria-hidden="true"></i>
                <span class="gx-aa-row__text"><strong>{{ device.name }}</strong><small>{{ device.android_auto ? 'Android Auto ready' : 'Bluetooth device' }} · {{ device.connected ? 'Connected' : device.paired ? 'Paired before' : 'Nearby' }}</small></span>
                <button class="gx-btn gx-btn--tonal" :disabled="deviceSelectionBlocked" @click="selectDevice(device.address)">{{ device.paired ? 'Connect' : 'Pair' }}</button>
              </li>
            </ul>
            <div v-if="pairing?.prompt" class="gx-aa-prompt" role="status"><strong>{{ pairing.receiver.name }}</strong>
              <p>{{ pairing.prompt.kind === 'confirmation' ? 'Check that this code matches your car, then confirm.' :
                pairing.prompt.kind === 'pin' ? 'Enter the PIN shown by your car.' :
                pairing.prompt.kind === 'passkey' ? 'Enter your car’s passkey.' :
                pairing.prompt.kind === 'authorization' ? 'Allow this car to pair?' : 'Enter this code in your car.' }}</p>
              <strong v-if="pairing.prompt.value" class="gx-aa-prompt__code">{{ pairing.prompt.value }}</strong>
              <input v-if="['pin','passkey'].includes(pairing.prompt.kind)" class="gx-field" type="text" maxlength="16" autocomplete="off"
                :inputmode="pairing.prompt.kind === 'passkey' ? 'numeric' : 'text'" :aria-label="pairing.prompt.kind === 'pin' ? 'Car PIN' : 'Car passkey'" v-model="pairValue" />
              <div v-if="!pairing.prompt.displayOnly" class="gx-driving__actions">
                <button class="gx-btn gx-btn--tonal" :disabled="busy" @click="respond(false)">Reject</button>
                <button class="gx-btn" :disabled="busy || !canRespond" @click="respond(true)">{{ pairing.prompt.kind === 'pin' ? 'Send PIN' : pairing.prompt.kind === 'passkey' ? 'Send Passkey' : 'Confirm' }}</button></div>
            </div>
            <p v-if="pairWhenReady" class="gx-muted" role="status"><span class="gx-aa-spinner" aria-hidden="true"></span> Turning on Android Auto, then searching…</p>
            <p v-else-if="!pairing?.active && pairingReason" class="gx-muted" role="status">{{ pairingReason }}</p>
            <div class="gx-driving__actions">
              <button v-if="!pairing?.active" class="gx-btn" :class="{ 'gx-btn--tonal': !!selected }" :disabled="busy || pairWhenReady || !!pairingReason" @click="startPairing"><i class="bi bi-search"></i> {{ selected ? 'Pair Another Car' : 'Find My Car' }}</button>
              <button v-else class="gx-btn gx-btn--tonal" :disabled="busy" @click="cancelPairing">Cancel Search / Pairing</button>
            </div>
            <details class="gx-aa-wiki"><summary>Stuck pairing? Pairing order and wireless adapters</summary>
              <p><strong>Keep this page open while pairing</strong> so the car’s PIN or code doesn’t time out.</p>
              <p><strong>Car with built-in wireless Android Auto:</strong> open the car’s phone pairing screen, tap Find My Car, choose your car, then confirm the code on both screens.</p>
              <p><strong>Wireless adapter</strong> (AAWireless, Motorola MA1, Carlinkit…): pair your car in <a href="/bluetooth">Bluetooth</a> first so calls keep working, then put the adapter in pairing mode and pair it here. Adapter names often look like AndroidAuto-XXXX.</p>
              <p><strong>Start fresh:</strong></p>
              <ol>
                <li>Forget the car on the comma: <a href="/bluetooth">Bluetooth</a> → Forget.</li>
                <li>Delete the comma from the car’s Bluetooth list.</li>
                <li>Turn the car off and on (or unplug the adapter for 5 seconds).</li>
                <li>Pair again here.</li>
              </ol>
            </details>
          </div>
        </li>

        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': !!runtime?.running }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="runtime?.running" class="bi bi-check-lg"></i><template v-else>3</template></span>
            <div><h3>Connect &amp; Drive</h3><p>Start streaming to your dashboard.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <p v-if="runtime?.running" class="gx-aa-pill gx-aa-pill--ready" role="status">Connected<span v-if="runtime.state"> · {{ runtime.state }}</span><span v-if="runtime.detail"> — {{ runtime.detail }}</span></p>
            <p v-else-if="runtime?.state && runtime.state !== 'idle'" class="gx-muted" role="status">Projection: {{ runtime.state }}<span v-if="runtime.detail"> — {{ runtime.detail }}</span>.</p>
            <button v-if="!runtime?.running" class="gx-btn gx-aa-cta" :disabled="busy || !!connectReason" @click="connect">{{ selected ? 'Connect to ' + selected.name : 'Connect to Your Car' }}</button>
            <button v-else class="gx-btn gx-btn--tonal gx-aa-cta" :disabled="busy" @click="control('stop')">Disconnect</button>
            <p v-if="connectReason" class="gx-muted" role="status">{{ connectReason }}</p>
            <p v-else-if="!setup.identity.installed" class="gx-muted">Finish step 1 first — Connect will walk you through it.</p>
            <button type="button" class="gx-aa-switch" role="switch" :aria-checked="runtime?.auto_connect ? 'true' : 'false'"
              :disabled="busy || !setup.enabled || !setup.parked || pairing?.active" @click="control('auto_connect', { enabled: !runtime?.auto_connect })">
              <span class="gx-aa-row__text"><strong>Automatic Connection</strong><small>Connect to your car whenever you start driving.</small></span>
              <span class="gx-aa-switch__track" aria-hidden="true"><span class="gx-aa-switch__thumb"></span></span>
            </button>
            <p v-if="runtime?.companion_name" class="gx-muted">Car: {{ runtime.companion_name }}</p>
            <details class="gx-aa-wiki"><summary>Stuck connecting? Wi-Fi and screen troubleshooting</summary>
              <p><strong>How it connects:</strong> after Bluetooth, the car (or adapter) creates its own hidden 5 GHz Wi-Fi network and tells the comma how to join. The picture streams over that Wi-Fi.</p>
              <p><strong>First connection:</strong> stay in Park or offroad mode, and keep the car’s screen on.</p>
              <p><strong>Black or frozen screen:</strong> tap Disconnect, wait a few seconds, then connect again. If it keeps happening, turn the car off and on.</p>
              <p><strong>Car says the phone isn’t compatible:</strong> make sure wireless Android Auto (sometimes called “smartphone connection”) is turned on in the car’s settings, and that step 1 shows Ready.</p>
              <p>Wired USB setup is unavailable. Use wireless Android Auto or a wireless adapter.</p>
            </details>
          </div>
        </li>
      </ol>

      <details v-if="setup" class="gx-card gx-aa-advanced"><summary>Advanced Tools &amp; Diagnostics</summary>
        <div class="gx-aa-advanced__body">
          <p v-if="setup.identity.expires">Certificate: {{ setup.identity.expired ? 'expired' : 'valid until' }} {{ formatDate(setup.identity.expires) }}.</p>
          <p v-if="setup.identity.warning" role="status">{{ setup.identity.warning }}</p>
          <p v-if="setup.identity.error" role="status">{{ setup.identity.error }}</p>
          <p v-if="setup.import?.state === 'failed' && !installOpen" role="status">Last package check: {{ setup.import.error || 'failed' }}</p>
          <div class="gx-driving__actions">
            <button class="gx-btn gx-btn--tonal" :disabled="busy" @click="refresh">Refresh</button>
            <button class="gx-btn gx-btn--tonal" :disabled="busy || !setup.enabled || !setup.serviceReady || !setup.parked || pairing?.active" @click="loadReceivers">Find Paired Cars</button>
            <a class="gx-btn gx-btn--tonal" href="#/logs/android-auto">Session Logs</a>
            <button v-if="setup.enabled" class="gx-btn gx-btn--tonal" :disabled="busy" @click="setEnabled(false)">Turn Off Android Auto</button>
          </div>
          <p class="gx-muted">If the video encoder can’t start, projection stops and reports the error in step 3. Projection support still needs validation with your car and this device. Maximum package size: {{ Math.floor(setup.maxUploadBytes / 1048576) }} MB.</p>
        </div>
      </details>

      <div v-if="removeOpen && setup" class="gx-settings__modal gx-aa-sheet" @click.self="closeRemove" @keydown.esc="closeRemove">
        <div class="gx-card gx-settings__dialog gx-aa-sheet__dialog gx-aa-confirm" role="alertdialog" aria-modal="true" aria-labelledby="gx-aa-remove-title" aria-describedby="gx-aa-remove-body">
          <div><h3 id="gx-aa-remove-title">Remove the package?</h3>
            <p id="gx-aa-remove-body">Are you sure you want to remove the package? The device will not connect to your car until you re-add one.</p></div>
          <div class="gx-aa-confirm__actions">
            <button type="button" class="gx-btn gx-btn--tonal" @click="closeRemove">Cancel</button>
            <button type="button" class="gx-btn gx-aa-danger" :disabled="busy" @click="removePackage">Confirm</button>
          </div>
        </div>
      </div>

      <div v-if="installOpen && setup" class="gx-settings__modal gx-aa-sheet" @click.self="closeInstall" @keydown.esc="closeInstall">
        <div ref="installDialog" class="gx-card gx-settings__dialog gx-aa-sheet__dialog" role="dialog" aria-modal="true" aria-labelledby="gx-aa-install-title" tabindex="-1">
          <button type="button" class="gx-aa-sheet__close" aria-label="Close" @click="closeInstall"><i class="bi bi-x-lg"></i></button>
          <div v-if="installState === 'done'" class="gx-aa-sheet__done">
            <i class="bi bi-check-circle-fill gx-aa-ok" aria-hidden="true"></i>
            <h3 id="gx-aa-install-title">You’re all set</h3>
            <p>{{ expiry.label }}</p>
            <ul class="gx-aa-checks"><li v-for="check in checks" :key="check.label" :class="'gx-aa-check--' + check.status">{{ check.label }}</li></ul>
            <button class="gx-btn gx-aa-cta" @click="closeInstall">Done</button>
          </div>
          <template v-else>
            <div><h3 id="gx-aa-install-title">Set Up Android Auto Support</h3>
              <p class="gx-muted">A quick one-time setup that enables wireless projection with your car.</p></div>
            <ol class="gx-aa-sheet__steps">
              <li :class="{ 'gx-aa-sheet__step--muted': installState !== 'choose' }">
                <strong>Download Android Auto</strong>
                <a class="gx-btn gx-btn--tonal" :href="apkmirror" target="_blank" rel="noopener noreferrer">Open APKMirror <i class="bi bi-box-arrow-up-right"></i></a>
                <ol class="gx-aa-sheet__substeps">
                  <li>Open <strong>Android Auto</strong> on APKMirror, then open the <strong class="gx-aa-hl">All versions</strong> list and click through the versions to compare their release dates.</li>
                  <li>Click the version with the <strong>newest release date</strong>.</li>
                  <li>Click <strong>Scroll down to Available downloads</strong>.</li>
                  <li>Under <strong>Variant</strong>, click the <strong>17.x.xxxx‑release</strong> or <strong>18.x.xxxx‑release</strong> entry.</li>
                  <li>Click <strong>Download APK Bundle</strong> (or <strong>Download APK</strong>). You get an <strong>.apk</strong>, <strong>.xapk</strong> or <strong>.apkm</strong> file. Leave it zipped.</li>
                </ol>
                <small>You don’t need the APKMirror Installer app.</small>
              </li>
              <li :class="{ 'gx-aa-sheet__step--muted': installState !== 'choose' }">
                <strong>Choose the downloaded file</strong>
                <label class="gx-btn gx-btn--tonal gx-aa-file" :class="{ 'gx-aa-file--disabled': installState !== 'choose' }">
                  <input type="file" accept=".apk,.xapk,.apkm" aria-label="Android Auto APK, XAPK, or APKM" :disabled="installState !== 'choose'" @change="choosePackage" />
                  <i class="bi bi-folder2-open"></i> {{ packageFile ? 'Choose a Different File' : 'Choose File' }}</label>
                <small v-if="packageFile && !packageError" class="gx-aa-picked"><i class="bi bi-file-earmark-zip"></i> {{ packageFile.name }} · {{ Math.ceil(packageFile.size / 1048576) }} MB</small>
                <small v-if="packageError" class="gx-aa-bad" role="alert">{{ packageError }}</small>
              </li>
              <li>
                <strong>Install</strong>
                <button v-if="installState === 'choose'" class="gx-btn" :disabled="!!uploadReason" @click="upload">{{ setup.enabled ? 'Install' : 'Turn On and Install' }}</button>
                <small v-if="installState === 'choose' && uploadReason && packageFile && !packageError" class="gx-muted" role="status">{{ uploadReason }}</small>
                <div v-if="installState === 'uploading'" role="status" aria-live="polite" class="gx-aa-progress">
                  <progress :value="uploadProgress?.loaded || 0" :max="uploadProgress?.total || 1"></progress>
                  <small>Sending to your comma… {{ uploadProgress ? Math.round(100 * uploadProgress.loaded / uploadProgress.total) : 0 }}%</small>
                </div>
                <ul v-if="['checking', 'failed'].includes(installState)" class="gx-aa-checks" aria-live="polite">
                  <li v-for="check in checks" :key="check.label" :class="'gx-aa-check--' + check.status">{{ check.label }}</li>
                </ul>
                <div v-if="installState === 'failed'" class="gx-aa-problem" role="alert">
                  <p>{{ problem }}</p>
                  <button class="gx-btn gx-btn--tonal" @click="chooseAgain">Choose Another File</button>
                </div>
                <p v-if="error && installState === 'choose' && installAttempted" class="gx-aa-bad" role="alert">{{ error }}</p>
              </li>
            </ol>
            <small class="gx-muted">Your package stays on this comma. Maximum size {{ Math.floor(setup.maxUploadBytes / 1048576) }} MB.</small>
          </template>
        </div>
      </div>
    </section>`,
}
