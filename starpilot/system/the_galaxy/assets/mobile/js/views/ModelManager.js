import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"

function text(value, fallback = "") {
  return value === null || value === undefined ? fallback : String(value)
}

function releasedTs(value) {
  const n = Date.parse(text(value, ""))
  return Number.isNaN(n) ? 0 : n
}

export const ModelManager = {
  name: "ModelManager",
  data() {
    return {
      loading: true,
      error: "",
      busy: "",
      sortMode: "release_date",
      userFilter: "all",
      communityFilter: "all",
      allowGpu: false,
      models: [],
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
        .filter((m) => this.userFilter === "all" ? true : !!m.userFavorite === (this.userFilter === "yes"))
        .filter((m) => this.communityFilter === "all" ? true : !!m.communityFavorite === (this.communityFilter === "yes"))
      rows.sort((a, b) => {
        if (mode === "release_date") {
          const delta = releasedTs(b.released) - releasedTs(a.released)
          if (delta !== 0) return delta
        }
        return text(a.label, a.value).localeCompare(text(b.label, b.value), undefined, { sensitivity: "base", numeric: true })
      })
      return rows
    },
    anyGpuBlocked() {
      return (this.models || []).some((m) => !!m.requiresGpu && !m.gpuAvailable)
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
  beforeUnmount() { this.poll?.destroy() },
  methods: {
    gpuBlocked(model) {
      return !!model.requiresGpu && !model.gpuAvailable && !this.allowGpu
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
      try {
        const p = await api.getModelStatus()
        this.models = Array.isArray(p.models) ? p.models.filter((m) => m && typeof m === "object") : []
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
        this.loading = false
      } catch (e) {
        this.error = e?.message || String(e)
        this.loading = false
      }
    },
    async runAction(action, model = null) {
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
        let msg = ""
        if (action === "select-small" || action === "select-big") {
          const profile = action === "select-big" ? "big" : "small"
          const p = await api.setActiveModel(profile, key)
          msg = p?.message || `Selected "${label}".`
        } else if (action === "download") {
          const p = await api.startModelDownload(key, this.allowGpu)
          msg = p?.message || `Downloading "${label}"...`
        } else if (action === "downloadAll") {
          const p = await api.downloadAllModels(this.allowGpu)
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
        if (msg) showSnackbar(msg)
        await this.refresh()
      } catch (e) {
        showSnackbar(e?.message || String(e), "error")
      } finally {
        this.busy = ""
      }
    },
  },
  template: `
    <div class="gx-view">
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
            <span class="gx-chip" style="background:var(--primary);color:var(--on-primary);">Active: {{ currentLabel }}</span>
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
          <div style="padding: var(--sp-3); display:grid; gap:12px;">
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button v-if="status.downloading" type="button" class="gx-btn gx-btn--danger" :disabled="!!busy" @click="runAction('cancel')"><i class="bi bi-stop-circle"></i> Cancel Download</button>
              <button v-else type="button" class="gx-btn" :disabled="!!busy" @click="runAction('downloadAll')"><i class="bi bi-download"></i> Download All Missing</button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!!busy" @click="runAction('refresh')"><i v-if="busy === 'refresh:'" class="bi bi-arrow-repeat gx-spin"></i><i v-else class="bi bi-arrow-clockwise"></i> Refresh</button>
            </div>

            <div class="gx-row" style="border-top:none;">
              <span class="gx-row__label">Active Small</span>
              <select class="gx-field" style="flex:1;" :value="activeSmallModel" :disabled="!!busy || status.isOnroad" @change="runAction('select-small', installedSmallModels.find(m => m.value === $event.target.value))">
                <option v-for="m in installedSmallModels" :key="m.value" :value="m.value">{{ m.label || m.value }}</option>
              </select>
            </div>

            <div class="gx-row" style="border-top:none;">
              <span class="gx-row__label">Active Big</span>
              <select class="gx-field" style="flex:1;" :value="activeBigModel" :disabled="!!busy || status.isOnroad" @change="$event.target.value ? runAction('select-big', installedBigModels.find(m => m.value === $event.target.value)) : runAction('select-big')">
                <option value="">None — always use Active Small</option>
                <option v-for="m in installedBigModels" :key="m.value" :value="m.value">{{ m.label || m.value }}</option>
              </select>
            </div>

            <div class="gx-row" style="border-top:none;">
              <span class="gx-row__label">Sort</span>
              <select class="gx-field" style="flex:1;" :value="sortMode" @change="sortMode = $event.target.value">
                <option value="release_date">Release Date</option>
                <option value="alphabetical">Alphabetical</option>
              </select>
            </div>

            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <select class="gx-field" style="flex:1; min-width:140px;" :value="userFilter" @change="userFilter = $event.target.value">
                <option value="all">Your Favorite: All</option>
                <option value="yes">Your Favorite: Yes</option>
                <option value="no">Your Favorite: No</option>
              </select>
              <select class="gx-field" style="flex:1; min-width:140px;" :value="communityFilter" @change="communityFilter = $event.target.value">
                <option value="all">Community: All</option>
                <option value="yes">Community: Yes</option>
                <option value="no">Community: No</option>
              </select>
            </div>

            <div class="gx-row" style="border-top:none;">
              <div class="gx-row__info">
                <span class="gx-row__label">Download GPU models without GPU</span>
                <span v-if="anyGpuBlocked" class="gx-row__desc">GPU models are very large and will not run without an external GPU.</span>
              </div>
              <label class="gx-switch">
                <input type="checkbox" v-model="allowGpu" />
                <span class="gx-switch__track"></span>
                <span class="gx-switch__thumb"></span>
              </label>
            </div>
          </div>
        </section>

        <template v-if="!sorted.length">
          <div class="gx-card"><div class="gx-empty">No models available.</div></div>
        </template>
        <template v-else>
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
                  <span class="gx-chip">{{ m.requiresGpu ? 'eGPU' : 'On-device GPU' }}</span>
                  <span v-if="m.version" class="gx-chip">Version {{ m.version }}</span>
                  <span v-if="m.released" class="gx-chip">Released {{ m.released }}</span>
                  <span v-if="m.partial" class="gx-chip">Partial Files</span>
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
                <button type="button" class="gx-btn" :disabled="!!busy" @click="runAction(m.requiresGpu ? 'select-big' : 'select-small', m)"><i class="bi bi-play-fill"></i> Set Active {{ m.requiresGpu ? 'Big' : 'Small' }}</button>
                <button v-if="!m.builtin" type="button" class="gx-btn gx-btn--tonal" style="color:var(--error);" :disabled="!!busy" @click="runAction('delete', m)"><i class="bi bi-trash"></i> Delete</button>
              </template>
              <template v-else>
                <button type="button" class="gx-btn" :disabled="!!busy || gpuBlocked(m)" @click="runAction('download', m)"><i class="bi bi-download"></i> {{ gpuBlocked(m) ? 'GPU Required' : 'Download' }}</button>
              </template>
            </div>
            </section>
          </div>
        </template>
      </template>
    </div>
  `,
}
