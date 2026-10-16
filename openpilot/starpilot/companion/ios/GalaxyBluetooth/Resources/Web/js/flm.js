import { GxState } from "./state.js"
import { GxNotice } from "./notice.js"
import { LocalHistoryFeed, validLocalHistory } from './record-history.js'

const SEGMENT = /^(?:[a-f0-9]{8}--[a-f0-9]{10}|[0-9]{4}-[0-9]{2}-[0-9]{2}--[0-9]{2}-[0-9]{2}-[0-9]{2}|[a-f0-9]{16}[|_](?:[a-f0-9]{8}--[a-f0-9]{10}|[0-9]{4}-[0-9]{2}-[0-9]{2}--[0-9]{2}-[0-9]{2}-[0-9]{2}))--[0-9]{1,6}$/
const STATES = ['idle', 'running', 'completed', 'canceled', 'failed', 'unavailable']
const RESULTS = ['measured', 'insufficient_samples', 'missing_car_params', 'unsupported_car', 'unsupported_controller']
const FAILURE = {
  not_parked: 'Park the vehicle before analyzing recordings.',
  canceled: 'Analysis was canceled.',
  source_changed: 'A selected recording changed. Refresh the inventory.',
  invalid_segment: 'A selected full log is unavailable. Refresh the inventory.',
  busy: 'Another analysis is already running.',
  invalid_request: 'Select one to five closed full logs, then try again.',
  operation_changed: 'The analysis session changed. Refresh status.',
  process_failed: 'The analysis process stopped unexpectedly. Its error was saved to the device log.',
  deadline: 'Analysis exceeded its time limit. Try one segment at a time.',
  recording_unavailable: 'A selected recording is missing, still open, or changed. Refresh recordings.',
  decode_failed: 'A selected full log could not be decoded. Try another segment.',
  resource_limit: 'This recording exceeds the analysis memory limit. Try a smaller segment.',
}
const labelFailure = (code) => FAILURE[code] || 'Offline analysis is unavailable.'
const finite = (value) => typeof value === 'number' && Number.isFinite(value)

export function selectableSegments(inventory) {
  if (!validLocalHistory(inventory)) return []
  return inventory.routes.flatMap((route) => route.segments.filter((segment) => segment.files.rlog &&
    typeof segment.segmentName === 'string' && SEGMENT.test(segment.segmentName))
    .map((segment) => ({ routeId: route.routeId, number: segment.number, name: segment.segmentName })))
}

export function validFlmStatus(value) {
  return value?.version === 1 && STATES.includes(value.state) &&
    (value.operationId === null || typeof value.operationId === 'string' && /^[a-zA-Z0-9:_-]{1,100}$/.test(value.operationId)) &&
    Number.isSafeInteger(value.selected) && value.selected >= 0 && value.selected <= 5 &&
    Number.isSafeInteger(value.processed) && value.processed >= 0 && value.processed <= value.selected &&
    (value.errorCode === null || typeof value.errorCode === 'string' && /^[a-z_]{1,60}$/.test(value.errorCode)) &&
    (value.state === 'idle' ? value.operationId === null : value.operationId !== null)
}

function validSeries(points) {
  return Array.isArray(points) && points.length <= 160 && points.every((point) =>
    point && finite(point.mono_ns) && point.mono_ns > 0 && finite(point.desired_lat_accel) &&
    finite(point.actual_lat_accel) && Number.isSafeInteger(point.continuity_id) && point.continuity_id >= 0)
}

function validAnalysis(value) {
  return value && typeof value.route === 'string' && value.route.length <= 80 &&
    Number.isSafeInteger(value.number) && value.number >= 0 && RESULTS.includes(value.status) &&
    (value.car_params_sha256 === null || typeof value.car_params_sha256 === 'string' && /^[a-f0-9]{64}$/.test(value.car_params_sha256)) &&
    ['messages', 'torque_frames', 'eligible_samples'].every((key) => Number.isSafeInteger(value[key]) && value[key] >= 0) &&
    [value.mean_abs_error, value.root_mean_square_error].every((number) => number === null || finite(number) && number >= 0) &&
    Array.isArray(value.exclusions) && value.exclusions.length <= 32 && value.exclusions.every((item) =>
      Array.isArray(item) && item.length === 2 && typeof item[0] === 'string' && /^[a-z_]{1,60}$/.test(item[0]) &&
      Number.isSafeInteger(item[1]) && item[1] >= 0) && validSeries(value.series) &&
    Array.isArray(value.windows) && value.windows.length <= 128 && typeof value.windows_truncated === 'boolean'
}

