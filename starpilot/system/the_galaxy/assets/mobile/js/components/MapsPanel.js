import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"
import { GalaxyConfirm } from "./GalaxyModal.js"
import { GxNotice } from "./GxNotice.js"

const STATUS_DEFAULTS = {
  cancelling: false,
  downloading: false,
  isOnroad: false,
  lastUpdate: "Never",
  mapsPresent: false,
  selectedCount: 0,
  storageBytes: 0,
  storageKnown: false,
  scheduleLabel: "Monthly",
  downloadProgress: {},
}

const PROGRESS_DEFAULTS = {
  active: false,
  cancelled: false,
  completed: false,
  downloadedBytes: 0,
  downloadedFiles: 0,
  estimatedDownloadBytes: 0,
  estimateSource: "",
  etaSeconds: 0,
  percent: 0,
  phase: "idle",
  primaryLocation: "",
  storageKnown: false,
  totalFiles: 0,
}

function toProgress(value) {
  const p = value && typeof value === "object" ? value : {}
  return { ...PROGRESS_DEFAULTS, ...p }
}

function uniqueSorted(values) {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }))
}

export const MapsPanel = {
  name: "MapsPanel",
  components: { GxNotice },
  data() {
    return {
      loadingCatalog: true,
      loadingStatus: true,
      statusInFlight: false,
      actionBusy: false,
      savingSelection: false,
      savingSchedule: false,
      error: "",
      search: "",
      sections: [],
      scheduleOptions: [],
      status: { ...STATUS_DEFAULTS },
      progress: { ...PROGRESS_DEFAULTS },
      selectedSaved: [],
      selectedDraft: [],
      scheduleSaved: "2",
      scheduleDraft: "2",
      tokenLabels: {},
      expandedGroups: {},
    }
  },
  created() {
    this.poll = usePolling(() => this.refreshStatus(), { interval: 2500 })
    this.poll.start()
    this.loadCatalog()
  },
  beforeUnmount() { this.poll?.destroy() },
  computed: {
    filteredSections() {
      const query = (this.search || "").trim().toLowerCase()
      const visibleRegions = (regions) => {
        if (!query) return regions || []
        return (regions || []).filter((r) =>
          `${r.label} ${r.code} ${r.token}`.toLowerCase().includes(query))
      }
      return (this.sections || [])
        .map((section) => ({
          ...section,
          groups: (section.groups || [])
            .map((group) => ({
              ...group,
              expandKey: `${section.key}:${group.key}`,
              visibleRegions: visibleRegions(group.regions),
            }))
            .filter((group) => group.visibleRegions.length > 0),
        }))
        .filter((section) => section.groups.length > 0)
    },
    selectionDirty() {
      return !this.sameSorted(this.selectedDraft, this.selectedSaved)
    },
    scheduleDirty() {
      return String(this.scheduleDraft) !== String(this.scheduleSaved)
    },
    showProgress() {
      const p = this.status.downloading
        || this.progress.completed
        || this.progress.cancelled
        || this.progress.estimatedDownloadBytes > 0
      return this.loadingStatus ? false : p
    },
    downloaderLabel() {
      if (this.loadingStatus) return "Checking..."
      if (this.status.downloading) return this.status.cancelling ? "Cancelling" : "Downloading"
      return "Idle"
    },
    storageLabel() {
      return this.status.storageKnown ? this.formatBytes(this.status.storageBytes) : "Calculating…"
    },
    estimateLabel() {
      const p = this.progress
      if (!this.selectionDirty && p.estimatedDownloadBytes > 0) {
        return `~${this.formatBytes(p.estimatedDownloadBytes)} additional`
      }
      return this.selectedDraft.length > 0 ? "Not yet available" : "Select regions"
    },
    canDownload() {
      return !this.loadingStatus && !this.actionBusy && !this.status.isOnroad
        && !this.status.downloading && this.selectedDraft.length > 0
    },
    canCancel() {
      return !this.loadingStatus && !this.actionBusy && this.status.downloading
    },
    canRemove() {
      return !this.loadingStatus && !this.actionBusy && !this.status.downloading
        && !this.status.isOnroad && this.status.mapsPresent
    },
  },
  methods: {
    sameSorted(a, b) {
      if (a.length !== b.length) return false
      const sa = uniqueSorted(a)
      const sb = uniqueSorted(b)
      return sa.every((x, i) => x === sb[i])
    },
    formatBytes(bytes) {
      const value = Number(bytes || 0)
      if (value <= 0) return "0 MB"
      const units = ["B", "KB", "MB", "GB", "TB"]
      const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
      const scaled = value / (1024 ** index)
      return `${scaled >= 10 || index === 0 ? scaled.toFixed(0) : scaled.toFixed(2)} ${units[index]}`
    },
    formatDuration(seconds) {
      const value = Math.max(0, Math.round(Number(seconds || 0)))
      if (value < 60) return `${value}s`
      const minutes = Math.floor(value / 60)
      if (minutes < 60) return `${minutes}m ${value % 60}s`
      return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
    },
    tokenLabel(token) {
      return this.tokenLabels[token] || token
    },
    groupSelectedCount(group) {
      const tokens = new Set((group.regions || []).map((r) => r.token))
      return this.selectedDraft.filter((t) => tokens.has(t)).length
    },
    async loadCatalog() {
      try {
        const payload = await api.getMapsCatalog()
        this.sections = Array.isArray(payload?.sections) ? payload.sections : []
        this.scheduleOptions = Array.isArray(payload?.scheduleOptions) ? payload.scheduleOptions : []
        const labels = {}
        for (const section of this.sections) {
          for (const group of section.groups || []) {
            for (const region of group.regions || []) labels[region.token] = region.label
          }
        }
        this.tokenLabels = labels
      } catch (e) {
        this.error = e?.message || "Failed to load the map catalog."
      } finally {
        this.loadingCatalog = false
      }
    },
    async refreshStatus() {
      if (this.statusInFlight) return
      this.statusInFlight = true
      try {
        const payload = await api.getMapsStatus()
        if (!payload) return
        const wasSelDirty = this.selectionDirty
        const wasSchDirty = this.scheduleDirty
        this.status = { ...STATUS_DEFAULTS, ...payload }
        this.progress = toProgress(payload.downloadProgress)
        const locs = Array.isArray(payload.selectedLocations) ? payload.selectedLocations.slice() : []
        this.selectedSaved = uniqueSorted(locs)
        if (!wasSelDirty) this.selectedDraft = [...this.selectedSaved]
        this.scheduleSaved = String(payload.scheduleValue ?? this.scheduleSaved)
        if (!wasSchDirty) this.scheduleDraft = this.scheduleSaved
        this.error = ""
      } catch (e) {
        this.error = e?.message || "Failed to load map status."
      } finally {
        this.loadingStatus = false
        this.statusInFlight = false
      }
    },
    toggleToken(token, enabled) {
      const next = new Set(this.selectedDraft)
      if (enabled) next.add(token)
      else next.delete(token)
      this.selectedDraft = [...next]
    },
    isGroupOpen(group) {
      return !!String(this.search || "").trim() || !!this.expandedGroups[group.expandKey]
    },
    toggleGroup(group) {
      const key = group.expandKey
      this.expandedGroups = { ...this.expandedGroups, [key]: !this.expandedGroups[key] }
    },
    setGroup(group, enabled) {
      const next = new Set(this.selectedDraft)
      for (const region of group.regions || []) {
        if (enabled) next.add(region.token)
        else next.delete(region.token)
      }
      this.selectedDraft = [...next]
    },
    resetDraft() {
      this.selectedDraft = [...this.selectedSaved]
      this.scheduleDraft = this.scheduleSaved
    },
    clearAll() {
      this.selectedDraft = []
    },
    async saveSelection() {
      if (this.savingSelection || !this.selectionDirty) return
      this.savingSelection = true
      try {
        const payload = await api.mapsOp("selection", { selectedLocations: this.selectedDraft })
        showSnackbar(payload?.message || "Map selection saved.")
        await this.refreshStatus()
      } catch (e) {
        showSnackbar(e?.message || "Failed to save map selection.", "error")
      } finally {
        this.savingSelection = false
      }
    },
    async saveSchedule() {
      if (this.savingSchedule || !this.scheduleDirty) return
      this.savingSchedule = true
      try {
        const payload = await api.mapsOp("schedule", { schedule: this.scheduleDraft })
        showSnackbar(payload?.message || "Map schedule updated.")
        await this.refreshStatus()
      } catch (e) {
        showSnackbar(e?.message || "Failed to update map schedule.", "error")
      } finally {
        this.savingSchedule = false
      }
    },
    async startDownload() {
      if (this.actionBusy || this.status.downloading || this.status.isOnroad || this.selectedDraft.length === 0) return
      this.actionBusy = true
      try {
        const payload = await api.mapsOp("download", {
          selectedLocations: this.selectedDraft,
          schedule: this.scheduleDraft,
        })
        showSnackbar(payload?.message || "Map download started.")
        await this.refreshStatus()
      } catch (e) {
        showSnackbar(e?.message || "Failed to start map download.", "error")
      } finally {
        this.actionBusy = false
      }
    },
    async cancelDownload() {
      if (this.actionBusy || !this.status.downloading) return
      this.actionBusy = true
      try {
        const payload = await api.mapsOp("cancel")
        showSnackbar(payload?.message || "Map download cancellation requested.")
        await this.refreshStatus()
      } catch (e) {
        showSnackbar(e?.message || "Failed to cancel map download.", "error")
      } finally {
        this.actionBusy = false
      }
    },
    async removeMaps() {
      if (this.actionBusy || this.status.downloading || this.status.isOnroad || !this.status.mapsPresent) return
      const ok = await GalaxyConfirm({
        title: "Remove Maps",
        message: "Are you sure you want to remove all downloaded offline maps?",
        confirmLabel: "Yes, Remove",
        danger: true,
      })
      if (!ok) return
      this.actionBusy = true
      try {
        const payload = await api.mapsOp("remove")
        showSnackbar(payload?.message || "Maps removed.")
        await this.refreshStatus()
      } catch (e) {
        showSnackbar(e?.message || "Failed to remove maps.", "error")
      } finally {
        this.actionBusy = false
      }
    },
  },
  template: `
    <div style="display:grid; gap:12px;">
      <section class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-map"></i>
          <span class="gx-section__title">Offline Maps</span>
        </div>
        <div style="padding: var(--sp-3); display:grid; gap:6px;">
          <p style="margin:0; color:var(--text-muted);">Select regions, start downloads, and manage offline maps entirely from Galaxy.</p>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Downloader</span>
            <span class="gx-row__value">{{ downloaderLabel }}</span>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Saved Regions</span>
            <span class="gx-row__value">{{ loadingStatus ? 'Checking...' : status.selectedCount }}</span>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Additional Storage</span>
            <span class="gx-row__value">{{ estimateLabel }}</span>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Last Updated</span>
            <span class="gx-row__value">{{ status.lastUpdate || 'Never' }}</span>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Storage Used</span>
            <span class="gx-row__value">{{ storageLabel }}</span>
          </div>
          <GxNotice v-if="status.isOnroad" text="Map downloads and removal are blocked while driving." style="margin:8px 0;" />
          <GxNotice v-if="selectionDirty" text="You have unsaved region changes. Downloading now will use the current selection." style="margin:8px 0;" />
          <GxNotice v-if="scheduleDirty" text="You have an unsaved schedule change. Downloading now will also apply it." style="margin:8px 0;" />
          <div style="display:flex; gap:8px; margin-top:8px; flex-wrap:wrap; align-items:center;">
            <button type="button" class="gx-btn" :disabled="!canDownload && !canCancel" @click="status.downloading ? cancelDownload() : startDownload()">
              <i class="bi" :class="status.downloading ? 'bi-x-circle' : 'bi-download'"></i>
              {{ status.downloading ? (status.cancelling ? 'Cancelling...' : 'Cancel Download') : 'Download Maps' }}
            </button>
            <button type="button" class="gx-btn gx-btn--tonal" style="color:var(--error);" :disabled="!canRemove" @click="removeMaps">Remove Maps</button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="savingSelection || loadingCatalog || !selectionDirty" @click="saveSelection">
              {{ savingSelection ? 'Saving...' : 'Save Selection' }}
            </button>
            <button type="button" class="gx-btn gx-btn--text" :disabled="!selectionDirty && !scheduleDirty" @click="resetDraft">Reset</button>
            <button type="button" class="gx-btn gx-btn--text" :disabled="selectedDraft.length === 0" @click="clearAll">Clear All</button>
          </div>
        </div>
      </section>

      <section v-if="showProgress" class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-arrow-down-circle"></i>
          <span class="gx-section__title">{{ status.downloading ? 'Download Progress' : progress.completed ? 'Last Download' : progress.cancelled ? 'Download Cancelled' : 'Download Estimate' }}</span>
          <span class="gx-row__value">{{ Math.round(progress.percent) }}%</span>
        </div>
        <div style="padding: var(--sp-3); display:grid; gap:6px;">
          <div style="height:8px; border-radius:4px; background:var(--glass-border, rgba(127,127,127,.2)); overflow:hidden;">
            <div :style="'width:' + Math.round(progress.percent) + '%;height:100%;background:var(--primary);transition:width .3s;'"></div>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Estimate</span>
            <span class="gx-row__value">{{ progress.estimatedDownloadBytes > 0 ? '~' + formatBytes(progress.estimatedDownloadBytes) + ' additional storage' : 'Storage estimate unavailable' }}</span>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Stored</span>
            <span class="gx-row__value">{{ progress.downloadedBytes > 0 ? formatBytes(progress.downloadedBytes) + ' added storage' : 'Storage reconciles after completion' }}</span>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Files</span>
            <span class="gx-row__value">{{ progress.totalFiles > 0 ? progress.downloadedFiles + ' / ' + progress.totalFiles + ' files' : 'Waiting for map service...' }}</span>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">ETA</span>
            <span class="gx-row__value">{{ status.downloading && progress.etaSeconds > 0 ? 'About ' + formatDuration(progress.etaSeconds) + ' remaining' : 'ETA unavailable until files start arriving' }}</span>
          </div>
          <div v-if="progress.primaryLocation" class="gx-row__desc">Current region: {{ progress.primaryLocation }}</div>
        </div>
      </section>

      <section class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-sliders"></i>
          <span class="gx-section__title">Regions &amp; Schedule</span>
        </div>
        <div style="padding: var(--sp-3); display:grid; gap:8px;">
          <div class="gx-row" style="border-top:none; flex-wrap:wrap;">
            <span class="gx-row__label">Search</span>
            <input class="gx-field" style="flex:1; min-width:180px;" type="search" v-model="search" placeholder="Filter by name or code" />
          </div>
          <div class="gx-row" style="border-top:none; flex-wrap:wrap;">
            <span class="gx-row__label">Auto Update</span>
            <GalaxySelect class="gx-field" style="flex:1; min-width:160px;" :value="scheduleDraft" @change="scheduleDraft = $event.target.value">
              <option v-for="opt in scheduleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
            </GalaxySelect>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="savingSchedule || !scheduleDirty" @click="saveSchedule">
              {{ savingSchedule ? 'Applying...' : 'Apply' }}
            </button>
          </div>
          <div class="gx-row" style="border-top:none; flex-wrap:wrap;">
            <span class="gx-row__label">Selected Regions</span>
            <div style="display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end; flex:1;">
              <template v-if="selectedDraft.length">
                <span v-for="token in selectedDraft" :key="token" class="gx-chip">{{ tokenLabel(token) }}</span>
              </template>
              <span v-else class="gx-row__desc" style="margin:0;">No regions selected.</span>
            </div>
          </div>
          <div class="gx-note" style="margin:0;">Saved schedule: {{ status.scheduleLabel }} · Draft regions: {{ selectedDraft.length }}</div>
        </div>
      </section>

      <div v-if="loadingCatalog" class="gx-loading">Loading map catalog...</div>
      <div v-else-if="filteredSections.length === 0" class="gx-empty">No regions match the current search.</div>

      <section v-for="section in filteredSections" :key="section.key" class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-globe"></i>
          <span class="gx-section__title">{{ section.title }}</span>
          <span class="gx-section__count">{{ section.groups.length }}</span>
        </div>
        <div style="padding: var(--sp-3); display:grid; gap:12px; grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));">
          <div v-for="group in section.groups" :key="group.key" class="gx-card" style="margin:0; align-self:start;">
            <div class="gx-section__header" role="button" tabindex="0" style="min-height:0; padding:var(--sp-2) var(--sp-3);"
              @click="toggleGroup(group)" @keydown.enter="toggleGroup(group)" @keydown.space.prevent="toggleGroup(group)">
              <span class="gx-section__title" style="font-size:var(--fs-base);">{{ group.title }}</span>
              <span class="gx-section__count">{{ groupSelectedCount(group) }} selected</span>
              <i class="bi bi-chevron-down gx-chevron" :class="{ open: isGroupOpen(group) }"></i>
            </div>
            <transition name="gx-collapse">
              <div v-show="isGroupOpen(group)" style="padding:0 var(--sp-3) var(--sp-2);">
                <div style="display:flex; gap:8px; padding:var(--sp-2) 0;">
                  <button type="button" class="gx-btn gx-btn--tonal" style="min-height:34px; padding:0 var(--sp-3);" @click="setGroup(group, true)">Select All</button>
                  <button type="button" class="gx-btn gx-btn--text" style="min-height:34px;" @click="setGroup(group, false)">Clear</button>
                </div>
                <div style="display:grid; gap:2px; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));">
                  <label v-for="region in group.visibleRegions" :key="region.token" class="gx-row" style="border:none; border-radius:var(--radius-md); min-height:0; padding:6px 8px; gap:8px; cursor:pointer;">
                    <input type="checkbox" :checked="selectedDraft.includes(region.token)" @change="toggleToken(region.token, $event.target.checked)" style="accent-color:var(--primary); width:16px; height:16px; flex:none;" />
                    <span style="flex:1; min-width:0; overflow-wrap:anywhere;">{{ region.label }}</span>
                    <span style="font-size:var(--fs-xs); color:var(--text-muted); flex:none;">{{ region.code }}</span>
                  </label>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </section>

      <GxNotice v-if="error" tone="danger" :text="error" />
    </div>
  `,
}
