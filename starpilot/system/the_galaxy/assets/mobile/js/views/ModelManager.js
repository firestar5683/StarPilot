import { api, showSnackbar } from "../api.js"
import {readComparison, comparisonRows} from '/assets/components/tools/model_comparison.js'
import { usePolling } from "../composables.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"
import { openGalaxyHelpDialog } from "../components/FeatureHelp.js"
import { readHardwareFilter, saveHardwareFilter, matchesHardware, hardwareLabel, fileSizeText, modelManagerMetrics, trackingStatus, compareMetrics, readModelHistory, historyRow } from "/assets/components/tools/model_metrics.js"

function text(value, fallback = "") {
  return value === null || value === undefined ? fallback : String(value)
}

function releasedTs(value) {
  const n = Date.parse(text(value, ""))
  return Number.isNaN(n) ? 0 : n
}

// Survives SPA unmount: a new instance must read after a sent write settles.
let selectionWrite = null

export const ModelManager = {
  name: "ModelManager",
  data() {
    return {
      loading: true,
      error: "",
      busy: "",
      selectionUncertain: true,
      statusGeneration: 0,
      disposed: false,
      sortMode: "release_date",
      userFilter: "all",
      communityFilter: "all",
      hardwareFilter: readHardwareFilter(),
      models: [],
      histories: {},
      modelEngagement: {},
      period: 'all', statsMode: 'all', comparison: [], comparisonStatus: '', comparisonRequest: 0,
      currentModel: "",
      activeSmallModel: "",
      activeBigModel: "",
      summary: { installed: 0, missing: 0, total: 0 },
      status: {
        modelToDownload: "",
        downloadAll: false,
        downloading: false,
        progress: "",
        isOnroad: false,
      },
    }
  },
  computed: {
    currentLabel() {
      const key = text(this.currentModel, "")
      if (!key) return "none"
      const match = (this.models || []).find((m) => text(m && m.value, "") === key)
      return match ? text(match.label, key) : key
    },
    installedSmallModels() {
      return (this.models || []).filter((m) => m?.installed && !m?.requiresGpu)
    },
    installedBigModels() {
      return (this.models || []).filter((m) => m?.installed && !!m?.requiresGpu)
    },
    sorted() {
      const mode = this.sortMode
      const rows = (this.models || [])
        .filter((m) => m && typeof m === "object")
        .filter((m) => matchesHardware(m, this.hardwareFilter))
        .filter((m) => this.userFilter === "all" ? true : !!m.userFavorite === (this.userFilter === "yes"))
        .filter((m) => this.communityFilter === "all" ? true : !!m.communityFavorite === (this.communityFilter === "yes"))
      rows.sort((a, b) => {
        if (["distance", "interventions", "disengagements"].includes(mode)) {
          const delta = compareMetrics(a, b, mode)
          if (delta !== 0) return delta
        }
        if (mode === "release_date") {
          const delta = releasedTs(b.released) - releasedTs(a.released)
          if (delta !== 0) return delta
        }
        return text(a.label, a.value).localeCompare(text(b.label, b.value), undefined, { sensitivity: "base", numeric: true })
      })
      return rows
    },
    downloadTargetLabel() {
      if (this.status.downloadAll) return "all missing models"
      const key = text(this.status.modelToDownload, "")
      const match = (this.models || []).find((m) => text(m && m.value, "") === key)
      return match ? text(match.label, key) : key || "a model"
    },
  },
  created() {
    this.poll = usePolling(() => this.refresh(), { interval: 2000 })
    this.poll.start()
  },
  beforeUnmount() {
    this.disposed = true
    ++this.statusGeneration
    this.poll?.destroy()
  },
  methods: {
    comparisonRows,
    async loadComparison() {
      const request = ++this.comparisonRequest
      this.comparisonStatus = 'Loading…'
      this.comparison = []
      this.histories = {}
      try {
        const rows = await readComparison(this.period, this.statsMode)
        if (request !== this.comparisonRequest) return
        this.comparison = rows
        this.comparisonStatus = rows.length ? '' : 'No recorded comparisons for this period.'
      } catch (error) {
        if (request === this.comparisonRequest) this.comparisonStatus = error.message
      }
    },
    hardwareLabel,
    fileSizeText,
    modelManagerMetrics,
    trackingStatus,
    historyRow,
    async loadHistory(key, more = false) {
      const prior = this.histories[key]
      if (prior?.loading) return
      if (!more && prior?.open) { this.histories[key] = {...prior, open:false}; return }
      this.histories[key] = {rows:[], ...prior, open:true, loading:true, error:""}
      try {
        const period = this.period, mode = this.statsMode
        const result = await readModelHistory(key, more ? prior.rows.length : 0, period, mode)
        if (period !== this.period || mode !== this.statsMode) return
        this.histories[key] = {...result, rows:more ? [...prior.rows, ...result.rows] : result.rows, open:true, loading:false, error:""}
      } catch (error) {
        this.histories[key] = {...this.histories[key], loading:false, error:error.message}
      }
    },
    setHardwareFilter(value) {
      this.hardwareFilter = saveHardwareFilter(value)
    },
    rowState(model) {
      const key = text(model.value, "")
      if (key && key === this.currentModel) return "active"
      if (this.status.downloading) {
        const isTarget = !this.status.downloadAll && this.status.modelToDownload === key
        if (this.status.downloadAll || isTarget) return "cancellable"
        return "busy"
      }
      if (model.installed) return "installed"
      return "available"
    },
    actionAllowedOnroad(action) {
      if (action === "refresh" || action === "favorite" || action === "unfavorite") return true
      return !this.status.isOnroad
    },
    async refresh() {
      const generation = ++this.statusGeneration
      try {
        if (selectionWrite) await selectionWrite.catch(() => {})
        if (this.disposed || generation !== this.statusGeneration) return
        const p = await api.getModelStatus()
        if (this.disposed || generation !== this.statusGeneration) return
        this.models = Array.isArray(p.models) ? p.models.filter((m) => m && typeof m === "object") : []
        this.modelEngagement = p.modelEngagement || {}
        this.currentModel = text(p.currentModel, "")
        this.activeSmallModel = text(p.activeSmallModel, "")
        this.activeBigModel = text(p.activeBigModel, "")
        const s = p.summary && typeof p.summary === "object" ? p.summary : {}
        this.summary = {
          installed: Number(s.installed) || 0,
          missing: Number(s.missing) || 0,
          total: Number(s.total) || 0,
        }
        this.status = {
          modelToDownload: text(p.modelToDownload, ""),
          downloadAll: !!p.downloadAll,
          downloading: !!p.downloading,
          progress: text(p.progress, ""),
          isOnroad: !!p.isOnroad,
        }
        this.error = ""
        this.selectionUncertain = false
        this.loading = false
      } catch (e) {
        if (this.disposed || generation !== this.statusGeneration) return
        this.error = e?.message || String(e)
        this.loading = false
      }
    },
    async runAction(action, model = null) {
      const selecting = action === "select-small" || action === "select-big"
      if (this.disposed || (selecting && this.selectionUncertain)) return
      if (this.busy) {
        showSnackbar("Please wait for the current action to finish.", "error")
        return
      }
      if (!this.actionAllowedOnroad(action)) {
        showSnackbar("Actions are blocked while onroad.", "error")
        return
      }
      const key = text(model && model.value, "")
      const label = text(model && model.label, key || "model")
      this.busy = `${action}:${key}`
      try {
        let allowGpu = false
        const needsGpuPrompt = action === "download"
          ? model?.requiresGpu && !model.gpuAvailable
          : action === "downloadAll" && this.models.some(m => !m.installed && m.requiresGpu && !m.gpuAvailable)
        if (needsGpuPrompt) {
          allowGpu = await openGalaxyHelpDialog({
            title: "No external GPU detected",
            paragraphs: [action === "downloadAll"
              ? "This download includes models that require an external GPU. You can download them now, but they cannot run until a compatible GPU is connected and detected."
              : `“${label}” requires an external GPU. You can download it now, but it cannot run until a compatible GPU is connected and detected.`,
              "GPU model files can be large. Downloading does not activate a model or change the model currently in use."],
            confirmLabel: "Download anyway", cancelLabel: "Cancel",
          })
          if (!allowGpu || this.disposed) return
          // The car can change state while a confirmation is open.
          await this.refresh()
          if (this.disposed || this.error || !this.actionAllowedOnroad(action) || this.status.downloading) {
            if (!this.disposed) showSnackbar("Download not started. Check the device status and try again while parked.", "error")
            return
          }
        }
        let msg = ""
        if (action === "select-small" || action === "select-big") {
          const profile = action === "select-big" ? "big" : "small"
          this.selectionUncertain = true
          ++this.statusGeneration // Pre-write polls cannot reconcile this selection.
          selectionWrite = api.setActiveModel(profile, key)
          let p
          try { p = await selectionWrite } finally { selectionWrite = null }
          msg = p?.message || `Selected "${label}".`
        } else if (action === "download") {
          const p = await api.startModelDownload(key, allowGpu)
          msg = p?.message || `Downloading "${label}"...`
        } else if (action === "downloadAll") {
          const p = await api.downloadAllModels(allowGpu)
          msg = p?.message || "Started downloading all models."
        } else if (action === "cancel") {
          const p = await api.postAction("/api/models/cancel")
          msg = p?.message || "Cancellation requested."
        } else if (action === "delete") {
          const ok = await GalaxyConfirm({
            title: "Delete model",
            message: `Delete local files for "${label}"?`,
            confirmLabel: "Delete",
            danger: true,
          })
          if (!ok) return
          const p = await api.deleteModel(key)
          msg = p?.message || `Deleted files for "${label}".`
        } else if (action === "favorite" || action === "unfavorite") {
          const add = action === "favorite"
          const favs = (this.models || [])
            .filter((m) => m && m.userFavorite && text(m.value, "") !== key)
            .map((m) => text(m.value, ""))
            .filter(Boolean)
          if (add) favs.push(key)
          const p = await api.saveModelPreferences({ userFavorites: favs })
          msg = p?.message || (add ? "Model added to your favorites." : "Model removed from your favorites.")
        } else if (action === "refresh") {
          const p = await api.postAction("/api/models/refresh_manifest")
          msg = p?.message || "Model manifest refreshed."
        }
        if (this.disposed) return
        if (msg) showSnackbar(msg)
        await this.refresh()
      } catch (e) {
        if (this.disposed) return
        showSnackbar(e?.message || String(e), "error")
        // Reconcile a possibly accepted request before releasing the action lock.
        await this.refresh()
      } finally {
        if (!this.disposed) this.busy = ""
      }
    },
  },
  template: `
    <div class="gx-view gx-model-manager">
      <div v-if="loading" class="gx-card">
        <div class="gx-loading" style="padding: var(--sp-4);">Loading models...</div>
      </div>

      <template v-else>
        <section class="gx-card">
          <div class="gx-section__header">
            <i class="bi bi-cpu"></i>
            <span class="gx-section__title">Model Manager</span>
          </div>
          <div style="padding: var(--sp-3); display:flex; flex-wrap:wrap; gap:6px;">
            <span class="gx-chip">{{ summary.installed }} installed</span>
            <span class="gx-chip">{{ summary.missing }} missing</span>
            <span class="gx-chip">{{ summary.total }} total</span>
            <span class="gx-chip" style="background:var(--primary);color:var(--on-primary);">Selected: {{ currentLabel }}</span>
          </div>
          <div style="padding: 0 var(--sp-3) var(--sp-3);">
            <div v-if="error" class="gx-alert gx-alert--warn" style="border:none; margin:0 0 8px;">
              <i class="bi bi-exclamation-triangle-fill gx-alert__icon"></i>
              <div class="gx-alert__body"><strong>Status load failed</strong><span>{{ error }}</span></div>
            </div>
            <div v-if="status.isOnroad" class="gx-alert gx-alert--warn" style="border:none; margin:0 0 8px;">
              <i class="bi bi-car-front-fill gx-alert__icon"></i>
              <div class="gx-alert__body"><span>Onroad: switching models and downloads are disabled.</span></div>
            </div>
            <div v-if="status.downloading" class="gx-alert gx-alert--info" style="border:none; margin:0;">
              <i class="bi bi-arrow-repeat gx-spin gx-alert__icon"></i>
              <div class="gx-alert__body">
                <strong>Downloading {{ downloadTargetLabel }}</strong>
                <span v-if="status.progress">{{ status.progress }}</span>
              </div>
            </div>
          </div>
        </section>

        <section class="gx-card">
          <div class="gx-section__header">
            <i class="bi bi-sliders"></i>
            <span class="gx-section__title">Controls</span>
          </div>
          <div style="padding: var(--sp-3); display:grid; grid-template-columns:minmax(0, 1fr); gap:12px;">
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button v-if="status.downloading" type="button" class="gx-btn gx-btn--danger" :disabled="!!busy" @click="runAction('cancel')"><i class="bi bi-stop-circle"></i> Cancel Download</button>
              <button v-else type="button" class="gx-btn" :disabled="!!busy" @click="runAction('downloadAll')"><i class="bi bi-download"></i> Download all missing — entire catalogue</button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!!busy" @click="runAction('refresh')"><i v-if="busy === 'refresh:'" class="bi bi-arrow-repeat gx-spin"></i><i v-else class="bi bi-arrow-clockwise"></i> Refresh</button>
            </div>

            <div class="gx-row" style="border-top:none;">
              <span class="gx-row__label">Active Small</span>
              <GalaxySelect class="gx-field" style="flex:1;" :value="activeSmallModel" :disabled="!!busy || selectionUncertain || status.isOnroad" @change="runAction('select-small', installedSmallModels.find(m => m.value === $event.target.value))">
                <option v-for="m in installedSmallModels" :key="m.value" :value="m.value">{{ m.label || m.value }}</option>
              </GalaxySelect>
            </div>

            <div class="gx-row" style="border-top:none;">
              <span class="gx-row__label">Active Big</span>
              <GalaxySelect class="gx-field" style="flex:1;" :value="activeBigModel" :disabled="!!busy || selectionUncertain || status.isOnroad" @change="$event.target.value ? runAction('select-big', installedBigModels.find(m => m.value === $event.target.value)) : runAction('select-big')">
                <option value="">None — always use Active Small</option>
                <option v-for="m in installedBigModels" :key="m.value" :value="m.value">{{ m.label || m.value }}</option>
              </GalaxySelect>
            </div>

            <div class="gx-row" style="border-top:none;">
              <span class="gx-row__label">Sort</span>
              <GalaxySelect class="gx-field" style="flex:1;" :value="sortMode" @change="sortMode = $event.target.value">
                <option value="release_date">Release Date</option>
                <option value="alphabetical">Alphabetical</option>
                <option value="distance">Total distance</option>
                <option value="interventions">Miles / intervention</option>
                <option value="disengagements">Miles / disengagement</option>
              </GalaxySelect>
            </div>

            <div class="gx-row" style="border-top:none;">
              <label class="gx-row__label" for="gx-model-hardware">Model hardware</label>
              <GalaxySelect id="gx-model-hardware" class="gx-field" style="flex:1; min-width:0;" :value="hardwareFilter" @change="setHardwareFilter($event.target.value)">
                <option value="both">Both</option>
                <option value="gpu">GPU models only</option>
                <option value="comma">Comma models only</option>
              </GalaxySelect>
            </div>

            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <GalaxySelect class="gx-field" style="flex:1; min-width:140px;" :value="userFilter" @change="userFilter = $event.target.value">
                <option value="all">Your Favorite: All</option>
                <option value="yes">Your Favorite: Yes</option>
                <option value="no">Your Favorite: No</option>
              </GalaxySelect>
              <GalaxySelect class="gx-field" style="flex:1; min-width:140px;" :value="communityFilter" @change="communityFilter = $event.target.value">
                <option value="all">Community: All</option>
                <option value="yes">Community: Yes</option>
                <option value="no">Community: No</option>
              </GalaxySelect>
            </div>

          </div>
        </section>

        <section class="gx-card" style="padding:var(--sp-3);">
          <strong>Per-model driving</strong>
          <span class="gx-chip" style="margin-left:8px;">{{ sorted.length }} of {{ models.length }} models · All time</span>
        </section>

        <template v-if="!sorted.length">
          <div class="gx-card"><div class="gx-empty">No models match these filters. Try Both or clear the favourite filters.</div></div>
        </template>
        <template v-else>
          <details class="gx-card gx-model-comparison" @toggle="$event.target.open && loadComparison()">
            <summary>Compare recorded revisions and assistance modes</summary>
            <p>Cards show all-time assisted distance (Total distance), pooled across revisions. Comparisons keep each loaded revision, backend, pair and assistance mode separate. Periods include drives started in the selected window.</p>
            <label for="gx-period">Period</label>
            <GalaxySelect id="gx-period" class="gx-field" v-model="period" @change="loadComparison()"><option value="all">All time</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option></GalaxySelect>
            <label for="gx-stats-mode">Assistance mode</label>
            <GalaxySelect id="gx-stats-mode" class="gx-field" v-model="statsMode" @change="loadComparison()"><option value="all">All modes (separate rows)</option><option value="full">Full assistance</option><option value="aol">Lateral only</option></GalaxySelect>
            <p>{{ comparisonStatus }}</p>
            <article class="gx-model-history-row" v-for="row in comparisonRows(comparison, hardwareFilter)"><strong>{{ row.configuration }}</strong><div>{{ row.mode }}</div><div>{{ row.values }}</div><div>{{ row.counts }}</div></article>
            <p>Event averages use eligible exposure / episode count, not completed-interval averages. Intervention exposure excludes held inputs and the 2 s release/rearm period in definition v2 (historical v1 used 0.5 s). Mixed or unknown definitions retain distance and counts but have no event averages. Disengagement exposure includes the enabled session. Zero events are not ranked as infinite. These observations are not controlled safety scores.</p>
          </details>
          <div class="gx-card-grid">
            <section class="gx-card" v-for="m in sorted" :key="m.value">
            <div style="display:flex; align-items:flex-start; gap:8px; padding: var(--sp-3);">
              <div style="flex:1; min-width:0;">
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                  <strong>{{ m.label || m.value }}</strong>
                  <span v-if="m.userFavorite" class="gx-chip">Your Favorite</span>
                  <span v-if="m.communityFavorite" class="gx-chip">Community Favorite</span>
                </div>
                <div style="margin-top:6px; display:flex; flex-wrap:wrap; gap:6px;">
                  <span class="gx-chip">{{ m.value }}</span>
                  <span v-if="m.builtin" class="gx-chip">Built-in</span>
                  <span class="gx-chip">{{ hardwareLabel(m) }}</span>
                  <span v-if="m.version" class="gx-chip">Version {{ m.version }}</span>
                  <span v-if="m.released" class="gx-chip">Released {{ m.released }}</span>
                  <span v-if="m.partial" class="gx-chip">Partial Files</span>
                  <span class="gx-chip">File size: {{ fileSizeText(m) }}</span>
                </div>
              </div>
              <button type="button" class="gx-icon-btn" :disabled="!!busy" :title="m.userFavorite ? 'Remove from your favorites' : 'Add to your favorites'" @click="runAction(m.userFavorite ? 'unfavorite' : 'favorite', m)">
                <i class="bi" :class="m.userFavorite ? 'bi-star-fill' : 'bi-star'"></i>
              </button>
            </div>
            <div style="padding: 0 var(--sp-3) var(--sp-3); display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
              <template v-if="rowState(m) === 'active'">
                <span class="gx-chip" style="background:var(--primary);color:var(--on-primary);">Active model</span>
              </template>
              <template v-else-if="rowState(m) === 'busy'">
                <span class="gx-chip"><i class="bi bi-hourglass-split"></i> Busy</span>
              </template>
              <template v-else-if="rowState(m) === 'cancellable'">
                <button type="button" class="gx-btn gx-btn--danger" :disabled="!!busy" @click="runAction('cancel', m)"><i class="bi bi-x-circle"></i> Cancel</button>
              </template>
              <template v-else-if="rowState(m) === 'installed'">
                <button type="button" class="gx-btn" :disabled="!!busy || selectionUncertain" @click="runAction(m.requiresGpu ? 'select-big' : 'select-small', m)"><i class="bi bi-play-fill"></i> Set Active {{ m.requiresGpu ? 'Big' : 'Small' }}</button>
                <button v-if="!m.builtin" type="button" class="gx-btn gx-btn--tonal" style="color:var(--error);" :disabled="!!busy" @click="runAction('delete', m)"><i class="bi bi-trash"></i> Delete</button>
              </template>
              <template v-else>
                <button type="button" class="gx-btn" :disabled="!!busy || status.isOnroad" @click="runAction('download', m)"><i class="bi bi-download"></i> Download</button>
              </template>
            </div>
            <dl class="gx-model-metrics" aria-label="Per-model driving statistics">
              <div v-for="metric in modelManagerMetrics(m, modelEngagement[m.value])" :key="metric.label" :class="{ 'gx-model-metric-total': metric.primary }">
                <dt :title="metric.description">{{ metric.label }}</dt>
                <dd>{{ metric.value }}</dd>
              </div>
            </dl>
            <p class="gx-row__desc" style="padding:0 var(--sp-3) var(--sp-3); margin:0;">{{ trackingStatus(m) }}</p>
            <div class="gx-model-history">
              <button type="button" class="gx-btn gx-btn--tonal" @click="loadHistory(m.value)">{{ histories[m.value]?.open ? 'Close history' : 'Drive history' }}</button>
              <div v-if="histories[m.value]?.open">
                <p v-if="histories[m.value].error">{{ histories[m.value].error }}</p>
                <p v-else-if="histories[m.value].loading">Loading…</p>
                <p v-else-if="!histories[m.value].rows.length">No recorded drives</p>
                <div class="gx-model-history-row" v-for="(entry, i) in histories[m.value].rows" :key="i">
                  <strong>{{ historyRow(entry).title }}</strong><div>{{ historyRow(entry).configuration }}</div><div>{{ historyRow(entry).values }}</div><div>{{ historyRow(entry).counts }}</div>
                </div>
                <button v-if="histories[m.value].more" type="button" class="gx-btn gx-btn--tonal" :disabled="histories[m.value].loading" @click="loadHistory(m.value, true)">More drives</button>
              </div>
            </div>
            </section>
          </div>
        </template>
      </template>
    </div>
  `,
}
