import { GxDialog } from "./dialog.js"
import { requestJson } from "./startup.js"
import { GxNotice } from "./notice.js"
import { connectionError } from "./polling.js"
import { uploadPackage } from "./android-auto.js"
import { GalaxySettingRow, switchRow } from "./galaxy-setting-row.js"

const ADDRESS = /^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$/
export const DOWNLOAD_PAGE = "https://developer.spotify.com/documentation/soloist/reference/downloads-and-updates"
const STAGES = ["reading", "unpacking", "verifying", "testing", "installing", "done"]
const CHECKS = [
  { stage: "reading", label: "Received the download", codes: ["TOO_LARGE"] },
  { stage: "unpacking", label: "Unpacked safely", codes: ["NOT_ARCHIVE", "CORRUPT", "UNSAFE", "NO_PLAYER", "WRONG_ARCH"] },
  { stage: "verifying", label: "Matches Spotify’s official download", codes: ["NOT_OFFICIAL", "OFFLINE"] },
  { stage: "testing", label: "Runs on this comma", codes: ["INCOMPATIBLE", "EXPIRED"] },
  { stage: "installing", label: "Installed", codes: ["DRIVING"] },
]

function validSetup(value) {
  return value && typeof value.enabled === "boolean" && typeof value.parked === "boolean" && typeof value.keyPresent === "boolean" &&
    value.release && typeof value.release.installed === "boolean" && value.preferences && Array.isArray(value.devices) &&
    value.import && Number.isSafeInteger(value.maxUploadBytes) && value.maxUploadBytes > 0 && value.links
}

// Name and size checks that catch the usual wrong downloads before sending anything.
export function archivePreflight(file) {
  const name = typeof file?.name === "string" ? file.name : ""
  if (/arm32|armv7|x86_64|amd64/i.test(name)) return "That’s the download for a different computer. Choose ARMv8/AArch64 Linux (soloist_release_arm64.tar.gz)."
  if (/\.tar$/i.test(name)) return "Your browser unpacked the download. Download it again and keep the .tar.gz file as it is."
  if (/^soloist$/i.test(name)) return "That’s the unpacked player. Upload the .tar.gz file exactly as it downloaded."
  if (name && !/\.(tar\.gz|tgz|gz)$/i.test(name)) return "Choose the soloist_release_arm64.tar.gz file you downloaded."
  return ""
}

export function importProblem(job) {
  if (job?.state !== "failed") return ""
  switch (job.code) {
    case "NOT_ARCHIVE": return "That isn’t the Soloist download. Choose soloist_release_arm64.tar.gz."
    case "CORRUPT": return "This file looks incomplete or damaged. Download it again and wait for it to finish."
    case "WRONG_ARCH": return "That’s the download for a different computer. On Spotify’s page, choose ARMv8/AArch64 Linux."
    case "NO_PLAYER": case "UNSAFE": return "This archive isn’t a Soloist release. Download it again from Spotify’s page."
    case "NOT_OFFICIAL": return "This file doesn’t match the build Spotify is offering right now. Spotify may have just released a new one; download it again and upload the new file."
    case "OFFLINE": return "Your comma needs an internet connection to check this download with Spotify. Connect it to Wi‑Fi or cellular and try again."
    case "EXPIRED": return "This Soloist build has expired. Download the newest one from Spotify."
    case "INCOMPATIBLE": return job.error || "This Soloist build doesn’t run on this comma yet."
    case "DRIVING": return "Put the car in Park or use offroad mode, then install again."
    case "TOO_LARGE": return "This file is too large to be the Soloist download."
    case "CANCELLED": return "Setup authorization changed. Sign in to Galaxy and try again."
    default: return job.error || "Something went wrong. Try again."
  }
}

export function installChecks(job) {
  const at = job?.state === "done" ? STAGES.length : STAGES.indexOf(job?.stage)
  const ends = CHECKS.map((_, index) => STAGES.indexOf(index + 1 < CHECKS.length ? CHECKS[index + 1].stage : "done"))
  let failed = -1
  if (job?.state === "failed") {
    failed = CHECKS.findIndex((check) => check.codes.includes(job.code))
    if (failed < 0) failed = Math.max(0, ends.findIndex((end) => at < end))
  }
  return CHECKS.map((check, index) => ({
    label: check.label,
    status: failed >= 0 ? (index < failed ? "done" : index === failed ? "failed" : "pending") :
      at >= ends[index] ? "done" : at >= STAGES.indexOf(check.stage) ? "active" : "pending",
  }))
}