export function validFlmReport(value, operationId) {
  return value?.schemaVersion === 1 && ['offline_tracking_diagnostics', 'gm_flm_evidence_profiles'].includes(value.purpose) &&
    (value.purpose === 'offline_tracking_diagnostics' || validGmEvidence(value.gmEvidence)) &&
    value.operationId === operationId && value.tuneRecommendation === null && value.vehicleQualification === false &&
    Array.isArray(value.segments) && value.segments.length >= 1 && value.segments.length <= 5 && value.segments.every((entry) =>
      entry?.source && typeof entry.source.segmentName === 'string' && SEGMENT.test(entry.source.segmentName) &&
      typeof entry.source.sha256 === 'string' && /^[a-f0-9]{64}$/.test(entry.source.sha256) &&
      Number.isSafeInteger(entry.source.compressedBytes) && entry.source.compressedBytes > 0 &&
      ['zst', 'bz2'].includes(entry.source.codec) && validAnalysis(entry.analysis))
}

// Each continuity ID is a distinct measured interval. Never draw through an excluded gap.
export function flmChart(series) {
  if (!validSeries(series) || !series.length) return { valid: false, paths: [[], []] }
  const first = series[0].mono_ns, last = series.at(-1).mono_ns
  const values = series.flatMap((point) => [point.desired_lat_accel, point.actual_lat_accel])
  const lo = Math.min(0, ...values), hi = Math.max(0, ...values), span = Math.max(.01, hi - lo)
  const x = (stamp) => 48 + Math.max(0, Math.min(1, (stamp - first) / Math.max(1, last - first))) * 576
  const y = (value) => 132 - (value - lo) / span * 114
  const paths = [[], []]
  for (const [keyIndex, key] of ['desired_lat_accel', 'actual_lat_accel'].entries()) {
    let points = [], prior = null
    const flush = () => { if (points.length >= 2) paths[keyIndex].push(points.join(' ')); points = [] }
    for (const point of series) {
      if (prior && (point.continuity_id !== prior.continuity_id || point.mono_ns <= prior.mono_ns)) flush()
      points.push(`${x(point.mono_ns).toFixed(1)},${y(point[key]).toFixed(1)}`)
      prior = point
    }
    flush()
  }
  return { valid: true, paths, top: hi.toFixed(2), bottom: lo.toFixed(2), zeroY: y(0),
    duration: Math.max(0, (last - first) / 1e9).toFixed(1) }
}

