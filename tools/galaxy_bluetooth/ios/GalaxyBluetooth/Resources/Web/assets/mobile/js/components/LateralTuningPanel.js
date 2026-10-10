import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"
import { GalaxyConfirm, GalaxyPrompt } from "./GalaxyModal.js"
import { GxNotice } from "./GxNotice.js"

const MAX_ROUTES = 250
const MAX_SEGMENTS = 5

export const LateralTuningPanel = {
  name: "LateralTuningPanel",
  components: { GxNotice },
  data() {
    return {
      loading: true,
      busy: false,
      error: "",
      loadingRoutes: false,
      workspace: { reports: [], savedTunes: [], currentCarFingerprint: "", activeTrial: null, status: {} },
      statusData: null,
      isOnroad: false,
      laneCentering: false,
      routes: [],
      selectedRoutes: [],
      segmentRanges: {},
      report: null,
      reportLoading: false,
      loadedReportId: "",
      lastStatusReportId: "",
      feedbackAccepted: [],
      feedbackIgnored: [],
      feedbackNotes: "",
      pending: null,
      pendingName: "",
      maxSegments: MAX_SEGMENTS,
    }
  },
  created() {
    this.poll = usePolling(() => this.refresh(), { interval: 4000 })
    this.refresh()
    this.loadRoutes()
    this.poll.start()
  },
  beforeUnmount() { this.poll?.destroy() },
  computed: {
    status() {
      const merged = { ...((this.workspace.status) || {}), ...(this.statusData || {}) }
      return merged
    },
    activeTrial() { return this.workspace.activeTrial || null },
    comparisonRows() {
      const rep = this.report
      if (!rep) return []
      const stock = rep.stockParams || {}
      const current = rep.currentParams || {}
      const trial = (this.activeTrial && this.activeTrial.appliedGenericParams) || {}
      const angle = rep.car && rep.car.controlPath === "angle"
      const pairs = angle
        ? [["Auto steer delay", "UseAutoSteerDelay"], ["Steer delay", "SteerDelay"], ["Steer ratio", "SteerRatio"]]
        : [
            ["Lat accel", "SteerLatAccel"], ["Friction", "SteerFriction"], ["Auto steer delay", "UseAutoSteerDelay"],
            ["Steer delay", "SteerDelay"], ["Steer ratio", "SteerRatio"], ["KP", "SteerKP"],
          ]
      const rows = pairs.map(([label, key]) => ({
        key,
        label,
        curve: false,
        stock: stock[key],
        current: Object.prototype.hasOwnProperty.call(trial, key) ? trial[key] : current[key],
      }))
      if (angle) return rows
      const merged = this.mergedOverrides
      for (const [family, payload] of Object.entries(stock.FLMBaseFrictionThresholds || {})) {
        const override = (merged.baseFrictionThresholds || {})[family]
        rows.push({
          key: `friction-${family}`,
          code: family,
          label: `${family} friction threshold`,
          curve: true,
          stock: (payload && payload.values) || [],
          current: (override && override.values) || (payload && payload.values) || [],
        })
      }
      for (const [symbol, value] of Object.entries(merged.vehicleKnobs || {})) {
        if (!Object.prototype.hasOwnProperty.call(stock.FLMVehicleKnobs || {}, symbol)) continue
        rows.push({
          key: symbol,
          code: symbol,
          label: symbol.split(".").slice(1).join("."),
          curve: false,
          stock: stock.FLMVehicleKnobs[symbol],
          current: value,
        })
      }
      return rows
    },
    mergedOverrides() {
      const trial = this.activeTrial || {}
      return {
        baseFrictionThresholds: trial.appliedFrictionThresholds || {},
        vehicleKnobs: trial.appliedVehicleKnobs || {},
      }
    },
    angleControl() {
      const rep = this.report
      return !!(rep && rep.car && rep.car.controlPath === "angle")
    },
    canAnalyze() {
      return this.selectedRoutes.length > 0 && this.selectedSegmentCount > 0 && this.selectedSegmentCount <= MAX_SEGMENTS && !this.isOnroad && !this.laneCentering
    },
    selectedSegmentCount() {
      return this.selectedRoutes.reduce((total, routeName) => total + this.routeSelectedSegmentCount(routeName), 0)
    },
    canApplyTrial() {
      const trial = this.activeTrial
      return !this.busy && !(trial && trial.rollbackAvailable === false)
    },
  },
  methods: {
    num(value, fallback = 0) {
      const n = Number(value)
      return Number.isFinite(n) ? n : fallback
    },
    fmtVal(value) {
      if (Array.isArray(value)) return this.curveStr(value)
      if (typeof value === "boolean") return value ? "On" : "Off"
      const n = Number(value)
      return Number.isFinite(n) ? n.toFixed(3) : String(value ?? "-")
    },
    curveStr(values) { return `[${(values || []).map((v) => Number(v).toFixed(3)).join(", ")}]` },
    fmtAge(epoch) {
      const at = Number(epoch)
      if (!Number.isFinite(at) || at <= 0) return "unknown"
      const age = Math.max(0, Math.round(Date.now() / 1000 - at))
      if (age < 5) return "just now"
      if (age < 60) return `${age}s ago`
      if (age < 3600) return `${Math.round(age / 60)}m ago`
      return `${Math.round(age / 3600)}h ago`
    },
    fmtDate(value) {
      if (!value) return "unknown"
      const n = Number(value)
      if (Number.isFinite(n)) {
        if (n <= 0) return "unknown"
        return new Date(n > 100000000000 ? n : n * 1000).toLocaleString()
      }
      const d = new Date(value)
      return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString()
    },
    fmtLen(route) {
      const seg = Math.max(0, Math.round(this.num(route && route.segmentCount)))
      if (!seg) return "Length unavailable"
      const min = Math.max(1, Math.round(this.num(route && route.approxDurationSeconds) / 60) || seg)
      const dur = min >= 60 ? `${Math.floor(min / 60)}h ${min % 60}m` : `~${min} min`
      return `${seg} segment${seg === 1 ? "" : "s"} (${dur})`
    },
    routeSegmentBounds(routeName) {
      const route = this.routes.find((item) => item && item.name === routeName) || {}
      const count = Math.max(0, Math.round(this.num(route.segmentCount)))
      const first = Math.max(0, Math.round(this.num(route.firstSegmentNum)))
      return { first, last: first + Math.max(0, count - 1), count }
    },
    routeSelectedSegmentCount(routeName) {
      const bounds = this.routeSegmentBounds(routeName)
      if (!bounds.count) return 0
      const selected = this.segmentRanges[routeName] || {}
      const rawStart = String(selected.start ?? "").trim()
      const rawEnd = String(selected.end ?? "").trim()
      const start = Math.min(bounds.last, Math.max(bounds.first, rawStart === "" ? bounds.first : this.num(rawStart, bounds.first)))
      const end = Math.max(bounds.first, Math.min(bounds.last, rawEnd === "" ? bounds.last : this.num(rawEnd, bounds.last)))
      return end >= start ? end - start + 1 : 0
    },
    setSegmentRange(routeName, key, value) {
      const cleaned = String(value ?? "").replace(/[^\d]/g, "")
      this.segmentRanges = {
        ...this.segmentRanges,
        [routeName]: {
          ...(this.segmentRanges[routeName] || {}),
          [key]: cleaned,
        },
      }
    },
    syncFeedback(report) {
      const fb = (report && report.feedback) || {}
      this.feedbackAccepted = Array.isArray(fb.acceptedDimensions) ? [...fb.acceptedDimensions] : []
      this.feedbackIgnored = Array.isArray(fb.ignoredDimensions) ? [...fb.ignoredDimensions] : []
      this.feedbackNotes = typeof fb.notes === "string" ? fb.notes : ""
    },
    fbState(dimensionId) {
      if (this.feedbackAccepted.includes(dimensionId)) return "accepted"
      if (this.feedbackIgnored.includes(dimensionId)) return "ignored"
      return "unset"
    },
    pathList() {
      const rep = this.report
      if (!rep) return []
      if (Array.isArray(rep.paths) && rep.paths.length) return rep.paths
      return [{
        key: rep.primaryPathKey || "cleanup_pass",
        title: "Recommendations",
        description: "",
        whySelected: "",
        isPrimary: true,
        suggestions: rep.suggestions || [],
        profiles: rep.profiles || [],
      }]
    },
    primaryPath() {
      const paths = this.pathList()
      const key = (this.report && (this.report.selectedPathKey || this.report.primaryPathKey)) || ""
      return paths.find((p) => p.key === key) || paths.find((p) => p.isPrimary) || paths[0] || null
    },
    pathSelected(key) {
      const rep = this.report
      const active = (rep && (rep.selectedPathKey || rep.primaryPathKey)) || ""
      return key === active
    },
    suggestions() {
      const p = this.primaryPath()
      return (p && (p.suggestions || [])) || (this.report && this.report.suggestions) || []
    },
    profiles() {
      const p = this.primaryPath()
      const list = (p && (p.profiles || [])) || []
      return list.length ? list : ((this.report && this.report.profiles) || [])
    },
    genericEntries(profile) {
      return Object.entries(profile && profile.genericParams || {}).filter(([key]) => key !== "AdvancedLateralTune")
    },
    frictionEntries(profile) {
      return Object.entries(((profile && profile.flmOverrides) || {}).baseFrictionThresholds || {})
    },
    knobEntries(profile) {
      return Object.entries(((profile && profile.flmOverrides) || {}).vehicleKnobs || {})
    },
    reportTimestamp(report) {
      if (!report) return ""
      const at = Number(report.createdAt)
      return Number.isFinite(at) && at > 1000000000 ? this.fmtDate(at) : ""
    },
    async runWith(fn, okMessage) {
      if (this.busy) return null
      this.busy = true
      this.error = ""
      try {
        const payload = await fn()
        showSnackbar(payload && payload.message ? payload.message : okMessage)
        await this.refresh()
        return payload
      } catch (e) {
        const msg = (e && (e.data?.error || e.message)) || "Action failed."
        this.error = msg
        showSnackbar(msg, "error")
        return null
      } finally {
        this.busy = false
      }
    },
    async refresh() {
      try {
        const ws = await api.getFlmWorkspace()
        if (ws && typeof ws === "object") {
          this.workspace = {
            reports: Array.isArray(ws.reports) ? ws.reports : [],
            savedTunes: Array.isArray(ws.savedTunes) ? ws.savedTunes : [],
            currentCarFingerprint: ws.currentCarFingerprint || "",
            activeTrial: ws.activeTrial || null,
            status: (ws.status && typeof ws.status === "object") ? ws.status : {},
          }
        }
        const st = await api.getFlmStatus().catch(() => null)
        if (st && typeof st === "object") {
          this.isOnroad = !!st.isOnroad
          this.laneCentering = !!st.laneCentering
          this.statusData = (st.status && typeof st.status === "object") ? st.status : null
          this.workspace.savedTunes = Array.isArray(st.savedTunes) && st.savedTunes.length
            ? st.savedTunes : this.workspace.savedTunes
          this.workspace.activeTrial = st.activeTrial || this.workspace.activeTrial
          this.workspace.reports = Array.isArray(st.reports) && st.reports.length
            ? st.reports : this.workspace.reports
        }
        this.error = ""
        this.loading = false
        this.autoOpenReport()
      } catch (e) {
        this.error = (e && e.message) || "Failed to load tuning workspace."
        this.loading = false
        throw e
      }
    },
    autoOpenReport() {
      const statusId = this.status.reportId || ""
      if (statusId && statusId !== this.lastStatusReportId) {
        this.lastStatusReportId = statusId
        this.loadReport(statusId)
        return
      }
      if (!this.loadedReportId && (this.workspace.reports[0] || {}).reportId) {
        this.loadReport(this.workspace.reports[0].reportId)
      }
    },
    async loadReport(reportId) {
      if (!reportId || reportId === this.loadedReportId && this.report) return
      this.loadedReportId = reportId
      this.reportLoading = true
      try {
        const report = await api.getFlmReport(reportId)
        if (!report) throw new Error("Report not found.")
        this.report = report
        this.syncFeedback(report)
        this.error = ""
      } catch (e) {
        this.report = null
        showSnackbar((e && e.message) || "Failed to load report.", "error")
      } finally {
        this.reportLoading = false
      }
    },
    async loadRoutes() {
      if (this.loadingRoutes) return
      this.loadingRoutes = true
      this.routes = []
      try {
        await api.getRoutesStream({
          onProgress: () => {},
          onRoutes: (list) => {
            for (const route of (list || [])) {
              if (!route || !route.name) continue
              if (this.routes.some((r) => r.name === route.name)) continue
              if (this.routes.length >= MAX_ROUTES) return
              this.routes.push(route)
            }
          },
        })
      } catch (e) {
        showSnackbar((e && e.message) || "Failed to load routes.", "error")
      } finally {
        this.loadingRoutes = false
      }
    },
    toggleRoute(name) {
      const set = new Set(this.selectedRoutes)
      const ranges = { ...this.segmentRanges }
      if (set.has(name)) {
        set.delete(name)
        delete ranges[name]
      } else {
        const remaining = MAX_SEGMENTS - this.selectedSegmentCount
        if (remaining <= 0) {
          showSnackbar(`FLM is limited to ${MAX_SEGMENTS} segments at a time.`, "error")
          return
        }
        const bounds = this.routeSegmentBounds(name)
        if (!bounds.count) return
        set.add(name)
        if (bounds.count > remaining) {
          ranges[name] = { start: String(bounds.first), end: String(bounds.first + remaining - 1) }
        }
      }
      this.segmentRanges = ranges
      this.selectedRoutes = [...set]
    },
    selectFirstSegments() {
      const selected = []
      const ranges = {}
      let remaining = MAX_SEGMENTS
      for (const route of this.routes) {
        if (remaining <= 0) break
        const bounds = this.routeSegmentBounds(route.name)
        if (!bounds.count) continue
        const take = Math.min(bounds.count, remaining)
        selected.push(route.name)
        if (take < bounds.count) {
          ranges[route.name] = { start: String(bounds.first), end: String(bounds.first + take - 1) }
        }
        remaining -= take
      }
      this.selectedRoutes = selected
      this.segmentRanges = ranges
    },
    clearSelection() {
      this.selectedRoutes = []
      this.segmentRanges = {}
    },
    selectedSegmentRanges() {
      const ranges = {}
      for (const routeName of this.selectedRoutes) {
        const selected = this.segmentRanges[routeName] || {}
        const start = String(selected.start ?? "").trim()
        const end = String(selected.end ?? "").trim()
        if (start || end) ranges[routeName] = { start: start || null, end: end || null }
      }
      return ranges
    },
    async analyze() {
      if (!this.canAnalyze || this.busy) return
      const ok = await this.runWith(() => api.flmAnalyze(this.selectedRoutes, this.selectedSegmentRanges()), "FLM analysis started.")
      if (ok && this.selectedRoutes.length) {
        this.selectedRoutes = []
        this.segmentRanges = {}
      }
    },
    async stopAnalyze() {
      await this.runWith(() => api.flmStopAnalyze(), "FLM analysis stopped.")
    },
    async revertTrial() {
      await this.runWith(() => api.flmRevertTrial(), "Trial reverted.")
    },
    async acceptBaseline() {
      const ok = await GalaxyConfirm({
        title: "Keep Current as Baseline",
        message: "Keep the currently applied tuning values and end this trial? This does not restore the previous tune.",
        confirmLabel: "Yes, Keep",
      })
      if (!ok) return
      await this.runWith(() => api.flmAcceptTrial(), "Current tune kept as baseline.")
    },
    async applyTrial(profileId) {
      const rep = this.report
      if (!rep || !rep.reportId || !this.canApplyTrial) return
      await this.runWith(() => api.flmApplyTrial(rep.reportId, profileId), "Trial profile applied.")
    },
    async selectPath(pathKey) {
      const rep = this.report
      if (!rep || !rep.reportId || this.pathSelected(pathKey)) return
      const payload = await this.runWith(() => api.flmSelectPath(rep.reportId, pathKey), "Path selected.")
      if (payload && payload.report) {
        this.report = payload.report
        this.syncFeedback(payload.report)
      }
    },
    toggleFeedback(dimensionId, mode) {
      const current = this.fbState(dimensionId)
      const next = current === mode ? "unset" : mode
      const accepted = new Set(this.feedbackAccepted)
      const ignored = new Set(this.feedbackIgnored)
      accepted.delete(dimensionId)
      ignored.delete(dimensionId)
      if (next === "accepted") accepted.add(dimensionId)
      if (next === "ignored") ignored.add(dimensionId)
      this.feedbackAccepted = [...accepted]
      this.feedbackIgnored = [...ignored]
      this.saveFeedback()
    },
    async saveFeedback() {
      const rep = this.report
      if (!rep || !rep.reportId || this.busy) return
      this.busy = true
      try {
        const payload = await api.flmSaveFeedback(rep.reportId, {
          acceptedDimensions: this.feedbackAccepted,
          ignoredDimensions: this.feedbackIgnored,
          notes: this.feedbackNotes,
        })
        if (payload && payload.report) { this.report = payload.report; this.syncFeedback(payload.report) }
        showSnackbar((payload && payload.message) || "Feedback saved.")
        await this.refresh()
      } catch (e) {
        const msg = (e && (e.data?.error || e.message)) || "Failed to save feedback."
        showSnackbar(msg, "error")
      } finally {
        this.busy = false
      }
    },
    async deleteReport(report) {
      if (!report || !report.reportId) return
      const ok = await GalaxyConfirm({
        title: "Delete Report",
        message: "Delete this saved tuning report and its generated trial data?",
        confirmLabel: "Yes, Delete",
        danger: true,
      })
      if (!ok) return
      await this.runWith(() => api.flmDeleteReport(report.reportId), "Report deleted.")
      if (this.loadedReportId === report.reportId) {
        this.report = null
        this.loadedReportId = ""
      }
    },
    startPending(kind, opts = {}) {
      this.pending = { kind, tuneId: opts.tuneId || "" }
      this.pendingName = opts.name || ""
      this.$nextTick(() => {
        const editor = this.$refs.pendingEditor
        editor?.scrollIntoView({ behavior: "smooth", block: "center" })
        editor?.querySelector("input")?.focus()
      })
    },
    cancelPending() { this.pending = null; this.pendingName = "" },
    async confirmPending() {
      const p = this.pending
      const name = String(this.pendingName || "").trim()
      if (!p) return
      if (p.kind === "save" || p.kind === "rename") {
        if (!name) { showSnackbar("A name is required.", "error"); return }
      }
      this.pending = null
      this.pendingName = ""
      try {
        if (p.kind === "save") {
          await this.runWith(() => api.flmSaveTune(name), "Tune saved.")
        } else if (p.kind === "rename") {
          await this.runWith(() => api.flmRenameSavedTune(p.tuneId, name), "Tune renamed.")
        } else if (p.kind === "discord") {
          if (!name) { showSnackbar("A Discord username is required.", "error"); return }
          await this.runWith(() => api.flmSubmitTune(p.tuneId, name), "Tune submitted to Firestar.")
        }
      } catch (e) {  }
    },
    saveCurrent() {
      const trial = this.activeTrial
      if (!trial) return
      const def = trial.profileLabel || this.workspace.currentCarFingerprint || "Saved Tune"
      this.startPending("save", { name: def })
    },
    async deleteSavedTune(tune) {
      const ok = await GalaxyConfirm({
        title: "Delete Saved Tune",
        message: `Delete saved tune "${tune.name || "Saved Tune"}"?`,
        confirmLabel: "Yes, Delete",
        danger: true,
      })
      if (!ok) return
      await this.runWith(() => api.flmDeleteSavedTune(tune.tuneId), "Saved tune deleted.")
    },
    async applySavedTune(tune) {
      await this.runWith(() => api.flmApplySavedTune(tune.tuneId), "Saved tune applied.")
    },
    async renameSavedTune(tune) {
      if (!tune?.tuneId || this.busy) return
      const name = await GalaxyPrompt({
        title: "Rename Saved Tune",
        message: `Choose a new name for “${tune.name || "Saved Tune"}”.`,
        initialValue: tune.name || "",
        placeholder: "Name this tune...",
        confirmLabel: "Rename",
      })
      if (name === null) return
      await this.runWith(() => api.flmRenameSavedTune(tune.tuneId, name), "Tune renamed.")
    },
    async submitTune(tune) {
      const ok = await GalaxyConfirm({
        title: "Send to Firestar",
        message: "Think this FLM tune is genuinely good and worth sharing? Only the tune values, car identity, and your Discord username are sent; routes and driving logs are not included.",
        confirmLabel: "Continue",
      })
      if (!ok) return
      this.startPending("discord", { tuneId: tune.tuneId })
    },
  },
  template: `
    <div>
      <section class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-diagram-3"></i>
          <span class="gx-section__title">Lateral Tuning (FLM)</span>
        </div>
        <div style="padding: var(--sp-4);">
          <p style="color: var(--text-muted); line-height:1.6; margin:0 0 var(--sp-3);">
            Analyze one or more local routes, review deterministic lateral findings, apply a bounded trial, drive, then revert or refine.
          </p>
          <GxNotice v-if="laneCentering" title="Before using FLM:" text="Turn Lane Centering off. FLM must analyze the model's unmodified lateral request; routes recorded with Lane Centering enabled are excluded." style="margin:0 0 var(--sp-3);" />
          <GxNotice v-if="isOnroad" text="FLM analysis is offroad-only. Stop the car and go offroad before starting a run." style="margin:0 0 var(--sp-3);" />
          <GxNotice v-if="activeTrial && activeTrial.rollbackAvailable === false" text="The original rollback data is unavailable. Keep the current tune as the new baseline before applying another trial." style="margin:0 0 var(--sp-3);" />
          <GxNotice v-if="error" tone="danger" :text="error" style="margin:0 0 var(--sp-3);" />

          <div style="display:flex; gap:8px; margin-bottom: var(--sp-3); flex-wrap:wrap;">
            <button type="button" class="gx-btn" :disabled="busy || !canAnalyze" @click="analyze">
              <i class="bi bi-graph-up-arrow"></i> Analyze Selected
            </button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy || !status.running" @click="stopAnalyze">
              <i class="bi bi-stop-fill"></i> Stop
            </button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy || !activeTrial || activeTrial.rollbackAvailable === false" @click="revertTrial">
              <i class="bi bi-arrow-counterclockwise"></i> Revert Trial
            </button>
            <button v-if="activeTrial && activeTrial.rollbackAvailable === false" type="button" class="gx-btn" :disabled="busy" @click="acceptBaseline">
              <i class="bi bi-check2-circle"></i> Keep as Baseline
            </button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy || !activeTrial" @click="saveCurrent">
              <i class="bi bi-save"></i> Save Tune
            </button>
            <button type="button" class="gx-icon-btn" title="Refresh" :disabled="busy || loading" @click="refresh"><i class="bi bi-arrow-clockwise"></i></button>
          </div>

          <div v-if="loading" class="gx-loading">Loading tuning workspace...</div>

          <div class="gx-section__header" style="padding:0 0 6px;"><i class="bi bi-activity"></i><span class="gx-section__title">Workspace status</span></div>
          <div>
            <div class="gx-row" style="border-top:none;"><span class="gx-row__label">State</span><span class="gx-row__value">{{ status.state || 'idle' }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Running</span><span class="gx-row__value">{{ status.running ? 'Yes' : 'No' }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Onroad</span><span class="gx-row__value">{{ isOnroad ? 'Yes' : 'No' }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Lane Centering</span><span class="gx-row__value">{{ laneCentering ? 'On' : 'Off' }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Updated</span><span class="gx-row__value">{{ fmtAge(status.updatedAt) }}</span></div>
            <div v-if="status.currentSegment" class="gx-row"><span class="gx-row__label">Current segment</span><span class="gx-row__value">{{ status.currentSegment }}</span></div>
            <div v-if="status.lastSkippedSegment" class="gx-row"><span class="gx-row__label">Skipped</span><span class="gx-row__value">{{ status.lastSkippedSegment }}</span></div>
            <div v-if="activeTrial" class="gx-row"><span class="gx-row__label">Active trial</span><span class="gx-row__value">{{ activeTrial.profileLabel || activeTrial.profileId || 'Active' }}</span></div>
            <div v-if="status.running && status.total" class="gx-row"><span class="gx-row__label">Progress</span><span class="gx-row__value">{{ num(status.progress,0) }} / {{ num(status.total,0) }}</span></div>
          </div>
        </div>
      </section>

      <section class="gx-card" style="margin-top: var(--sp-3);">
        <div class="gx-section__header">
          <i class="bi bi-collection"></i>
          <span class="gx-section__title">Saved Tunes</span>
        </div>
        <div style="padding: var(--sp-4);">
          <p style="color: var(--text-muted); line-height:1.6; margin:0 0 var(--sp-3);">Save a working FLM trial, switch between setups, then use Revert Trial to return to the exact manual settings from before FLM.</p>
          <div v-if="!workspace.savedTunes.length" class="gx-empty">No saved tunes yet. Apply a trial, then save it here.</div>
          <div v-for="tune in workspace.savedTunes" :key="tune.tuneId" style="border-top:1px solid var(--glass-border); padding: var(--sp-2) 0;">
            <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:8px;">
              <div style="min-width:0;">
                <strong>{{ tune.name || 'Saved Tune' }}<span v-if="tune.active" style="color:var(--primary);"> (Active)</span></strong>
                <div class="gx-row__desc">{{ tune.carFingerprint || 'Unknown car' }}{{ tune.pathLabel ? ' / ' + tune.pathLabel : '' }}</div>
                <div class="gx-row__desc">{{ tune.genericParamCount }} generic, {{ tune.frictionCurveCount }} friction curve, {{ tune.vehicleKnobCount }} knobs</div>
                <div class="gx-row__desc">{{ fmtAge(tune.updatedAt) }}</div>
              </div>
              <div style="display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end;">
                <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy || tune.active" @click="applySavedTune(tune)">{{ tune.active ? 'Active' : 'Apply' }}</button>
                <button type="button" class="gx-btn gx-btn--text" :disabled="busy" @click="renameSavedTune(tune)">Rename</button>
                <button type="button" class="gx-btn gx-btn--text" :disabled="busy || tune.active" style="color:var(--error);" @click="deleteSavedTune(tune)">Delete</button>
                <button type="button" class="gx-btn gx-btn--text" :disabled="busy" @click="submitTune(tune)">Firestar</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div v-if="pending" ref="pendingEditor" class="gx-card" style="margin-top: var(--sp-3);">
        <div style="padding: var(--sp-4); display:grid; gap:10px;">
          <div class="gx-section__header" style="padding:0 0 6px;">
            <i class="bi bi-pencil-square"></i>
            <span class="gx-section__title">{{ pending.kind === 'discord' ? 'Send to Firestar' : pending.kind === 'rename' ? 'Rename Tune' : 'Save Current Tune' }}</span>
          </div>
          <input v-if="pending.kind === 'discord'" class="gx-field gx-field--full" v-model="pendingName" placeholder="Enter your Discord username..." @keyup.enter="confirmPending" />
          <input v-else class="gx-field gx-field--full" v-model="pendingName" placeholder="Name this tune..." @keyup.enter="confirmPending" />
          <div style="display:flex; justify-content:flex-end; gap:8px;">
            <button type="button" class="gx-btn gx-btn--text" @click="cancelPending">Cancel</button>
            <button type="button" class="gx-btn" :disabled="busy" @click="confirmPending"><i class="bi bi-check2-circle"></i> Confirm</button>
          </div>
        </div>
      </div>

      <section class="gx-card" style="margin-top: var(--sp-3);">
        <div class="gx-section__header">
          <i class="bi bi-journal-arrow-down"></i>
          <span class="gx-section__title">Local Routes</span>
        </div>
        <div style="padding: var(--sp-4);">
          <p style="color: var(--text-muted); line-height:1.6; margin:0 0 var(--sp-2);">Pick routes and segment ranges to analyze. A run is limited to 5 segments total.</p>
          <div v-if="loadingRoutes" class="gx-loading">Loading local routes...</div>
          <div v-else-if="!routes.length" class="gx-empty">No local routes found.</div>
          <div v-else>
            <span class="gx-chip" :style="selectedSegmentCount > maxSegments ? 'background:var(--error);color:var(--on-error);' : ''">
              {{ selectedSegmentCount }}/{{ maxSegments }} segments selected
            </span>
            <button type="button" class="gx-btn gx-btn--text" style="font-size:var(--fs-xs);" @click="selectFirstSegments">Select first {{ maxSegments }}</button>
            <button type="button" class="gx-btn gx-btn--text" style="font-size:var(--fs-xs);" @click="clearSelection">Clear</button>
            <div v-for="route in routes" :key="route.name" style="border-top:1px solid var(--glass-border); padding: var(--sp-2) 0;">
              <label style="display:flex; gap:10px; align-items:flex-start; cursor:pointer;">
                <input type="checkbox" :checked="selectedRoutes.includes(route.name)" :disabled="!selectedRoutes.includes(route.name) && selectedSegmentCount >= maxSegments" @change="toggleRoute(route.name)" style="margin-top:4px;" />
                <span style="min-width:0;">
                  <strong>{{ fmtDate(route.timestamp) }}</strong>
                  <div class="gx-row__desc" style="word-break:break-all;">{{ route.name }}</div>
                  <div class="gx-row__desc">{{ fmtLen(route) }} · {{ routeSelectedSegmentCount(route.name) }} selected</div>
                </span>
              </label>
              <div v-if="selectedRoutes.includes(route.name)" style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin:8px 0 0 28px;">
                <span class="gx-row__desc">Segments</span>
                <input class="gx-field" style="width:92px;" type="number" :min="routeSegmentBounds(route.name).first" :max="routeSegmentBounds(route.name).last" inputmode="numeric" placeholder="First"
                  :value="segmentRanges[route.name]?.start || ''" @input="setSegmentRange(route.name, 'start', $event.target.value)" />
                <span class="gx-row__desc">to</span>
                <input class="gx-field" style="width:92px;" type="number" :min="routeSegmentBounds(route.name).first" :max="routeSegmentBounds(route.name).last" inputmode="numeric" placeholder="Last"
                  :value="segmentRanges[route.name]?.end || ''" @input="setSegmentRange(route.name, 'end', $event.target.value)" />
                <small class="gx-row__desc">Blank uses the whole route.</small>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="gx-card" style="margin-top: var(--sp-3);">
        <div class="gx-section__header">
          <i class="bi bi-sliders"></i>
          <span class="gx-section__title">Reports</span>
        </div>
        <div style="padding: var(--sp-4);">
          <div v-if="loading || !workspace.reports.length" class="gx-empty">No reports yet. Analyze routes to generate findings.</div>
          <div v-for="report in workspace.reports" :key="report.reportId" class="gx-row" style="cursor:pointer;" @click="loadReport(report.reportId)">
            <span class="gx-row__label">{{ report.carFingerprint || 'Unknown car' }}<span class="gx-row__desc">{{ fmtDate(report.createdAt) }}<span v-if="report.controlPath"> / {{ report.controlPath }}</span></span></span>
            <span class="gx-row__value">
              <span v-if="loadedReportId === report.reportId" class="gx-chip" style="background:var(--primary);color:var(--on-primary);">Open</span>
              <span v-else>Open</span>
            </span>
          </div>
        </div>
      </section>

      <section v-if="report && !reportLoading" class="gx-card" style="margin-top: var(--sp-3);">
        <div class="gx-section__header">
          <i class="bi bi-clipboard-data"></i>
          <span class="gx-section__title">Report Summary</span>
          <button type="button" class="gx-icon-btn" title="Delete report" style="color:var(--error); margin-left:auto;" @click="deleteReport(report)"><i class="bi bi-trash"></i></button>
        </div>
        <div style="padding: var(--sp-4);">
          <div>
            <div class="gx-row" style="border-top:none;"><span class="gx-row__label">Car</span><span class="gx-row__value">{{ report.car && report.car.carFingerprint || 'Unknown' }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Control path</span><span class="gx-row__value">{{ report.car && report.car.controlPath || 'unknown' }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Created</span><span class="gx-row__value">{{ reportTimestamp(report) }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Samples</span><span class="gx-row__value">{{ num(report.summary && report.summary.sampleCount) }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Processed segments</span><span class="gx-row__value">{{ num(report.summary && report.summary.processedSegments) }}</span></div>
            <div v-if="report.summary && report.summary.usedQlogFallback" class="gx-row"><span class="gx-row__label">qlog fallback</span><span class="gx-row__value">Yes</span></div>
          </div>

          <div v-if="comparisonRows.length" style="margin-top: var(--sp-3);">
            <div class="gx-section__header" style="padding:0 0 6px;">
              <i class="bi bi-git-compare"></i>
              <span class="gx-section__title">{{ angleControl ? 'Applicable Angle Settings' : 'Stock vs Current FLM' }}</span>
            </div>
            <div v-if="!angleControl" class="gx-row__desc" style="margin-bottom: 6px;">Active trial values are shown in the current column when one is applied.</div>
            <div v-for="row in comparisonRows" :key="row.key" class="gx-row">
              <span class="gx-row__label" :title="row.code || row.key">{{ row.label }}</span>
              <span class="gx-row__value" style="text-align:right;">
                <span class="gx-row__desc">{{ row.curve ? 'stock ' + curveStr(row.stock) : 'stock ' + fmtVal(row.stock) }}</span>
                <span style="color:var(--primary);">{{ row.curve ? curveStr(row.current) : fmtVal(row.current) }}</span>
              </span>
            </div>
          </div>

          <div v-for="path in pathList()" :key="path.key" style="margin-top: var(--sp-3);">
            <div class="gx-section__header" style="padding:0 0 6px;"><i class="bi bi-signpost-split"></i><span class="gx-section__title">{{ path.title }}</span></div>
            <p v-if="path.description" style="color:var(--text-muted); margin:0 0 6px; line-height:1.5;">{{ path.description }}</p>
            <p v-if="path.whySelected" style="margin:0 0 6px; line-height:1.5;"><strong>Why this path:</strong> {{ path.whySelected }}</p>
            <button v-if="!pathSelected(path.key) && pathList().length > 1" type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="selectPath(path.key)">Use this path</button>
          </div>

          <div v-if="(report.addTheseParametersAndStartHere || []).length" style="margin-top: var(--sp-3);">
            <div class="gx-section__header" style="padding:0 0 6px;"><i class="bi bi-bezier2"></i><span class="gx-section__title">Add these and start here</span></div>
            <ul style="margin:0; padding-left:18px; line-height:1.7; color:var(--text-muted);"><li v-for="line in report.addTheseParametersAndStartHere" :key="line">{{ line }}</li></ul>
          </div>
          <div v-if="(report.warnings || []).length" style="margin-top: var(--sp-3);">
            <div class="gx-section__header" style="padding:0 0 6px;"><i class="bi bi-exclamation-triangle"></i><span class="gx-section__title">Warnings</span></div>
            <ul style="margin:0; padding-left:18px; line-height:1.7; color:var(--text-muted);"><li v-for="w in report.warnings" :key="w">{{ w }}</li></ul>
          </div>
        </div>
      </section>

      <section v-if="report && !reportLoading" class="gx-card" style="margin-top: var(--sp-3);">
        <div class="gx-section__header">
          <i class="bi bi-list-check"></i>
          <span class="gx-section__title">Findings &amp; feedback</span>
        </div>
        <div style="padding: var(--sp-4);">
          <div class="gx-row__desc" style="margin-bottom: var(--sp-2);">Finding decisions save immediately and regenerate trial profiles.</div>
          <textarea class="gx-field gx-field--full" rows="2" style="resize:vertical; min-height:48px;" placeholder="Optional tuning notes" v-model="feedbackNotes"></textarea>
          <div style="display:flex; justify-content:flex-end; margin: var(--sp-2) 0 var(--sp-3);">
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="saveFeedback"><i class="bi bi-bookmark-check"></i> Save Notes</button>
          </div>

          <div v-if="!suggestions().length" class="gx-empty">No findings for the active path.</div>
          <div v-for="s in suggestions()" :key="s.dimensionId || s.bucket" style="border:1px solid var(--glass-border); border-radius:var(--radius-lg); padding: var(--sp-3); margin-bottom: var(--sp-3);">
            <div class="gx-section__header" style="padding:0 0 6px;"><i class="bi bi-bullseye"></i><span class="gx-section__title">{{ (s.bucket || 'finding').replace(/_/g, ' ') }}</span></div>
            <p v-if="s.evidence && (s.evidence.speedBand || s.evidence.directionBias || s.evidence.eventCount)" style="margin:0 0 6px; color:var(--text-muted); font-size:var(--fs-xs);">
              {{ s.evidence.speedBand || 'mixed' }} | {{ s.evidence.directionBias || 'center' }} | {{ num(s.evidence.eventCount) }} event(s)
            </p>
            <p v-if="s.observedBehavior" style="margin:0 0 6px; line-height:1.5;"><strong>Observed:</strong> {{ s.observedBehavior }}</p>
            <p v-if="s.likelyInterpretation" style="margin:0 0 6px; line-height:1.5;"><strong>Interpretation:</strong> {{ s.likelyInterpretation }}</p>
            <p v-if="s.primaryAdjustment" style="margin:0 0 6px; line-height:1.5;"><strong>Primary adjustment:</strong> {{ s.primaryAdjustment }}</p>
            <p v-if="s.whatNotToTouchYet" style="margin:0 0 6px; line-height:1.5;"><strong>What not to touch yet:</strong> {{ s.whatNotToTouchYet }}</p>
            <p v-if="s.ifThatWasWrong" style="margin:0 0 6px; line-height:1.5;"><strong>Next thing to try:</strong> {{ s.ifThatWasWrong }}</p>
            <div v-if="s.currentVsSuggested" style="border-top:1px solid var(--glass-border); padding-top: var(--sp-2);">
              <strong style="font-size:var(--fs-sm);">Current vs suggested:</strong>
              <p v-if="s.currentVsSuggested.type === 'friction_curve'" style="margin:4px 0 0; color:var(--text-muted); font-size:var(--fs-sm); word-break:break-all;">
                <code>{{ s.currentVsSuggested.family }}</code> {{ curveStr(s.currentVsSuggested.current) }} &rarr; {{ curveStr(s.currentVsSuggested.suggested) }}
              </p>
              <p v-else style="margin:4px 0 0; color:var(--text-muted); font-size:var(--fs-sm); word-break:break-all;">
                <code>{{ s.currentVsSuggested.paramKey || s.currentVsSuggested.symbol }}</code> {{ fmtVal(s.currentVsSuggested.current) }} &rarr; {{ fmtVal(s.currentVsSuggested.suggested) }}
              </p>
            </div>
            <div style="display:flex; gap:8px; margin-top: var(--sp-2); flex-wrap:wrap;">
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy" :style="fbState(s.dimensionId) === 'accepted' ? 'background:var(--primary);color:var(--on-primary);' : ''" @click="toggleFeedback(s.dimensionId, 'accepted')">{{ fbState(s.dimensionId) === 'accepted' ? 'Matched' : 'Matches Experience' }}</button>
              <button type="button" class="gx-btn gx-btn--text" :disabled="busy" :style="fbState(s.dimensionId) === 'ignored' ? 'color:var(--error);' : ''" @click="toggleFeedback(s.dimensionId, 'ignored')">{{ fbState(s.dimensionId) === 'ignored' ? 'Ignored' : 'Ignore' }}</button>
            </div>
          </div>
        </div>
      </section>

      <section class="gx-card" style="margin-top: var(--sp-3);">
        <div class="gx-section__header">
          <i class="bi bi-flask"></i>
          <span class="gx-section__title">Trial Profiles</span>
          <button type="button" class="gx-btn gx-btn--text" style="margin-left:auto;" :disabled="busy || !activeTrial" @click="saveCurrent">Save Current</button>
        </div>
        <div style="padding: var(--sp-4);">
          <p style="color: var(--text-muted); line-height:1.6; margin:0 0 var(--sp-3);">Apply one bounded profile at a time. Revert restores the exact advanced-lateral and FLM state from before the trial.</p>
          <div v-if="reportLoading" class="gx-loading">Loading report profiles...</div>
          <div v-else-if="report && !profiles().length" class="gx-empty">No trial profiles for this report.</div>
          <div v-if="!report" class="gx-empty">Open a report to view and apply its trial profiles.</div>
          <div v-for="profile in profiles()" :key="profile.id" style="border:1px solid var(--glass-border); border-radius:var(--radius-lg); padding: var(--sp-3); margin-bottom: var(--sp-3);">
            <div class="gx-section__header" style="padding:0 0 6px;">
              <span class="gx-section__title">{{ profile.label }}</span>
              <button type="button" class="gx-btn" style="margin-left:auto;" :disabled="busy || !canApplyTrial" @click="applyTrial(profile.id)"><i class="bi bi-play-fill"></i> Apply Trial</button>
            </div>
            <p v-if="profile.description" style="margin:0 0 var(--sp-2); color:var(--text-muted); line-height:1.5;">{{ profile.description }}</p>
            <div v-if="genericEntries(profile).length || frictionEntries(profile).length || knobEntries(profile).length">
              <span v-for="[key, value] in genericEntries(profile)" :key="key" class="gx-chip" style="margin:2px;"><code>{{ key }}</code>: {{ fmtVal(value) }}</span>
              <span v-for="[family, payload] in frictionEntries(profile)" :key="family" class="gx-chip" style="margin:2px;"><code>{{ family }}</code>: {{ curveStr(payload && payload.values || []) }}</span>
              <span v-for="[symbol, value] in knobEntries(profile)" :key="symbol" class="gx-chip" style="margin:2px;"><code>{{ symbol }}</code>: {{ fmtVal(value) }}</span>
            </div>
            <div v-else class="gx-row__desc" style="margin-top:4px;">No parameter overrides in this profile.</div>
          </div>
        </div>
      </section>

    </div>
  `,
}
