import { GxState } from "./state.js"
import { GxDialog } from "./dialog.js"
import { GxIconButton } from "./icon-button.js"
import { requestJson } from "./startup.js"
import { GxNotice } from "./notice.js"
import { connectionError } from "./polling.js"
import { BluetoothDeviceList } from "./bluetooth-devices.js"
import { GalaxySettingRow, switchRow } from "./galaxy-setting-row.js"

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

  async setEnabled(enabled, enableBluetooth = false) {
    if (!this.active || this.busy || typeof enabled !== "boolean" ||
      typeof enableBluetooth !== "boolean" || enableBluetooth && !enabled || enabled && !this.setup?.installReady) return false
    const payload = { enabled, ...(enableBluetooth ? { enableBluetooth: true } : {}) }
    const result = await this.request("./api/android-auto/enable", {
      method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    }, enableBluetooth ? 45000 : 8000)
    if (result === null) return false
    await this.refresh()
    return true
  }

  async upload(file) {
    if (!this.active || this.busy || !this.setup || this.setup.import?.state === "running" ||
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
    if (!this.active || this.busy || !this.setup || this.setup.import?.state === "running") return false
    const result = await this.request("./api/android-auto/identity", { method: "DELETE" }, 30000)
    if (result === null) return false
    await this.refresh()
    return true
  }
}

export const APKMIRROR_URL = "https://www.apkmirror.com/apk/google-inc/android-auto/"
// Signed APKPure links the comma looked up; the browser downloads the app itself.
export const DOWNLOAD_LINK = /^https:\/\/download\.pureapk\.com\/b\/X?APK\/[!-~]+$/
const WRONG_DOWNLOAD = "That’s not the Android Auto download. Download it again in step 1."

