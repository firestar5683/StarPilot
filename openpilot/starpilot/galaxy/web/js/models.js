import { GxDialog } from "./dialog.js"
import { GxState } from "./state.js"
import { GxSummary } from "./summary.js"
import { GxIconButton } from "./icon-button.js"
import { GxNotice } from "./notice.js"
import { connectionError } from "./polling.js"
import { GalaxySelect } from "./galaxy-select.js"

// Read-only model identity; a saved label never proves what modeld loaded.
export class ModelStatusFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancel = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, later, cancel })
    this.active = false
    this.generation = 0
    this.displayGeneration = 0
    this.request = null
    this.poll = null
    this.expiry = null
  }

  stop() {
    this.active = false
    this.generation++
    this.displayGeneration++
    this.request?.abort()
    this.request = null
    if (this.poll !== null) this.cancel(this.poll)
    if (this.expiry !== null) this.cancel(this.expiry)
    this.poll = this.expiry = null
    this.publish({ status: "idle", data: null, error: "" })
  }

  start() {
    this.stop()
    this.active = true
    return this.load()
  }

  async load() {
    if (!this.active) return
    const generation = ++this.generation
    this.request?.abort()
    if (this.poll !== null) this.cancel(this.poll)
    this.poll = null
    const request = new AbortController()
    this.request = request
    const timeout = this.later(() => request.abort(), 2500)
    try {
      const response = await this.fetcher("./api/models/status", { signal: request.signal, cache: "no-store" })
      if (!this.active || generation !== this.generation || request.signal.aborted) return
      if (response.status === 401) {
        this.stop()
        this.unauthorized()
        return
      }
      if (!response.ok) throw new Error("Model status is unavailable")
      const data = await response.json()
      if (!this.active || generation !== this.generation || request.signal.aborted) return
      const states = ["unavailable", "loading", "identity-unavailable", "active", "stale", "failed"]
      const variants = [null, "small", "chestnut"]
      const digest = data?.artifactSha256
      const ids = Array.isArray(data?.catalog) ? data.catalog.map(m => m?.id) : []
      if (data?.schemaVersion !== 1 || !ids.length || new Set(ids).size !== ids.length ||
          data.catalog.some(m => typeof m.id !== "string" || !m.id || typeof m.name !== "string" || typeof m.selectable !== "boolean") ||
          !ids.includes(data.requestedId) || !(data.loadedId === null || ids.includes(data.loadedId)) || !variants.includes(data.variant) ||
          !states.includes(data.health) || ![null, "chestnut-load-failed", "chestnut-run-stalled", "selected-load-failed"].includes(data.fallbackReason) ||
          !(digest === null || typeof digest === "string" && /^[0-9a-f]{64}$/.test(digest)) ||
          typeof data.pendingNextStart !== "boolean" ||
          (data.pendingNextStart && (data.loadedId === null || data.requestedId === data.loadedId)) ||
          (data.loadedId === null ? data.variant !== null || digest !== null : data.variant === null || digest === null) ||
          (data.health === "active" && data.loadedId === null)) {
        throw new Error("Invalid model status")
      }
      this.publish({ status: "ready", data, error: "" })
      if (this.expiry !== null) this.cancel(this.expiry)
      const displayGeneration = ++this.displayGeneration
      this.expiry = this.later(() => {
        if (this.active && displayGeneration === this.displayGeneration) {
          this.publish({ status: "stale", data: null, error: "Model status refresh delayed" })
        }
      }, 1500)
    } catch (error) {
      if (this.active && generation === this.generation) {
        this.displayGeneration++
        if (this.expiry !== null) this.cancel(this.expiry)
        this.expiry = null
        this.publish({ status: "unavailable", data: null, error: error.message })
      }
    } finally {
      this.cancel(timeout)
      if (generation === this.generation) this.request = null
      if (this.active && generation === this.generation) this.poll = this.later(() => this.load(), 1000)
    }
  }
}


const FILTER_KEY = "galaxy.modelManager.hardwareFilter";
const FILTERS = new Set(["both", "gpu", "comma"]);

function readHardwareFilter() {
  try {
    const value = localStorage.getItem(FILTER_KEY);
    return FILTERS.has(value) ? value : "both";
  } catch {
    return "both";
  }
}