export class FlmFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, later, cancelTimer })
    this.active = false; this.generation = 0; this.inFlight = null; this.timer = this.deadline = null; this.busy = false
    this.status = null; this.report = null; this.error = ''
  }
  emit() { this.publish({ operation: this.status, report: this.report, operationError: this.error,
    busy: this.busy, requesting: this.inFlight !== null }) }
  stop() {
    this.active = false; this.generation++
    this.inFlight?.abort(); this.inFlight = null
    if (this.timer !== null) this.cancelTimer(this.timer)
    if (this.deadline !== null) this.cancelTimer(this.deadline)
    this.timer = this.deadline = null; this.busy = false; this.status = this.report = null; this.error = ''
    this.emit()
  }
  start() { this.stop(); this.active = true; return this.refresh() }
  async request(url, options = {}, timeoutMs = 10000) {
    const generation = this.generation, controller = new AbortController()
    this.inFlight = controller
    this.emit()
    let timer = null
    const timeout = new Promise((_, reject) => { timer = this.later(() => { controller.abort(); reject(new Error('Offline analysis timed out. Refresh status before trying again.')) }, timeoutMs); this.deadline = timer })
    try {
      const response = await Promise.race([this.fetcher(url, { credentials: 'same-origin', cache: 'no-store', ...options, signal: controller.signal }), timeout])
      if (!this.active || generation !== this.generation || controller.signal.aborted) return null
      if (response.status === 401) { this.stop(); this.unauthorized(); return null }
      const body = await Promise.race([response.json(), timeout])
      if (!this.active || generation !== this.generation || controller.signal.aborted) return null
      if (response.status === 503 && ['setup_required', 'access_unavailable'].includes(body?.code)) {
        this.stop(); this.unauthorized(); return null
      }
      if (!response.ok) throw new Error(labelFailure(body?.code))
      return body
    } finally {
      if (timer !== null) this.cancelTimer(timer)
      if (this.deadline === timer) this.deadline = null
      if (this.inFlight === controller) {
        this.inFlight = null
        if (this.active && generation === this.generation) this.emit()
      }
    }
  }
  schedule() {
    if (!this.active || this.timer !== null) return
    this.timer = this.later(() => { this.timer = null; this.refresh() }, this.status?.state === 'running' ? 1000 : 5000)
  }
  async refresh() {
    if (!this.active || this.inFlight || this.busy) return
    const generation = this.generation
    try {
      const status = await this.request('./api/flm/status')
      if (!this.active || generation !== this.generation || status === null) return
      if (!validFlmStatus(status)) throw new Error('Offline analysis status is unavailable.')
      const previousId = this.status?.operationId
      this.status = status
      if (previousId !== status.operationId || status.state !== 'completed') this.report = null
      this.error = status.state === 'failed' || status.state === 'unavailable' ? labelFailure(status.errorCode) : ''
      this.emit()
      if (status.state === 'completed' && this.report === null) await this.loadReport(status.operationId, generation)
    } catch (error) {
      if (this.active && generation === this.generation) { this.error = error.message; this.emit() }
    } finally { if (generation === this.generation) this.schedule() }
  }
  async loadReport(id, generation = this.generation) {
    try {
      const report = await this.request(`./api/flm/report?operationId=${encodeURIComponent(id)}`)
      if (!this.active || generation !== this.generation || report === null || this.status?.operationId !== id) return
      if (!validFlmReport(report, id)) throw new Error('Offline analysis report is unavailable.')
      this.report = report; this.error = ''; this.emit()
    } catch (error) {
      if (this.active && generation === this.generation) { this.error = error.message; this.emit() }
    }
  }
  async mutate(url, body) {
    if (!this.active || this.inFlight || this.busy) return
    const generation = this.generation
    if (this.timer !== null) this.cancelTimer(this.timer)
    this.timer = null
    this.busy = true; this.error = ''; this.emit()
    try {
      const status = await this.request(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (!this.active || generation !== this.generation || status === null) return
      if (!validFlmStatus(status)) throw new Error('Offline analysis response is unavailable.')
      this.status = status
      this.report = null; this.emit()
    } catch (error) {
      if (this.active && generation === this.generation) { this.error = error.message; this.emit() }
    } finally {
      if (this.active && generation === this.generation) { this.busy = false; this.emit(); this.refresh() }
    }
  }
  startAnalysis(segments) { return this.mutate('./api/flm/start', { segments }) }
  startTraining(segments, token) { return this.mutate('./api/flm/train', { segments, token }) }
  async feedback(feedback) {
    if (!this.active || this.inFlight || this.busy || !this.report?.gmEvidence) return
    const generation = this.generation, operationId = this.status?.operationId
    this.busy = true; this.emit()
    try {
      const value = await this.request('./api/flm/recommend', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operationId, feedback }) })
      if (!this.active || generation !== this.generation || this.status?.operationId !== operationId || value === null) return
      if (value.version !== 1 || value.operationId !== operationId || !validGmEvidence(value.recommendation)) throw new Error('Trial profiles are unavailable.')
      this.report = { ...this.report, gmEvidence: value.recommendation }; this.emit()
    } catch (error) { if (generation === this.generation) { this.error = error.message; this.emit() } }
    finally { if (generation === this.generation) { this.busy = false; this.emit() } }
  }
  cancelAnalysis() {
    if (this.status?.state !== 'running' || !this.status.operationId) return
    return this.mutate('./api/flm/cancel', { operationId: this.status.operationId })
  }
}

export const FlmChart = {
  name: 'FlmChart',
  props: { series: { type: Array, required: true } },
  computed: { chart() { return flmChart(this.series) } },
  template: `<svg viewBox="0 0 640 170" role="img" aria-label="Desired and actual lateral acceleration in recorded intervals">
    <line class="gx-plot-axis" x1="48" y1="18" x2="48" y2="132"/><line class="gx-plot-axis" x1="48" y1="132" x2="624" y2="132"/>
    <template v-if="chart.valid"><line class="gx-plot-zero" x1="48" :y1="chart.zeroY" x2="624" :y2="chart.zeroY"/>
      <text class="gx-plot-label" x="42" y="21" text-anchor="end">{{ chart.top }}</text>
      <text class="gx-plot-label" x="42" y="135" text-anchor="end">{{ chart.bottom }}</text>
      <text class="gx-plot-label" x="52" y="160">0 s</text><text class="gx-plot-label" x="624" y="160" text-anchor="end">+{{ chart.duration }} s</text>
    </template><g v-for="(paths, index) in chart.paths" :key="index"><polyline v-for="(points, part) in paths" :key="part" :points="points"
      :class="index === 0 ? 'gx-plot-desired' : 'gx-plot-actual'"/></g>
  </svg>`,
}