export function releaseInfo(release, locale = undefined) {
  if (!release?.installed) return { level: "none", label: "Not installed" }
  const date = release.expires ? new Date(release.expires) : null
  const on = date && !Number.isNaN(date.getTime()) ? date.toLocaleDateString(locale, { month: "short", day: "numeric" }) : ""
  const version = release.version ? `Version ${release.version}` : "Installed"
  if (release.expired) return { level: "expired", label: `${version} · expired${on ? ` on ${on}` : ""}` }
  if (release.level === "soon") return { level: "soon", label: `${version} · expires in ${release.daysLeft} day${release.daysLeft === 1 ? "" : "s"}` }
  return { level: "ok", label: `${version}${on ? ` · works until ${on}` : ""}` }
}

const STATE_TEXT = {
  missing_package: "Install Spotify Soloist to finish setup.",
  missing_key: "Add your API key to finish setup.",
  no_output: "Choose where music plays.",
  audio_unavailable: "This StarPilot build is missing Spotify’s audio component.",
  waiting_output: "Waiting for your speaker to connect.",
  starting: "Starting…",
  connecting: "Starting…",
  waiting: "Ready to pair. Open Spotify on your phone and pick this device.",
  ready: "Ready. Pick this device in Spotify to play.",
  playing: "Playing",
  retrying: "Restarting…",
  failed: "Spotify couldn’t start.",
  expired: "This Soloist build expired. Install the newest one.",
}

export function serviceLabel(setup) {
  if (!setup?.enabled) return "Off"
  const service = setup.service
  if (!service) return "Starting…"
  if (service.state === "ready" && service.player?.status === "paused") return "Paused"
  return service.message && !["ready", "playing", "waiting"].includes(service.state) ? service.message : STATE_TEXT[service.state] || "Starting…"
}

// Where the track is now, from Soloist's anchor and the elapsed wall-clock time since it.
export function positionNow(position, durationMs, now = Date.now()) {
  if (!position) return 0
  const value = position.ms + Math.max(0, now - position.at) * position.speed
  return Math.max(0, Math.min(durationMs ?? value, value))
}