export function downloadLink(release) {
  if (typeof release?.url === "string" && DOWNLOAD_LINK.test(release.url) && typeof release.version === "string" &&
      release.version.length <= 128 && /^[0-9]+(?:\.[0-9]+)+-release$/.test(release.version) &&
      Number.isSafeInteger(release.size) && release.size > 0) {
    return { direct: true, url: release.url, version: release.version.replace(/-release$/, ""), megabytes: Math.ceil(release.size / 1048576) }
  }
  return { direct: false, url: APKMIRROR_URL }
}
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
  if (name && !/\.(apk|xapk|apkm|zip)$/i.test(name)) return "That’s not an Android package. Choose the .apk, .xapk, .apkm, or .zip file you downloaded."
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
    case "UNVERIFIED": return "No phone certificate issued by Google’s Automotive Link root was found. Choose another Android Auto release."
    case "EXPIRED": {
      const on = formatDate(job.expires, undefined, locale)
      return `This Android Auto version expired${on ? ` on ${on}` : ""}. Download a newer stable release.`
    }
    case "NOT_YET_VALID": return "This version isn’t valid yet. Check that the comma’s date and time are correct."
    case "UNSUPPORTED_VERSION":
      return job.error || "This version stores its key differently. Choose another Android Auto release."
    case "TOO_LARGE": return "This file is too large to be the Android Auto app."
    case "CANCELLED": return "Setup authorization changed. Sign in to Galaxy and try again."
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
  components: { GxState, GxIconButton, GxNotice, GxDialog, GalaxySettingRow },
  props: {
    mode: { type: String, required: true }, localAccess: { type: Boolean, required: true },
    unauthorized: { type: Function, required: true }
  },
  data: () => ({
    setup: null, pairing: null, selected: null, runtime: null, receivers: [], endReason: "", busy: false, error: "",
    pairValue: "", packageFile: null, uploadProgress: null, installOpen: false, removeOpen: false, installAttempted: false, installBaseline: null,
    downloadStarted: false, packageMagicError: "", packageChecking: false, packageSelection: 0,
    installFileName: "", pairWhenReady: false, enableOpen: false, showSteps: false
  }),
  mounted() {
    this.feed = new AndroidAutoFeed({ publish: (value) => Object.assign(this, value), unauthorized: this.unauthorized })
    this.visibility = () => {
      if (document.hidden) this.feed.stop(true)
      else this.begin()
    }
    document.addEventListener("visibilitychange", this.visibility)
    if (!document.hidden) this.begin()
  },
  beforeUnmount() { this.finishEnable(false); document.removeEventListener("visibilitychange", this.visibility); this.feed?.stop(true) },
  watch: {
    mode() { if (!document.hidden) this.begin(); else this.feed?.stop(true) },
    localAccess() { if (!document.hidden) this.begin(); else this.feed?.stop(true) },
    'pairing.prompt.id'() { this.pairValue = "" },
    'pairing.active'(active, was) { if (was && !active) this.loadReceivers() },
    // Find car on a fresh device turns Android Auto on first, then searches once the service is up.
    'setup.serviceReady'() { this.resumePairing() },
    busy(value) { if (!value) this.resumePairing() },
    'setup.enabled'(enabled) { if (!enabled) this.pairWhenReady = false },
  },
  computed: {
    canRespond() { return validPromptInput(this.pairing?.prompt, this.pairValue) },
    expiry() { return expiryInfo(this.setup?.identity) },
    projecting() { return this.runtime?.state === "streaming" },
    supportReady() { return !!(this.setup?.enabled && this.setup.identity.installed) },
    // Returning drivers see a status card; the setup steps fold away below it.
    setupDone() { return !!(this.supportReady && this.selected && !this.pairing?.active) },
    download() { return downloadLink(this.setup?.download) },
    uploadPercent() {
      const { loaded, total } = this.uploadProgress || {}
      return total > 0 ? Math.min(100, Math.round(100 * loaded / total)) : 0
    },
    downloadsHint() {
      if (typeof navigator === "undefined") return ""
      if (/iPhone|iPad|iPod/i.test(navigator.userAgent || "") || navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1) return "In Files, open Downloads."
      return /Android/i.test(navigator.userAgent || "") ? "Open Downloads." : ""
    },
    packageError() {
      if (!this.packageFile) return ""
      const preflight = packagePreflight(this.packageFile)
      if (preflight) return preflight
      if (!Number.isSafeInteger(this.packageFile.size) || this.packageFile.size <= 0) return "The selected file is empty or its size cannot be read."
      if (this.setup && this.packageFile.size > this.setup.maxUploadBytes) return "The selected package exceeds the maximum size shown below."
      return this.packageMagicError
    },
    uploadReason() {
      if (!this.packageFile) return "Choose your Android Auto package."
      if (this.packageError) return this.packageError
      if (this.packageChecking) return "Checking downloaded file…"
      if (!this.setup) return "Load setup status first."
      if (!this.setup.enabled && !this.setup.installReady) return "The Android Auto display and encoder must be installed before uploading."
      if (this.setup.import?.state === "running") return "Wait for the current package check to finish."
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
    onPhone() {
      return typeof navigator !== "undefined" && (navigator.userAgentData?.mobile === true ||
        /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "") || navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
    },
    removeReason() {
      if (!this.setup) return "Load setup status first."
      if (this.setup.import?.state === "running") return "Wait for the current package check to finish."
      return ""
    },
    // Bluetooth pairing and the car's Wi-Fi handoff need no Android Auto package; only projection does.
    pairingReason() {
      if (!this.setup) return "Load setup status first."
      if (!this.setup.installReady) return "This build is missing the Android Auto display or encoder."
      if (this.setup.enabled && !this.setup.serviceReady) return "Waiting for the Android Auto service to start."
      if (!this.setup.bluetoothEnabled && this.setup.enabled) return "Turn on Bluetooth on the Bluetooth page."
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
      return !!this.pairingReason || !this.pairing?.active ||
        !!this.pairing?.prompt || ["pairing", "connecting"].includes(this.pairing?.state) || !!this.runtime?.running
    },
  },
  methods: {
    switchRow,
    async begin() {
      await this.feed.start()
      if (this.setup?.enabled && this.setup.serviceReady && !this.pairing?.active) this.loadReceivers()
    },
    refresh() { return this.feed.refresh() },
    setEnabled(enabled) {
      if (!enabled) {
        this.pairWhenReady = false
        this.finishEnable(false)
        return this.feed.setEnabled(false)
      }
      if (!this.setup?.installReady || this.busy || this.enableOpen) return Promise.resolve(false)
      if (this.setup.bluetoothEnabled) return this.feed.setEnabled(true)
      this.enableOpen = true
      return new Promise((resolve) => { this.enableResolve = resolve })
    },
    finishEnable(enabled) {
      const resolve = this.enableResolve
      this.enableResolve = null
      this.enableOpen = false
      resolve?.(enabled)
    },
    cancelEnable() { if (!this.busy) this.finishEnable(false) },
    async confirmEnable() {
      if (!this.enableOpen || this.busy) return false
      const enabled = await this.feed.setEnabled(true, true)
      this.finishEnable(enabled)
      return enabled
    },
    startPairing() {
      if (this.pairingReason || this.runtime?.running) return false
      if (!this.setup.enabled) return this.setEnabled(true).then((enabled) => {
        this.pairWhenReady = enabled
        return this.resumePairing()
      })
      return this.feed.action("./api/android-auto/pairing")
    },
    resumePairing() {
      if (!this.pairWhenReady || !this.setup?.enabled || !this.setup.serviceReady || this.busy) return false
      this.pairWhenReady = false
      return this.startPairing()
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
      this.chooseAgain()
      Object.assign(this, { installOpen: true, downloadStarted: false })
    },
    closeInstall() { this.installOpen = false },
    markDownloadStarted() {
      if (!this.busy && ["choose", "failed"].includes(this.installState)) this.chooseAgain()
      this.downloadStarted = true
    },
    chooseAgain() {
      this.packageSelection++
      Object.assign(this, { installAttempted: false, packageFile: null, packageMagicError: "", packageChecking: false })
    },
    async choosePackage(event) {
      const file = event.target.files?.[0] || null
      const selection = ++this.packageSelection
      Object.assign(this, { packageFile: file, packageMagicError: "", packageChecking: false })
      // Leave useful name/size errors intact; never read the full package into browser memory.
      if (!file || packagePreflight(file) || !Number.isSafeInteger(file.size) || file.size <= 0 || file.size > this.setup?.maxUploadBytes) return
      this.packageChecking = true
      let error = ""
      try {
        if (file.size < 5 * 1024 * 1024) error = WRONG_DOWNLOAD
        else {
          const bytes = new Uint8Array(await file.slice(0, 4).arrayBuffer())
          if (bytes.length !== 4 || ![0x50, 0x4b, 0x03, 0x04].every((byte, i) => bytes[i] === byte)) error = WRONG_DOWNLOAD
        }
      } catch { error = WRONG_DOWNLOAD }
      if (selection === this.packageSelection) Object.assign(this, { packageMagicError: error, packageChecking: false })
    },
    async upload() {
      if (this.busy || this.uploadReason) return false
      const file = this.packageFile
      Object.assign(this, { installAttempted: true, installBaseline: this.setup.import?.started ?? null, installFileName: file.name || "" })
      if (!this.setup.enabled && !await this.setEnabled(true)) { this.installAttempted = false; return false }
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
    loadReceivers() { return this.feed.loadReceivers() },
    control(action, extra = {}) { return this.feed.control(action, extra) },
  },
  template: `
    <section class="gx-driving" aria-label="Android Auto setup" :inert="busy" :aria-busy="busy || undefined">
      <header class="gx-page-header">
        <h2>Android Auto</h2>
        <p>Show the StarPilot driving view on your car’s screen. Set up support, pair your car, then connect.</p>
      </header>
      <GxNotice tone="warn">Android Auto uses the comma’s Wi-Fi to project to your car and disconnects it from your current Wi-Fi network. Use the Galaxy hotspot for local access during projection. Remote Galaxy access requires Internet on the comma.</GxNotice>
      <GxNotice tone="danger" v-if="error && setup">{{ error }}</GxNotice>
      <GxNotice v-if="!setup" :busy="!error" :tone="error ? 'danger' : 'info'">{{ error || "Checking Android Auto setup… Reconnecting automatically…" }}</GxNotice>
      <section v-if="setup && setupDone" class="gx-card gx-aa-step gx-aa-home" aria-labelledby="gx-aa-home-title">
        <div class="gx-aa-step__head">
          <span class="gx-aa-step__num" :class="{ 'gx-aa-home__icon--live': projecting }" aria-hidden="true"><i class="bi bi-car-front"></i></span>
          <div><h3 id="gx-aa-home-title">{{ projecting ? 'Connected to ' + selected.name : runtime?.running ? 'Connecting to ' + selected.name : selected.name }}</h3>
            <p role="status">{{ runtime?.running && runtime.state !== 'streaming' && runtime.label ? runtime.label : runtime?.running ? 'Showing StarPilot on your car’s screen.' : runtime?.auto_connect ? 'Connects automatically when you start driving.' : 'Ready to connect.' }}</p></div>
        </div>
        <div class="gx-aa-step__body">
          <p v-if="expiry.level === 'soon'" class="gx-aa-pill gx-aa-pill--soon" role="status">{{ expiry.label }}</p>
          <button v-if="!runtime?.running" class="gx-btn gx-aa-cta" :disabled="!!connectReason" @click="connect">Connect</button>
          <button v-else class="gx-btn gx-btn--tonal gx-aa-cta" @click="control('stop')">Disconnect</button>
          <GalaxySettingRow :row="switchRow('Automatic Connection', runtime?.auto_connect, 'Connect to your car whenever you start driving.')"
            :index="0" :busy="busy" :disabled="!setup.enabled || !setup.parked || !!pairing?.active"
            :save-value="(index, value) => control('auto_connect', { enabled: value === 'On' })" />
          <div class="gx-actions">
            <a class="gx-btn gx-btn--tonal" href="#/theme_maker/android_auto"><i class="bi bi-layout-text-window" aria-hidden="true"></i> Customize Dashboard</a>
            <button type="button" class="gx-btn gx-btn--tonal" :aria-expanded="showSteps" aria-controls="gx-aa-steps" @click="showSteps = !showSteps">
              <i :class="showSteps ? 'bi bi-chevron-up' : 'bi bi-gear'" aria-hidden="true"></i> {{ showSteps ? 'Hide Setup' : 'Setup and Pairing' }}</button>
          </div>
        </div>
      </section>
      <ol v-if="setup" v-show="!setupDone || showSteps" id="gx-aa-steps" class="gx-aa__steps">
        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': supportReady }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="supportReady" class="bi bi-check-lg"></i><template v-else>1</template></span>
            <div><h3>Android Auto Support</h3><p>The one-time setup that lets your comma talk to your car.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <p v-if="!setup.installReady" class="gx-aa-pill gx-aa-pill--expired" role="status">Not available on this build — the Android Auto display and encoder are missing.</p>
            <template v-else>
              <div class="gx-aa-status">
                <span class="gx-aa-pill" :class="'gx-aa-pill--' + expiry.level" role="status">{{ expiry.label }}</span>
                <button v-if="hasPackage" type="button" class="gx-icon-btn gx-recordings__danger" aria-label="Delete Package" :disabled="!!removeReason" :title="removeReason || 'Delete Package'" @click="openRemove"><i class="bi bi-trash3"></i></button>
                <span v-if="setup.enabled && !setup.serviceReady" class="gx-note" role="status">Starting…</span>
                <div class="gx-actions gx-aa-status__actions">
                  <button v-if="!setup.identity.installed" class="gx-btn" @click="openInstall">{{ setup.identity.expired || setup.identity.error ? 'Reinstall' : 'Install support' }}</button>
                  <button v-else-if="expiry.level === 'soon'" class="gx-btn" @click="openInstall">Update</button>
                  <button v-else class="gx-btn gx-btn--tonal" @click="openInstall">Install newer version</button>
                </div>
              </div>
              <GalaxySettingRow :row="switchRow('Android Auto', setup.enabled, 'Turn off to stop connecting to your car. Your setup and paired car stay saved.')"
                :index="0" :busy="busy" :disabled="enableOpen" :save-value="(index, value) => setEnabled(value === 'On')" />
              <p v-if="setup.import?.state === 'running' && !installOpen" class="gx-note" role="status">Checking your package…</p>
            </template>
            <details class="gx-aa-wiki"><summary>Stuck installing? Common problems</summary>
              <ul>
                <li><strong>The download button opens APKMirror instead:</strong> the comma couldn’t reach APKPure just now. Download the newest Android Auto release from APKMirror, or close this window and try again in a few minutes.</li>
                <li><strong>“This is the APKMirror Installer app”:</strong> you downloaded the helper app. Go back to the Android Auto release page and use <strong>Download APK Bundle</strong> there.</li>
                <li><strong>“Not Android Auto” or an unverified file:</strong> make sure the app is <strong>Android Auto</strong> by <strong>Google LLC</strong>, and that the variant name ends in <strong>‑release</strong> (not beta or alpha).</li>
                <li><strong>Certificate expired:</strong> that release is too old. Download again in step 1; it always gets the newest release.</li>
                <li><strong>The file won’t pick or was rejected:</strong> don’t unzip it. Use the .apk, .xapk or .apkm file exactly as downloaded. A .zip name from Safari is fine too.</li>
                <li><strong>Upload is slow or stops:</strong> stay on this page and keep the comma awake and on the same Wi-Fi until it finishes.</li>
              </ul>
              <ul>
                <li><strong>Why is this needed?</strong> Car screens only talk to devices that present Google’s Android Auto certificate. Your comma reads it from your own copy of the app, on the device. No Android app is installed on the comma.</li>
              </ul>
            </details>
          </div>
        </li>

        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': !!selected && !pairing?.active }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="selected && !pairing?.active" class="bi bi-check-lg"></i><template v-else>2</template></span>
            <div><h3>Pair Your Car</h3><p>Open your car’s phone pairing screen, then tap Find car. You can do this before step 1 is finished.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <ul v-if="!pairing?.active && receivers.length" class="gx-aa-list" aria-label="Paired cars">
              <li v-for="car in receivers" :key="car.address" class="gx-aa-row">
                <i class="bi bi-car-front" aria-hidden="true"></i>
                <span class="gx-aa-row__text"><strong>{{ car.name }}</strong><small>{{ selected?.address === car.address ? 'Used for Android Auto' : 'Paired' }}</small></span>
                <span v-if="selected?.address === car.address" class="gx-aa-pill gx-aa-pill--ready"><i class="bi bi-check-lg"></i> Selected</span>
                <button v-else class="gx-btn gx-btn--tonal" :disabled="!setup.parked || runtime?.running" @click="control('select_receiver', { address: car.address })">Use</button>
              </li>
            </ul>
            <p v-else-if="!pairing?.active && selected" class="gx-aa-row"><i class="bi bi-car-front" aria-hidden="true"></i><span class="gx-aa-row__text"><strong>{{ selected.name }}</strong><small>Used for Android Auto</small></span></p>
            <p v-if="!pairing?.active && endReason === 'canceled'" class="gx-note" role="status">Pairing canceled. Start again when your car is ready.</p>
            <p v-else-if="!pairing?.active && endReason" class="gx-note" role="status">The pairing window ended without choosing a car. Try again when your car’s pairing screen is open.</p>
            <p v-if="waitingForCar" role="status">{{ pairing.discovering ? "Searching for nearby cars and adapters…" : "Choose your car or wireless adapter below." }}</p>
            <p v-else-if="pairing?.active && pairing.approved && (!pairing.state || pairing.state === 'idle')" role="status">Approved {{ pairing.receiver?.name }}. Finishing Bluetooth pairing…</p>
            <p v-if="pairing?.state === 'pairing' && !pairing.prompt && !pairing.approved" role="status">Pairing with {{ pairing.receiver?.name || 'the selected device' }}…</p>
            <p v-if="pairing?.state === 'connecting'" role="status">Connecting to {{ pairing.receiver?.name || 'the selected device' }}…</p>
            <p v-if="['paired', 'connected'].includes(pairing?.state)" role="status"><i class="bi bi-check-circle-fill gx-aa-ok"></i> {{ pairing.receiver?.name || 'Device' }} {{ pairing.state === 'connected' ? 'connected' : 'paired' }}.</p>
            <GxNotice tone="danger" v-if="pairing?.error">{{ pairing.error }}</GxNotice>
            <ul v-if="pairing?.active" class="gx-aa-list" aria-label="Nearby devices">
              <li v-if="!pairing.devices?.length && waitingForCar" class="gx-aa-row gx-note" role="status"><span class="gx-spinner" aria-hidden="true"></span>Nothing found yet. Keep your car’s pairing screen open.</li>
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
              <div v-if="!pairing.prompt.displayOnly" class="gx-driving__actions gx-actions">
                <button class="gx-btn gx-btn--tonal" @click="respond(false)">Reject</button>
                <button class="gx-btn" :disabled="!canRespond" @click="respond(true)">{{ pairing.prompt.kind === 'pin' ? 'Send PIN' : pairing.prompt.kind === 'passkey' ? 'Send Passkey' : 'Confirm' }}</button></div>
            </div>
            <p v-if="pairWhenReady" class="gx-note" role="status"><span class="gx-spinner" aria-hidden="true"></span> Turning on Android Auto, then searching…</p>
            <p v-else-if="!pairing?.active && pairingReason" class="gx-note" role="status">{{ pairingReason }}</p>
            <div class="gx-driving__actions gx-actions">
              <button v-if="!pairing?.active" class="gx-btn" :class="{ 'gx-btn--tonal': !!selected }" :disabled="pairWhenReady || !!pairingReason" @click="startPairing"><i class="bi bi-search"></i> {{ selected ? 'Pair another' : 'Find car' }}</button>
              <button v-else class="gx-btn gx-btn--tonal" @click="cancelPairing">Cancel Search / Pairing</button>
            </div>
            <details class="gx-aa-wiki"><summary>Stuck pairing? Pairing order and wireless adapters</summary>
              <ul>
                <li><strong>Keep this page open while pairing</strong> so the car’s PIN or code doesn’t time out.</li>
                <li><strong>Cars with built-in wireless Android Auto:</strong> open the car’s phone pairing screen, then tap <strong>Find car</strong> above. Choose your car, then confirm the code on both screens.</li>
                <li><strong>Wireless adapter</strong> (AAWireless, Motorola MA1, Carlinkit…): pair your car in <a href="#/bluetooth">Bluetooth</a> first so calls keep working, then put the adapter in pairing mode and pair it here. Adapter names often look like AndroidAuto-XXXX.</li>
              </ul>
              <p><strong>Start fresh:</strong></p>
              <ol>
                <li>Forget the car on the comma: <a href="#/bluetooth">Bluetooth</a> → Forget.</li>
                <li>Delete the comma from the car’s Bluetooth list.</li>
                <li>Turn the car off and on (or unplug the adapter for 5 seconds).</li>
                <li>Pair again here.</li>
              </ol>
            </details>
          </div>
        </li>

        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': projecting }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="projecting" class="bi bi-check-lg"></i><template v-else>3</template></span>
            <div><h3>Connect &amp; Drive</h3><p>Start streaming to your dashboard.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <p v-if="projecting" class="gx-aa-pill gx-aa-pill--ready" role="status">Connected<span v-if="runtime.state"> · {{ runtime.label || runtime.state }}</span><span v-if="runtime.detail"> — {{ runtime.detail }}</span></p>
            <p v-else-if="runtime?.state && runtime.state !== 'idle'" class="gx-note" role="status">Projection: {{ runtime.label || runtime.state }}<span v-if="runtime.detail"> — {{ runtime.detail }}</span>.</p>
            <button v-if="!runtime?.running" class="gx-btn gx-aa-cta" :disabled="!!connectReason" @click="connect">{{ selected ? 'Connect to ' + selected.name : 'Connect to car' }}</button>
            <button v-else class="gx-btn gx-btn--tonal gx-aa-cta" @click="control('stop')">Disconnect</button>
            <p v-if="connectReason" class="gx-note" role="status">{{ connectReason }}</p>
            <p v-else-if="!setup.identity.installed" class="gx-note">Finish step 1 first — Connect will walk you through it.</p>
            <GalaxySettingRow :row="switchRow('Automatic Connection', runtime?.auto_connect, 'Connect to your car whenever you start driving.')"
              :index="0" :busy="busy" :disabled="!setup.enabled || !setup.parked || !!pairing?.active"
              :save-value="(index, value) => control('auto_connect', { enabled: value === 'On' })" />
            <p v-if="runtime?.companion_name" class="gx-note">Car: {{ runtime.companion_name }}</p>
            <details class="gx-aa-wiki"><summary>Stuck connecting? Wi-Fi and screen troubleshooting</summary>
              <ul>
                <li><strong>How it connects:</strong> after Bluetooth, the car (or adapter) creates its own hidden 5 GHz Wi-Fi network and tells the comma how to join. The picture streams over that Wi-Fi.</li>
                <li><strong>First connection:</strong> stay in Park or offroad mode, and keep the car’s screen on.</li>
                <li><strong>Black or frozen screen:</strong> tap Disconnect, wait a few seconds, then connect again. If it keeps happening, turn the car off and on.</li>
                <li><strong>Car says the phone isn’t compatible:</strong> make sure wireless Android Auto (sometimes called “smartphone connection”) is turned on in the car’s settings, and that step 1 shows Ready.</li>
                <li>Wired USB setup is unavailable. Use wireless Android Auto or a wireless adapter.</li>
              </ul>
            </details>
          </div>
        </li>

        <li class="gx-card gx-aa-step">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true">4</span>
            <div><h3>Customize Your Dashboard</h3><p>Once connected, customize your dashboard setup.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <a class="gx-btn gx-btn--tonal gx-aa-cta" href="#/theme_maker/android_auto">Customize Dashboard</a>
            <a class="gx-btn gx-btn--tonal gx-aa-cta" href="#/navigation/maps"><i class="bi bi-map" aria-hidden="true"></i> Offline Road Maps</a>
            <p class="gx-note">Save road lines for the map overlay so it keeps drawing roads with no signal.</p>
          </div>
        </li>
      </ol>

      <section v-if="setup" class="gx-card gx-aa-faq" aria-labelledby="gx-aa-faq-title">
        <div class="gx-aa-faq__head">
          <h3 id="gx-aa-faq-title">FAQ</h3>
          <p>Quick answers to the problems people run into most. Tap a question to open it.</p>
        </div>

        <h4>Getting connected</h4>
        <details class="gx-aa-wiki"><summary>It won’t connect at all. Where do I start?</summary>
          <p>Go down this list. Most problems are one of these:</p>
          <ul>
            <li><strong>Step 1 says Ready.</strong> If it says Expired or Needs reinstalling, fix that first.</li>
            <li><strong>Step 2 shows your car</strong> with a check mark next to it.</li>
            <li><strong>The car is on</strong> and its screen is awake, not just the accessory power.</li>
            <li><strong>Wireless Android Auto is turned on in the car’s settings.</strong> Some cars call it “smartphone connection” or “phone projection.”</li>
            <li><strong>Bluetooth is on</strong> in the comma’s <a href="#/bluetooth">Bluetooth</a> page.</li>
            <li><strong>No phone is taking over.</strong> See “It won’t connect automatically when other phones are paired” below.</li>
          </ul>
          <p>Still nothing? Look at the status line in step 3. The next question explains what it means.</p>
        </details>
        <details class="gx-aa-wiki"><summary>What do the status messages in step 3 mean?</summary>
          <p>They show how far the comma got. Find the last one you saw:</p>
          <ul>
            <li><strong>Connecting to car / Finding Android Auto:</strong> the comma is reaching the car over Bluetooth. Make sure the car is on and was paired in step 2.</li>
            <li><strong>Starting wireless setup / Waiting for car:</strong> the comma asked the car to start Android Auto. If it stops here, wireless Android Auto is probably turned off in the car, or the car is busy with your phone.</li>
            <li><strong>Getting car Wi‑Fi / Joining car Wi‑Fi:</strong> the car is sharing its private Wi‑Fi with the comma. If it keeps failing here, try turning the car off and on.</li>
            <li><strong>Authenticating:</strong> the car is checking the Android Auto certificate. If it fails here, updating the package in step 1 may help.</li>
            <li><strong>Projecting:</strong> everything is working.</li>
            <li><strong>Car showing its own screen:</strong> the car switched to one of its own screens, often because the radio, map, or another car screen was opened. Tapping the Android Auto icon on the car’s screen usually brings it back.</li>
            <li><strong>Retrying:</strong> something interrupted the connection. The comma tries again by itself, so give it a moment.</li>
          </ul>
        </details>
        <details class="gx-aa-wiki"><summary>It won’t connect automatically when other phones are paired to my car</summary>
          <p>When you start the car, it reconnects to the phones it knows, usually starting with its favorite or the one used most recently. Most cars run Android Auto on only one device at a time, so whichever device gets there first usually wins. If that’s a phone, the comma may have to wait.</p>
          <p>The comma keeps asking about every 30 seconds while you drive, so it can usually take over within about half a minute once the screen is free.</p>
          <p><strong>Things that may help the car pick the comma:</strong></p>
          <ol>
            <li><strong>Make the comma the car’s preferred device.</strong> Many cars have a setting for this in the phone or Bluetooth menu, called something like “Preferred device,” “Priority phone,” or “Primary device.”</li>
            <li><strong>Turn off wireless Android Auto on the phones.</strong> On each phone paired to the car, including other drivers’ phones, open <strong>Settings → Android Auto</strong> and turn off wireless Android Auto for this car, or remove the car from its list of connected cars.</li>
            <li><strong>Make room for the comma.</strong> Some cars only keep two phones connected at once. If two are already connected, there may be no room left for the comma. Turn off Bluetooth on one phone, or delete old phones the car no longer needs.</li>
            <li><strong>Using a wireless adapter?</strong> Usually the adapter chooses which phone to use, not the car. Try removing the adapter from your phone’s Bluetooth list, or setting the comma as the main device in the adapter’s app.</li>
          </ol>
          <p>Your phone may be able to stay connected for music. See “Can I still take calls and play music from my phone?” below.</p>
        </details>
        <details class="gx-aa-wiki"><summary>Can I still take calls and play music from my phone?</summary>
          <p>It depends on your car. The comma never handles calls or audio itself, but to show StarPilot it connects to the car as a phone.</p>
          <p>Some cars treat the phone and Android Auto as one device. In those cars, choosing your real phone as the car’s phone can move Android Auto to that phone and disconnect the comma. Other cars may let both stay connected.</p>
          <p><strong>If the comma disconnects when your phone connects, try this:</strong></p>
          <ul>
            <li><strong>For music:</strong> if your car lets you, connect your phone for <strong>audio only</strong> (sometimes called “media audio” or “music”) in the car’s Bluetooth device list, not as the phone. Then choose Bluetooth Audio as the car’s sound source.</li>
            <li><strong>For a call:</strong> switch the car’s phone to your real phone. The comma will likely disconnect. When you switch back, it usually reconnects within about half a minute.</li>
          </ul>
          <p>The comma can’t pass calls through to your phone yet.</p>
        </details>
        <details class="gx-aa-wiki"><summary>Will this work with my car?</summary>
          <p>It’s made for cars that have <strong>wireless Android Auto</strong> built in, though not every car has been tested. If your car only has wired Android Auto through a USB cable, a <strong>wireless adapter</strong> (AAWireless, Motorola MA1, Carlinkit, and similar) may work. A direct USB cable from the comma isn’t supported yet.</p>
          <p>Every car brand does things a little differently. If yours gives you trouble, a log from your car helps get it fixed. You can download one from <strong>Connection Logs</strong> at the bottom of this page.</p>
        </details>

        <h4>While driving</h4>
        <details class="gx-aa-wiki"><summary>It connected, but the car screen is black or frozen</summary>
          <p>The first picture can take up to about <strong>30 seconds</strong> while StarPilot gets its view ready, so wait a little first. If it’s still black:</p>
          <ol>
            <li>Tap <strong>Disconnect</strong> in step 3, wait a few seconds, then connect again.</li>
            <li>If that doesn’t help, turn the car off, wait until its screen goes dark, and turn it back on.</li>
          </ol>
        </details>
        <details class="gx-aa-wiki"><summary>It disconnects while I’m driving</summary>
          <p>Short drops usually fix themselves. The comma reconnects on its own and step 3 shows <strong>Retrying</strong> in the meantime.</p>
          <p>If it happens often, a phone may be taking the screen back. See “It won’t connect automatically when other phones are paired” above. If it keeps happening, download your <strong>Connection Logs</strong> at the bottom of this page so it can be looked at.</p>
        </details>
        <details class="gx-aa-wiki"><summary>Does it start by itself, or do I tap Connect every time?</summary>
          <p>With <strong>Automatic Connection</strong> turned on, it tries to connect each time you start driving, so you usually don’t need to open this page.</p>
          <ul>
            <li>If you tap <strong>Disconnect</strong>, it stays off for the rest of that drive and starts again on your next one.</li>
            <li>It usually ends by itself about a minute after you turn the car off.</li>
          </ul>
        </details>
        <details class="gx-aa-wiki"><summary>Why are some buttons grayed out?</summary>
          <p>Pairing, switching cars, and changing settings require <strong>Park</strong> or <strong>offroad mode</strong>. Turning Android Auto on or off, package uploads, package deletion, Connect, and Disconnect work on-road and off-road.</p>
        </details>
        <details class="gx-aa-wiki"><summary>Why did this page or my comma’s Wi‑Fi drop when it connected?</summary>
          <p>Android Auto talks to the car over the car’s own private Wi‑Fi. While it’s connected, the comma uses its Wi‑Fi for the car instead of your home or hotspot Wi‑Fi, disconnecting Galaxy over that network.</p>
          <p>Use the Galaxy hotspot for local access while Android Auto is connected. Without another Internet connection, remote Galaxy access is unavailable until your usual Wi‑Fi reconnects. The comma’s cell connection is not affected by Android Auto.</p>
        </details>

        <h4>Setup and upkeep</h4>
        <details class="gx-aa-wiki"><summary>Step 1 says it expires soon, or that it expired</summary>
          <p>Every version of the Android Auto app comes with a Google certificate that has an end date. When it gets close, step 1 shows an <strong>Update</strong> button. Download the newest version the same way you did the first time and install it.</p>
          <p>It takes about two minutes, and your paired car and settings stay as they are.</p>
        </details>
        <details class="gx-aa-wiki"><summary>I have more than one car. How do I switch?</summary>
          <p>Pair each car in step 2 with <strong>Pair another</strong>. All your paired cars appear in the list. Tap <strong>Use</strong> next to the one you’re driving. Disconnect first if Android Auto is running.</p>
        </details>
        <details class="gx-aa-wiki"><summary>Is my information private?</summary>
          <p>Yes. Your extracted Android Auto identity stays on your comma. The app downloads straight to your phone or computer, and the copy you upload is deleted after import. Connection logs also stay on the comma until you download them yourself. They leave out Wi‑Fi passwords, Bluetooth addresses, and your vehicle ID.</p>
        </details>

        <h4>Still stuck?</h4>
        <details class="gx-aa-wiki"><summary>How do I start over from scratch?</summary>
          <ol>
            <li>Remove the car on the comma: <a href="#/bluetooth">Bluetooth</a> → Forget.</li>
            <li>Delete the comma from your car’s Bluetooth list.</li>
            <li>Turn the car off and on, or unplug a wireless adapter for 5 seconds.</li>
            <li>Pair again in step 2 with the car’s pairing screen open.</li>
          </ol>
        </details>
        <div class="gx-driving__actions gx-actions">
          <a class="gx-btn gx-btn--tonal" href="#/logs/android-auto"><i class="bi bi-journal-text"></i> Connection Logs</a>
        </div>
      </section>

      <GxDialog v-if="enableOpen && setup" :inert="busy" labelledby="gx-aa-enable-title" describedby="gx-aa-enable-body" alert @close="cancelEnable">
          <div><h3 id="gx-aa-enable-title">Enable Bluetooth?</h3>
            <p id="gx-aa-enable-body">Android Auto requires Bluetooth for setup and connecting to your car. Bluetooth is currently off. Enable Bluetooth and turn on Android Auto?</p></div>
          <div class="gx-settings__controls gx-actions">
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="cancelEnable">Cancel</button>
            <button type="button" class="gx-btn" :disabled="busy" @click="confirmEnable">{{ busy ? 'Enabling…' : 'Enable Bluetooth and Turn On' }}</button>
          </div>
      </GxDialog>

      <GxDialog v-if="removeOpen && setup" :inert="busy" labelledby="gx-aa-remove-title" describedby="gx-aa-remove-body" alert @close="closeRemove">
          <div><h3 id="gx-aa-remove-title">Remove Android Auto support?</h3>
            <p id="gx-aa-remove-body">This deletes the Android Auto certificate and key from this comma. Android Auto will disconnect first if connected. Your comma won’t connect to your car until you set it up again.</p></div>
          <div class="gx-settings__controls gx-actions">
            <button type="button" class="gx-btn gx-btn--tonal" @click="closeRemove">Cancel</button>
            <button type="button" class="gx-btn gx-btn--danger" @click="removePackage">Remove</button>
          </div>
      </GxDialog>

      <GxDialog v-if="installOpen && setup" labelledby="gx-aa-install-title" class="gx-aa-sheet__dialog" @close="closeInstall">
        <div class="gx-aa-sheet__toolbar">
          <button type="button" class="gx-icon-btn" aria-label="Close" @click="closeInstall"><i class="bi bi-x-lg"></i></button>
        </div>
        <div class="gx-aa-sheet__body">
          <div v-if="installState === 'done'" class="gx-message gx-aa-sheet__done">
            <div class="gx-aa-done-badge"><i class="bi bi-check-lg" aria-hidden="true"></i></div>
            <h3 id="gx-aa-install-title">You’re all set</h3>
            <p class="gx-note">{{ expiry.label }}</p>
            <p v-if="!setup.enabled" class="gx-note">Turn on Android Auto in step 1 to connect to your car.</p>
            <ul class="gx-aa-checks"><li v-for="check in checks" :key="check.label" :class="'gx-aa-check--' + check.status">{{ check.label }}</li></ul>
            <button class="gx-btn gx-aa-cta" @click="closeInstall">Done</button>
          </div>
          <div v-else class="gx-stack">
            <div class="gx-stack gx-aa-sheet__head">
              <div class="gx-cluster gx-aa-sheet__lead">
                <div>
                  <h3 id="gx-aa-install-title">{{ setup.identity.installed ? 'Install a Newer Version' : 'Set Up Android Auto Support' }}</h3>
                  <p class="gx-note">{{ setup.identity.installed ? 'Current version: ' + expiry.label + '. Your paired car and settings stay as they are.' : 'One-time setup so your car accepts your comma.' }}</p>
                </div>
              </div>
            </div>
            <ol class="gx-aa-sheet__steps">
              <li class="gx-aa-step-card" :class="{ 'gx-aa-sheet__step--muted': installState !== 'choose' }">
                <div class="gx-aa-step-card__head">
                  <span class="gx-aa-step__num gx-aa-step-card__num">1</span>
                  <div class="gx-aa-step-card__title">
                    <strong>Download Android Auto</strong>
                    <small>{{ download.direct ? 'Saves the app to this ' + (onPhone ? 'phone' : 'computer') : 'Get the newest release from APKMirror' }}</small>
                  </div>
                </div>
                <div class="gx-aa-step-card__body">
                  <a v-if="download.direct" class="gx-btn gx-btn--tonal" :href="download.url" rel="noreferrer" download @click="markDownloadStarted">
                    <i class="bi bi-download" aria-hidden="true"></i> Download Android Auto {{ download.version }} · {{ download.megabytes }} MB
                  </a>
                  <a v-else class="gx-btn gx-btn--tonal" :href="download.url" target="_blank" rel="noopener noreferrer" @click="markDownloadStarted">
                    <i class="bi bi-box-arrow-up-right" aria-hidden="true"></i> Open APKMirror
                  </a>
                  <small v-if="download.direct" class="gx-note">From APKPure, a third-party mirror (<a class="gx-link" href="https://apkpure.com/terms.html" target="_blank" rel="noopener noreferrer">terms</a>). Don’t unzip it.</small>
                </div>
              </li>
              <li class="gx-aa-step-card" :class="{ 'gx-aa-sheet__step--muted': installState !== 'choose' }">
                <div class="gx-aa-step-card__head">
                  <span class="gx-aa-step__num gx-aa-step-card__num">2</span>
                  <div class="gx-aa-step-card__title">
                    <strong>Choose the downloaded file</strong>
                    <small>{{ downloadStarted && downloadsHint ? downloadsHint : 'The file you just downloaded' }}</small>
                  </div>
                </div>
                <div class="gx-aa-step-card__body">
                  <label class="gx-btn gx-btn--tonal gx-aa-file" :class="{ 'gx-aa-file--disabled': installState !== 'choose' }">
                    <input type="file" :accept="onPhone ? undefined : '.apk,.xapk,.apkm,.zip'" aria-label="Android Auto APK, XAPK, APKM, or ZIP" :disabled="installState !== 'choose'" @change="choosePackage" />
                    <i class="bi bi-folder2-open"></i> {{ packageFile ? 'Choose a Different File' : 'Choose File' }}
                  </label>
                  <small v-if="packageChecking" role="status" class="gx-note">Checking downloaded file…</small>
                  <div v-if="packageFile && !packageError && !packageChecking" class="gx-chip gx-aa-file-chip">
                    <i class="bi bi-file-earmark-zip"></i>
                    <span>{{ packageFile.name }}</span>
                    <small>{{ Math.ceil(packageFile.size / 1048576) }} MB</small>
                  </div>
                  <small v-if="packageError" class="gx-aa-bad" role="alert">{{ packageError }}</small>
                </div>
              </li>
              <li class="gx-aa-step-card">
                <div class="gx-aa-step-card__head">
                  <span class="gx-aa-step__num gx-aa-step-card__num">3</span>
                  <div class="gx-aa-step-card__title">
                    <strong>Install</strong>
                    <small>Send it to your comma and check the certificate</small>
                  </div>
                </div>
                <div class="gx-aa-step-card__body">
                  <button v-if="installState === 'choose'" class="gx-btn gx-aa-cta" :disabled="!!uploadReason" @click="upload">
                    {{ setup.enabled ? 'Install' : 'Turn On and Install' }}
                  </button>
                  <small v-if="installState === 'choose' && uploadReason && packageFile && !packageError" class="gx-note" role="status">{{ uploadReason }}</small>
                  <div v-if="installState === 'uploading'" role="status" aria-live="polite" class="gx-stack">
                    <div class="gx-update-progress__track" role="progressbar" aria-label="Sending to your comma" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="uploadPercent">
                      <div class="gx-update-progress__fill" :style="{ width: uploadPercent + '%' }"></div>
                    </div>
                    <small>Sending to your comma… {{ uploadPercent }}%</small>
                  </div>
                  <ul v-if="['checking', 'failed'].includes(installState)" class="gx-aa-checks" aria-live="polite">
                    <li v-for="check in checks" :key="check.label" :class="'gx-aa-check--' + check.status">{{ check.label }}</li>
                  </ul>
                  <GxNotice v-if="installState === 'failed'" tone="danger">
                    <p>{{ problem }}</p>
                    <button class="gx-btn gx-btn--tonal" @click="chooseAgain">Choose Another File</button>
                  </GxNotice>
                  <p v-if="error && installState === 'choose' && installAttempted" class="gx-aa-bad" role="alert">{{ error }}</p>
                </div>
              </li>
            </ol>
            <div class="gx-stack gx-aa-sheet__footer">
              <small class="gx-note gx-aa-trademark">Google and Android Auto are trademarks of Google LLC. StarPilot is not affiliated with or endorsed by Google or APKPure.</small>
              <small class="gx-note">The uploaded file is deleted after import. Maximum size {{ Math.floor(setup.maxUploadBytes / 1048576) }} MB.</small>
            </div>
          </div>
        </div>
      </GxDialog>
    </section>`,
}