function saveHardwareFilter(value) {
  const filter = FILTERS.has(value) ? value : "both";
  try { localStorage.setItem(FILTER_KEY, filter); } catch {}
  return filter;
}

function matchesHardware(model, filter) {
  if (filter === "gpu") return model?.requiresGpu === true;
  if (filter === "comma") return model?.requiresGpu === false;
  return true;
}

function hardwareLabel(model) {
  if (model?.requiresGpu === true) return "GPU · External";
  if (model?.requiresGpu === false) return "Comma · On-device";
  return "Hardware unknown";
}

function bytes(value) {
  return Number.isSafeInteger(value) && value > 0 ? value : null;
}

function formatBytes(value) {
  return value >= 1e9 ? `${(value / 1e9).toFixed(2)} GB` : `${(value / 1e6).toFixed(1)} MB`;
}

function fileSizeText(model) {
  const installed = bytes(model?.fileSizeBytes);
  const declared = bytes(model?.declaredSizeBytes || model?.artifactSize);
  const downloaded = bytes(model?.downloadedBytes);
  if (model?.partial || model?.sizeStatus === "partial") {
    return `Partial: ${downloaded ? formatBytes(downloaded) : "unknown"} / ${declared ? formatBytes(declared) : "unknown"}`;
  }
  if (installed && declared && installed !== declared) return `${formatBytes(installed)} · size mismatch`;
  if (installed) return formatBytes(installed);
  if (declared) return `${formatBytes(declared)} · declared`;
  return "Unavailable";
}


const actionPaths = { "select-small": "active", "select-big": "active", favorite: "preferences", unfavorite: "preferences",
  "enable-randomizer": "preferences", "disable-randomizer": "preferences", exclude: "preferences", include: "preferences",
  download: "download", downloadAll: "download_all", cancel: "cancel", delete: "delete", refresh: "refresh_manifest", jetlink: "jetlink" }
const actionCapabilities = { "select-small": "select", "select-big": "select", favorite: "favorites", unfavorite: "favorites",
  "enable-randomizer": "randomizer", "disable-randomizer": "randomizer", exclude: "exclusions", include: "exclusions",
  download: "download", downloadAll: "downloadAll", cancel: "cancel", delete: "delete", refresh: "refresh", jetlink: "jetlink" }

export function fitsModelProfile(model, profile) {
  return Array.isArray(model?.profiles) ? model.profiles.includes(profile) : profile === "big" ? model?.requiresGpu === true : model?.requiresGpu === false
}

export function modelActionAllowed(data, action, model = null) {
  if (!data || data.capabilities?.[actionCapabilities[action]] !== true) return false
  if (data.isOnroad !== false && !["favorite", "unfavorite", "cancel"].includes(action)) return false
  if (action === "jetlink") return data.jetlink !== undefined
  if (["select-small", "select-big"].includes(action)) {
    if (data.downloading || data.randomizer === true) return false
    if (action === "select-big" && model === null) return true
    return model?.installed === true && model.selectable === true && fitsModelProfile(model, action === "select-big" ? "big" : "small")
  }
  if (action === "download") return !data.downloading && !!model && !model.installed && model.downloadAvailable === true
  if (action === "downloadAll") return !data.downloading && data.models.some(m => !m.installed && m.downloadAvailable === true)
  if (action === "cancel") return data.downloading === true
  if (action === "delete") return !data.downloading && !!model && !model.builtin && model.deletable !== false &&
    (model.installed || model.partial) && ![data.currentModel, data.activeSmallModel, data.activeBigModel].includes(model.value)
  if (["exclude", "include"].includes(action)) return !!model
  if (["enable-randomizer", "disable-randomizer"].includes(action)) return !data.downloading
  return ["favorite", "unfavorite"].includes(action) ? !!model : action === "refresh" && !data.downloading
}