export function validGmEvidence(value) {
  return value?.fit === false && value.vehicleQualification === false &&
    /^[a-f0-9]{64}$/.test(value.context?.sourceToken) && value.context?.version === 1 &&
    typeof value.context?.capability?.fingerprint === 'string' &&
    ['standard', 'starpilot'].includes(value.context?.capability?.controller) &&
    Array.isArray(value.summaries) && value.summaries.length <= 128 &&
    value.summaries.every((row) => typeof row.dimensionId === 'string' && finite(row.severity)) &&
    Array.isArray(value.paths) && value.paths.length === 2 && value.paths.every((path) =>
      ['baseline_fix', 'cleanup_pass'].includes(path.key) && Array.isArray(path.suggestions) &&
      Array.isArray(path.profiles) && path.profiles.length <= 3 && path.profiles.every((profile) =>
        typeof profile.id === 'string' && profile.id.length <= 128 && typeof profile.label === 'string' &&
        (profile.canonical === null ? typeof profile.unavailableReason === 'string' :
          typeof profile.canonical?.manual === 'string' && profile.canonical.manual.length <= 4096 &&
          ['torque_universal', 'gm_bolt_2022_2023'].includes(profile.canonical?.surface?.profile))))
}

// Local authenticated profile editor; all mutation authority stays with the parked owner.
export function validLiveFlm(value) {
  if (value?.version !== 1 || typeof value.available !== 'boolean' || typeof value.editable !== 'boolean') return false
  if (!value.available && !value.token) return true
  if (!value.available) {
    // A stale rich profile cannot be edited under the current STANDARD law.
    // Only its exact current owner token and reset action remain reachable.
    return value.editable === false && typeof value.resettable === 'boolean' &&
      /^[a-f0-9]{64}$/.test(value.token) && typeof value.vehicle === 'string' && value.vehicle.length > 0 &&
      ['standard', 'starpilot'].includes(value.controller) && ['torque_universal', 'gm_bolt_2022_2023'].includes(value.profile) &&
      typeof value.reason === 'string' && value.reason.length > 0 && value.reason.length <= 256
  }
  const surface = (entry) => entry?.profile === value.profile && entry.knobs &&
    Object.keys(entry.knobs).length === Object.keys(value.knobs || {}).length &&
    Object.entries(entry.knobs).every(([key, number]) => value.knobs?.[key] && finite(number) &&
      number >= value.knobs[key].min && number <= value.knobs[key].max) &&
    (entry.baseValues === null || Array.isArray(entry.baseValues) && entry.baseValues.length === 5 &&
      entry.baseValues.every((number) => finite(number) && number >= .05))
  if (!/^[a-f0-9]{64}$/.test(value.token) || typeof value.vehicle !== 'string' ||
      !['standard', 'starpilot'].includes(value.controller) || !['torque_universal', 'gm_bolt_2022_2023'].includes(value.profile) ||
      !value.knobs || Object.keys(value.knobs).length > 32 ||
      !Object.values(value.knobs).every((range) => finite(range.min) && finite(range.max) && range.min <= range.max) ||
      !Array.isArray(value.curveDefaults) || value.curveDefaults.length !== 5 || !value.curveDefaults.every((n) => finite(n) && n >= .05) ||
      !surface(value.defaults) || !value.state?.saved || Object.keys(value.state.saved).length > 4) return false
  const state = value.state
  if (typeof value.manual !== 'string' || value.manual.length > 4096 || typeof value.manualConflict !== 'boolean' ||
      !value.preconditions || !value.inactiveKnobs || Object.entries(value.inactiveKnobs).some(([key, reason]) =>
        !value.knobs[key] || typeof reason !== 'string' || reason.length > 256) || !state.manual || Object.keys(state.manual).some((id) => !state.saved[id]) ||
      Object.values(state.manual).some((raw) => typeof raw !== 'string' || raw.length > 4096) ||
      Object.entries(value.preconditions).some(([id, reasons]) => !state.saved[id] || !Array.isArray(reasons) ||
        reasons.some((reason) => typeof reason !== 'string' || reason.length > 256))) return false
  return Object.entries(state.saved).every(([id, item]) => /^[a-zA-Z0-9_-]{1,48}$/.test(id) &&
    typeof item?.label === 'string' && item.label.trim().length > 0 && item.label.length <= 80 && surface(item.surface)) &&
    typeof state.applied === 'boolean' && typeof state.baselineApplied === 'boolean' &&
    (state.active === null ? !state.applied : Boolean(state.saved[state.active]) && state.applied) &&
    (state.baselineActive === null ? !state.baselineApplied : Boolean(state.saved[state.baselineActive]) && state.baselineApplied) &&
    (state.trial === null ? state.baselineActive === null : /^[a-f0-9]{32}$/.test(state.trial) && state.applied)
}

