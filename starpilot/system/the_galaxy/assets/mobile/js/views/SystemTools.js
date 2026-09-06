import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"
import { GalaxySection } from "../components/GalaxySection.js"
import { GxNotice } from "../components/GxNotice.js"

function shortCommit(commit) {
  return String(commit || "").slice(0, 10) || "—"
}

function toPercent(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return 0
  return Math.max(0, Math.min(100, n))
}

export const SystemTools = {
  name: "SystemTools",
  components: { GalaxySection, GxNotice },
  data() {
    return {
      branches: [],
      currentBranch: "",
      branchLoading: true,
      isOnroad: false,
      fastStatus: null,
      checkedForUpdates: false,
      busy: "",
      profiles: [],
      profileBusy: "",
    }
  },
  created() { this.poll = usePolling(() => this.loadFastStatus(), { interval: 3000 }); this.poll.start() },
  mounted() { this.loadBranches(); this.loadProfiles() },
  beforeUnmount() { this.poll?.destroy() },
  computed: {
    updateAvailable() { return !!this.fastStatus?.updateAvailable && !this.fastStatus?.running },
    factoryResetStatus() {
      const s = this.fastStatus
      if (!s || String(s?.lastMode || "").trim() !== "factory-reset") return null
      return {
        running: !!s.running,
        stage: String(s.stage || "idle"),
        message: String(s.message || ""),
        lastError: String(s.lastError || ""),
        progressLabel: String(s.progressLabel || ""),
        progressDetail: String(s.progressDetail || ""),
        progressPercent: toPercent(s.progressPercent),
        progressStep: Number(s.progressStep || 0),
        progressTotalSteps: Number(s.progressTotalSteps || 5),
      }
    },
  },
  methods: {
    shortCommit,
    async loadBranches() {
      try {
        const data = await api.getUpdateBranches()
        this.branches = Array.isArray(data?.branches) ? data.branches : []
        this.currentBranch = data?.currentBranch || ""
        this.isOnroad = !!data?.isOnroad
      } catch (e) {
        showSnackbar("Failed to load update info.", "error")
      } finally {
        this.branchLoading = false
      }
    },
    async loadFastStatus() {
      try { this.fastStatus = await api.getUpdateFastStatus() } catch (e) { this.fastStatus = null }
    },
    async backupToggles() {
      try {
        const blob = await api.backupToggles()
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = "toggle-backup.json"
        a.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
        showSnackbar("Toggle backup downloaded.")
      } catch (e) {
        showSnackbar(e?.message || "Backup failed.", "error")
      }
    },
    async loadProfiles() {
      try {
        const data = await api.getToggleProfiles()
        this.profiles = Array.isArray(data?.slots) ? data.slots : []
        this.isOnroad = !!data?.isOnroad
      } catch (e) {
        this.profiles = []
      }
    },
    async saveProfile(profile) {
      if (this.profileBusy || this.isOnroad) return
      if (profile.saved && !(await GalaxyConfirm({
        title: `Overwrite ${profile.label}?`,
        message: "This replaces the settings currently stored in this slot.",
        confirmLabel: "Overwrite",
      }))) return
      this.profileBusy = `save-${profile.slot}`
      try {
        const result = await api.saveToggleProfile(profile.slot)
        showSnackbar(result?.message || `Saved ${profile.label}.`)
        await this.loadProfiles()
      } catch (e) {
        showSnackbar(e?.message || "Failed to save settings profile.", "error")
      } finally {
        this.profileBusy = ""
      }
    },
    async loadProfile(profile) {
      if (this.profileBusy || this.isOnroad || !profile.saved || profile.invalid) return
      if (!(await GalaxyConfirm({
        title: `Load ${profile.label}?`,
        message: "This applies every saved setting in the slot to the device.",
        confirmLabel: "Load Settings",
      }))) return
      this.profileBusy = `load-${profile.slot}`
      try {
        const result = await api.loadToggleProfile(profile.slot)
        showSnackbar(result?.message || `Loaded ${profile.label}.`)
      } catch (e) {
        showSnackbar(e?.message || "Failed to load settings profile.", "error")
      } finally {
        this.profileBusy = ""
      }
    },
    onRestoreFile(e) {
      const file = e.target.files[0]
      e.target.value = ""
      if (!file) return
      if (file.size > 5_000_000) { showSnackbar("That toggle backup file is too large.", "error"); return }
      file.text().then((text) => {
        let data
        try { data = JSON.parse(text) } catch { showSnackbar("That file is not a valid toggle backup.", "error"); return }
        if (!data || typeof data !== "object" || Array.isArray(data)) { showSnackbar("That file is not a valid toggle backup.", "error"); return }
        api.restoreToggles(data).then((res) => {
          showSnackbar(res?.message || "Toggles restored!")
        }).catch((err) => showSnackbar(err?.message || "Failed to restore toggles.", "error"))
      })
    },
    async resetDefault() {
      if (!(await GalaxyConfirm({ title: "Reset toggles to default?", message: "This resets all toggles to their default values and reboots.", confirmLabel: "Reset", danger: true }))) return
      try {
        await api.resetTogglesDefault()
        showSnackbar("Resetting toggles to default... rebooting.")
      } catch (e) {
        showSnackbar("Reset failed.", "error")
      }
    },
    onBranchSelect(e) {
      const branch = e.target.value
      e.target.value = this.currentBranch || ""
      this.switchBranch(branch)
    },
    async switchBranch(branch) {
      if (!branch || branch === this.currentBranch) return
      if (!(await GalaxyConfirm({ title: "Switch branch?", message: `Switch to ${branch} and update?`, confirmLabel: "Switch" }))) return
      try {
        await api.setUpdateBranch(branch)
        showSnackbar(`Switching to ${branch}...`)
      } catch (e) {
        showSnackbar(e?.message || "Switch failed.", "error")
      }
    },
    async checkUpdates() {
      if (this.busy) return
      this.busy = "check"
      try {
        await this.loadFastStatus()
        this.checkedForUpdates = true
        const st = this.fastStatus
        if (st?.running) showSnackbar("An update is already running.")
        else if (st?.updateAvailable) showSnackbar(st?.message || "Update available.")
        else showSnackbar(st?.message || "No update available — you're up to date.")
      } catch (e) {
        showSnackbar("Failed to check for updates.", "error")
      } finally {
        this.busy = ""
      }
    },
    async applyFastUpdate() {
      if (this.busy || this.isOnroad) return
      if (this.fastStatus?.running) { showSnackbar("Fast update is already running."); return }
      if (!this.checkedForUpdates || !this.updateAvailable) {
        showSnackbar("No update available. Run \"Check for Updates\" first.", "error")
        return
      }
      const st = this.fastStatus
      const confirmed = await GalaxyConfirm({
        title: "Update available",
        message: `Fast update to the latest commit on ${st?.branch || "this branch"}.\n\nYour device will reboot when the update is done.`,
        confirmLabel: "Update & Reboot",
        danger: true,
      })
      if (!confirmed) return
      await this.runUpdate("fast")
    },
    async runUpdate(action) {
      if (this.busy) return
      this.busy = action
      try {
        if (action === "rollback") {
          const st = this.fastStatus
          if (st && !st.rollbackAvailable) {
            showSnackbar("No previous installed version is available to roll back to.", "error")
            return
          }
        }
        if (action !== "fast") {
          const actionLabels = { recover: "Recover the interrupted update?", rollback: "Roll back to the previous installed version?" }
          if (!(await GalaxyConfirm({ title: actionLabels[action] || "Continue?", message: "Your device will reboot when the operation is done.", confirmLabel: "Continue", danger: true }))) return
        }
        const fn = action === "fast" ? api.updateFast : action === "recover" ? api.updateRecover : api.updateRollback
        const payload = await fn()
        showSnackbar(payload?.message || "Update started.")
        await this.loadFastStatus()
      } catch (e) {
        showSnackbar(e?.message || "Update failed.", "error")
      } finally {
        this.busy = ""
      }
    },
    async factoryReset() {
      if (!(await GalaxyConfirm({ title: "Factory reset (SAVE ME)?", message: "This wipes params, backups, themes, models, maps, and route data, then reboots. This cannot be undone.", confirmLabel: "Factory Reset", danger: true }))) return
      try {
        await api.factoryReset()
        showSnackbar("SAVE ME initiated — factory resetting...")
      } catch (e) {
        showSnackbar(e?.message || "Factory reset failed.", "error")
      }
    },
    async deleteAllDrivingRoutes() {
      if (!(await GalaxyConfirm({ title: "Delete All Driving Routes", message: "This permanently deletes all local routes from standard, high-resolution, and alternate footage storage. It does not reset settings or reboot the device.", confirmLabel: "Delete Routes", danger: true }))) return
      try {
        const payload = await api.deleteAllRoutes(true)
        showSnackbar(payload?.message || "All local driving routes deleted.")
      } catch (e) {
        showSnackbar(e?.message || "Failed to delete driving routes.", "error")
      }
    },
  },
  template: `
    <div>
      <h2 style="margin-top:0;">System Tools</h2>

      <GalaxySection title="Software & Updates" icon="bi-arrow-up-circle" :collapsible="false">
        <div style="padding: var(--sp-3);">
          <div v-if="branchLoading" class="gx-loading">Loading update info...</div>
          <template v-else>
            <GxNotice v-if="isOnroad" text="Updates and branch switching are only available while offroad." style="margin-bottom:12px;" />

            <div v-if="fastStatus" class="gx-card" style="margin-bottom:12px;">
              <div class="gx-section__header">
                <i class="bi bi-arrow-repeat"></i>
                <span class="gx-section__title">Update Status</span>
                <span v-if="fastStatus.running" class="gx-chip" style="background:var(--primary);color:var(--on-primary);">{{ fastStatus.progressPercent }}%</span>
                <span v-else-if="fastStatus.updateAvailable" class="gx-chip" style="background:var(--warning);color:var(--black);">Update available</span>
                <span v-else class="gx-chip">Up to date</span>
              </div>
              <div style="padding: var(--sp-3); display:grid; gap:6px;">
                <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;"><span class="gx-row__label">Branch</span><span class="gx-row__value">{{ fastStatus.branch || currentBranch || '—' }}</span></div>
                <div v-if="fastStatus.running" class="gx-row" style="border-top:none; min-height:0; padding:4px 0;"><span class="gx-row__label">Stage</span><span class="gx-row__value">{{ fastStatus.stage }} · {{ fastStatus.progressLabel }}</span></div>
                <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;"><span class="gx-row__label">Local</span><span class="gx-row__value" style="font-family:monospace;">{{ shortCommit(fastStatus.localCommit) }}</span></div>
                <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;"><span class="gx-row__label">Remote</span><span class="gx-row__value" style="font-family:monospace;">{{ shortCommit(fastStatus.remoteCommit) }}</span></div>
                <div v-if="fastStatus.message" class="gx-note">{{ fastStatus.message }}</div>
                <div v-if="fastStatus.warning && (fastStatus.running || fastStatus.updateAvailable)" class="gx-note gx-note--danger">{{ fastStatus.warning }}</div>
                <div v-if="fastStatus.agnosUpdate?.available && fastStatus.agnosUpdate?.warnings?.length" style="margin-top:4px;">
                  <div v-for="w in fastStatus.agnosUpdate.warnings" :key="w" class="gx-note gx-note--danger"><i class="bi bi-exclamation-triangle-fill"></i> {{ w }}</div>
                </div>
              </div>
            </div>

            <div class="gx-card" style="margin-bottom:12px;">
              <div class="gx-section__header"><i class="bi bi-git-branch"></i><span class="gx-section__title">Switch Branch</span></div>
              <div style="padding: var(--sp-3);">
                <select class="gx-field gx-field--full" :disabled="!!isOnroad" @change="onBranchSelect">
                  <option v-if="!branches.length" value="">No branches available</option>
                  <option v-for="b in branches" :key="b" :value="b" :selected="b === currentBranch">{{ b === currentBranch ? b + ' (current)' : b }}</option>
                </select>
              </div>
            </div>

            <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap;">
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!!busy || isOnroad || !!fastStatus?.running" @click="checkUpdates">
                <i v-if="busy === 'check'" class="bi bi-arrow-repeat gx-spin"></i>
                <i v-else class="bi bi-search"></i> {{ busy === 'check' ? 'Checking...' : 'Check for Updates' }}
              </button>
              <button type="button" class="gx-btn" :disabled="!updateAvailable || !!busy || isOnroad" @click="applyFastUpdate">
                <i class="bi bi-arrow-up-circle"></i> {{ busy === 'fast' ? 'Updating...' : 'Update Now' }}
              </button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!!busy || isOnroad" @click="runUpdate('recover')">Recover</button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!!busy || isOnroad" @click="runUpdate('rollback')">Rollback</button>
            </div>
            <p class="gx-note">Check for Updates scans for a newer commit. Use <strong>Update Now</strong> to install it.</p>
            <p class="gx-note"><strong>Recover</strong> continues an update that was interrupted (for example, by power loss mid-install). <strong>Rollback</strong> returns the device to the previously installed version if the current one has a problem.</p>
            <p v-if="checkedForUpdates && !updateAvailable && !fastStatus?.running" class="gx-note">
              The device is up to date. Update becomes available only after a check finds a newer commit.
            </p>
          </template>
        </div>
      </GalaxySection>

      <GalaxySection title="Backup & Restore" icon="bi-arrow-repeat" :collapsible="false">
        <div style="padding: var(--sp-3);">
          <h4 style="margin:0 0 4px;">Settings Profiles</h4>
          <p class="gx-note" style="margin:0 0 10px;">Keep two local configurations for different vehicles, drivers, or troubleshooting. Profiles never include pairing or sensitive device data.</p>
          <GxNotice v-if="isOnroad" text="Park the vehicle to save or load a profile." style="margin-bottom:12px;" />
          <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:10px; margin-bottom:16px;">
            <div v-for="profile in profiles" :key="profile.slot" class="gx-card" style="padding:12px;">
              <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:10px;">
                <strong>{{ profile.label }}</strong>
                <span class="gx-chip">{{ profile.invalid ? 'Damaged' : profile.saved ? profile.settingsCount + ' settings' : 'Empty' }}</span>
              </div>
              <div style="display:flex; gap:8px; flex-wrap:wrap;">
                <button type="button" class="gx-btn gx-btn--tonal" :disabled="!!profileBusy || isOnroad" @click="saveProfile(profile)">
                  <i class="bi bi-save"></i> {{ profileBusy === 'save-' + profile.slot ? 'Saving...' : profile.saved ? 'Overwrite' : 'Save Current' }}
                </button>
                <button type="button" class="gx-btn" :disabled="!!profileBusy || isOnroad || !profile.saved || profile.invalid" @click="loadProfile(profile)">
                  <i class="bi bi-arrow-down-circle"></i> {{ profileBusy === 'load-' + profile.slot ? 'Loading...' : 'Load' }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <div style="padding: var(--sp-3); display:flex; gap:8px; flex-wrap:wrap;">
          <button type="button" class="gx-btn" @click="backupToggles"><i class="bi bi-download"></i> Backup Toggles</button>
          <button type="button" class="gx-btn gx-btn--tonal" @click="$refs.restoreInput.click()"><i class="bi bi-upload"></i> Restore Toggles</button>
          <button type="button" class="gx-btn gx-btn--tonal" @click="resetDefault">Reset to Default</button>
          <button type="button" class="gx-btn gx-btn--danger" @click="deleteAllDrivingRoutes">Delete All Driving Routes</button>
          <input ref="restoreInput" type="file" accept=".json" style="display:none;" @change="onRestoreFile" />
        </div>
        <p class="gx-note" style="padding: 0 var(--sp-4);">Backup downloads your toggle settings as a JSON file. Restore re-applies one, and Reset to Default clears them back to stock and reboots.</p>

        <div v-if="factoryResetStatus" style="padding: var(--sp-3); border-top: 1px solid var(--border-color, rgba(255,255,255,.08));">
          <div class="gx-section__header">
            <i class="bi bi-arrow-repeat" :class="{ 'gx-spin': factoryResetStatus.running }"></i>
            <span class="gx-section__title">Factory Reset Status</span>
            <span class="gx-chip">{{ factoryResetStatus.progressStep }}/{{ factoryResetStatus.progressTotalSteps }}{{ factoryResetStatus.progressLabel ? ' · ' + factoryResetStatus.progressLabel : '' }}</span>
          </div>
          <div style="padding: var(--sp-3);">
            <div style="height:8px; border-radius:999px; background:var(--surface, rgba(255,255,255,.1)); overflow:hidden;">
              <div :style="{ height: '100%', width: factoryResetStatus.progressPercent + '%', background: factoryResetStatus.stage === 'error' ? 'var(--error)' : 'var(--primary)', transition: 'width .4s' }"></div>
            </div>
            <p v-if="factoryResetStatus.message" style="margin:8px 0 0;">{{ factoryResetStatus.message }}</p>
            <p v-if="factoryResetStatus.progressDetail" class="gx-note" style="margin:4px 0 0;">{{ factoryResetStatus.progressDetail }}</p>
            <p v-if="factoryResetStatus.lastError" class="gx-note gx-note--danger" style="margin:4px 0 0;">Last Error: {{ factoryResetStatus.lastError }}</p>
          </div>
        </div>
      </GalaxySection>

      <GalaxySection title="Danger Zone" icon="bi-exclamation-triangle" :collapsible="false">
        <div style="padding: var(--sp-3); display:grid; gap:12px;">
          <p class="gx-note" style="margin:0;">Last resort only. <strong>Factory Reset (also known as SAVE ME)</strong> wipes params, backups, themes, models, maps, and route data, then reboots the device. This cannot be undone.</p>
          <button type="button" class="gx-btn gx-btn--danger" style="justify-self:start;" @click="factoryReset">Factory Reset Device (SAVE ME)</button>
        </div>
      </GalaxySection>
    </div>
  `,
}
