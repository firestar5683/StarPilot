import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"

const MAX_POINTS = 240
const POLL_INTERVAL_MS = 750
const ADVANCED_TERMS_KEY = "plotsShowAdvancedTerms"
const QUALITY_WINDOW_SECONDS = 30
const QUALITY_MIN_SAMPLES = 8

const LATERAL_QUALITY_CONFIG = {
  desiredKey: "desiredLateralAccel",
  actualKey: "actualLateralAccel",
  minSpeedMps: 0.5,
  minDemand: 0.008,
  allowLowDemandFallback: true,
  fallbackMinSpeedMps: 0.5,
  fallbackMinPeakDemand: 0.01,
  great: 0.15,
  good: 0.30,
  fair: 0.50,
}

const LONGITUDINAL_QUALITY_CONFIG = {
  desiredKey: "desiredLongitudinalAccel",
  actualKey: "actualLongitudinalAccel",
  minSpeedMps: 0.0,
  minDemand: 0.05,
  allowLowDemandFallback: true,
  fallbackMinSpeedMps: 1.5,
  fallbackMinPeakDemand: 0.04,
  applyPersistenceRules: true,
  warnError: 0.50,
  severeError: 0.90,
  great: 0.32,
  good: 0.52,
  fair: 0.78,
}

const LINE_COLORS = {
  desired: "#7aa2f7",
  actual: "#9ece6a",
  p: "#5ec8c8",
  i: "#d4a060",
  d: "#e05577",
  f: "#bb9af7",
}

const TONE_COLORS = {
  great: "#6cc56e",
  good: "#5ec8c8",
  fair: "#d4a060",
  poor: "#e05577",
  na: "var(--text-muted)",
}