export class ModelManagerFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancel = id => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, later, cancel })
    this.active = false
    this.generation = 0
    this.request = this.poll = this.expiry = null
    this.data = null
    this.saving = false
    this.lastError = ""
  }
  stop() {
    this.active = false
    this.generation++
    this.request?.abort()
    this.request = null
    if (this.poll !== null) this.cancel(this.poll)
    this.poll = null
    if (this.expiry !== null) this.cancel(this.expiry)
    this.expiry = null
    this.data = null
    this.saving = false
    this.publish({ loading: false, data: null, error: "" })
  }
  start() {
    this.stop()
    this.active = true
    return this.load()
  }
  async requestJson(path, payload) {
    const generation = ++this.generation
    if (payload) this.lastError = ""
    this.request?.abort()
    if (this.poll !== null) this.cancel(this.poll)
    this.poll = null
    const request = new AbortController()
    this.request = request
    const timeout = this.later(() => {
      if (!this.active || generation !== this.generation) return
      request.abort()
      this.generation++
      this.request = null
      this.data = null
      this.saving = false
      this.lastError = payload ? "The result is unknown. Checking automatically…" : "Model Manager is unavailable. Reconnecting automatically…"
      this.publish({ loading: false, data: null, error: this.lastError })
      this.poll = this.later(() => this.load(), 2000)
    }, 10000)
    try {
      const response = await this.fetcher(`./api/models/${path}`, { signal: request.signal, cache: "no-store", credentials: "same-origin",
        ...(payload ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) } : {}) })
      if (!this.active || generation !== this.generation || request.signal.aborted) return null
      const data = await response.json()
      if (!this.active || generation !== this.generation || request.signal.aborted) return null
      if (response.status === 401 || ["access_unavailable", "setup_required"].includes(data?.code)) {
        this.stop()
        this.unauthorized()
        return null
      }
      if (!response.ok) throw new Error(data?.message || data?.error || "Model request failed")
      return data
    } catch (error) {
      if (this.active && generation === this.generation) {
        this.data = null
        this.lastError = connectionError(error)
        this.publish({ loading: false, data: null, error: this.lastError })
      }
      return null
    } finally {
      this.cancel(timeout)
      if (this.request === request) this.request = null
    }
  }
  async load() {
    if (!this.active || this.saving) return null
    if (!this.data && !this.lastError) this.publish({ loading: true, data: null, error: "" })
    const data = await this.requestJson("manager")
    if (!this.active) return null
    if (data) {
      if (data.schemaVersion !== 1 || !Array.isArray(data.models) ||
          data.models.some(m => !m || typeof m.value !== "string" || typeof m.label !== "string") ||
          typeof data.isOnroad !== "boolean" || typeof data.capabilities !== "object" || data.capabilities === null) {
        this.data = null
        this.publish({ loading: false, data: null, error: "Invalid Model Manager response" })
      } else {
        this.data = data
        this.lastError = ""
        if (this.expiry !== null) this.cancel(this.expiry)
        this.expiry = null
        if (data.jetlink?.active === true) {
          this.expiry = this.later(() => {
            this.expiry = null
            if (!this.active || this.data !== data) return
            this.data = { ...data, jetlink: { ...data.jetlink, active: false, state: "checking execution", runtimeState: "unavailable" } }
            this.publish({ loading: false, data: this.data, error: "" })
          }, 1500)
        }
        this.publish({ loading: false, data, error: "" })
      }
    }
    if (this.poll === null) this.poll = this.later(() => this.load(), this.data?.jetlink?.mode !== "off" && this.data?.jetlink ? 1000 : 2000)
    return this.data
  }
  async action(action, model = null, extra = {}) {
    if (!this.active || this.saving || !this.data) return null
    if (model !== null) {
      model = this.data.models.find(m => m.value === model.value)
      if (!model) return null
    }
    if (!modelActionAllowed(this.data, action, model)) return null
    const data = this.data
    const key = model?.value || ""
    let payload = action === "jetlink" ? extra : {}
    if (action.startsWith("select-")) payload = { profile: action === "select-big" ? "big" : "small", model: key }
    else if (["favorite", "unfavorite"].includes(action)) {
      const userFavorites = data.models.filter(m => m.userFavorite && m.value !== key).map(m => m.value)
      if (action === "favorite") userFavorites.push(key)
      payload = { userFavorites }
    } else if (["exclude", "include"].includes(action)) {
      const blacklistedModels = (data.blacklistedModels || []).filter(value => value !== key)
      if (action === "exclude") blacklistedModels.push(key)
      payload = { blacklistedModels }
    } else if (["enable-randomizer", "disable-randomizer"].includes(action)) payload = { randomizer: action === "enable-randomizer" }
    else if (["download", "delete"].includes(action)) payload = { model: key }
    if (["download", "downloadAll"].includes(action)) payload.allowGpuWithoutGpu = extra.allowGpuWithoutGpu === true
    if (typeof data.view === "string") payload.view = data.view
    this.saving = true
    this.data = null
    const result = await this.requestJson(actionPaths[action], payload)
    if (!this.active) return null
    this.saving = false
    const error = this.lastError
    await this.load()
    if (error && this.active) this.publish({ loading: false, data: this.data, error })
    return result
  }
}