export const FlmLiveEditor = {
  name: 'FlmLiveEditor',
  components: { GxNotice },
  emits: ['source'],
  props: { unauthorized: { type: Function, required: true } },
  data: () => ({ live: null, error: '', busy: false, id: 'profile1', label: 'My surface', draft: null, useCurve: false, curve: [] }),
  mounted() { this.closed = false; this.load() },
  beforeUnmount() { this.closed = true; this.abort?.abort() },
  methods: {
    async request(url, body = null) {
      if (this.closed || this.busy || document.hidden) return null
      this.busy = true; this.error = ''; this.abort = new AbortController()
      const timer = setTimeout(() => this.abort.abort(), 10000)
      try {
        const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store', signal: this.abort.signal,
          ...(body === null ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) })
        if (response.status === 401) { this.unauthorized(); return null }
        const value = await response.json()
        if (!response.ok) throw new Error(value.error || 'The surface changed. Refresh before trying again.')
        if (!validLiveFlm(value)) throw new Error('Surface profiles are unavailable.')
        if (this.closed) return null
        this.live = value
        this.$emit?.('source', value)
        return value
      } catch (error) { if (!this.closed) this.error = error.name === 'AbortError' ? 'The request timed out. Refresh to check its result.' : error.message; return null }
      finally { clearTimeout(timer); if (!this.closed) this.busy = false }
    },
    async load() { const value = await this.request('./api/flm/live'); if (value?.defaults) this.choose(this.id) },
    choose(id) {
      this.id = id
      const saved = this.live?.state?.saved?.[id]
      this.label = saved?.label || 'My surface'
      this.draft = JSON.parse(JSON.stringify(saved?.surface || this.live?.defaults || null))
      this.useCurve = Boolean(this.draft && this.draft.baseValues !== null)
      this.curve = [...(this.useCurve ? this.draft.baseValues : this.live?.curveDefaults || [])]
    },
    create() {
      const id = [1, 2, 3, 4].map((n) => `profile${n}`).find((key) => !this.live.state.saved[key])
      if (id) this.choose(id)
    },
    async action(action, extra = {}) {
      if (!this.live?.token || this.busy || !(action === 'reset' ? this.live.resettable : this.live.editable)) return
      const value = await this.request('./api/flm/live-action', { action, token: this.live.token, ...extra })
      if (value?.defaults) this.choose(this.id)
    },
    save() {
      if (!this.draft || !this.label.trim() || Object.values(this.draft.knobs).some((v) => !finite(v)) ||
          this.useCurve && this.curve.some((v) => !finite(v) || v < .05)) return
      this.action('save', { id: this.id, label: this.label, surface: { ...this.draft, baseValues: this.useCurve ? this.curve : null } })
    },
    trial() { this.action('trial', { id: this.id }) },
    restore() { this.action('restore', { trial: this.live.state.trial }) },
    accept() { this.action('accept', { trial: this.live.state.trial }) },
  },
  template: `<section class="gx-card gx-flm__panel gx-stack" :inert="busy" :aria-busy="busy || undefined"><h3>GM Trial Tunes</h3>
    <p class="gx-note">Save the current manual choices from Tuning together with this surface. Applying a trial switches both; Restore returns the original session baseline. Other vehicle preferences are retained.</p>
    <div class="gx-actions"><button type="button" class="gx-btn gx-btn--tonal" @click="load">Refresh</button></div>
    <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
    <p v-if="live && !live.available" class="gx-note">{{ live.reason || "Choose an eligible GM torque controller to edit its surface." }}</p>
    <div v-if="live?.resettable && !live.available" class="gx-actions"><button type="button" class="gx-btn gx-btn--tonal" @click="action('reset')">Reset this surface binding</button></div>
    <template v-if="live?.available && draft">
      <p class="gx-note">{{ live.vehicle.replaceAll('_', ' ') }} · {{ live.controller === 'standard' ? 'Standard' : 'StarPilot' }}</p>
      <p v-if="!live.editable" class="gx-note">Park the vehicle to save, apply or restore a profile.</p>
      <label class="gx-field-group"><span class="gx-row__label">Profile</span><select class="gx-field" :value="id" @change="choose($event.target.value)"><option v-for="(item, key) in live.state.saved" :value="key">{{ item.label }}</option><option v-if="!live.state.saved[id]" :value="id">New profile</option></select></label>
      <div class="gx-actions"><button type="button" class="gx-btn gx-btn--tonal" @click="create" :disabled="Object.keys(live.state.saved).length >= 4">New profile</button></div>
      <label class="gx-field-group"><span class="gx-row__label">Name</span><input class="gx-field" v-model="label" maxlength="80" :disabled="!live.editable"></label>
      <label class="gx-field-group" v-for="(range, key) in live.knobs" :key="key"><span class="gx-row__label">{{ key.replaceAll('_', ' ') }}</span><input class="gx-field" type="number" v-model.number="draft.knobs[key]" :min="range.min" :max="range.max" step="0.001" :disabled="!live.editable || live.inactiveKnobs?.[key]"><small v-if="live.inactiveKnobs?.[key]" class="gx-note">{{ live.inactiveKnobs[key] }}</small></label>
      <label class="gx-row"><input type="checkbox" v-model="useCurve" :disabled="!live.editable"><span>Use the selected controller base friction curve</span></label>
      <template v-if="useCurve"><label class="gx-field-group" v-for="(speed, index) in [0,5,10,15,25]" :key="index"><span class="gx-row__label">At {{ speed }} m/s</span><input class="gx-field" type="number" min="0.05" step="0.001" v-model.number="curve[index]" :disabled="!live.editable"></label></template>
      <p v-for="reason in live.preconditions[id] || []" :key="reason" class="gx-note">{{ reason }}</p>
      <p v-if="live.manualConflict" class="gx-note">Manual choices changed after this trial. Keep as baseline to retain those edits, or review them before restoring; FLM will not overwrite them.</p>
      <p v-if="live.state.applied" class="gx-note">Active: {{ live.state.saved[live.state.active]?.label }}</p>
      <div class="gx-actions">
        <button type="button" class="gx-btn" @click="save" :disabled="!live.editable">Save manual choices and surface</button>
        <button type="button" class="gx-btn gx-btn--tonal" @click="trial" :disabled="!live.editable || !live.state.saved[id] || live.manualConflict || live.preconditions[id]?.length">Apply trial</button>
        <button v-if="live.state.trial" type="button" class="gx-btn gx-btn--tonal" @click="restore" :disabled="!live.editable || live.manualConflict">Restore baseline</button>
        <button v-if="live.state.trial" type="button" class="gx-btn gx-btn--tonal" @click="accept" :disabled="!live.editable">Keep as baseline</button>
        <button v-if="live.state.applied" type="button" class="gx-btn gx-btn--tonal" @click="action('disable')" :disabled="!live.editable">Use controller surface</button>
        <button type="button" class="gx-btn gx-btn--danger" @click="action('delete', { id })" :disabled="!live.editable || !live.state.saved[id] || id === live.state.active || id === live.state.baselineActive">Delete profile</button>
      </div>
    </template>
  </section>`,
  components: { GxNotice },
}

