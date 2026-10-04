import { decodeLayoutBackup, encodeLayoutBackup, MAX_LAYOUT_BACKUP_BYTES } from "./layout-backup.js"
import { GalaxySelect } from "./galaxy-select.js"

const ACTIONS = new Set(["check", "download", "select", "install", "preferences", "fast", "rollback"])
const REQUEST_STATES = new Set(["pending", "complete", "failed"])
const UPDATER_ACTIVE = new Set(["checking...", "downloading...", "finalizing update...", "updating..."])
const PRIMARY_BRANCHES = ["StarPilot", "Dom"]
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
    (data.installed.displayVersion === undefined || text(data.installed.displayVersion)) &&
    [updater.targetChangeFound, updater.finalizedUpdateReady].every(flag) &&
    (updater.failedCount === null || Number.isSafeInteger(updater.failedCount) && updater.failedCount >= 0) &&
    (operations === undefined || !!operations && typeof operations.parked === "boolean" && Array.isArray(operations.availableBranches) &&
    operations.availableBranches.length <= 256 && operations.availableBranches.every((branch) =>
      typeof branch === "string" && branch.length > 0 && branch.length <= 128) &&
    text(operations.selectedTarget) && text(operations.reason) &&
    (operations.canFastUpdate === undefined || typeof operations.canFastUpdate === "boolean") &&
    (operations.canRollback === undefined || typeof operations.canRollback === "boolean") &&
    (operations.automaticDownloads === undefined || flag(operations.automaticDownloads)) &&
    (operations.canConfigure === undefined || typeof operations.canConfigure === "boolean") &&
    (operations.history === undefined || validHistory(operations.history)) &&
    [operations.canCheck, operations.canDownload, operations.canSelect, operations.canInstall].every((value) => typeof value === "boolean") &&
    (request === null || !!request && typeof request.id === "string" && request.id.length <= 100 &&
      ACTIONS.has(request.action) && text(request.target) && REQUEST_STATES.has(request.state) && text(request.error) &&
      (request.outcome === undefined || ["up_to_date", "restarting"].includes(request.outcome))))
}

export function validHistory(value) {
  const rows = (items) => Array.isArray(items) && items.length <= 20 && items.every((row) =>
    /^[0-9a-f]{40}$/.test(row?.hash) && typeof row.date === "string" && row.date.length <= 64 &&
    typeof row.subject === "string" && row.subject.length <= 512)
  return !!value && rows(value.installed) && rows(value.downloaded) &&
    [value.currentReleaseNotes, value.downloadedReleaseNotes].every((notes) => notes === null || typeof notes === "string" && notes.length <= 65536)
}