export const ModelsPage = {
  name: "ModelsPage",
  components: { GxDialog, GxState, GxSummary, GxIconButton, GalaxySelect, GxNotice },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data() {
    return { loading: true, error: "", message: "", trackingProgress: false, busy: "", selectionUncertain: true, disposed: false,
      sortMode: "release_date", userFilter: "all", communityFilter: "all", hardwareFilter: readHardwareFilter(),
      models: [], currentModel: "", activeSmallModel: "", activeBigModel: "", capabilities: {},
      summary: { installed: 0, missing: 0, total: 0 }, status: { isOnroad: true },
      runtime: { status: "idle", data: null, error: "" }, dialog: null }
  },
  computed: {
    currentLabel() { return this.models.find(m => m.value === this.currentModel)?.label || this.currentModel || "none" },
    installedSmallModels() { return this.models.filter(m => (m.value === this.activeSmallModel || m.installed && m.selectable) && fitsModelProfile(m, "small")) },
    installedBigModels() { return this.models.filter(m => (m.value === this.activeBigModel || m.installed && m.selectable) && fitsModelProfile(m, "big")) },
    sorted() {
      return this.models.filter(m => matchesHardware(m, this.hardwareFilter))
        .filter(m => this.userFilter === "all" || !!m.userFavorite === (this.userFilter === "yes"))
        .filter(m => this.communityFilter === "all" || !!m.communityFavorite === (this.communityFilter === "yes"))
        .sort((a, b) => (this.sortMode === "release_date" ? (Date.parse(b.released) || 0) - (Date.parse(a.released) || 0) : 0) ||
          (a.label || a.value).localeCompare(b.label || b.value, undefined, { sensitivity: "base", numeric: true }))
    },
    downloadTargetLabel() { return this.status.downloadAll ? "all missing models" : this.models.find(m => m.value === this.status.modelToDownload)?.label || "a model" },
  },
  created() {
    this.feed = new ModelStatusFeed({ publish: update => { this.runtime = update }, unauthorized: this.unauthorized })
    this.manager = new ModelManagerFeed({ publish: update => {
      this.loading = update.loading
      this.error = update.error
      this.selectionUncertain = !update.data
      this.capabilities = update.data?.capabilities || {}
      if (!update.data && this.status.jetlink) this.status = { ...this.status, jetlink: { ...this.status.jetlink, active: false, state: "unavailable" } }
      if (update.data) {
        const p = update.data
        this.models = p.models
        this.currentModel = p.currentModel || ""
        this.activeSmallModel = p.activeSmallModel || ""
        this.activeBigModel = p.activeBigModel || ""
        this.summary = p.summary || { installed: 0, missing: 0, total: 0 }
        this.status = p
        if (this.trackingProgress && p.progress) {
          this.message = p.progress
          if (!p.downloading) this.trackingProgress = false
        }
      }
    }, unauthorized: this.unauthorized })
  },
  mounted() {
    this.visibility = () => {
      if (document.hidden) { this.finishDialog(false); this.feed.stop(); this.manager.stop() }
      else if (this.mode === "local") { this.feed.start(); this.manager.start() }
    }
    document.addEventListener("visibilitychange", this.visibility)
    if (this.mode === "local" && !document.hidden) { this.feed.start(); this.manager.start() }
  },
  beforeUnmount() {
    this.disposed = true
    this.finishDialog(false)
    document.removeEventListener("visibilitychange", this.visibility)
    this.feed.stop()
    this.manager.stop()
  },
  methods: {
    hardwareLabel, fileSizeText,
    setHardwareFilter(value) { this.hardwareFilter = saveHardwareFilter(value) },
    canAction(action, model = null) { return !this.busy && !this.selectionUncertain && modelActionAllowed(this.status, action, model) },
    rowState(model) {
      if ([this.currentModel, this.activeSmallModel, this.activeBigModel].includes(model.value)) return "active"
      if (this.status.downloading) return this.status.downloadAll || this.status.modelToDownload === model.value ? "cancellable" : "busy"
      return model.installed ? "installed" : "available"
    },
    confirmAction(dialog) {
      return new Promise(resolve => {
        this.dialog = dialog
        this.resolveDialog = resolve
        this.$nextTick(() => this.$refs.confirmButton?.focus())
      })
    },
    finishDialog(value) {
      this.resolveDialog?.(value)
      this.resolveDialog = null
      this.dialog = null
    },
    async configureJetlink(mode, chargePhone = this.status.jetlink?.chargePhone === true) {
      if (!this.canAction("jetlink")) return
      this.busy = "jetlink:"
      try {
        const result = await this.manager.action("jetlink", null, { mode, chargePhone })
        if (result) this.message = result.message
      } finally { this.busy = "" }
    },
    async runAction(action, model = null) {
      if (this.disposed || !this.canAction(action, model)) return
      this.busy = `${action}:${model?.value || ""}`
      this.message = ""
      this.trackingProgress = false
      try {
        let allowGpuWithoutGpu = false
        if (action === "enable-randomizer" && !await this.confirmAction({ title: "Model Randomizer", message: "Choose a different installed, verified model each start. Excluded models are skipped. Favorites do not change the random pool.", confirmLabel: "Enable" })) return
        if (action === "delete" && !await this.confirmAction({ title: "Delete Model", message: `Delete local files for "${model.label}"?`, confirmLabel: "Delete", danger: true })) return
        const needsGpu = action === "download" ? model.requiresGpu && !model.gpuAvailable : action === "downloadAll" &&
          this.models.some(m => !m.installed && m.requiresGpu && !m.gpuAvailable && m.downloadAvailable === true)
        if (needsGpu) {
          allowGpuWithoutGpu = await this.confirmAction({ title: "No External GPU Detected", confirmLabel: "Download Anyway",
            message: "These model files require an external GPU. You can download them now, but they cannot run until a compatible GPU is connected and detected. GPU model files can be large. Downloading does not activate a model." })
          if (!allowGpuWithoutGpu) return
        }
        if (this.disposed) return
        const result = await this.manager.action(action, model, { allowGpuWithoutGpu })
        if (!this.disposed && result) {
          this.trackingProgress = ["download", "downloadAll", "refresh"].includes(action)
          this.message = (this.trackingProgress && this.status.progress) || result.message ||
            (action.startsWith("select-") ? "Selection saved for the next start." : "Saved.")
        }
      } finally { if (!this.disposed) this.busy = "" }
    },
  },

  template: `
    <div class="gx-view gx-model-manager">
      <GxState v-if="mode !== 'local'">Model Manager is unavailable in the offline preview.</GxState>
      <GxState v-else-if="loading" loading>Reading installed models and available downloads…</GxState>

      <template v-else>
        <header class="gx-settings__header gx-page-header"><div><h2>Model Manager</h2>
          <p>Bundled model files, download state, and runtime health.</p></div></header>
        <GxNotice v-if="message" tone="info">{{ message }}</GxNotice>
        <GxNotice v-if="error" tone="danger" title="Model Manager">{{ error }}</GxNotice>
        <GxNotice v-if="status.isOnroad" tone="warn">Park the vehicle before changing or downloading models.</GxNotice>
        <GxNotice v-if="status.downloading" :title="'Downloading ' + downloadTargetLabel">{{ status.progress || 'Keep the device connected until the download finishes.' }}</GxNotice>
        <section class="gx-card">
          <div class="gx-section__header">
            <i aria-hidden="true" class="bi bi-cpu"></i>
            <span class="gx-section__title">Installed models</span>
          </div>
          <GxSummary :items="[{label: 'Installed', value: summary.installed}, {label: 'Missing', value: summary.missing}, {label: 'Total', value: summary.total}]" />
          <p class="gx-model-selection">Selected: <strong>{{ currentLabel }}</strong></p>
        </section>

        <section v-if="status.jetlink" class="gx-card">
          <div class="gx-section__header"><i aria-hidden="true" class="bi bi-usb-symbol"></i><span class="gx-section__title">Jetlink</span></div>
          <div class="gx-info-card">
            <div class="gx-field-group">
              <label for="gx-jetlink-mode" class="gx-row__label">Remote model connection</label>
              <GalaxySelect id="gx-jetlink-mode" class="gx-field" :value="status.jetlink.mode" :disabled="!canAction('jetlink')" @change="configureJetlink($event.target.value)">
                <option value="off">Off</option>
                <option value="usb" :disabled="!status.jetlink.supported || status.jetlink.chestnut">USB computer</option>
                <option value="ios" :disabled="!status.jetlink.supported || status.jetlink.chestnut">iPhone / iPad</option>
              </GalaxySelect>
            </div>
            <p class="gx-note" role="status"><span class="gx-chip">{{ status.jetlink.state }}</span><span v-if="status.jetlink.model && !status.jetlink.active"> · selected: {{ status.jetlink.model }}</span></p>
            <p v-if="status.jetlink.progress">{{ status.jetlink.progress }}</p>
            <p v-if="status.jetlink.reason" class="gx-model-reason">{{ status.jetlink.reason }}</p>
            <p v-if="status.jetlink.chestnut" class="gx-model-reason">Chestnut is connected. Jetlink stays off while Chestnut is fitted.</p>
            <p class="gx-model-reason">Prepared means the remote model is built, not active. The local Small model remains available. Small and Chestnut catalog selections are unchanged.</p>
            <div v-if="status.jetlink.mode === 'ios'" class="gx-row">
              <span class="gx-row__label">Charge phone over USB</span>
              <button class="gx-btn gx-btn--tonal" type="button" :aria-pressed="status.jetlink.chargePhone" :disabled="!canAction('jetlink')" @click="configureJetlink(status.jetlink.mode, !status.jetlink.chargePhone)">{{ status.jetlink.chargePhone ? 'On' : 'Off' }}</button>
            </div>
            <p class="gx-model-reason">Set up parked with a USB 3 data cable and separate power. Keep the computer awake; keep the iPhone app open and unlocked.</p>
            <a href="https://github.com/zoompilot/jetlink/blob/c17cd5c/docs/README.md" target="_blank" rel="noopener noreferrer">Jetlink setup guides</a>
          </div>
        </section>

        <section class="gx-card">
          <div class="gx-section__header">
            <i aria-hidden="true" class="bi bi-sliders"></i>
            <span class="gx-section__title">Controls</span>
          </div>
          <div class="gx-panel gx-stack">
            <p class="gx-note">Selections take effect the next time the driving model starts.</p>
            <div class="gx-actions">
              <button v-if="status.downloading" type="button" class="gx-btn gx-btn--danger" :disabled="!canAction('cancel')" @click="runAction('cancel')"><i aria-hidden="true" class="bi bi-stop-circle"></i> Cancel Download</button>
              <button v-else type="button" class="gx-btn" :disabled="!canAction('downloadAll')" @click="runAction('downloadAll')"><i aria-hidden="true" class="bi bi-download"></i> Download Missing Models</button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!canAction('refresh')" @click="runAction('refresh')"><i aria-hidden="true" v-if="busy === 'refresh:'" class="bi bi-arrow-repeat gx-spin"></i><i aria-hidden="true" v-else class="bi bi-arrow-clockwise"></i> Check model catalog</button>
            </div>

            <div class="gx-row gx-row--borderless">
              <span class="gx-row__label">Model Randomizer</span>
              <button type="button" class="gx-btn gx-btn--tonal" :aria-pressed="status.randomizer === true" :disabled="!canAction(status.randomizer ? 'disable-randomizer' : 'enable-randomizer')" @click="runAction(status.randomizer ? 'disable-randomizer' : 'enable-randomizer')">{{ status.randomizer ? 'On' : 'Off' }}</button>
            </div>
            <p v-if="status.randomizer" class="gx-model-reason">A different verified model is chosen each start. {{ status.gpuAvailable && activeBigModel ? 'Chestnut Big' : 'Small on-device' }} models are used. {{ (status.blacklistedModels || []).length }} excluded. Favorites only mark your preferred models.</p>
            <p v-if="!status.gpuAvailable" class="gx-model-reason">Chestnut is not detected. Active Small is used; your Big selection is saved for later.</p>

            <div class="gx-row gx-model-control gx-row--borderless">
              <span class="gx-row__label">Active Small · On-device</span>
              <GalaxySelect aria-label="Active Small" class="gx-field" :value="activeSmallModel" :disabled="!!busy || selectionUncertain || capabilities.select !== true || status.isOnroad || status.randomizer" @change="runAction('select-small', installedSmallModels.find(m => m.value === $event.target.value))">
                <option v-for="m in installedSmallModels" :key="m.value" :value="m.value" :disabled="!m.installed || !m.selectable">{{ m.label || m.value }}</option>
              </GalaxySelect>
            </div>

            <div class="gx-row gx-model-control gx-row--borderless">
              <span class="gx-row__label">Active Big · Chestnut</span>
              <GalaxySelect aria-label="Active Big" class="gx-field" :value="activeBigModel" :disabled="!!busy || selectionUncertain || capabilities.select !== true || status.isOnroad || status.randomizer" @change="$event.target.value ? runAction('select-big', installedBigModels.find(m => m.value === $event.target.value)) : runAction('select-big')">
                <option value="">None — always use Active Small</option>
                <option v-for="m in installedBigModels" :key="m.value" :value="m.value" :disabled="!m.installed || !m.selectable">{{ m.label || m.value }}</option>
              </GalaxySelect>
            </div>

            <div class="gx-row gx-model-control gx-row--borderless">
              <span class="gx-row__label">Sort</span>
              <GalaxySelect aria-label="Sort models" class="gx-field" :value="sortMode" @change="sortMode = $event.target.value">
                <option value="release_date">Release Date</option>
                <option value="alphabetical">Alphabetical</option>
              </GalaxySelect>
            </div>

            <div class="gx-row gx-model-control gx-row--borderless">
              <label class="gx-row__label" for="gx-model-hardware">Model hardware</label>
              <GalaxySelect id="gx-model-hardware" class="gx-field" :value="hardwareFilter" @change="setHardwareFilter($event.target.value)">
                <option value="both">Both</option>
                <option value="gpu">GPU models only</option>
                <option value="comma">Comma models only</option>
              </GalaxySelect>
            </div>

            <div class="gx-actions">
              <GalaxySelect aria-label="Your Favorite filter" class="gx-field gx-filter-field" :value="userFilter" @change="userFilter = $event.target.value">
                <option value="all">Your Favorite: All</option>
                <option value="yes">Your Favorite: Yes</option>
                <option value="no">Your Favorite: No</option>
              </GalaxySelect>
              <GalaxySelect aria-label="Community Favorite filter" class="gx-field gx-filter-field" :value="communityFilter" @change="communityFilter = $event.target.value">
                <option value="all">Community: All</option>
                <option value="yes">Community: Yes</option>
                <option value="no">Community: No</option>
              </GalaxySelect>
            </div>

          </div>
        </section>

        <template v-if="!sorted.length">
          <div class="gx-card"><div class="gx-empty">No models match these filters. Try Both or clear the favorite filters.</div></div>
        </template>
        <template v-else>
          <div class="gx-card-grid">
            <section class="gx-card" v-for="m in sorted" :key="m.value">
            <div class="gx-panel gx-cluster">
              <div class="gx-grow">
                <div class="gx-actions">
                  <strong>{{ m.label || m.value }}</strong>
                  <span v-if="m.userFavorite" class="gx-chip">Your Favorite</span>
                  <span v-if="m.communityFavorite" class="gx-chip">Community Favorite</span>
                  <span v-if="m.blacklisted" class="gx-chip">Excluded from randomizer</span>
                </div>
                <div class="gx-actions gx-tags">
                  <span class="gx-chip">{{ m.value }}</span>
                  <span v-if="m.builtin" class="gx-chip">Built-in</span>
                  <span class="gx-chip">{{ hardwareLabel(m) }}</span>
                  <span v-if="m.version" class="gx-chip">Version {{ m.version }}</span>
                  <span v-if="m.released" class="gx-chip">Released {{ m.released }}</span>
                  <span v-if="m.partial" class="gx-chip">Partial Files</span>
                  <span class="gx-chip">File size: {{ fileSizeText(m) }}</span>
                </div>
              </div>
              <button type="button" class="gx-icon-btn" :disabled="!canAction(m.userFavorite ? 'unfavorite' : 'favorite', m)" :aria-label="(m.userFavorite ? 'Remove from your favorites: ' : 'Add to your favorites: ') + m.label" :title="m.userFavorite ? 'Remove from your favorites' : 'Add to your favorites'" @click="runAction(m.userFavorite ? 'unfavorite' : 'favorite', m)">
                <i aria-hidden="true" class="bi" :class="m.userFavorite ? 'bi-star-fill' : 'bi-star'"></i>
              </button>
            </div>
            <p v-if="m.unavailableReason" class="gx-model-reason">{{ m.unavailableReason }}</p>
            <div class="gx-panel-footer gx-actions">
              <button v-if="status.randomizer || m.blacklisted" type="button" class="gx-btn gx-btn--tonal" :disabled="!canAction(m.blacklisted ? 'include' : 'exclude', m)" @click="runAction(m.blacklisted ? 'include' : 'exclude', m)">{{ m.blacklisted ? 'Include in Randomizer' : 'Exclude from Randomizer' }}</button>
              <template v-if="rowState(m) === 'active'">
                <span class="gx-chip gx-chip--selected">Selected model</span>
              </template>
              <template v-else-if="rowState(m) === 'busy'">
                <span class="gx-chip"><i aria-hidden="true" class="bi bi-hourglass-split"></i> Busy</span>
              </template>
              <template v-else-if="rowState(m) === 'cancellable'">
                <button type="button" class="gx-btn gx-btn--danger" :disabled="!canAction('cancel', m)" @click="runAction('cancel', m)"><i aria-hidden="true" class="bi bi-x-circle"></i> Cancel</button>
              </template>
              <template v-else-if="rowState(m) === 'installed'">
                <button type="button" class="gx-btn" :disabled="!canAction(m.requiresGpu ? 'select-big' : 'select-small', m)" @click="runAction(m.requiresGpu ? 'select-big' : 'select-small', m)"><i aria-hidden="true" class="bi bi-play-fill"></i> Set Active {{ m.requiresGpu ? 'Big' : 'Small' }}</button>
                <button v-if="!m.builtin" type="button" class="gx-btn gx-btn--tonal gx-text-danger" :disabled="!canAction('delete', m)" @click="runAction('delete', m)"><i aria-hidden="true" class="bi bi-trash"></i> Delete</button>
              </template>
              <template v-else>
                <GxIconButton :label="'Download ' + m.label" icon="bi-download" :disabled="!canAction('download', m)" @click="runAction('download', m)" />
              </template>
            </div>
            </section>
          </div>
        </template>
        <section class="gx-card gx-model-runtime">
          <div class="gx-section__header"><i aria-hidden="true" class="bi bi-cpu"></i><span class="gx-section__title">Running model</span></div>
          <div v-if="!selectionUncertain && status.jetlink?.active" class="gx-model-runtime__body">
            <p>Active · Jetlink remote model</p>
            <p v-if="status.jetlink.activeCheckpoint">{{ status.jetlink.activeCheckpoint }}</p>
            <p v-if="status.jetlink.activeArtifactSha256">{{ status.jetlink.activeArtifactSha256.slice(0,16) }}…</p>
          </div>
          <div class="gx-model-runtime__body" v-else-if="runtime.status === 'ready' && runtime.data">
            <p>{{ runtime.data.health.replaceAll('-', ' ') }} · {{ runtime.data.loadedId ? (runtime.data.variant === 'chestnut' ? 'Chestnut big' : 'Small') : 'No verified load receipt' }}</p>
            <p v-if="runtime.data.loadedId">{{ runtime.data.loadedId }} · {{ runtime.data.artifactSha256.slice(0,16) }}…</p>
            <p v-if="runtime.data.pendingNextStart">A saved selection is waiting for the next start.</p>
            <p v-if="runtime.data.fallbackReason">Fallback: {{ runtime.data.fallbackReason.replaceAll('-', ' ') }}</p>
          </div>
          <p v-else class="gx-panel gx-note">{{ runtime.error || 'Checking the running model…' }}</p>
        </section>
      </template>
      <GxDialog v-if="dialog" labelledby="gx-model-dialog-title" @close="finishDialog(false)">
          <h3 id="gx-model-dialog-title">{{ dialog.title }}</h3><p>{{ dialog.message }}</p>
          <div class="gx-settings__controls gx-actions"><button class="gx-btn gx-btn--tonal" type="button" @click="finishDialog(false)">Cancel</button><button ref="confirmButton" class="gx-btn" :class="{'gx-btn--danger': dialog.danger}" type="button" @click="finishDialog(true)">{{ dialog.confirmLabel }}</button></div>
      </GxDialog>
    </div>
  `,
}