function toNumber(value, fallback = 0) {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

// Canvas 2D cannot interpret CSS custom properties ("var(--x)"), so it silently
// keeps the previous colour (default black) when assigned one -> invisible text
// in dark mode. Resolve the token to a concrete colour from the live theme.
function cssColor(name, fallback) {
  try {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    if (value && !value.startsWith("var(")) return value
  } catch (e) {}
  return fallback
}

function fmtNum(value, digits = 2) {
  return toNumber(value).toFixed(digits)
}

function formatAge(seconds) {
  const value = Math.max(0, toNumber(seconds))
  if (value < 1) return `${Math.round(value * 1000)} ms`
  return `${value.toFixed(1)} s`
}

function formatSourceLabel(kind, source) {
  const normalizedKind = String(kind || "").toLowerCase()
  const normalizedSource = String(source || "").toLowerCase()

  if (normalizedKind === "lateral") {
    if (normalizedSource === "torquestate") return "Steering controller output"
    if (normalizedSource === "curvature") return "Path model estimate"
  }
  if (normalizedKind === "longitudinal") {
    if (normalizedSource.includes("atarget")) return "Planner target acceleration + measured acceleration"
    if (normalizedSource.includes("pid sum")) return "PID term sum + measured acceleration"
    if (normalizedSource.includes("caroutput")) return "Final accel command + measured acceleration"
    if (normalizedSource.includes("livelocationkalman")) return "Control output + calibrated acceleration"
    if (normalizedSource === "controlsstate") return "Planner target output"
  }
  if (normalizedKind === "lateralterms") {
    if (normalizedSource === "torquestate") return "Steering torque controller"
    if (normalizedSource === "pidstate") return "Steering angle PID controller"
  }
  if (normalizedKind === "longitudinalterms") {
    if (normalizedSource === "controlsstate") return "Longitudinal controller terms"
  }
  return "Live control signal"
}

function percentile(sortedValues, percentileValue) {
  const values = Array.isArray(sortedValues) ? sortedValues : []
  if (!values.length) return 0
  const p = Math.max(0, Math.min(1, Number(percentileValue)))
  const index = (values.length - 1) * p
  const lower = Math.floor(index)
  const upper = Math.ceil(index)
  if (lower === upper) return values[lower]
  const weight = index - lower
  return values[lower] * (1 - weight) + values[upper] * weight
}

function signalMagnitude(sample, config) {
  const desired = Math.abs(toNumber(sample?.[config.desiredKey], 0))
  const actual = Math.abs(toNumber(sample?.[config.actualKey], 0))
  return Math.max(desired, actual)
}

function computeQuality(samples, config) {
  const safeSamples = Array.isArray(samples) ? samples : []
  if (safeSamples.length < 2) {
    return { label: "na", value: null, detail: "Waiting for data" }
  }

  const latestTs = toNumber(safeSamples[safeSamples.length - 1]?.timestamp, 0)
  const cutoffTs = latestTs > 0 ? latestTs - QUALITY_WINDOW_SECONDS : 0
  const recentSamples = safeSamples.filter((sample) => toNumber(sample?.timestamp, 0) >= cutoffTs)

  const eligibleSignalSamples = recentSamples.filter((sample) => {
    const speed = Math.abs(toNumber(sample?.speed, 0))
    const signal = signalMagnitude(sample, config)
    const speedOk = config.minSpeedMps <= 0 ? true : speed >= config.minSpeedMps
    const demandOk = config.minDemand <= 0 ? true : signal >= config.minDemand
    return speedOk && demandOk
  })

  let eligibleSamples = eligibleSignalSamples
  let usedLowDemandFallback = false
  const allowLowDemandFallback = config.allowLowDemandFallback !== false
  if (allowLowDemandFallback && eligibleSamples.length < QUALITY_MIN_SAMPLES && recentSamples.length >= QUALITY_MIN_SAMPLES) {
    const totalSpeed = recentSamples.reduce((sum, sample) => sum + Math.abs(toNumber(sample?.speed, 0)), 0)
    const avgSpeed = recentSamples.length > 0 ? totalSpeed / recentSamples.length : 0
    const peakDemand = recentSamples.reduce((peak, sample) => Math.max(peak, signalMagnitude(sample, config)), 0)
    const fallbackMinSpeed = Math.max(0, toNumber(config.fallbackMinSpeedMps, 0))
    const fallbackMinPeakDemand = Math.max(0, toNumber(config.fallbackMinPeakDemand, 0))
    if (avgSpeed >= fallbackMinSpeed && peakDemand >= fallbackMinPeakDemand) {
      eligibleSamples = recentSamples
      usedLowDemandFallback = true
    }
  }

  if (eligibleSamples.length < QUALITY_MIN_SAMPLES) {
    const qualifier = allowLowDemandFallback ? "eligible" : "signal"
    return {
      label: "na",
      value: null,
      detail: `Need ${QUALITY_MIN_SAMPLES} samples (${eligibleSamples.length} ${qualifier} / ${recentSamples.length} total)`,
    }
  }

  const errors = eligibleSamples
    .map((sample) => Math.abs(toNumber(sample?.[config.desiredKey], 0) - toNumber(sample?.[config.actualKey], 0)))
    .sort((a, b) => a - b)

  if (!errors.length) {
    return { label: "na", value: null, detail: "No eligible samples" }
  }

  const p50 = percentile(errors, 0.50)
  const p90 = percentile(errors, 0.90)
  const robustError = 0.7 * p50 + 0.3 * p90
  const sampleSummary = `${eligibleSamples.length} samples / ${QUALITY_WINDOW_SECONDS}s${usedLowDemandFallback ? ", low-demand fallback" : ""}`

  if (config.applyPersistenceRules) {
    const warnThreshold = Math.max(config.warnError || 0.35, config.good || 0.35)
    const severeThreshold = Math.max(config.severeError || 0.70, config.fair || 0.55)
    const warnFrac = errors.filter((value) => value > warnThreshold).length / errors.length
    const severeFrac = errors.filter((value) => value > severeThreshold).length / errors.length

    let label = "poor"
    if (robustError <= config.great && warnFrac <= 0.18 && severeFrac <= 0.05) label = "great"
    else if (robustError <= config.good && warnFrac <= 0.34 && severeFrac <= 0.12) label = "good"
    else if (robustError <= config.fair && warnFrac <= 0.55 && severeFrac <= 0.24) label = "fair"

    const warnPct = Math.round(warnFrac * 100)
    const severePct = Math.round(severeFrac * 100)
    return {
      label,
      value: robustError,
      detail: `${sampleSummary}, ${warnPct}% > ${fmtNum(warnThreshold)} and ${severePct}% > ${fmtNum(severeThreshold)}`,
    }
  }

  let label = "poor"
  if (robustError <= config.great) label = "great"
  else if (robustError <= config.good) label = "good"
  else if (robustError <= config.fair) label = "fair"

  return { label, value: robustError, detail: sampleSummary }
}

function buildChartConfigs() {
  return [
    {
      id: "lateral",
      advanced: false,
      title: "Lateral Response",
      unit: "m/s²",
      legendDigits: 2,
      rangeDigits: 2,
      rangeFloor: 1.5,
      rangeMult: 1.25,
      roundDiv: 10,
      sourceKind: "lateral",
      sourceKey: "lateralSource",
      series: [
        { key: "desiredLateralAccel", label: "Target", legendClass: "desired", lineKey: "desired" },
        { key: "actualLateralAccel", label: "Measured", legendClass: "actual", lineKey: "actual" },
      ],
    },
    {
      id: "longitudinal",
      advanced: false,
      title: "Longitudinal Response",
      unit: "m/s²",
      legendDigits: 2,
      rangeDigits: 2,
      rangeFloor: 1.5,
      rangeMult: 1.25,
      roundDiv: 10,
      sourceKind: "longitudinal",
      sourceKey: "longitudinalSource",
      series: [
        { key: "desiredLongitudinalAccel", label: "Target", legendClass: "desired", lineKey: "desired" },
        { key: "actualLongitudinalAccel", label: "Measured", legendClass: "actual", lineKey: "actual" },
      ],
    },
    {
      id: "lateralTerms",
      advanced: true,
      title: "Lateral Controller Terms",
      unit: "",
      legendDigits: 3,
      rangeDigits: 3,
      rangeFloor: 0.15,
      rangeMult: 1.35,
      roundDiv: 1000,
      sourceKind: "lateralterms",
      sourceKey: "lateralTermsSource",
      series: [
        { key: "lateralP", label: "P", legendClass: "p", lineKey: "p" },
        { key: "lateralI", label: "I", legendClass: "i", lineKey: "i" },
        { key: "lateralD", label: "D", legendClass: "d", lineKey: "d" },
        { key: "lateralF", label: "F", legendClass: "f", lineKey: "f" },
      ],
    },
    {
      id: "longitudinalTerms",
      advanced: true,
      title: "Longitudinal Accel Cmd Terms",
      unit: "",
      legendDigits: 3,
      rangeDigits: 3,
      rangeFloor: 0.15,
      rangeMult: 1.35,
      roundDiv: 1000,
      sourceKind: "longitudinalterms",
      sourceKey: "longitudinalTermsSource",
      series: [
        { key: "longitudinalUpAccelCmd", label: "Up", legendClass: "p", lineKey: "p" },
        { key: "longitudinalUiAccelCmd", label: "Ui", legendClass: "i", lineKey: "i" },
        { key: "longitudinalUfAccelCmd", label: "Uf", legendClass: "f", lineKey: "f" },
      ],
    },
  ]
}

export const Plots = {
  name: "Plots",
  props: { embedded: { type: Boolean, default: false } },
  data() {
    return {
      loading: true,
      error: "",
      paused: false,
      showAdvancedTerms: false,
      live: null,
      samples: [],
    }
  },
  created() {
    this.charts = buildChartConfigs()
    this.lastTs = 0
    try {
      this.showAdvancedTerms = localStorage.getItem(ADVANCED_TERMS_KEY) === "1"
    } catch (e) { this.showAdvancedTerms = false }
    this.poll = usePolling(() => this.load(), { interval: POLL_INTERVAL_MS, enabled: () => !this.paused })
    this.poll.start()
  },
  beforeUnmount() { this.poll?.destroy() },
  computed: {
    shownCharts() {
      return this.charts.filter((c) => !c.advanced || this.showAdvancedTerms)
    },
    sourceLabelMap() {
      const live = this.live || {}
      return this.charts.reduce((map, c) => {
        map[c.id] = formatSourceLabel(c.sourceKind, live[c.sourceKey])
        return map
      }, {})
    },
    statusCard() {
      const live = this.live || {}
      return {
        onroad: live.isOnroad ? "Yes" : "No",
        age: formatAge(live.sampleAgeSeconds),
        speed: fmtNum(live.speed),
        count: this.samples.length,
        bootStabilizing: !!live.bootStabilizing,
        lastError: live.lastError || "",
      }
    },
    qualities() {
      return {
        lateral: computeQuality(this.samples, LATERAL_QUALITY_CONFIG),
        longitudinal: computeQuality(this.samples, LONGITUDINAL_QUALITY_CONFIG),
      }
    },
    empty() {
      return this.samples.length <= 1
    },
  },
  methods: {
    setChartRef(chart, el) {
      if (chart) chart.el = el || null
    },
    latestValue(key) {
      const latest = this.samples[this.samples.length - 1]
      if (latest) return latest[key]
      return toNumber(this.live?.[key])
    },
    chartLegend(chart) {
      return chart.series.map((s) => ({
        color: LINE_COLORS[s.lineKey],
        label: s.label,
        value: fmtNum(this.latestValue(s.key), chart.legendDigits),
      }))
    },
    toneStyle(label) {
      return { color: TONE_COLORS[label] || TONE_COLORS.na }
    },
    qualitySentence(kind) {
      const q = this.qualities[kind]
      const toneLabel = q.label === "na" ? "N/A" : q.label[0].toUpperCase() + q.label.slice(1)
      const base = kind === "lateral" ? "Your lateral tuning is" : "Your longitudinal tuning is"
      const error = q.value === null ? q.detail : `${fmtNum(q.value)} m/s² error (${q.detail})`
      return { base, toneLabel, error, label: q.label }
    },
    pushSample(payload) {
      const timestamp = toNumber(payload.timestamp, 0)
      if (!timestamp || timestamp <= 0 || timestamp === this.lastTs) return
      this.lastTs = timestamp
      const sample = {
        timestamp,
        speed: toNumber(payload.speed),
        desiredLateralAccel: toNumber(payload.desiredLateralAccel),
        actualLateralAccel: toNumber(payload.actualLateralAccel),
        desiredLongitudinalAccel: toNumber(payload.desiredLongitudinalAccel),
        actualLongitudinalAccel: toNumber(payload.actualLongitudinalAccel),
        lateralP: toNumber(payload.lateralP),
        lateralI: toNumber(payload.lateralI),
        lateralD: toNumber(payload.lateralD),
        lateralF: toNumber(payload.lateralF),
        longitudinalUpAccelCmd: toNumber(payload.longitudinalUpAccelCmd),
        longitudinalUiAccelCmd: toNumber(payload.longitudinalUiAccelCmd),
        longitudinalUfAccelCmd: toNumber(payload.longitudinalUfAccelCmd),
      }
      this.samples.push(sample)
      if (this.samples.length > MAX_POINTS) {
        this.samples.splice(0, this.samples.length - MAX_POINTS)
      }
    },
    async load() {
      try {
        const payload = await api.getPlotsLive()
        this.live = payload && typeof payload === "object" ? payload : this.live
        this.error = ""
        this.loading = false
        if (payload && !payload.stale) this.pushSample(payload)
        this.$nextTick(() => this.redraw())
      } catch (e) {
        this.error = e?.message || "Failed to load live plot data"
        this.loading = false
        throw e
      }
    },
    redraw() {
      for (const chart of this.charts) {
        if (chart.el) this.drawChart(chart)
      }
    },
    computeHalf(samples, keys, floor, mult, roundDiv) {
      let maxAbs = 0
      for (const sample of samples) {
        for (const key of keys) {
          const v = Math.abs(toNumber(sample?.[key]))
          if (v > maxAbs) maxAbs = v
        }
      }
      return Math.max(floor, Math.ceil(maxAbs * mult * roundDiv) / roundDiv)
    },
    drawChart(chart) {
      const cv = chart.el
      const ctx = cv.getContext("2d")
      const dpr = window.devicePixelRatio || 1
      const W = cv.clientWidth || 360
      const H = cv.clientHeight || 240
      cv.width = Math.round(W * dpr)
      cv.height = Math.round(H * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, W, H)

      const samples = this.samples
      const n = samples.length
      const pad = 8

      if (n <= 1) {
        ctx.fillStyle = cssColor("--text-muted", "#999999")
        ctx.font = "12px system-ui, sans-serif"
        ctx.textAlign = "center"
        ctx.fillText("Waiting for enough live samples...", W / 2, H / 2)
        return
      }

      const keys = chart.series.map((s) => s.key)
      const half = this.computeHalf(samples, keys, chart.rangeFloor, chart.rangeMult, chart.roundDiv)
      const min = -half
      const max = half
      const span = Math.max(1e-6, max - min)
      const clampVal = (v) => Math.max(min, Math.min(max, toNumber(v)))
      const yFor = (v) => pad + ((max - clampVal(v)) / span) * (H - 2 * pad)

      const gridStyle = cssColor("--glass-border", "rgba(128,128,128,0.25)")
      const axisStyle = cssColor("--text-muted", "#aaaaaa")
      ctx.lineWidth = 1
      for (const gv of [max * 0.5, 0, min * 0.5]) {
        ctx.strokeStyle = gv === 0 ? axisStyle : gridStyle
        ctx.beginPath()
        ctx.moveTo(0, yFor(gv))
        ctx.lineTo(W, yFor(gv))
        ctx.stroke()
      }

      ctx.font = "10px system-ui, sans-serif"
      ctx.fillStyle = cssColor("--text-muted", "#999999")
      ctx.textAlign = "left"
      const unitSuffix = chart.unit ? ` ${chart.unit}` : ""
      ctx.fillText(fmtNum(max, chart.rangeDigits) + unitSuffix, 3, pad + 6)
      ctx.fillText("0", 3, yFor(0) + 3)
      ctx.fillText(fmtNum(min, chart.rangeDigits) + unitSuffix, 3, H - 4)

      const last = samples[samples.length - 1]
      if (last) {
        ctx.textAlign = "right"
        ctx.fillText(`-${formatAge(toNumber(Date.now() / 1000, 0) - toNumber(last.timestamp, 0))}`, W - 3, pad + 6)
      }

      ctx.lineWidth = 1.5
      ctx.lineJoin = "round"
      for (const s of chart.series) {
        ctx.strokeStyle = LINE_COLORS[s.lineKey]
        ctx.beginPath()
        for (let i = 0; i < n; i++) {
          const x = (i / (n - 1)) * W
          const y = yFor(samples[i][s.key])
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.stroke()
      }
    },
    togglePaused() {
      this.paused = !this.paused
      if (this.paused) return
      this.load().catch((e) => {
        this.error = e?.message || "Failed to resume live data"
      })
      if (this.poll) this.poll.start()
    },
    async clearHistory() {
      this.samples = []
      this.lastTs = 0
      this.$nextTick(() => this.redraw())
      showSnackbar("Plot history cleared.")
    },
    toggleAdvancedTerms() {
      this.showAdvancedTerms = !this.showAdvancedTerms
      try {
        localStorage.setItem(ADVANCED_TERMS_KEY, this.showAdvancedTerms ? "1" : "0")
      } catch (e) { console.warn("Failed to persist plots advanced terms preference", e) }
      this.$nextTick(() => this.redraw())
    },
    retry() {
      this.loading = true
      this.error = ""
      this.load().catch((e) => {
        this.error = e?.message || String(e)
        this.loading = false
      })
    },
  },
  template: `
    <div class="gx-view">
      <h2 v-if="!embedded" style="margin-top:0;">Plots</h2>

      <section class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-graph-up-arrow"></i>
          <span class="gx-section__title">Live tuning status</span>
        </div>
        <div style="padding: var(--sp-3);">
          <p style="color: var(--text-muted); line-height:1.6; margin:0 0 var(--sp-3);">
            Live comparison view for tuning diagnostics. These scores are a quick health check, not a final verdict.
            Short spikes from bumps, lane changes, traffic transitions, and manual inputs can temporarily lower a score.
          </p>

          <div v-if="loading" class="gx-loading">Loading live data...</div>

          <div v-if="error" class="gx-alert gx-alert--warn" style="border:none; margin:0 0 var(--sp-2);">
            <i class="bi bi-exclamation-triangle-fill gx-alert__icon"></i>
            <div class="gx-alert__body"><strong>Error:</strong> <span>{{ error }}</span></div>
          </div>

          <div v-if="!loading || live">
            <div class="gx-row" style="border-top:none;"><span class="gx-row__label">Onroad</span><span class="gx-row__value">{{ statusCard.onroad }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Sample Age</span><span class="gx-row__value">{{ statusCard.age }}</span></div>
            <div class="gx-row"><span class="gx-row__label">Vehicle Speed</span><span class="gx-row__value">{{ statusCard.speed }} m/s</span></div>
            <div class="gx-row"><span class="gx-row__label">Samples</span><span class="gx-row__value">{{ statusCard.count }}</span></div>

            <template v-if="statusCard.bootStabilizing">
              <div class="gx-alert gx-alert--warn" style="margin: var(--sp-3) 0 0;">
                <i class="bi bi-hourglass-split gx-alert__icon"></i>
                <div class="gx-alert__body"><strong>Boot stabilizing</strong><span>Plots are warming up after startup.</span></div>
              </div>
            </template>
            <div v-if="statusCard.lastError" class="gx-alert gx-alert--warn" style="margin: var(--sp-3) 0 0;">
              <i class="bi bi-exclamation-triangle gx-alert__icon"></i>
              <div class="gx-alert__body"><strong>Source Error:</strong> <span>{{ statusCard.lastError }}</span></div>
            </div>

            <div style="display:grid; gap: var(--sp-2); margin-top: var(--sp-3);">
              <div v-for="q in [qualitySentence('lateral'), qualitySentence('longitudinal')]" :key="q.base">
                <p style="margin:0; font-weight: var(--fw-bold, 600);">
                  {{ q.base }} <span :style="toneStyle(q.label)">{{ q.toneLabel }}</span>
                </p>
                <p style="margin:2px 0 0; color: var(--text-muted); font-size: var(--fs-xs, 0.8rem);">{{ q.error }}</p>
              </div>
            </div>

            <p style="color: var(--text-muted); font-size: var(--fs-xs, 0.8rem); margin: var(--sp-3) 0 0; line-height:1.6;">
              Match rating uses a 30-second rolling window. Strong steering or accel moments are preferred, but gentler
              windows can still earn a rating. Longitudinal also checks how much of the window stays above error limits.
            </p>

            <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top: var(--sp-3);">
              <button type="button" class="gx-btn gx-btn--tonal" @click="togglePaused">
                <i class="bi" :class="paused ? 'bi-play-fill' : 'bi-pause-fill'"></i> {{ paused ? 'Resume Live' : 'Pause Live' }}
              </button>
              <button type="button" class="gx-btn gx-btn--tonal" @click="clearHistory">
                <i class="bi bi-trash"></i> Clear History
              </button>
              <button type="button" class="gx-btn gx-btn--tonal" @click="retry">
                <i class="bi bi-arrow-clockwise"></i> Refresh
              </button>
            </div>
          </div>
        </div>
      </section>

      <div style="display:grid; gap: var(--sp-3); margin-top: var(--sp-3);">
        <section v-for="chart in shownCharts.filter(c => !c.advanced)" :key="chart.id" class="gx-card" style="overflow:hidden;">
          <div class="gx-section__header">
            <i class="bi bi-activity"></i>
            <span class="gx-section__title">{{ chart.title }}</span>
          </div>
          <div style="padding: var(--sp-3);">
            <p style="margin:0 0 var(--sp-2); color: var(--text-muted); font-size: var(--fs-xs, 0.8rem);">
              Source: {{ sourceLabelMap[chart.id] }}
            </p>
            <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom: var(--sp-2);">
              <span v-for="item in chartLegend(chart)" :key="item.label" style="display:inline-flex; align-items:center; gap:4px; font-size: var(--fs-xs, 0.8rem);">
                <i style="width:10px; height:3px; border-radius:2px; display:inline-block; background: item.color;"></i>
                {{ item.label }}: {{ item.value }}
              </span>
            </div>
            <div v-if="!empty" style="width:100%; position:relative;">
              <canvas :ref="(el) => setChartRef(chart, el)" style="width:100%; height:220px; display:block;"></canvas>
            </div>
            <div v-else class="gx-empty">Waiting for enough live samples...</div>
          </div>
        </section>
      </div>

      <div style="margin-top: var(--sp-3);">
        <button type="button" class="gx-btn gx-btn--tonal" @click="toggleAdvancedTerms">
          <i class="bi" :class="showAdvancedTerms ? 'bi-eye-slash' : 'bi-sliders'"></i>
          {{ showAdvancedTerms ? 'Hide Advanced Controller Terms' : 'Show Advanced Controller Terms' }}
        </button>
      </div>

      <div v-if="showAdvancedTerms" style="display:grid; gap: var(--sp-3); margin-top: var(--sp-3);">
        <section v-for="chart in shownCharts.filter(c => c.advanced)" :key="chart.id" class="gx-card" style="overflow:hidden;">
          <div class="gx-section__header">
            <i class="bi bi-sliders"></i>
            <span class="gx-section__title">{{ chart.title }}</span>
          </div>
          <div style="padding: var(--sp-3);">
            <p style="margin:0 0 var(--sp-2); color: var(--text-muted); font-size: var(--fs-xs, 0.8rem);">
              Source: {{ sourceLabelMap[chart.id] }}
            </p>
            <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom: var(--sp-2);">
              <span v-for="item in chartLegend(chart)" :key="item.label" style="display:inline-flex; align-items:center; gap:4px; font-size: var(--fs-xs, 0.8rem);">
                <i style="width:10px; height:3px; border-radius:2px; display:inline-block; background: item.color;"></i>
                {{ item.label }}: {{ item.value }}
              </span>
            </div>
            <div v-if="!empty" style="width:100%; position:relative;">
              <canvas :ref="(el) => setChartRef(chart, el)" style="width:100%; height:220px; display:block;"></canvas>
            </div>
            <div v-else class="gx-empty">Waiting for enough live samples...</div>
          </div>
        </section>
      </div>
    </div>
  `,
}