export class SoftwareStatusFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, later, cancelTimer })
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
      const response = await this.fetcher(body === null ? "./api/software/status" : "./api/software/action", {
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
        if (["fast", "rollback"].includes(body.action)) {
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
          (!this.uncertainAction?.branch || observed.target === this.uncertainAction.branch)
        const selectionObserved = this.uncertainAction?.action === "select" &&
          payload.operations.selectedTarget === this.uncertainAction.branch
        const preferenceObserved = this.uncertainAction?.action === "preferences" &&
          payload.operations.automaticDownloads === this.uncertainAction.automaticDownloads
        if (this.uncertain && (requestObserved || selectionObserved || preferenceObserved)) {
          this.uncertain = false
          this.uncertainAction = null
          this.actionPriorRequestId = null
        }
        if (this.installBaseline?.action === "fast" && observed?.action === "fast" && observed.target === this.installBaseline.target &&
            ["complete", "failed"].includes(observed.state)) {
          if (observed.state === "failed" || observed.outcome === "up_to_date") {
            this.installBaseline = null
            this.notice = observed.state === "failed" ? "" : "Installed branch is already up to date. No restart needed."
          } else this.notice = "Update installed. Waiting to reconnect and verify the installed build."
        }
        if (this.installBaseline && payload.installed.branch === this.installBaseline.target &&
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
          if (error?.rejected && ["install", "fast", "rollback"].includes(body.action)) this.installBaseline = null
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

  action(action, branch = null) {
    const operations = this.data?.operations
    const capability = { check: "canCheck", download: "canDownload", select: "canSelect", install: "canInstall", fast: "canFastUpdate", rollback: "canRollback" }[action]
    if (!this.active || !capability || this.mutating || this.blocked || this.uncertain || !operations?.parked ||
        operations[capability] !== true || operations.request?.state === "pending") return null
    if (action === "select" && (branch === "other:" || !operations.availableBranches.includes(branch) || branch === operations.selectedTarget)) return null
    if (["download", "install"].includes(action) && (!branch || branch !== operations.selectedTarget)) return null
    if (action === "fast" && (!branch || branch !== this.data.installed.branch && !operations.availableBranches.includes(branch))) return null
    if (action === "rollback" && branch !== this.data.installed.branch) return null
    this.actionPriorRequestId = operations.request?.id ?? null
    if (action === "install") this.installBaseline = { commit: this.data.installed.commit,
      branch: this.data.installed.branch, target: branch }
    if (["fast", "rollback"].includes(action)) this.installBaseline = { commit: this.data.installed.commit, branch: this.data.installed.branch, target: branch, action }
    return this.run(action === "check" ? { action } : { action, branch })
  }
}

export const SoftwarePage = {
  components: { GalaxySelect },
  name: "SoftwarePage",
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ status: "idle", data: null, busy: false, uncertain: false, notice: "", error: "",
    primaryChoice: "", draftBranch: "", draftTouched: false, dialog: null,
    layoutBusy: false, layoutNotice: "", layoutError: "", layoutDraft: null }),
  created() {
    this.feed = new SoftwareStatusFeed({ publish: (update) => {
      Object.assign(this.$data, update)
      if (update.data && !this.draftTouched) this.syncDraftBranch(update.data.operations.selectedTarget)
    }, unauthorized: this.unauthorized })
  },
  mounted() { if (this.mode === "local") this.feed.start() },
  beforeUnmount() { this.feed.stop() },
  computed: {
    operations() { return this.data?.operations },
    pending() { return this.operations?.request?.state === "pending" },
    actionDisabled() { return this.busy || this.uncertain || this.pending || !!this.error || !this.operations?.parked },
    primaryBranchHelp() {
      return this.primaryChoice === "StarPilot" ? "Stable releases. Recommended for most users." :
        this.primaryChoice === "Dom" ? "Latest features and fixes under development. Updates regularly and may introduce bugs." : ""
    },
    otherBranches() {
      const available = this.operations?.availableBranches || []
      const selected = this.operations?.selectedTarget
      const installed = this.data?.installed?.branch
      return [...new Set([selected, installed, ...available].filter((branch) => branch && branch !== "other:" && !PRIMARY_BRANCHES.includes(branch)))].map((branch) => ({
        name: branch, listed: available.includes(branch), current: branch === installed,
      }))
    },
    canStageBranch() {
      return !!this.draftBranch && this.draftBranch !== "other:" &&
        this.operations?.availableBranches.includes(this.draftBranch) &&
        this.draftBranch !== this.operations.selectedTarget &&
        (this.primaryChoice === "other:" ? !PRIMARY_BRANCHES.includes(this.draftBranch) : this.primaryChoice === this.draftBranch)
    },
  },
  methods: {
    async layoutRequest(document = undefined, revision = undefined) {
      const response = await fetch("./api/ui/layout", document === undefined ? {
        credentials: "same-origin", cache: "no-store",
      } : {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ revision, document }),
      })
      if (response.status === 401) this.unauthorized()
      const value = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(value.error || "Visual layout is unavailable. Refresh and try again.")
      return value
    },
    async exportLayout() {
      if (this.layoutBusy) return
      this.layoutBusy = true
      this.layoutNotice = this.layoutError = ""
      try {
        const snapshot = await this.layoutRequest()
        if (snapshot.valid !== true) throw new Error("Saved visual layout is invalid. Repair it in Colors & Layout before exporting.")
        const contents = await encodeLayoutBackup(snapshot.document)
        const url = URL.createObjectURL(new Blob([contents], { type: "application/json" }))
        try {
          const link = document.createElement("a")
          link.href = url
          link.download = "StarPilot-visual-layout-backup.json"
          document.body.append(link)
          link.click()
          link.remove()
        } finally { setTimeout(() => URL.revokeObjectURL(url), 1000) }
        this.layoutNotice = "Visual layout backup downloaded."
      } catch (error) { this.layoutError = error.message || "Could not export visual layout." }
      finally { this.layoutBusy = false }
    },
    async chooseLayoutFile(event) {
      const file = event.target.files?.[0]
      event.target.value = ""
      if (!file || this.layoutBusy) return
      this.layoutError = this.layoutNotice = ""
      try {
        if (file.size > MAX_LAYOUT_BACKUP_BYTES) throw new Error("Visual layout backup is too large.")
        this.layoutDraft = await decodeLayoutBackup(await file.text())
        this.dialog = { action: "restoreLayout", title: "Restore visual layout",
          message: "Replace the saved onroad layout and colors with this backup? Turn off the vehicle first. Other settings stay as they are.",
          label: "Restore layout" }
      } catch (error) { this.layoutDraft = null; this.layoutError = error.message || "Could not read visual layout backup." }
    },
    async restoreLayout() {
      const draft = this.layoutDraft
      this.layoutDraft = null
      if (!draft || this.layoutBusy) return
      this.layoutBusy = true
      this.layoutError = this.layoutNotice = ""
      try {
        const current = await this.layoutRequest()
        if (current.editable !== true) throw new Error("Park the vehicle before restoring the visual layout.")
        const saved = await this.layoutRequest(draft, current.revision)
        if (saved.valid !== true) throw new Error("Visual layout could not be verified after restore.")
        this.layoutNotice = "Visual layout restored."
      } catch (error) { this.layoutError = error.message || "Could not restore visual layout." }
      finally { this.layoutBusy = false }
    },
    syncDraftBranch(branch) {
      this.draftBranch = branch || ""
      this.primaryChoice = PRIMARY_BRANCHES.includes(this.draftBranch) ? this.draftBranch : this.draftBranch ? "other:" : ""
    },
    onPrimaryBranchChange() {
      this.draftTouched = true
      if (this.primaryChoice === "other:") {
        if (!this.otherBranches.some((option) => option.name === this.draftBranch)) {
          const selected = this.operations?.selectedTarget
          this.draftBranch = this.otherBranches.some((option) => option.name === selected) ? selected : ""
        }
      } else this.draftBranch = this.primaryChoice
    },
    onOtherBranchChange() { this.draftTouched = true },
    shown(value) { return value ?? "Unavailable" },
    reported(value) { return value ? new Date(value).toLocaleString() : "Unavailable" },
    shortCommit(value) { return value ? value.slice(0, 12) : "Unavailable" },
    requestMessage(request) {
      if (!request) return ""
      if (request.state === "failed") return request.error || "Update request failed. Refresh and try again."
      if (["fast", "rollback"].includes(request.action)) return request.state === "pending" ? `Updating ${request.target}…` :
        request.outcome === "up_to_date" ? "Installed branch is already up to date. No restart needed." :
        "Update installed. Waiting to reconnect and verify the installed build."
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
      const branch = this.operations?.selectedTarget || this.data?.installed?.branch
      if (this.actionDisabled || this.operations?.canFastUpdate !== true || !branch) return
      this.dialog = { action: "fast", branch, title: "Fast Update",
        message: `Download latest version of ${branch} and restart?`, label: "Fast Update" }
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
    closeDialog() { this.dialog = null; this.layoutDraft = null },
    async confirmDialog() {
      const choice = this.dialog
      if (!choice) return
      this.dialog = null
      if (choice.action === "restoreLayout") { await this.restoreLayout(); return }
      const result = await this.feed.action(choice.action, choice.branch)
      if (result && choice.action === "select") {
        this.draftTouched = false
        this.syncDraftBranch(result.operations.selectedTarget)
      }
    },
  },
  template: `
    <div class="gx-view">
      <h2>Software &amp; Updates</h2>
      <p class="gx-note">Turn off the vehicle before checking, downloading or installing updates. Selecting a branch saves the target for the next check.</p>
      <div v-if="mode !== 'local'" class="gx-card gx-message" role="status">Software updates are unavailable in preview.</div>
      <template v-else>
        <div class="gx-software-actions"><button type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="feed.load()">Refresh status</button>
          <button type="button" class="gx-btn" :disabled="actionDisabled || !operations?.canCheck" @click="feed.action('check')">Check for updates</button></div>
        <p v-if="status === 'loading' && !data" role="status">Loading software updates…</p>
        <div v-if="error" class="gx-card gx-message" role="alert">{{ error }}
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="feed.load()">Refresh</button></div>
        <p v-if="notice" class="gx-card gx-message" role="status">{{ notice }}</p>
        <template v-if="data">
          <section class="gx-card gx-software-card"><h3>Installed Build</h3>
            <dl><dt>Version</dt><dd>{{ shown(data.installed.displayVersion ?? data.installed.version) }}</dd><dt>Branch</dt><dd>{{ shown(data.installed.branch) }}</dd>
              <dt>Commit</dt><dd>{{ shortCommit(data.installed.commit) }}</dd></dl></section>
          <section class="gx-card gx-software-card"><h3>Target Branch</h3>
            <p class="gx-note">Current target: {{ shown(operations.selectedTarget) }}</p>
            <div class="gx-software-branch"><GalaxySelect v-model="primaryChoice" class="gx-field gx-field--full" aria-label="Target branch" :disabled="actionDisabled || !operations.canSelect" @change="onPrimaryBranchChange">
                <option value="" disabled>Choose a branch</option>
                <option value="StarPilot">StarPilot — Release</option><option value="Dom">Dom — Development</option>
                <option value="other:">Other branches…</option></GalaxySelect>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="actionDisabled || !operations.canSelect || !canStageBranch" @click="chooseBranch">Set target branch</button></div>
            <p v-if="primaryBranchHelp" class="gx-note">{{ primaryBranchHelp }}</p>
            <div v-if="primaryChoice === 'other:'" class="gx-software-other-branches">
              <label for="gx-other-branch" class="gx-row__label">Other branches</label>
              <p class="gx-note">Additional branches from this installation's repository.</p>
              <GalaxySelect id="gx-other-branch" v-model="draftBranch" class="gx-field gx-field--full" aria-label="Other branches" :disabled="actionDisabled || !operations.canSelect" @change="onOtherBranchChange">
                <option value="" disabled>{{ otherBranches.length ? 'Select another branch' : 'No other branches available' }}</option>
                <option v-for="branch in otherBranches" :key="branch.name" :value="branch.name" :disabled="!branch.listed">{{ branch.name }}{{ branch.current ? ' (current)' : '' }}{{ !branch.listed && !branch.current ? ' (unavailable)' : '' }}</option></GalaxySelect>
            </div>
            <p v-if="draftBranch && !operations.availableBranches.includes(draftBranch)" class="gx-note">This branch is not in the updater's available list and cannot be selected yet.</p>
            <p v-if="!operations.availableBranches.length" class="gx-note">No branch list is available yet. Check for updates to refresh it.</p></section>
          <section class="gx-card gx-software-card"><h3>Update</h3>
            <p v-if="operations.reason" class="gx-note">{{ operations.reason }}</p>
            <p v-else-if="!operations.parked" class="gx-note">Park the vehicle to change or install software.</p>
            <p v-if="operations.request" :role="operations.request.state === 'failed' ? 'alert' : 'status'">{{ requestMessage(operations.request) }}</p>
            <p v-else-if="data.updater.state">{{ data.updater.state }}</p>
            <p v-if="data.updater.targetChangeFound === true">An update was found for the target branch.</p>
            <p v-else-if="data.updater.targetChangeFound === false">No target change reported by the last check.</p>
            <div class="gx-software-actions"><button type="button" class="gx-btn" :disabled="actionDisabled || operations.canFastUpdate !== true || !data.installed.branch" @click="askFastUpdate">Fast Update</button><button type="button" class="gx-btn" :disabled="actionDisabled || operations.canRollback !== true" @click="askRollback">Previous version</button>
              <button type="button" class="gx-btn" :disabled="actionDisabled || !operations.canDownload || !operations.selectedTarget" @click="feed.action('download', operations.selectedTarget)">Download update</button>
              <button type="button" class="gx-btn" :disabled="actionDisabled || !operations.canInstall || !operations.selectedTarget" @click="askInstall">Restart &amp; install</button></div>
            <dl><dt>Last checked</dt><dd>{{ reported(data.updater.lastSuccessAt) }}</dd><dt>Last download</dt><dd>{{ reported(data.updater.lastFetchAt) }}</dd></dl></section>
          <section v-if="operations.automaticDownloads !== undefined" class="gx-card gx-software-card">
            <h3>Automatic Downloads</h3>
            <label class="gx-toggle-row"><input type="checkbox" :checked="operations.automaticDownloads === true"
              :disabled="busy || uncertain || !!error || !operations.canConfigure"
              @change="feed.configureAutomaticDownloads($event.target.checked)"> Download updates automatically</label>
            <p v-if="data.updater.fast" class="gx-note">{{ data.updater.fast.stage }}: {{ data.updater.fast.detail }}</p>
            <p class="gx-note">Keep the selected branch ready to install. Turn this off to download updates yourself; checking for updates and manual downloads still work.</p>
            <p v-if="operations.automaticDownloads === null" class="gx-note">The saved download preference could not be read. Turn off the vehicle, then choose a setting to repair it.</p>
          </section>
          <section class="gx-card gx-software-card">
            <h3>Visual Layout Backup</h3>
            <p class="gx-note">Save or restore your onroad layout and colors. This file does not include driving settings, calibration, credentials, or models.</p>
            <div class="gx-software-actions">
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="layoutBusy" @click="exportLayout">Download backup</button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="layoutBusy" @click="$refs.layoutFile.click()">Restore from file</button>
              <input ref="layoutFile" type="file" accept=".json,application/json" :disabled="layoutBusy" class="gx-sr-only" tabindex="-1" aria-label="Choose visual layout backup" @change="chooseLayoutFile">
            </div>
            <p v-if="layoutNotice" role="status">{{ layoutNotice }}</p>
            <p v-if="layoutError" role="alert">{{ layoutError }}</p>
          </section>
          <section v-if="operations.history" class="gx-card gx-software-card">
            <h3>Release Notes &amp; History</h3>
            <details v-if="operations.history.currentReleaseNotes"><summary>Installed Release Notes</summary><pre class="gx-release-notes">{{ operations.history.currentReleaseNotes }}</pre></details>
            <details v-if="operations.history.downloadedReleaseNotes"><summary>Downloaded Release Notes</summary><pre class="gx-release-notes">{{ operations.history.downloadedReleaseNotes }}</pre></details>
            <details v-for="group in [{key:'installed',label:'Installed Build History'},{key:'downloaded',label:'Downloaded Build History'}]" :key="group.key">
              <summary>{{ group.label }}</summary>
              <p v-if="!operations.history[group.key].length" class="gx-note">No local history is available for this build.</p>
              <ol v-else class="gx-build-history"><li v-for="entry in operations.history[group.key]" :key="entry.hash">
                <strong>{{ entry.subject }}</strong><small>{{ reported(entry.date) }} · {{ shortCommit(entry.hash) }}</small>
              </li></ol>
            </details>
          </section>
        </template>
        <Teleport to="body"><div v-if="dialog" class="gx-settings__modal" role="dialog" aria-modal="true" :aria-label="dialog.title" @click.self="closeDialog" @keydown.esc="closeDialog">
          <div class="gx-card gx-settings__dialog"><h3>{{ dialog.title }}</h3><p>{{ dialog.message }}</p>
            <div class="gx-settings__controls"><button type="button" class="gx-btn gx-btn--tonal" @click="closeDialog">Cancel</button>
              <button type="button" class="gx-btn" @click="confirmDialog">{{ dialog.label }}</button></div></div></div></Teleport>
      </template>
    </div>`,
}