export function formatTime(ms) {
  const seconds = Math.floor((ms || 0) / 1000)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`
}

export class SpotifyFeed {
  constructor({ publish, unauthorized = () => { }, fetcher = (...args) => fetch(...args), uploader = uploadPackage,
    later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, uploader, later, cancelTimer })
    this.active = false
    this.generation = 0
    this.pollTimer = null
    this.setup = null
    this.busy = false
    this.uploadProgress = null
    this.error = ""
  }

  emit() { this.publish({ setup: this.setup, busy: this.busy, uploadProgress: this.uploadProgress, error: this.error }) }

  start() { this.stop(); this.active = true; return this.refresh() }

  stop() {
    this.active = false
    this.generation++
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    this.pollTimer = null
    this.busy = false
    this.uploadProgress = null
    this.emit()
  }

  schedule() {
    if (!this.active) return
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    const fast = this.setup?.import?.state === "running" || this.setup?.service?.player?.connected
    this.pollTimer = this.later(() => { this.pollTimer = null; this.refresh() }, fast ? 1500 : 4000)
  }

  async request(path, options = {}, timeout = 8000, transport = this.fetcher) {
    const generation = this.generation
    try {
      const { response, data } = await requestJson(path, {
        fetcher: transport, timeout, later: this.later, cancel: this.cancelTimer, request: options, withResponse: true
      })
      if (!this.active || this.generation !== generation) return null
      if (response.status === 401) { this.stop(); this.unauthorized(); return null }
      if (!response.ok) throw new Error(data?.error || "Spotify setup is unavailable")
      return data
    } catch (error) {
      if (this.active && this.generation === generation) {
        this.error = error.name === "TimeoutError" ? "Your comma took too long to respond. Retrying…" : connectionError(error)
        this.emit()
      }
      return null
    }
  }

  async refresh() {
    if (!this.active) return
    const setup = await this.request("./api/spotify/setup")
    if (setup && validSetup(setup)) { this.setup = setup; if (!this.busy) this.error = "" }
    else if (setup) this.error = "Spotify setup response changed"
    this.emit()
    this.schedule()
  }

  async post(path, body, timeout = 10000) {
    if (!this.active || this.busy) return null
    this.busy = true
    this.error = ""
    this.emit()
    const result = await this.request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }, timeout)
    this.busy = false
    if (result && validSetup(result)) this.setup = result
    this.emit()
    if (result) this.refresh()
    return result
  }

  // Playback controls stay outside the busy gate so a slow command never blocks the next tap.
  async control(action, args = undefined) {
    if (!this.active) return null
    const result = await this.request("./api/spotify/control", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(args === undefined ? { action } : { action, args })
    }, 5000)
    if (result) this.later(() => this.refresh(), 400)
    return result
  }

  async upload(file) {
    if (!this.active || this.busy || !this.setup || this.setup.import?.state === "running" ||
      !file || !Number.isSafeInteger(file.size) || file.size <= 0 || file.size > this.setup.maxUploadBytes) return false
    this.busy = true
    this.uploadProgress = { loaded: 0, total: file.size }
    this.emit()
    const generation = this.generation
    const transport = (path, options) => this.uploader(path, options, (progress) => {
      if (this.active && generation === this.generation) { this.uploadProgress = progress; this.emit() }
    })
    const result = await this.request("./api/spotify/upload", {
      method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file
    }, 180000, transport)
    this.busy = false
    this.uploadProgress = null
    if (result && validSetup(result)) this.setup = result
    this.emit()
    this.schedule()
    return result !== null
  }

  async removeAll() {
    if (!this.active || this.busy) return false
    this.busy = true
    this.emit()
    const result = await this.request("./api/spotify", { method: "DELETE" }, 30000)
    this.busy = false
    if (result && validSetup(result)) this.setup = result
    this.emit()
    return result !== null
  }
}

export const SpotifyPage = {
  components: { GxNotice, GxDialog, GalaxySettingRow },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({
    setup: null, busy: false, error: "", uploadProgress: null, now: Date.now(),
    installOpen: false, removeOpen: false, resetOpen: false, showSetup: false, downloadStarted: false,
    archiveFile: null, archiveMagicError: "", archiveChecking: false, archiveSelection: 0, installAttempted: false, installBaseline: null,
    keyValue: "", keyEditing: false, nameValue: "", volumeDraft: null,
  }),
  mounted() {
    this.feed = new SpotifyFeed({ publish: (value) => Object.assign(this, value), unauthorized: this.unauthorized })
    this.visibility = () => { if (document.hidden) this.feed.stop(); else this.feed.start() }
    document.addEventListener("visibilitychange", this.visibility)
    this.clock = setInterval(() => { this.now = Date.now() }, 1000)
    if (!document.hidden) this.feed.start()
  },
  beforeUnmount() {
    document.removeEventListener("visibilitychange", this.visibility)
    clearInterval(this.clock)
    this.keyValue = ""
    this.feed?.stop()
  },
  watch: {
    mode() { if (!document.hidden) this.feed.start(); else this.feed.stop() },
    "setup.preferences.deviceName": { immediate: true, handler(value) { if (typeof value === "string") this.nameValue = value } },
  },
  computed: {
    release() { return releaseInfo(this.setup?.release) },
    installed() { return !!this.setup?.release.installed && !this.setup.release.expired },
    outputChosen() {
      const prefs = this.setup?.preferences
      return !!prefs && (["test", "android_auto"].includes(prefs.output) || ADDRESS.test(prefs.outputAddress))
    },
    setupDone() { return !!(this.installed && this.setup?.keyPresent && this.outputChosen) },
    player() { return this.setup?.service?.player || null },
    playing() { return this.player?.status === "playing" },
    track() { return this.player?.loggedIn ? this.player.track : null },
    can() { return new Set(this.player?.actions || []) },
    elapsed() { return positionNow(this.player?.position, this.track?.durationMs, this.now) },
    statusText() { return serviceLabel(this.setup) },
    outputName() {
      const prefs = this.setup?.preferences
      if (!prefs) return ""
      if (prefs.output === "android_auto") return "Android Auto"
      return prefs.output === "test" ? "Silent test output" : prefs.outputName || prefs.outputAddress || "Not chosen"
    },
    uploadPercent() {
      const { loaded, total } = this.uploadProgress || {}
      return total > 0 ? Math.min(100, Math.round(100 * loaded / total)) : 0
    },
    onPhone() {
      return typeof navigator !== "undefined" && (navigator.userAgentData?.mobile === true ||
        /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || "") || navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
    },
    downloadsHint() {
      if (typeof navigator === "undefined") return ""
      if (/iPhone|iPad|iPod/i.test(navigator.userAgent || "") || navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1) return "In Files, open Downloads."
      return /Android/i.test(navigator.userAgent || "") ? "Open Downloads." : ""
    },
    archiveError() {
      if (!this.archiveFile) return ""
      const preflight = archivePreflight(this.archiveFile)
      if (preflight) return preflight
      if (!Number.isSafeInteger(this.archiveFile.size) || this.archiveFile.size <= 0) return "The selected file is empty or its size cannot be read."
      if (this.setup && this.archiveFile.size > this.setup.maxUploadBytes) return "This file is too large to be the Soloist download."
      return this.archiveMagicError
    },
    uploadReason() {
      if (!this.archiveFile) return "Choose the file you downloaded."
      if (this.archiveError) return this.archiveError
      if (this.archiveChecking) return "Checking the file…"
      if (!this.setup?.parked) return "Put the car in Park or use offroad mode to install."
      if (this.setup.import?.state === "running") return "Wait for the current install to finish."
      return ""
    },
    installState() {
      const job = this.setup?.import
      const current = this.installAttempted && job && job.started !== this.installBaseline
      if (this.uploadProgress || this.installAttempted && this.busy && !current) return "uploading"
      if (job?.state === "running") return "checking"
      if (!current) return "choose"
      if (job.state === "done" && this.setup.release.installed) return "done"
      return job.state === "failed" ? "failed" : "choose"
    },
    checks() { return installChecks(this.setup?.import) },
    problem() { return importProblem(this.setup?.import) },
    keyValid() { return /^[A-Za-z0-9._~+/=-]{16,256}$/.test(this.keyValue.trim()) },
    nameValid() { return /^[^\x00-\x1f\x7f]{1,40}$/.test(this.nameValue.trim()) },
    outputChoices() {
      const devices = this.setup?.devices || []
      return devices.map((device) => ({ value: device.address, label: device.name + (device.connected ? " · connected" : "") }))
    },
  },
  methods: {
    switchRow, formatTime,
    setEnabled(enabled) { return this.feed.post("./api/spotify/enable", { enabled }) },
    async saveKey() {
      if (!this.keyValid || this.busy) return
      const key = this.keyValue.trim()
      this.keyValue = ""
      const result = await this.feed.post("./api/spotify/key", { key })
      if (result) this.keyEditing = false
    },
    removeKey() { return this.feed.post("./api/spotify/maintenance", { action: "remove_key" }) },
    chooseOutput(event) {
      const value = event.target.value
      if (["test", "android_auto"].includes(value)) return this.feed.post("./api/spotify/preferences", { output: value, outputAddress: "" })
      if (ADDRESS.test(value)) return this.feed.post("./api/spotify/preferences", { output: "bluetooth", outputAddress: value })
    },
    saveName() {
      if (!this.nameValid || this.nameValue.trim() === this.setup?.preferences.deviceName) return
      return this.feed.post("./api/spotify/preferences", { deviceName: this.nameValue.trim() })
    },
    saveCache(event) { return this.feed.post("./api/spotify/preferences", { cacheMb: Number(event.target.value) }) },
    clearCache() { return this.feed.post("./api/spotify/maintenance", { action: "clear_cache" }, 20000) },
    async resetSession() { this.resetOpen = false; return this.feed.post("./api/spotify/maintenance", { action: "reset_session" }, 20000) },
    async removeAll() { this.removeOpen = false; return this.feed.removeAll() },
    control(action, args) { return this.feed.control(action, args) },
    togglePlay() { return this.control(this.playing ? "pause" : "play") },
    commitVolume(event) {
      const volume = Math.round(Number(event.target.value))
      this.volumeDraft = null
      if (Number.isInteger(volume) && volume >= 0 && volume <= 100) return this.control("volume", { volume })
    },
    openInstall() { this.chooseAgain(); Object.assign(this, { installOpen: true, downloadStarted: false }) },
    closeInstall() { this.installOpen = false },
    markDownloadStarted() {
      if (!this.busy && ["choose", "failed"].includes(this.installState)) this.chooseAgain()
      this.downloadStarted = true
    },
    chooseAgain() {
      this.archiveSelection++
      Object.assign(this, { installAttempted: false, archiveFile: null, archiveMagicError: "", archiveChecking: false })
    },
    async chooseArchive(event) {
      const file = event.target.files?.[0] || null
      const selection = ++this.archiveSelection
      Object.assign(this, { archiveFile: file, archiveMagicError: "", archiveChecking: false })
      if (!file || archivePreflight(file) || !Number.isSafeInteger(file.size) || file.size <= 0 || file.size > this.setup?.maxUploadBytes) return
      this.archiveChecking = true
      let error = ""
      try {
        const bytes = new Uint8Array(await file.slice(0, 2).arrayBuffer())
        if (bytes[0] !== 0x1f || bytes[1] !== 0x8b) error = "That isn’t the Soloist download. Choose soloist_release_arm64.tar.gz."
        else if (file.size < 1024 * 1024) error = "This file is too small to be the Soloist download. Download it again."
      } catch { error = "The file couldn’t be read. Choose it again." }
      if (selection === this.archiveSelection) Object.assign(this, { archiveMagicError: error, archiveChecking: false })
    },
    async upload() {
      if (this.busy || this.uploadReason) return false
      Object.assign(this, { installAttempted: true, installBaseline: this.setup.import?.started ?? null })
      return this.feed.upload(this.archiveFile)
    },
  },
  template: `
    <section class="gx-driving gx-spotify" aria-label="Spotify" :aria-busy="busy || undefined">
      <header class="gx-page-header">
        <h2>Spotify</h2>
        <p>Play Spotify through your car or a Bluetooth speaker, with your comma as a Spotify Connect device you control from the Spotify app.</p>
      </header>
      <GxNotice tone="danger" v-if="error && setup">{{ error }}</GxNotice>
      <GxNotice v-if="!setup" :busy="!error" :tone="error ? 'danger' : 'info'">{{ error || "Checking Spotify setup… Reconnecting automatically…" }}</GxNotice>

      <section v-if="setup && setupDone" class="gx-card gx-aa-step gx-aa-home gx-spotify-now" aria-labelledby="gx-spotify-now-title">
        <div class="gx-spotify-now__main">
          <img v-if="track?.artwork" class="gx-spotify-now__art" :src="track.artwork" alt="" referrerpolicy="no-referrer" loading="lazy" />
          <span v-else class="gx-spotify-now__art gx-spotify-now__art--empty" aria-hidden="true"><i class="bi bi-music-note-beamed"></i></span>
          <div class="gx-spotify-now__text">
            <h3 id="gx-spotify-now-title">{{ track?.title || setup.preferences.deviceName }}</h3>
            <p v-if="track">{{ track.artists }}<template v-if="track.album"> · {{ track.album }}</template></p>
            <p role="status" class="gx-note">{{ statusText }}<template v-if="setup.enabled"> · {{ outputName }}</template></p>
          </div>
        </div>
        <div v-if="track && track.durationMs" class="gx-spotify-now__progress">
          <input type="range" min="0" :max="track.durationMs" step="1000" :value="elapsed" :disabled="!can.has('seek')" aria-label="Position"
            @change="control('seek', { positionMs: Math.round(Number($event.target.value)) })" />
          <small class="gx-note">{{ formatTime(elapsed) }} / {{ formatTime(track.durationMs) }}</small>
        </div>
        <div v-if="setup.enabled && player?.loggedIn" class="gx-actions gx-spotify-now__controls">
          <button type="button" class="gx-icon-btn" aria-label="Previous" :disabled="!can.has('skip_prev')" @click="control('previous')"><i class="bi bi-skip-start-fill"></i></button>
          <button type="button" class="gx-btn gx-spotify-now__play" :aria-label="playing ? 'Pause' : 'Play'" :disabled="!can.has(playing ? 'pause' : 'play') && !!track" @click="togglePlay">
            <i :class="playing ? 'bi bi-pause-fill' : 'bi bi-play-fill'" aria-hidden="true"></i></button>
          <button type="button" class="gx-icon-btn" aria-label="Next" :disabled="!can.has('skip_next')" @click="control('next')"><i class="bi bi-skip-end-fill"></i></button>
          <label v-if="player.volume !== null" class="gx-spotify-now__volume"><i class="bi bi-volume-up" aria-hidden="true"></i>
            <input type="range" min="0" max="100" step="1" :value="volumeDraft ?? player.volume" aria-label="Volume"
              @input="volumeDraft = Number($event.target.value)" @change="commitVolume" /></label>
        </div>
        <button v-if="setup.enabled && player?.loggedIn && !player.active" type="button" class="gx-btn gx-btn--tonal" @click="control('activate')">
          <i class="bi bi-broadcast" aria-hidden="true"></i> Play Here</button>
        <GalaxySettingRow :row="switchRow('Spotify', setup.enabled, 'Turn off to stop playing and free up the comma. Your setup stays saved.')"
          :index="0" :busy="busy" :save-value="(index, value) => setEnabled(value === 'On')" />
        <div class="gx-actions">
          <button type="button" class="gx-btn gx-btn--tonal" :aria-expanded="showSetup" aria-controls="gx-spotify-steps" @click="showSetup = !showSetup">
            <i :class="showSetup ? 'bi bi-chevron-up' : 'bi bi-gear'" aria-hidden="true"></i> {{ showSetup ? 'Hide Setup' : 'Setup and Settings' }}</button>
        </div>
      </section>

      <ol v-if="setup" v-show="!setupDone || showSetup" id="gx-spotify-steps" class="gx-aa__steps">
        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': installed }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="installed" class="bi bi-check-lg"></i><template v-else>1</template></span>
            <div><h3>Spotify Soloist</h3><p>Spotify’s player for devices like your comma. You download it from Spotify, then upload it here.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <div class="gx-aa-status">
              <span class="gx-aa-pill" :class="'gx-aa-pill--' + release.level" role="status">{{ release.label }}</span>
              <div class="gx-actions gx-aa-status__actions">
                <button v-if="!setup.release.installed" class="gx-btn" @click="openInstall">Install</button>
                <button v-else-if="release.level !== 'ok'" class="gx-btn" @click="openInstall">Update</button>
                <button v-else class="gx-btn gx-btn--tonal" @click="openInstall">Install newer version</button>
              </div>
            </div>
            <p v-if="setup.import?.state === 'running' && !installOpen" class="gx-note" role="status">Installing…</p>
            <p class="gx-note">Each Soloist build works for 90 days. Before it runs out, this step shows <strong>Update</strong>; download again the same way.</p>
          </div>
        </li>

        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': setup.keyPresent }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="setup.keyPresent" class="bi bi-check-lg"></i><template v-else>2</template></span>
            <div><h3>Your API Key</h3><p>Spotify gives each person their own key. Creating one needs Spotify Premium.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <template v-if="setup.keyPresent && !keyEditing">
              <span class="gx-aa-pill gx-aa-pill--ok" role="status">Key saved on this comma</span>
              <div class="gx-actions">
                <button type="button" class="gx-btn gx-btn--tonal" @click="keyEditing = true">Replace Key</button>
                <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="removeKey">Remove Key</button>
              </div>
            </template>
            <template v-else>
              <a class="gx-btn gx-btn--tonal" :href="setup.links.key" target="_blank" rel="noopener noreferrer">
                <i class="bi bi-box-arrow-up-right" aria-hidden="true"></i> Create Your API Key</a>
              <form class="gx-stack" @submit.prevent="saveKey">
                <label class="gx-stack"><span>Paste your key</span>
                  <input class="gx-field" type="password" v-model="keyValue" autocomplete="off" autocapitalize="off" spellcheck="false"
                    inputmode="text" maxlength="256" aria-describedby="gx-spotify-key-note" /></label>
                <div class="gx-actions">
                  <button type="submit" class="gx-btn" :disabled="!keyValid || busy">Save Key</button>
                  <button v-if="keyEditing" type="button" class="gx-btn gx-btn--tonal" @click="keyEditing = false; keyValue = ''">Cancel</button>
                </div>
              </form>
              <small id="gx-spotify-key-note" class="gx-note">The key stays on your comma and is never shown again. On your home network Galaxy isn’t encrypted, so save it from a network you trust.</small>
            </template>
          </div>
        </li>

        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': outputChosen }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="outputChosen" class="bi bi-check-lg"></i><template v-else>3</template></span>
            <div><h3>Where Music Plays</h3><p>Through Android Auto, or your car or a speaker over Bluetooth. Alerts keep playing from the comma itself.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <label class="gx-stack"><span>Play on</span>
              <select class="gx-field" :value="setup.preferences.output === 'bluetooth' ? setup.preferences.outputAddress : setup.preferences.output" :disabled="busy || !setup.parked" @change="chooseOutput">
                <option value="" disabled>Choose…</option>
                <option value="android_auto">Android Auto (with StarPilot on the car screen)</option>
                <optgroup label="Bluetooth">
                  <option v-for="choice in outputChoices" :key="choice.value" :value="choice.value">{{ choice.label }}</option>
                </optgroup>
                <option value="test">Silent test (no speaker)</option>
              </select></label>
            <small v-if="!setup.parked" class="gx-note">Put the car in Park or use offroad mode to change this.</small>
            <p v-if="setup.preferences.output === 'android_auto'" class="gx-note">Music plays through the car while <a class="gx-link" href="#/android-auto">Android Auto</a> is connected, and the car shows it as Android Auto audio. If you switch the car to the radio, Spotify pauses.</p>
            <p v-else-if="!outputChoices.length" class="gx-note">No paired devices yet. Pair your car or speaker on the <a class="gx-link" href="#/bluetooth">Bluetooth</a> page first.</p>
            <p v-else-if="setup.preferences.output === 'bluetooth'" class="gx-note">Don’t see it? Pair it on the <a class="gx-link" href="#/bluetooth">Bluetooth</a> page. In your car, choose <strong>Bluetooth Audio</strong> as the source.</p>
          </div>
        </li>

        <li class="gx-card gx-aa-step" :class="{ 'gx-aa-step--done': setupDone && setup.enabled && player?.loggedIn }">
          <div class="gx-aa-step__head">
            <span class="gx-aa-step__num" aria-hidden="true"><i v-if="setupDone && setup.enabled && player?.loggedIn" class="bi bi-check-lg"></i><template v-else>4</template></span>
            <div><h3>Connect Spotify</h3><p>Turn it on, then pick <strong>{{ setup.preferences.deviceName }}</strong> in the Spotify app’s device list.</p></div>
          </div>
          <div class="gx-aa-step__body">
            <GalaxySettingRow :row="switchRow('Spotify', setup.enabled, 'Runs Spotify on your comma. Turn off to stop playing; your setup stays saved.')"
              :index="0" :busy="busy" :save-value="(index, value) => setEnabled(value === 'On')" />
            <p v-if="setup.enabled" class="gx-note" role="status">{{ statusText }}</p>
            <p class="gx-note">The first time, your phone has to be on the same Wi‑Fi or hotspot as your comma. After that, Spotify remembers it.</p>
            <form class="gx-stack" @submit.prevent="saveName">
              <label class="gx-stack"><span>Name in Spotify</span>
                <input class="gx-field" type="text" v-model="nameValue" maxlength="40" autocomplete="off" /></label>
              <button type="submit" class="gx-btn gx-btn--tonal" :disabled="busy || !nameValid || nameValue.trim() === setup.preferences.deviceName">Save Name</button>
            </form>
          </div>
        </li>
      </ol>

      <section v-if="setup && (setupDone ? showSetup : setup.release.installed)" class="gx-card gx-stack" aria-labelledby="gx-spotify-manage-title">
        <h3 id="gx-spotify-manage-title">Storage and Account</h3>
        <label class="gx-stack"><span>Music cache</span>
          <select class="gx-field" :value="setup.preferences.cacheMb" :disabled="busy" @change="saveCache">
            <option v-for="size in setup.cacheChoices" :key="size" :value="size">{{ size >= 1024 ? (size / 1024) + ' GB' : size + ' MB' }}</option>
          </select></label>
        <div class="gx-actions">
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy || !setup.parked" @click="clearCache">Clear Cache</button>
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy || !setup.parked" @click="resetOpen = true">Use a Different Spotify Account</button>
          <button type="button" class="gx-btn gx-btn--danger" :disabled="busy || setup.import?.state === 'running'" @click="removeOpen = true">Remove Spotify</button>
        </div>
      </section>

      <section class="gx-settings gx-aa-wiki-list" aria-label="Spotify help">
        <h4>Help</h4>
        <details class="gx-aa-wiki"><summary>Why do I download Soloist myself?</summary>
          <p>Spotify asks that each person download Soloist from Spotify and use their own API key, so StarPilot can’t include it. Your comma checks that the file you upload is exactly what Spotify is offering before installing it.</p>
        </details>
        <details class="gx-aa-wiki"><summary>Spotify doesn’t show my comma</summary>
          <ol>
            <li>Make sure step 4 says <strong>Ready to pair</strong>.</li>
            <li>Put your phone on the same Wi‑Fi or hotspot as your comma. Some hotspots and guest networks block devices from seeing each other.</li>
            <li>In Spotify, tap the device icon and look for <strong>{{ setup?.preferences.deviceName || 'StarPilot' }}</strong>.</li>
          </ol>
        </details>
        <details class="gx-aa-wiki"><summary>Does it use my data plan?</summary>
          <p>Yes, when your comma streams over cellular. Music usually uses about 40–150 MB an hour depending on quality. Songs you’ve played recently come from the cache instead.</p>
        </details>
        <details class="gx-aa-wiki"><summary>Will music cover up StarPilot’s alerts?</summary>
          <p>Music plays through your car or speaker; alerts keep playing from the comma’s own speaker. Keep the music at a level where you can still hear the comma.</p>
        </details>
        <details class="gx-aa-wiki"><summary>Can I use it with Android Auto?</summary>
          <p>Yes. In step 3 choose <strong>Android Auto</strong>, and music plays through the car as Android Auto audio alongside the StarPilot screen. It needs Android Auto to be connected, so if it isn’t, music has nowhere to play.</p>
        </details>
        <details class="gx-aa-wiki"><summary>More help from Spotify</summary>
          <p><a class="gx-link" :href="setup?.links.help || '#'" target="_blank" rel="noopener noreferrer">Spotify’s Soloist getting-started guide</a></p>
        </details>
      </section>

      <GxDialog v-if="resetOpen && setup" labelledby="gx-spotify-reset-title" describedby="gx-spotify-reset-body" alert @close="resetOpen = false">
        <div><h3 id="gx-spotify-reset-title">Use a different Spotify account?</h3>
          <p id="gx-spotify-reset-body">This signs your comma out of Spotify and clears its cache. Then pick it in the Spotify app on the account you want.</p></div>
        <div class="gx-settings__controls gx-actions">
          <button type="button" class="gx-btn gx-btn--tonal" @click="resetOpen = false">Cancel</button>
          <button type="button" class="gx-btn" @click="resetSession">Sign Out</button>
        </div>
      </GxDialog>

      <GxDialog v-if="removeOpen && setup" labelledby="gx-spotify-remove-title" describedby="gx-spotify-remove-body" alert @close="removeOpen = false">
        <div><h3 id="gx-spotify-remove-title">Remove Spotify?</h3>
          <p id="gx-spotify-remove-body">This stops music and deletes Soloist, your API key, your Spotify sign-in and the music cache from this comma. Your Bluetooth devices and Android Auto setup stay as they are.</p></div>
        <div class="gx-settings__controls gx-actions">
          <button type="button" class="gx-btn gx-btn--tonal" @click="removeOpen = false">Cancel</button>
          <button type="button" class="gx-btn gx-btn--danger" @click="removeAll">Remove</button>
        </div>
      </GxDialog>

      <GxDialog v-if="installOpen && setup" labelledby="gx-spotify-install-title" class="gx-aa-sheet__dialog" @close="closeInstall">
        <div class="gx-aa-sheet__toolbar">
          <button type="button" class="gx-icon-btn" aria-label="Close" @click="closeInstall"><i class="bi bi-x-lg"></i></button>
        </div>
        <div class="gx-aa-sheet__body">
          <div v-if="installState === 'done'" class="gx-message gx-aa-sheet__done">
            <div class="gx-aa-done-badge"><i class="bi bi-check-lg" aria-hidden="true"></i></div>
            <h3 id="gx-spotify-install-title">Soloist is installed</h3>
            <p class="gx-note">{{ release.label }}</p>
            <ul class="gx-aa-checks"><li v-for="check in checks" :key="check.label" :class="'gx-aa-check--' + check.status">{{ check.label }}</li></ul>
            <button class="gx-btn gx-aa-cta" @click="closeInstall">Done</button>
          </div>
          <div v-else class="gx-stack">
            <div class="gx-stack gx-aa-sheet__head">
              <h3 id="gx-spotify-install-title">{{ setup.release.installed ? 'Install a Newer Soloist' : 'Install Spotify Soloist' }}</h3>
              <p class="gx-note">{{ setup.release.installed ? release.label + '. Your settings and Spotify sign-in stay as they are.' : 'Download it from Spotify, then send it to your comma.' }}</p>
            </div>
            <ol class="gx-aa-sheet__steps">
              <li class="gx-aa-step-card" :class="{ 'gx-aa-sheet__step--muted': installState !== 'choose' }">
                <div class="gx-aa-step-card__head">
                  <span class="gx-aa-step__num gx-aa-step-card__num">1</span>
                  <div class="gx-aa-step-card__title"><strong>Download Soloist</strong>
                    <small>From Spotify’s Downloads page, to this {{ onPhone ? 'phone' : 'computer' }}</small></div>
                </div>
                <div class="gx-aa-step-card__body">
                  <a class="gx-btn gx-btn--tonal" :href="setup.links.download" target="_blank" rel="noopener noreferrer" @click="markDownloadStarted">
                    <i class="bi bi-box-arrow-up-right" aria-hidden="true"></i> Open Spotify Downloads</a>
                  <ol class="gx-note gx-aa-mirror-steps">
                    <li>Download the <strong>ARMv8/AArch64 Linux</strong> build. The file is named <strong>{{ setup.archiveName }}</strong>.</li>
                    <li>Leave it as it is. Don’t unzip or open it.</li>
                  </ol>
                </div>
              </li>
              <li class="gx-aa-step-card" :class="{ 'gx-aa-sheet__step--muted': installState !== 'choose' }">
                <div class="gx-aa-step-card__head">
                  <span class="gx-aa-step__num gx-aa-step-card__num">2</span>
                  <div class="gx-aa-step-card__title"><strong>Choose the downloaded file</strong>
                    <small>{{ downloadStarted && downloadsHint ? downloadsHint : 'The file you just downloaded' }}</small></div>
                </div>
                <div class="gx-aa-step-card__body">
                  <label class="gx-btn gx-btn--tonal gx-aa-file" :class="{ 'gx-aa-file--disabled': installState !== 'choose' }">
                    <input type="file" :accept="onPhone ? undefined : '.gz,.tgz,application/gzip'" aria-label="Soloist .tar.gz download" :disabled="installState !== 'choose'" @change="chooseArchive" />
                    <i class="bi bi-folder2-open"></i> {{ archiveFile ? 'Choose a Different File' : 'Choose File' }}
                  </label>
                  <small v-if="archiveChecking" role="status" class="gx-note">Checking the file…</small>
                  <div v-if="archiveFile && !archiveError && !archiveChecking" class="gx-chip gx-aa-file-chip">
                    <i class="bi bi-file-earmark-zip"></i><span>{{ archiveFile.name }}</span><small>{{ Math.ceil(archiveFile.size / 1048576) }} MB</small>
                  </div>
                  <small v-if="archiveError" class="gx-aa-bad" role="alert">{{ archiveError }}</small>
                </div>
              </li>
              <li class="gx-aa-step-card">
                <div class="gx-aa-step-card__head">
                  <span class="gx-aa-step__num gx-aa-step-card__num">3</span>
                  <div class="gx-aa-step-card__title"><strong>Install</strong><small>Send it to your comma and check it with Spotify</small></div>
                </div>
                <div class="gx-aa-step-card__body">
                  <button v-if="installState === 'choose'" class="gx-btn gx-aa-cta" :disabled="!!uploadReason" @click="upload">Install</button>
                  <small v-if="installState === 'choose' && uploadReason && archiveFile && !archiveError" class="gx-note" role="status">{{ uploadReason }}</small>
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
              <small class="gx-note gx-aa-trademark">Spotify is a trademark of Spotify AB. StarPilot is not affiliated with or endorsed by Spotify.</small>
              <small class="gx-note">The uploaded file is deleted after install. Maximum size {{ Math.floor(setup.maxUploadBytes / 1048576) }} MB.</small>
            </div>
          </div>
        </div>
      </GxDialog>
    </section>`,
}
