import { GxDialog } from "./dialog.js"
import { GxState } from "./state.js"
import { GxNotice } from "./notice.js"
import { ToggleBackup } from "./toggle-backup.js"
import { GalaxySelect } from "./galaxy-select.js"
import { GalaxySettingRow, switchRow } from "./galaxy-setting-row.js"

const ACTIONS = new Set(["check", "download", "select", "install", "preferences", "fast", "rollback", "versions", "version"])
const REQUEST_STATES = new Set(["pending", "complete", "failed"])
const UPDATER_ACTIVE = new Set(["checking...", "downloading...", "finalizing update...", "updating..."])
const PRIMARY_BRANCHES = ["StarPilot", "Dom"]
const PRIMARY_BRANCH_LABELS = { StarPilot: "Stable — StarPilot", Dom: "Development — Dom" }
const PRIMARY_BRANCH_HELP = {
  StarPilot: "Stable releases. Recommended for most users.",
  Dom: "Latest features and fixes under development. Updates regularly and may introduce bugs.",
}
const unavailableOperations = () => ({ parked: false, availableBranches: [], selectedTarget: null,
  canCheck: false, canFastUpdate: false, canRollback: false, canDownload: false, canSelect: false, canInstall: false,
  reason: "Update controls are unavailable", request: null })

export function validSoftwareSnapshot(data) {
  const text = (value) => value === null || typeof value === "string"
  const flag = (value) => value === null || typeof value === "boolean"
  const updater = data?.updater, operations = data?.operations, request = operations?.request
  return data?.schemaVersion === 1 && !!data.installed && !!updater &&
    [data.installed.version, data.installed.branch, data.installed.commit, updater.state,
      updater.targetBranch, updater.lastSuccessAt, updater.lastFetchAt].every(text) &&
    (updater.lastCheckedAt === undefined || text(updater.lastCheckedAt)) &&
    (data.installed.displayVersion === undefined || text(data.installed.displayVersion)) &&
    [updater.targetChangeFound, updater.finalizedUpdateReady].every(flag) &&
    (updater.failedCount === null || Number.isSafeInteger(updater.failedCount) && updater.failedCount >= 0) &&
    (operations === undefined || !!operations && typeof operations.parked === "boolean" && Array.isArray(operations.availableBranches) &&
    operations.availableBranches.length <= 256 && operations.availableBranches.every((branch) =>
      typeof branch === "string" && branch.length > 0 && branch.length <= 128) &&
    text(operations.selectedTarget) && text(operations.reason) &&
    (operations.progress === undefined || operations.progress === null || typeof operations.progress === "object" &&
      text(operations.progress.stage) && (operations.progress.stage === null || operations.progress.stage.length <= 128) &&
      text(operations.progress.detail) && (operations.progress.detail === null || operations.progress.detail.length <= 512) &&
      (operations.progress.percent === null || Number.isFinite(operations.progress.percent) &&
       operations.progress.percent >= 0 && operations.progress.percent <= 100)) &&
    (operations.canFastUpdate === undefined || typeof operations.canFastUpdate === "boolean") &&
    (request?.selectedCommit === undefined || /^[0-9a-f]{40}$/.test(request.selectedCommit)) &&
    (operations.canRollback === undefined || typeof operations.canRollback === "boolean") &&
    (operations.automaticDownloads === undefined || flag(operations.automaticDownloads)) &&
    (operations.canConfigure === undefined || typeof operations.canConfigure === "boolean") &&
    (operations.history === undefined || validHistory(operations.history)) &&
    [operations.canCheck, operations.canDownload, operations.canSelect, operations.canInstall].every((value) => typeof value === "boolean") &&
    (request === null || !!request && typeof request.id === "string" && request.id.length <= 100 &&
      ACTIONS.has(request.action) && text(request.target) && REQUEST_STATES.has(request.state) && text(request.error) &&
      (request.outcome === undefined || ["up_to_date", "restarting"].includes(request.outcome))))
}