export function gmEventSeries(plot) {
  if (!plot || !Array.isArray(plot.times) || plot.times.length < 2 || plot.times.length > 160 ||
      !Array.isArray(plot.desired) || !Array.isArray(plot.actual) ||
      plot.times.length !== plot.desired.length || plot.times.length !== plot.actual.length ||
      !plot.times.every((time, index) => finite(time) && time >= 0 && (index === 0 || time > plot.times[index - 1])) ||
      ![...plot.desired, ...plot.actual].every(finite)) return []
  // Chart-only relative coordinates; these are not producer clock evidence.
  return plot.times.map((time, index) => ({ mono_ns: 1 + time*1e9, desired_lat_accel: plot.desired[index],
    actual_lat_accel: plot.actual[index], continuity_id: 0 }))
}

export const FlmPage = {
  name: 'FlmPage',
  components: { GxState, GxNotice, FlmChart, FlmLiveEditor },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true }, go: { type: Function, required: true } },
  data: () => ({ inventoryStatus: 'idle', inventory: null, inventoryError: '', operation: null, report: null,
    operationError: '', busy: false, requesting: false, selected: [], gmSource: null, accepted: [], ignored: [] }),
  created() {
    this.inventoryFeed = new LocalHistoryFeed({ publish: ({ status, data, error }) => {
      this.inventoryStatus = status; this.inventory = data; this.inventoryError = error
      if (data) this.selected = this.selected.filter((name) => selectableSegments(data).some((segment) => segment.name === name))
    }, unauthorized: this.unauthorized })
    this.operationFeed = new FlmFeed({ publish: (state) => {
      if (this.operation?.operationId !== state.operation?.operationId) { this.accepted = []; this.ignored = [] }
      Object.assign(this.$data, state)
    }, unauthorized: this.unauthorized })
  },
  mounted() {
    this.visibility = () => {
      if (document.hidden) { this.inventoryFeed.stop(); this.operationFeed.stop() }
      else if (this.mode === 'local') { this.inventoryFeed.start(); this.operationFeed.start() }
    }
    document.addEventListener('visibilitychange', this.visibility)
    if (this.mode === 'local' && !document.hidden) { this.inventoryFeed.start(); this.operationFeed.start() }
  },
  beforeUnmount() { document.removeEventListener('visibilitychange', this.visibility); this.inventoryFeed.stop(); this.operationFeed.stop() },
  computed: {
    available() { return selectableSegments(this.inventory) },
    analysisAvailable() { return this.selected.length >= 1 && this.selected.length <= 5 && this.operation?.state !== 'running' },
    canAnalyze() { return this.analysisAvailable && !this.busy && !this.requesting },
  },
  methods: {
    toggle(name) { this.selected = this.selected.includes(name) ? this.selected.filter((item) => item !== name) :
      this.selected.length < 5 ? [...this.selected, name] : this.selected },
    analyze() { if (this.canAnalyze && this.selected.every((name) => this.available.some((item) => item.name === name))) this.operationFeed.startAnalysis(this.selected) },
    train() { if (this.canAnalyze && this.gmSource?.editable) this.operationFeed.startTraining(this.selected, this.gmSource.token) },
    feedback() { this.operationFeed.feedback({ acceptedDimensions: this.accepted, ignoredDimensions: this.ignored }) },
    async saveReport(profile) {
      if (!profile.canonical || this.busy || this.requesting || !this.gmSource?.editable) return
      const editor = this.$refs.liveEditor
      const id = [1, 2, 3, 4].map((n) => `profile${n}`).find((key) => !editor.live.state.saved[key])
      if (!id) { this.operationError = 'Delete a saved profile before saving another trial.'; return }
      const value = await editor.request('./api/flm/save-report', { operationId: this.operation.operationId,
        token: this.gmSource.token, generatedId: profile.id, id, label: profile.label,
        feedback: this.report.gmEvidence.feedback })
      if (value?.available) editor.choose(id)
    },
    resultLabel(status) { return ({ measured: 'Measured', insufficient_samples: 'Insufficient samples', missing_car_params: 'Missing vehicle data',
      unsupported_car: 'Unsupported vehicle', unsupported_controller: 'Unsupported controller' })[status] || 'Unavailable' },
    eventSeries(plot) { return gmEventSeries(plot) },
    metric(value) { return finite(value) ? `${value.toFixed(2)} m/s²` : 'Unavailable' },
    exclusions(items) { return items.map(([reason, count]) => `${reason.replaceAll('_', ' ')}: ${count}`).join(' · ') || 'None recorded' },
  },
  template: `<div class="gx-view gx-flm" :inert="busy || requesting" :aria-busy="busy || requesting || undefined">
    <div class="gx-settings__header gx-page-header"><div><h2>FLM</h2><p>Review recorded torque tracking or generate GM trial choices from observed symptoms. A trial is a user-selected tune, not a fitted learner or vehicle qualification.</p></div></div>
    <GxState v-if="mode !== 'local'">Offline analysis requires authenticated local Galaxy access.</GxState>
    <template v-else>
      <FlmLiveEditor ref="liveEditor" :unauthorized="unauthorized" @source="gmSource = $event"/>

      <GxState v-if="inventoryStatus === 'loading'" loading>Reading local recordings…</GxState><GxNotice tone="danger" v-if="inventoryStatus === 'unavailable'">{{ inventoryError }}</GxNotice>
      <GxNotice v-if="inventory?.scanIncomplete" tone="warn">This recording scan was incomplete. More local segments may exist.</GxNotice>
      <section class="gx-card gx-flm__panel"><h3>Choose Full Logs</h3><p class="gx-note">Select 1–5 closed local segments. Quick logs alone cannot provide this report.</p>
        <div class="gx-actions">
          <button type="button" class="gx-btn" :disabled="!analysisAvailable" @click="analyze">Analyze selected</button><button type="button" class="gx-btn gx-btn--tonal" :disabled="!analysisAvailable || !gmSource?.editable" @click="train">Generate GM trials</button><span class="gx-note">{{ selected.length }} of 5 selected</span>
        </div>
        <p v-if="inventoryStatus === 'ready' && !available.length">No closed full logs found in this scan.</p>
        <div v-for="segment in available" :key="segment.name" class="gx-flm__choice"><label><input type="checkbox" :checked="selected.includes(segment.name)"
 :disabled="!selected.includes(segment.name) && selected.length>= 5 || operation?.state === 'running'" @change="toggle(segment.name)">
          <span>Route {{ segment.routeId }} · Segment {{ segment.number }}</span></label></div>
      </section>
      <section class="gx-card gx-flm__panel"><h3>Analysis</h3>
        <p v-if="operation?.state === 'running'" role="status">Analyzing {{ operation.processed }} of {{ operation.selected }} selected segments…</p>
        <p v-else-if="operation?.state === 'completed'" role="status">Analysis completed.</p>
        <p v-else-if="operation?.state === 'canceled'" role="status">Analysis canceled.</p>
        <GxNotice tone="danger" v-else-if="operation?.state === 'failed'">Analysis failed.</GxNotice>
        <p v-else-if="operation?.state === 'unavailable'" role="status">Analysis owner unavailable.</p>
        <p v-else role="status">No analysis running.</p>
        <GxNotice tone="danger" v-if="operationError">{{ operationError }}</GxNotice>

        <button v-if="operation?.state === 'running'" type="button" class="gx-btn gx-btn--tonal" @click="operationFeed.cancelAnalysis()">Cancel analysis</button>
      </section>
      <section v-if="report?.gmEvidence" class="gx-card gx-flm__panel"><h3>Recorded GM symptoms</h3>
        <p>{{ report.gmEvidence.decision.reason }}</p>
        <p>Only recordings matching the current final vehicle configuration are eligible. Gaps and driver overrides stay excluded.</p>
        <label v-for="row in report.gmEvidence.summaries" :key="row.dimensionId">
          {{ row.dimensionId.replaceAll('_', ' ') }}
          <input type="checkbox" v-model="accepted" :value="row.dimensionId">Confirmed
          <input type="checkbox" v-model="ignored" :value="row.dimensionId">Ignore
        </label>
        <div class="gx-actions"><button type="button" class="gx-btn" @click="feedback">Update trial choices</button></div>
        <section v-for="path in report.gmEvidence.paths" :key="path.key"><h4>{{ path.title }}</h4><p>{{ path.description }}</p>
          <article v-for="suggestion in path.suggestions" :key="suggestion.dimensionId"><p>{{ suggestion.observedBehavior }}</p><p>{{ suggestion.likelyInterpretation }}</p><p>{{ suggestion.primaryAdjustment }}</p><p>{{ suggestion.whatNotToTouchYet }}</p><p>{{ suggestion.ifThatWasWrong }}</p><flm-chart v-if="eventSeries(suggestion.plotData).length" :series="eventSeries(suggestion.plotData)"/></article>
          <div v-for="profile in path.profiles" :key="profile.id"><p>{{ profile.label }} · {{ profile.description }}</p>
            <p v-if="profile.unavailableReason">{{ profile.unavailableReason }}</p>
            <div class="gx-actions"><button type="button" class="gx-btn gx-btn--tonal" @click="saveReport(profile)" :disabled="!gmSource?.editable || !profile.canonical">Save trial for review</button></div>
          </div>
        </section>
      </section>
      <template v-if="report"><p class="gx-note">Offline diagnostic only · {{ report.segments.length }} {{ report.segments.length === 1 ? 'segment' : 'segments' }} · {{ report.gmEvidence ? "Human-selected GM trials" : "No tune recommendation" }}</p>
        <section v-for="entry in report.segments" :key="entry.source.segmentName" class="gx-card gx-flm__panel gx-plots__panel">
          <h3>{{ entry.source.segmentName }}</h3><p class="gx-note">{{ resultLabel(entry.analysis.status) }} · Full log SHA {{ entry.source.sha256.slice(0,12) }}…</p>
          <p>Eligible samples: {{ entry.analysis.eligible_samples }} · Mean absolute error: {{ metric(entry.analysis.mean_abs_error) }} · RMSE: {{ metric(entry.analysis.root_mean_square_error) }}</p>
          <p class="gx-note">Excluded observations: {{ exclusions(entry.analysis.exclusions) }}</p>
          <template v-if="entry.analysis.series.length"><p class="gx-note">Lateral acceleration · m/s² · gaps mark excluded or interrupted data</p>
            <p class="gx-flm__legend"><span class="gx-flm__legend-desired">Desired</span><span class="gx-flm__legend-actual">Actual</span></p>
            <flm-chart :series="entry.analysis.series" /></template>
          <p v-else class="gx-note">No eligible tracking series for this segment.</p>
        </section>
      </template>
    </template>
  </div>`,
}
