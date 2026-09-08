import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"

export const ModelLaboratory = {
  name: "ModelLaboratory",
  data() {
    return {
      loading: true,
      saving: false,
      error: "",
      message: "",
      dirty: false,
      chestnutReady: false,
      isOnroad: false,
      configuration: { enabled: false, lateralModel: "", longitudinalModel: "" },
      runtime: {},
      download: {},
      summary: {},
      models: [],
    }
  },
  computed: {
    availableModels() {
      return this.models.filter((m) => m && m.modelLabArtifactAvailable)
    },
    readyModels() {
      return this.availableModels.filter((m) => m.modelLabArtifactInstalled)
    },
    candidates() {
      const ready = this.readyModels
      const lat = this.configuration.lateralModel
      return ready.filter((m) => !lat || m.value !== lat)
    },
    selectionError() {
      if (this.isOnroad) return "Park before changing the laboratory pair."
      if (this.readyModels.length < 2) return "Download at least two eGPU variants before composing a pair."
      const lat = this.modelById(this.configuration.lateralModel)
      const lon = this.modelById(this.configuration.longitudinalModel)
      if (!lat || !lon) return "Choose two downloaded eGPU variants."
      if (lat.value === lon.value) return "Lateral and longitudinal models must be different."
      if (!lat.modelLabArtifactInstalled || !lon.modelLabArtifactInstalled) {
        return "Download both eGPU variants first."
      }
      if (!this.chestnutReady) return "Connect a firmware-ready Chestnut to enable this pair."
      return ""
    },
    runtimeState() {
      const r = this.runtime || {}
      return r.active ? "Pair active" : r.requested ? "Pair requested" : "Inactive"
    },
  },
  created() {
    this.poll = usePolling(() => this.refresh(), { interval: 2000 })
    this.poll.start()
  },
  beforeUnmount() {
    this.poll?.destroy()
  },
  methods: {
    modelById(id) {
      return this.models.find((m) => m.value === id)
    },
    modelLabel(id) {
      return this.modelById(id)?.label || id || "not selected"
    },
    artifactStatus(m) {
      if (m.modelLabArtifactInstalled) return { text: "eGPU variant downloaded", good: true }
      return { text: "eGPU variant not downloaded", good: false }
    },
    async refresh() {
      try {
        const payload = await api.getModelLab()
        this.applyPayload(payload)
      } catch (e) {
        this.error = e?.message || String(e)
      } finally {
        this.loading = false
      }
    },
    applyPayload(payload) {
      payload = payload || {}
      this.chestnutReady = Boolean(payload.chestnutReady)
      this.isOnroad = Boolean(payload.isOnroad)
      this.error = String(payload.configurationError || "")
      this.runtime = payload.runtime && typeof payload.runtime === "object" ? payload.runtime : {}
      this.download = payload.download && typeof payload.download === "object" ? payload.download : {}
      this.summary = payload.summary && typeof payload.summary === "object" ? payload.summary : {}
      this.models = Array.isArray(payload.models) ? payload.models : []
      const cfg = payload.configuration && typeof payload.configuration === "object" ? payload.configuration : {}
      const draft = { ...this.configuration }
      this.configuration = {
        enabled: Boolean(cfg.enabled),
        lateralModel: this.dirty ? draft.lateralModel : String(cfg.lateralModel || ""),
        longitudinalModel: this.dirty ? draft.longitudinalModel : String(cfg.longitudinalModel || ""),
      }
      this.normalizeSelection()
    },
    normalizeSelection() {
      const ready = this.readyModels
      if (!ready.some((m) => m.value === this.configuration.lateralModel)) {
        this.configuration.lateralModel = ready[0]?.value || ""
      }
      if (!ready.some((m) => m.value === this.configuration.longitudinalModel)) {
        const lon = ready.find((m) => m.value !== this.configuration.lateralModel)
        this.configuration.longitudinalModel = lon?.value || ""
      }
    },
    onLateralChange() {
      this.dirty = true
      const lon = this.modelById(this.configuration.longitudinalModel)
      const lat = this.modelById(this.configuration.lateralModel)
      if (lon && lat && lon.value === lat.value) {
        this.configuration.longitudinalModel = this.candidates[0]?.value || ""
      }
    },
    async save(enabled) {
      if (this.saving) return
      if (enabled && this.selectionError) {
        this.error = this.selectionError
        return
      }
      this.saving = true
      this.error = ""
      this.message = ""
      try {
        const payload = await api.saveModelLab({
          enabled,
          lateralModel: this.configuration.lateralModel,
          longitudinalModel: this.configuration.longitudinalModel,
        })
        this.dirty = false
        this.applyPayload(payload)
        this.message = String(payload?.message || "Model Laboratory configuration saved.")
        showSnackbar("Model Laboratory saved", "info")
      } catch (e) {
        this.error = e?.message || String(e)
      } finally {
        this.saving = false
      }
    },
    async prepareModel(modelId) {
      if (this.saving || !modelId) return
      this.saving = true
      this.error = ""
      this.message = ""
      try {
        const payload = await api.prepareModelLabArtifact(modelId)
        this.message = String(payload?.message || "eGPU variant download queued.")
        showSnackbar("eGPU variant download queued", "info")
        await this.refresh()
      } catch (e) {
        this.error = e?.message || String(e)
      } finally {
        this.saving = false
      }
    },
    async deleteModel(modelId) {
      if (this.saving || !modelId) return
      const model = this.modelById(modelId)
      if (!window.confirm(`Delete the eGPU variant for "${model?.label || modelId}"? The normal on-device model will not be removed.`)) return
      this.saving = true
      this.error = ""
      this.message = ""
      try {
        const payload = await api.deleteModelLabArtifact(modelId)
        this.dirty = false
        this.applyPayload(payload)
        this.message = String(payload?.message || "eGPU variant deleted.")
        showSnackbar("eGPU variant deleted", "info")
      } catch (e) {
        this.error = e?.message || String(e)
      } finally {
        this.saving = false
      }
    },
  },
  template: `
  <div class="gx-view">
    <div v-if="loading" class="gx-card"><div class="gx-loading">Loading laboratory status...</div></div>
    <template v-else>
      <div class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-bezier2"></i>
          <span class="gx-section__title">Model Laboratory</span>
          <span class="gx-chip" :style="chestnutReady ? 'color:var(--success);' : 'color:var(--warning);'">{{ chestnutReady ? 'Chestnut ready' : 'Chestnut required' }}</span>
          <span class="gx-chip" :style="isOnroad ? 'color:var(--warning);' : 'color:var(--success);'">{{ isOnroad ? 'Onroad · locked' : 'Parked · configurable' }}</span>
        </div>
        <div style="padding: 0 var(--sp-4) var(--sp-3); color:var(--text-muted); font-size:var(--fs-sm);">
          Use the lateral judgment of one small model and the longitudinal judgment of another.
        </div>
        <div v-if="error" class="gx-alert" style="margin:0 var(--sp-4) var(--sp-3);">
          <i class="bi bi-exclamation-triangle-fill" style="color:var(--error);"></i>
          <div class="gx-alert__body"><span style="color:var(--error);">{{ error }}</span></div>
        </div>
        <div v-if="message" class="gx-alert gx-alert--info" style="margin:0 var(--sp-4) var(--sp-3);">
          <i class="bi bi-check-circle-fill"></i>
          <div class="gx-alert__body"><span>{{ message }}</span></div>
        </div>
      </div>

      <div class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-cpu"></i>
          <span class="gx-section__title">Available models</span>
          <span class="gx-section__count">{{ summary.ready || 0 }} downloaded · {{ Math.max((summary.published || 0) - (summary.ready || 0), 0) }} available to download</span>
        </div>
        <div style="padding: 0 var(--sp-4) var(--sp-3); color:var(--text-muted); font-size:var(--fs-sm);">
          Download eGPU-compatible small models. These are separate from the small models in Model Manager because they are compiled for the eGPU.
        </div>
        <article v-for="m in availableModels" :key="m.value" class="gx-row">
          <div class="gx-row__info">
            <span class="gx-row__label">{{ m.label }}</span>
            <span class="gx-row__desc">{{ m.value }} · {{ m.series || 'Unknown series' }}</span>
          </div>
          <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">
            <span class="gx-chip">{{ m.version || 'unknown version' }}</span>
            <span class="gx-chip">{{ m.modelSize || 'small' }}</span>
            <span class="gx-chip" :style="artifactStatus(m).good ? 'color:var(--success);' : 'color:var(--warning);'">{{ artifactStatus(m).text }}</span>
            <button v-if="!m.modelLabArtifactInstalled" type="button" class="gx-btn gx-btn--tonal" :disabled="saving || isOnroad || !!download.model" @click="prepareModel(m.value)">
              {{ download.model === m.value ? 'Downloading · ' + (download.progress || 'starting…') : 'Download eGPU variant' }}
            </button>
            <button v-else type="button" class="gx-btn gx-btn--tonal" style="color:var(--error);" :disabled="saving || isOnroad || !!download.model" @click="deleteModel(m.value)">
              Delete eGPU variant
            </button>
          </div>
        </article>
      </div>

      <div class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-collection"></i>
          <span class="gx-section__title">Compose a pair</span>
          <span class="gx-chip" :style="configuration.enabled ? 'background:var(--success);color:var(--on-secondary);' : ''">{{ configuration.enabled ? 'Enabled' : 'Disabled' }}</span>
        </div>
        <div style="padding: 0 var(--sp-4); color:var(--text-muted); font-size:var(--fs-sm);">Choose from downloaded eGPU variant combinations below.</div>
        <div style="padding: var(--sp-4); display:grid; gap:var(--sp-3);">
          <label style="display:grid; gap:4px;">
            <strong style="font-size:var(--fs-sm);">Lateral model</strong>
            <small style="color:var(--text-muted); font-size:var(--fs-xs);">Path shape, curvature, lane geometry, and driving desire</small>
            <select class="gx-field" :value="configuration.lateralModel" @change="configuration.lateralModel = $event.target.value; onLateralChange()">
              <option value="">Choose a model</option>
              <option v-for="m in readyModels" :key="m.value" :value="m.value">{{ m.label }} · {{ m.version }}</option>
            </select>
          </label>
          <label style="display:grid; gap:4px;">
            <strong style="font-size:var(--fs-sm);">Longitudinal model</strong>
            <small style="color:var(--text-muted); font-size:var(--fs-xs);">Speed, acceleration, stopping, leads, and scene confidence</small>
            <select class="gx-field" :value="configuration.longitudinalModel" @change="configuration.longitudinalModel = $event.target.value; dirty = true">
              <option value="">Choose a model</option>
              <option v-for="m in candidates" :key="m.value" :value="m.value">{{ m.label }} · {{ m.version }}</option>
            </select>
          </label>
          <div style="display:flex; flex-wrap:wrap; gap:6px; align-items:center;">
            <strong>{{ modelLabel(configuration.lateralModel) }}</strong><span class="gx-row__desc" style="margin:0;">steers</span>
            <i class="bi bi-arrow-left-right"></i>
            <strong>{{ modelLabel(configuration.longitudinalModel) }}</strong><span class="gx-row__desc" style="margin:0;">paces</span>
          </div>
          <p v-if="selectionError" class="gx-row__desc" style="margin:0; color:var(--warning);">{{ selectionError }}</p>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button type="button" class="gx-btn" :disabled="saving || !!selectionError" @click="save(true)">
              <i class="bi bi-play-fill"></i> Enable for next drive
            </button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="saving || isOnroad || !configuration.enabled" @click="save(false)">
              <i class="bi bi-stop-fill"></i> Disable
            </button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="saving" @click="refresh">
              <i class="bi bi-arrow-clockwise"></i> Refresh
            </button>
          </div>
        </div>
      </div>

      <div class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-activity"></i>
          <span class="gx-section__title">Runtime</span>
          <span class="gx-chip" :style="runtime.active ? 'background:var(--success);color:var(--on-secondary);' : ''">{{ runtimeState }}</span>
        </div>
        <div style="padding: var(--sp-4); display:grid; gap:6px;">
          <div class="gx-row" style="border-top:none;"><span class="gx-row__label">Lateral</span><span class="gx-row__value">{{ modelLabel(runtime.lateralModel) }}</span></div>
          <div class="gx-row" style="border-top:none;"><span class="gx-row__label">Longitudinal</span><span class="gx-row__value">{{ modelLabel(runtime.longitudinalModel) }}</span></div>
          <div v-if="runtime.error" class="gx-alert" style="margin:0;"><i class="bi bi-exclamation-triangle-fill" style="color:var(--error);"></i><div class="gx-alert__body"><span style="color:var(--error);">{{ runtime.error }}</span></div></div>
          <p class="gx-row__desc" style="margin:0;">Both roles evaluate the same frame at 20 Hz. A runtime failure suppresses that frame and falls back to the built-in QCOM model.</p>
        </div>
      </div>

    </template>
  </div>
  `,
}