export function softwareProgress(updater, operations = {}) {
  if (!updater) return null
  const progress = operations.progress
  const fast = updater.state === "updating..." ? updater.fast : null
  const stage = progress?.stage || fast?.stage
  const active = UPDATER_ACTIVE.has(updater.state) && !["unavailable", "timed_out", "error", "complete"].includes(stage)
  const labels = { "checking...": "Checking for updates", "downloading...": "Downloading update",
    "finalizing update...": "Finalizing update", "updating...": "Updating software",
    checking: "Checking for updates", downloading: "Downloading update", finalizing: "Finalizing update",
    preparing: "Preparing update", fetching: "Downloading update", validating: "Validating update",
    applying: "Applying update", submodules: "Preparing dependencies", rebooting: "Restarting device",
    complete: "Update complete", error: "Update failed", unavailable: "Updater status unavailable", timed_out: "Update is taking longer than expected" }
  if (!active && (!stage || ["idle", "unknown"].includes(stage))) return null
  const percent = Number.isFinite(progress?.percent) && progress.percent >= 0 && progress.percent <= 100 ? progress.percent : null
  return { active, percent, label: labels[progress?.stage || fast?.stage] || progress?.stage || fast?.stage || labels[updater.state] || "Update status",
    detail: progress?.detail || fast?.detail || "" }
}

export function validHistory(value) {
  const rows = (items) => Array.isArray(items) && items.length <= 20 && items.every((row) =>
    /^[0-9a-f]{40}$/.test(row?.hash) && typeof row.date === "string" && row.date.length <= 64 &&
    typeof row.subject === "string" && row.subject.length <= 512)
  return !!value && rows(value.installed) && rows(value.downloaded) &&
    (value.recent === undefined || !!value.recent && (value.recent.branch === null || typeof value.recent.branch === "string") &&
      (value.recent.head === null || /^[0-9a-f]{40}$/.test(value.recent.head)) && rows(value.recent.entries)) &&
    [value.currentReleaseNotes, value.downloadedReleaseNotes].every((notes) => notes === null || typeof notes === "string" && notes.length <= 65536)
}

export class SoftwareStatusFeed {
  constructor({ includeHistory = true, publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { includeHistory, publish, unauthorized, fetcher, later, cancelTimer })
    this.active = false
    this.generation = 0
    this.controller = null
    this.timeout = null
    this.pollTimer = null
    this.data = null
    this.attempted = false
    this.busy = false
    this.mutating = false
    this.blocked = false
    this.uncertain = false
    this.uncertainAction = null
    this.actionPriorRequestId = null
    this.installBaseline = null
    this.notice = ""
    this.error = ""
  }

  emit(status) { this.publish({ status, data: this.data, busy: this.busy, uncertain: this.uncertain,
    notice: this.notice, error: this.error }) }

  stop() {
    this.active = false
    this.generation++
    this.controller?.abort()
    if (this.timeout !== null) this.cancelTimer(this.timeout)
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    this.controller = this.timeout = this.pollTimer = null
    this.data = this.installBaseline = this.uncertainAction = this.actionPriorRequestId = null
    this.attempted = false
    this.busy = this.mutating = this.blocked = this.uncertain = false
    this.notice = this.error = ""
    this.emit("idle")
  }

  start() { this.stop(); this.active = true; return this.load() }

  needsRapidPoll() {
    return this.uncertain || !!this.installBaseline || this.data?.operations?.parked === false ||
      this.data?.operations?.request?.state === "pending" || UPDATER_ACTIVE.has(this.data?.updater?.state)
  }

  schedulePoll(delay = null) {
    if (!this.active || this.pollTimer !== null || this.controller) return
    const generation = this.generation
    this.pollTimer = this.later(() => {
      this.pollTimer = null
      if (this.active && generation === this.generation) this.load()
    }, delay ?? (this.needsRapidPoll() ? 1000 : 5000))
  }

