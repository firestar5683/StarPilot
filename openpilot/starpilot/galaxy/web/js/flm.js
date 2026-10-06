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
  return value?.schemaVersion === 1 && value.purpose === 'offline_tracking_diagnostics' &&
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

export const FlmPage = {
  name: 'FlmPage',
  components: { GxNotice, FlmChart },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true }, go: { type: Function, required: true } },
  data: () => ({ inventoryStatus: 'idle', inventory: null, inventoryError: '', operation: null, report: null,
    operationError: '', busy: false, requesting: false, selected: [] }),
  created() {
    this.inventoryFeed = new LocalHistoryFeed({ publish: ({ status, data, error }) => {
      this.inventoryStatus = status; this.inventory = data; this.inventoryError = error
      if (data) this.selected = this.selected.filter((name) => selectableSegments(data).some((segment) => segment.name === name))
    }, unauthorized: this.unauthorized })
    this.operationFeed = new FlmFeed({ publish: (state) => Object.assign(this.$data, state), unauthorized: this.unauthorized })
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
  computed: { available() { return selectableSegments(this.inventory) }, canAnalyze() { return this.selected.length >= 1 && this.selected.length <= 5 && !this.busy && !this.requesting && this.operation?.state !== 'running' } },
  methods: {
    toggle(name) { this.selected = this.selected.includes(name) ? this.selected.filter((item) => item !== name) :
      this.selected.length < 5 ? [...this.selected, name] : this.selected },
    analyze() { if (this.canAnalyze && this.selected.every((name) => this.available.some((item) => item.name === name))) this.operationFeed.startAnalysis(this.selected) },
    resultLabel(status) { return ({ measured: 'Measured', insufficient_samples: 'Insufficient samples', missing_car_params: 'Missing vehicle data',
      unsupported_car: 'Unsupported vehicle', unsupported_controller: 'Unsupported controller' })[status] || 'Unavailable' },
    metric(value) { return finite(value) ? `${value.toFixed(2)} m/s²` : 'Unavailable' },
    exclusions(items) { return items.map(([reason, count]) => `${reason.replaceAll('_', ' ')}: ${count}`).join(' · ') || 'None recorded' },
  },
  template: `<div class="gx-view gx-flm">
    <div class="gx-settings__header"><div><h2>Offline Tracking</h2><p>Local recording diagnostics for Ioniq 6 steering torque tracking. Reports do not qualify a vehicle or recommend a tune.</p></div></div>
    <p v-if="mode !== 'local'" class="gx-card gx-message">Offline analysis requires authenticated local Galaxy access.</p>
    <template v-else>

      <p v-if="inventoryStatus === 'loading'" role="status" class="gx-card gx-message">Reading local recordings…</p><GxNotice tone="danger" v-if="inventoryStatus === 'unavailable'">{{ inventoryError }}</GxNotice>
      <p v-if="inventory?.scanIncomplete" role="status">This recording scan was incomplete. More local segments may exist.</p>
      <section class="gx-card gx-flm__panel"><h3>Choose Full Logs</h3><p class="gx-note">Select 1–5 closed local segments. Quick logs alone cannot provide this report.</p>
<div class="gx-flm__actions" style="position:sticky;top:0;z-index:1;background:var(--gx-surface, #181526);padding:0.75rem 0;display:flex;align-items:center;gap:1rem;flex-wrap:wrap">
          <button type="button" class="gx-btn" :disabled="!canAnalyze" @click="analyze">Analyze selected</button><span>{{ selected.length }} of 5 selected</span>
        </div>
        <p v-if="inventoryStatus === 'ready' && !available.length">No closed full logs found in this scan.</p>
        <div v-for="segment in available" :key="segment.name" class="gx-flm__choice"><label><input type="checkbox" :checked="selected.includes(segment.name)"
          :disabled="!selected.includes(segment.name) && selected.length >= 5 || operation?.state === 'running'" @change="toggle(segment.name)">
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

        <button v-if="operation?.state === 'running'" type="button" class="gx-btn gx-btn--tonal" :disabled="busy || requesting" @click="operationFeed.cancelAnalysis()">Cancel analysis</button>
      </section>
      <template v-if="report"><p class="gx-note">Offline diagnostic only · {{ report.segments.length }} {{ report.segments.length === 1 ? 'segment' : 'segments' }} · No tune recommendation</p>
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