  async run(body = null) {
    if (!this.active || this.mutating) return null
    const generation = ++this.generation
    this.controller?.abort()
    if (this.timeout !== null) this.cancelTimer(this.timeout)
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    this.pollTimer = null
    const controller = new AbortController()
    this.controller = controller
    this.busy = body !== null || this.data === null
    this.mutating = body !== null
    if (body !== null) this.error = ""
    this.emit(this.data ? "ready" : this.attempted ? "unavailable" : "loading")
    this.timeout = this.later(() => {
      if (!this.active || this.generation !== generation || this.controller !== controller) return
      controller.abort()
      this.generation++
      this.controller = this.timeout = null
      this.busy = this.mutating = false
      this.attempted = true
      this.blocked = true
      if (body !== null) { this.uncertain = true; this.uncertainAction = body }
      this.error = body !== null ? "The request timed out. Its result is unknown; wait for a fresh status before trying another action." :
        "Software status timed out. Refresh to try again."
      this.emit(this.data ? "ready" : "unavailable")
      this.schedulePoll(2000)
    }, 5000)
    try {
      const response = await this.fetcher(body === null ? "./api/software/status" + (this.includeHistory ? "" : "?history=0") : "./api/software/action", {
        credentials: "same-origin", cache: "no-store", signal: controller.signal,
        ...(body === null ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
      })
      if (!this.active || generation !== this.generation || controller.signal.aborted) return null
      const payload = typeof response.json === "function" ? await response.json().catch(() => null) : null
      if (!this.active || generation !== this.generation || controller.signal.aborted) return null
      if (response.status === 401 || response.status === 503 &&
          ["access_unavailable", "setup_required"].includes(payload?.code)) {
        this.stop()
        this.unauthorized()
        return null
      }
      if (!response.ok) {
        const error = new Error(payload?.error || payload?.message || "Software request failed. Refresh to try again.")
        error.rejected = response.status >= 400 && response.status < 500
        throw error
      }
      if (!validSoftwareSnapshot(payload)) throw new Error("Software response is unavailable. Refresh to try again.")
      this.data = payload.operations === undefined ? { ...payload, operations: unavailableOperations() } : payload
      this.attempted = true
      this.blocked = false
      if (body !== null) {
        this.uncertain = false
        this.uncertainAction = null
        this.actionPriorRequestId = null
        if (["fast", "rollback", "version"].includes(body.action)) {
          this.notice = `Updating ${body.branch}. Waiting for completion or reconnect.`
        } else if (body.action === "install") {
          this.installBaseline = this.installBaseline || { commit: payload.installed.commit, branch: payload.installed.branch, target: body.branch }
          this.notice = "Restart requested. Waiting to reconnect and verify the installed build."
        } else this.notice = body.action === "select" ? `Target branch set to ${body.branch}. Check and download the update when ready.` :
          body.action === "preferences" ? "Automatic download preference saved." : ""
      } else {
        const observed = payload.operations.request
        const requestObserved = !!observed && !!this.uncertainAction && observed.action === this.uncertainAction.action &&
          observed.id !== this.actionPriorRequestId &&
          (!this.uncertainAction?.branch || observed.target === this.uncertainAction.branch) &&
          (!this.uncertainAction?.selectedCommit || observed.selectedCommit === this.uncertainAction.selectedCommit)
        const selectionObserved = this.uncertainAction?.action === "select" &&
          payload.operations.selectedTarget === this.uncertainAction.branch
        const preferenceObserved = this.uncertainAction?.action === "preferences" &&
          payload.operations.automaticDownloads === this.uncertainAction.automaticDownloads
        if (this.uncertain && (requestObserved || selectionObserved || preferenceObserved)) {
          this.uncertain = false
          this.uncertainAction = null
          this.actionPriorRequestId = null
        }
        if (["fast", "version"].includes(this.installBaseline?.action) && observed?.action === this.installBaseline.action && observed.target === this.installBaseline.target &&
            (!this.installBaseline.selectedCommit || observed.selectedCommit === this.installBaseline.selectedCommit) &&
            ["complete", "failed"].includes(observed.state)) {
          if (observed.state === "failed" || observed.outcome === "up_to_date") {
            this.installBaseline = null
            this.notice = observed.state === "failed" ? "" : "Installed branch is already up to date. No restart needed."
          } else this.notice = "Update installed. Waiting to reconnect and verify the installed build."
        }
        if (this.installBaseline && payload.installed.branch === this.installBaseline.target &&
            (!this.installBaseline.selectedCommit || payload.installed.commit === this.installBaseline.selectedCommit) &&
            (payload.installed.commit && payload.installed.commit !== this.installBaseline.commit ||
             payload.installed.branch !== this.installBaseline.branch)) {
          this.installBaseline = null
          this.uncertain = false
          this.uncertainAction = null
          this.actionPriorRequestId = null
          this.notice = "Installed build verified after reconnect."
        }
      }
      this.error = ""
      this.emit("ready")
      return payload
    } catch (error) {
      if (this.active && generation === this.generation && !controller.signal.aborted) {
        this.attempted = true
        this.blocked = true
        if (body !== null) {
          this.uncertain = !error?.rejected
          this.uncertainAction = this.uncertain ? body : null
          if (error?.rejected && ["install", "fast", "rollback", "version"].includes(body.action)) this.installBaseline = null
        }
        this.error = error?.message || "Software request failed. Refresh to try again."
        this.emit(this.data ? "ready" : this.attempted ? "unavailable" : "loading")
      }
      return null
    } finally {
      if (this.controller === controller) {
        if (this.timeout !== null) this.cancelTimer(this.timeout)
        this.controller = this.timeout = null
        this.busy = this.mutating = false
        this.emit(this.data ? "ready" : "unavailable")
        this.schedulePoll(this.error ? 2000 : null)
      }
    }
  }

  load() { return this.run() }

  configureAutomaticDownloads(enabled) {
    if (!this.active || this.mutating || this.blocked || this.uncertain || this.data?.operations?.canConfigure !== true ||
        typeof enabled !== "boolean") return null
    return this.run({ action: "preferences", automaticDownloads: enabled,
      expectedAutomaticDownloads: this.data.operations.automaticDownloads })
  }

  action(action, branch = null, selection = null) {
    const operations = this.data?.operations
    const capability = { check: "canCheck", download: "canDownload", select: "canSelect", install: "canInstall", fast: "canFastUpdate", rollback: "canRollback", versions: "canFastUpdate", version: "canFastUpdate" }[action]
    if (!this.active || !capability || this.mutating || this.blocked || this.uncertain || !operations?.parked ||
        operations[capability] !== true || operations.request?.state === "pending") return null
    if (action === "select" && (branch === "other:" || !operations.availableBranches.includes(branch) || branch === operations.selectedTarget)) return null
    if (["download", "install"].includes(action) && (!branch || branch !== operations.selectedTarget)) return null
    if (["fast", "versions", "version"].includes(action) && (!branch || branch !== this.data.installed.branch && !operations.availableBranches.includes(branch))) return null
    if (action === "rollback" && branch !== this.data.installed.branch) return null
    if (action === "version") {
      if (selection?.expectedCommit !== this.data.installed.commit || !/^[0-9a-f]{40}$/.test(selection?.selectedCommit) ||
          operations.history?.recent?.branch !== branch ||
          !operations.history.recent.entries.some((row) => row.hash === selection.selectedCommit)) return null
    }
    this.actionPriorRequestId = operations.request?.id ?? null
    if (action === "install") this.installBaseline = { commit: this.data.installed.commit,
      branch: this.data.installed.branch, target: branch }
    if (["fast", "rollback", "version"].includes(action)) this.installBaseline = { commit: this.data.installed.commit, branch: this.data.installed.branch, target: branch, action, ...(action === "version" ? { selectedCommit: selection.selectedCommit } : {}) }
    if (action === "version") return this.run({ action, branch, expectedCommit: selection.expectedCommit, selectedCommit: selection.selectedCommit })
    return this.run(action === "check" ? { action } : { action, branch })
  }
}

export const SoftwarePage = {
  components: { GxDialog, GxState, GxNotice, GalaxySelect, GalaxySettingRow, ToggleBackup },
  name: "SoftwarePage",
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ status: "idle", data: null, busy: false, uncertain: false, notice: "", error: "",
    draftBranch: "", primaryChoice: "", draftTouched: false, dialog: null, historyKind: "recent", version: "" }),
  created() {
    this.feed = new SoftwareStatusFeed({ includeHistory: false, publish: (update) => {
      Object.assign(this.$data, update)
      if (update.data && !this.draftTouched) this.syncDraftBranch(update.data.operations.selectedTarget)
    }, unauthorized: this.unauthorized })
  },
  mounted() { if (this.mode === "local") this.feed.start() },
  beforeUnmount() { this.feed.stop() },
  computed: {
    operations() { return this.data?.operations },
    updateProgress() { return softwareProgress(this.data?.updater, this.operations) },
    pending() { return this.operations?.request?.state === "pending" },
    actionUnavailable() { return this.uncertain || this.pending || !!this.error || !this.operations?.parked },
    actionDisabled() { return this.busy || this.actionUnavailable },
    branchOptions() {
      const available = this.operations?.availableBranches || []
      return [...new Set([this.operations?.selectedTarget, this.data?.installed.branch, ...available].filter(branch => branch && branch !== "other:"))]
        .map(name => ({ name, available: available.includes(name) || name === this.data?.installed.branch }))
    },
    primaryBranchHelp() { return PRIMARY_BRANCH_HELP[this.primaryChoice] || "" },
    otherBranches() {
      const available = this.operations?.availableBranches || []
      const selected = this.operations?.selectedTarget
      const installed = this.data?.installed?.branch
      return [...new Set([selected, installed, ...available].filter(branch => branch && branch !== "other:" && !PRIMARY_BRANCHES.includes(branch)))]
        .map(name => ({ name, listed: available.includes(name), current: name === installed }))
    },
    canStageBranch() { return !!this.draftBranch && this.draftBranch !== "other:" && this.operations?.availableBranches.includes(this.draftBranch) && this.draftBranch !== this.operations.selectedTarget },
    branchChanging() { return !!this.draftBranch && this.draftBranch !== this.data?.installed.branch },
    versionEntries() {
      const history = this.operations?.history
      return this.historyKind === "recent" ? (history?.recent?.branch === this.draftBranch ? history.recent.entries : []) : history?.[this.historyKind] || []
    },
    commitsUrl() {
      const repository = this.operations?.repository
      return /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository || "") ? `https://github.com/${repository}/commits/${encodeURIComponent(this.draftBranch || this.data.installed.branch)}` : ""
    },
  },
  methods: {
    switchRow,
    syncDraftBranch(branch) {
      this.draftBranch = this.operations?.availableBranches.includes(branch) || branch === this.data?.installed.branch ? branch : this.data?.installed.branch || ""
      this.primaryChoice = PRIMARY_BRANCHES.includes(this.draftBranch) ? this.draftBranch : this.draftBranch ? "other:" : ""
    },
    changeBranch() { this.draftTouched = true; this.version = ""; this.primaryChoice = PRIMARY_BRANCHES.includes(this.draftBranch) ? this.draftBranch : this.draftBranch ? "other:" : "" },
    onPrimaryBranchChange() {
      this.draftTouched = true
      this.version = ""
      if (this.primaryChoice === "other:") {
        if (!this.otherBranches.some(option => option.name === this.draftBranch)) {
          const selected = this.operations?.selectedTarget
          this.draftBranch = this.otherBranches.some(option => option.name === selected) ? selected : ""
        }
      } else this.draftBranch = this.primaryChoice
    },
    onOtherBranchChange() { this.draftTouched = true; this.version = "" },
    branchLabel(branch) { return PRIMARY_BRANCH_LABELS[branch] || branch },
    primaryBranchHelpFor(branch) { return PRIMARY_BRANCH_HELP[branch] || "" },
    versionLabel(entry) { return `${entry.subject.trim() || this.shortCommit(entry.hash)} · ${entry.date ? new Date(entry.date).toLocaleDateString() : this.shortCommit(entry.hash)}` },
    shown(value) { return value ?? "Unavailable" },
    reported(value) { return value ? new Date(value).toLocaleString() : "Unavailable" },
    shortCommit(value) { return value ? value.slice(0, 12) : "Unavailable" },
    requestMessage(request) {
      if (!request) return ""
      if (request.state === "failed") return request.error || "Update request failed. Refresh and try again."
      if (["fast", "rollback", "version"].includes(request.action)) return request.state === "pending" ? `Updating ${request.target}…` :
        request.outcome === "up_to_date" ? "Installed branch is already up to date. No restart needed." :
        "Update installed. Waiting to reconnect and verify the installed build."
      if (request.action === "versions") return request.state === "pending" ? "Loading recent versions…" : "Recent versions loaded."
      if (request.action === "install") return "Restart requested. Waiting to reconnect and verify the installed build."
      if (request.state === "pending") return request.action === "check" ? "Checking for updates…" : "Downloading and preparing update…"
      return request.action === "check" ? "Update check finished." : request.action === "download" ? "Download finished." : "Target branch saved."
    },
    chooseBranch() {
      if (!this.operations?.canSelect || this.actionDisabled || !this.canStageBranch) return
      this.dialog = { action: "select", branch: this.draftBranch, title: "Change target branch",
        message: `Set ${this.draftBranch} as the target branch? This only stages the choice. Check for updates and download separately.`, label: "Set target branch" }
    },
    askFastUpdate() {
      const branch = this.draftBranch || this.operations?.selectedTarget || this.data?.installed?.branch
      if (this.actionDisabled || this.operations?.canFastUpdate !== true || !branch) return
      const switching = branch !== this.data?.installed?.branch
      this.dialog = { action: "fast", branch, title: switching ? "Switch branch" : "Fast Update",
        message: `Download latest version of ${branch} and restart?`, label: switching ? "Switch & update" : "Fast Update" }
    },
    loadHistory(event) {
      if (!event.target.open || this.operations?.history || this.busy) return
      this.feed.includeHistory = true
      this.feed.load()
    },
    async loadVersions() {
      const branch = this.draftBranch || this.operations?.selectedTarget || this.data?.installed?.branch
      if (this.actionDisabled || !branch) return
      if (branch !== this.operations.selectedTarget) {
        const result = await this.feed.action("select", branch)
        if (!result) return
      }
      return this.feed.action("versions", branch)
    },
    askVersion(entry) {
      const branch = this.operations?.history?.recent?.branch
      if (!entry || this.actionDisabled || this.operations?.canFastUpdate !== true || !branch) return
      this.dialog = { action: "version", branch, selectedCommit: entry.hash, expectedCommit: this.data.installed.commit,
        title: "Install recent version", message: `Install ${entry.subject} (${this.shortCommit(entry.hash)}) on ${branch} and restart?`, label: "Install" }
    },
    askRollback() {
      const branch = this.data?.installed?.branch
      if (this.actionDisabled || this.operations?.canRollback !== true || !branch) return
      this.dialog = { action: "rollback", branch, title: "Previous version",
        message: "Restore the previous installed version and restart? Automatic downloads will be turned off.", label: "Restore previous version" }
    },
    askInstall() {
      if (this.actionDisabled || !this.operations?.canInstall || !this.operations.selectedTarget) return
      this.dialog = { action: "install", branch: this.operations.selectedTarget, title: "Restart and install update",
        message: `Restart the device to install the finalized update for ${this.operations.selectedTarget}? Keep the vehicle parked and the device accessible.`, label: "Restart & install" }
    },
    closeDialog() { this.dialog = null },
    async confirmDialog() {
      const choice = this.dialog
      if (!choice) return
      this.dialog = null
      const result = await this.feed.action(choice.action, choice.branch, choice)
      if (result && choice.action === "select") {
        this.draftTouched = false
        this.syncDraftBranch(result.operations.selectedTarget)
      }
    },
  },
  template: `
    <div class="gx-view gx-stack" :inert="busy" :aria-busy="busy || undefined">
      <h2>Software &amp; Updates</h2>
      <GxState v-if="mode !== 'local'">Software updates are unavailable in preview.</GxState>
      <template v-else>
        <GxNotice v-if="error" tone="danger">{{ error }}</GxNotice>
        <section class="gx-card gx-panel gx-stack gx-software-card">
          <dl v-if="data" class="gx-software-summary">
            <div><dt>Branch</dt><dd>{{ shown(data.installed.branch) }}</dd></div>
            <div><dt>Version</dt><dd>{{ shown(data.installed.displayVersion ?? data.installed.version) }}</dd></div>
            <div><dt>Commit</dt><dd>{{ shortCommit(data.installed.commit) }}</dd></div>
          </dl>
          <p v-else role="status"><span v-if="busy" class="gx-spinner" aria-hidden="true"></span> {{ status === 'unavailable' ? 'Update status unavailable. Reconnecting…' : 'Reading update status…' }}</p>
          <GxNotice v-if="notice" :busy="busy || uncertain">{{ notice }}</GxNotice>
          <GxNotice v-else-if="operations?.request" :tone="operations.request.state === 'failed' ? 'danger' : 'info'" :busy="pending">{{ requestMessage(operations.request) }}</GxNotice>
          <div v-if="updateProgress" class="gx-update-progress" role="status">
            <div class="gx-update-progress__heading"><span>{{ updateProgress.label }}</span><span v-if="updateProgress.percent !== null">{{ Math.round(updateProgress.percent) }}%</span></div>
            <div v-if="updateProgress.active || updateProgress.percent !== null" class="gx-update-progress__track" role="progressbar" :aria-label="updateProgress.label"
              aria-valuemin="0" aria-valuemax="100" :aria-valuenow="updateProgress.percent ?? undefined">
              <div class="gx-update-progress__fill" :class="{'gx-update-progress__fill--indeterminate': updateProgress.active && updateProgress.percent === null}"
                :style="updateProgress.percent !== null ? {width: updateProgress.percent + '%'} : {}"></div>
            </div><p v-if="updateProgress.detail" class="gx-note">{{ updateProgress.detail }}</p>
          </div>
          <div class="gx-actions">
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="actionUnavailable || !operations?.canCheck" @click="feed.action('check')">Check for updates</button>
            <button type="button" class="gx-btn" :disabled="actionUnavailable || operations?.canFastUpdate !== true || !draftBranch || !branchOptions.some(branch => branch.name === draftBranch && branch.available)" @click="askFastUpdate">{{ branchChanging ? 'Switch & update' : 'Fast Update' }}</button>
            <button v-if="data?.updater.finalizedUpdateReady === true" type="button" class="gx-btn" :disabled="actionUnavailable || !operations.canInstall || !operations.selectedTarget" @click="askInstall">Restart &amp; install</button>
          </div>
          <p v-if="operations?.reason" class="gx-note">{{ operations.reason }}</p>
          <p v-else-if="data?.updater.targetChangeFound === true" class="gx-note">Update available for {{ operations.selectedTarget }}.</p>
          <p v-else-if="data?.updater.targetChangeFound === false && data?.updater.lastCheckedAt" class="gx-note">Up to date.</p>
          <p v-if="data?.updater.lastCheckedAt || data?.updater.lastFetchAt" class="gx-note">
            <span v-if="data.updater.lastCheckedAt">Checked {{ reported(data.updater.lastCheckedAt) }}</span>
            <span v-if="data.updater.lastFetchAt"> · Downloaded {{ reported(data.updater.lastFetchAt) }}</span>
          </p>
          <a v-if="commitsUrl" class="gx-link" :href="commitsUrl" target="_blank" rel="noopener noreferrer"><i class="bi bi-github" aria-hidden="true"></i> View commits</a>
          <GalaxySettingRow v-if="operations?.automaticDownloads !== undefined" class="gx-row--borderless"
            :row="switchRow('Download updates automatically', operations.automaticDownloads, 'Prepare updates while parked; restart when ready.')"
            :index="0" :busy="busy" :disabled="uncertain || !!error || !operations.canConfigure"
            :save-value="(index, value) => feed.configureAutomaticDownloads(value === 'On')" />
          <p v-if="operations?.automaticDownloads === null" class="gx-note">The download preference could not be read. Choose a setting while parked to repair it.</p>
          <details v-if="data" class="gx-software-options"><summary>Advanced options</summary><div class="gx-stack">
            <div class="gx-software-branch"><label class="gx-field-group gx-grow"><span class="gx-row__label">Branch</span>
              <GalaxySelect v-model="primaryChoice" class="gx-field gx-field--full" aria-label="Target branch" :disabled="actionUnavailable || !operations.canSelect" @change="onPrimaryBranchChange">
                <option value="" disabled>Choose a branch</option>
                <option value="StarPilot" :data-description="primaryBranchHelpFor('StarPilot')">Stable — StarPilot</option>
                <option value="Dom" :data-description="primaryBranchHelpFor('Dom')">Development — Dom</option>
                <option value="other:">Other branches…</option>
              </GalaxySelect>
            </label></div>
            <p v-if="primaryBranchHelp" class="gx-note">{{ primaryBranchHelp }}</p>
            <div v-if="primaryChoice === 'other:'" class="gx-software-other-branches">
              <label for="gx-other-branch" class="gx-row__label">Other branches</label>
              <p class="gx-note">Additional branches from this installation's repository.</p>
              <GalaxySelect id="gx-other-branch" v-model="draftBranch" class="gx-field gx-field--full" aria-label="Other branches" :disabled="actionUnavailable || !operations.canSelect" @change="onOtherBranchChange">
                <option value="" disabled>{{ otherBranches.length ? 'Select another branch' : 'No other branches available' }}</option>
                <option v-for="branch in otherBranches" :key="branch.name" :value="branch.name" :disabled="!branch.listed">{{ branch.name }}{{ branch.current ? ' (current)' : '' }}{{ !branch.listed && !branch.current ? ' (unavailable)' : '' }}</option>
              </GalaxySelect>
            </div>
            <p v-if="draftBranch && !operations.availableBranches.includes(draftBranch)" class="gx-note">This branch is not in the updater's available list and cannot be selected yet.</p>
            <p v-else-if="!operations.availableBranches.length" class="gx-note">No branch list is available yet. Check for updates to refresh it.</p>
            <p v-if="branchChanging" class="gx-note">Switch &amp; update installs {{ draftBranch }} and restarts the device.</p>
            <div class="gx-actions">
              <button v-if="canStageBranch" type="button" class="gx-btn gx-btn--tonal" :disabled="actionUnavailable || !operations.canSelect" @click="chooseBranch">Save target</button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="actionUnavailable || !operations.canDownload || !operations.selectedTarget || draftBranch !== operations.selectedTarget" @click="feed.action('download', operations.selectedTarget)">Normal Update</button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="actionUnavailable || operations.canRollback !== true" @click="askRollback">Previous version</button>
            </div>
            <p class="gx-note">Normal downloads without restarting. Previous version restores your last installed build.</p>
          </div></details>
          <details v-if="data" class="gx-software-options" @toggle="loadHistory($event)"><summary>Versions &amp; release notes</summary><div class="gx-stack">
            <div class="gx-tabs gx-actions" aria-label="Version source">
              <button v-for="source in [{key:'recent',label:'Available'},{key:'installed',label:'Installed'}, ...(operations.history?.downloaded.length ? [{key:'downloaded',label:'Downloaded'}] : [])]" :key="source.key" type="button" class="gx-btn gx-btn--tonal" :aria-pressed="historyKind === source.key" @click="historyKind=source.key; version=''">{{ source.label }}</button>
            </div>
            <template v-if="historyKind === 'recent'">
              <div class="gx-actions">
                <GalaxySelect v-if="versionEntries.length" v-model="version" class="gx-field gx-filter-field" aria-label="Version"><option value="" disabled>Choose a version</option>
                  <option v-for="entry in versionEntries" :key="entry.hash" :value="entry.hash">{{ versionLabel(entry) }}</option></GalaxySelect>
                <button type="button" class="gx-btn gx-btn--tonal" :disabled="actionUnavailable || !operations.canFastUpdate" @click="loadVersions">Load versions</button>
                <button v-if="versionEntries.length" type="button" class="gx-btn" :disabled="actionUnavailable || !version || version === data.installed.commit || !operations.canFastUpdate" @click="askVersion(versionEntries.find(entry => entry.hash === version))">Install version</button>
              </div><p class="gx-note">Up to 20 compatible versions of {{ draftBranch }}.</p>
            </template>
            <ul v-else-if="versionEntries.length" class="gx-build-history" aria-label="Build history"><li v-for="entry in versionEntries" :key="entry.hash"><strong>{{ entry.subject.trim() || shortCommit(entry.hash) }}</strong><small>{{ reported(entry.date) }} · {{ shortCommit(entry.hash) }}</small></li></ul>
            <p v-else class="gx-note">{{ operations.history ? 'No versions saved.' : 'Reading history…' }}</p>
            <pre v-if="historyKind === 'installed' && operations.history?.currentReleaseNotes" class="gx-release-notes">{{ operations.history.currentReleaseNotes }}</pre>
            <pre v-if="historyKind === 'downloaded' && operations.history?.downloadedReleaseNotes" class="gx-release-notes">{{ operations.history.downloadedReleaseNotes }}</pre>
          </div></details>
        </section>
        <ToggleBackup :unauthorized="unauthorized" />
        <GxDialog v-if="dialog" labelledby="gx-software-status-confirm-title" @close="closeDialog"><h3 id="gx-software-status-confirm-title">{{ dialog.title }}</h3><p>{{ dialog.message }}</p>
          <div class="gx-actions"><button type="button" class="gx-btn gx-btn--tonal" @click="closeDialog">Cancel</button><button type="button" class="gx-btn" @click="confirmDialog">{{ dialog.label }}</button></div>
        </GxDialog>
      </template>
    </div>`,
}
