import { api, showSnackbar } from "../api.js"
import { usePolling, formatAgeSeconds } from "../composables.js"

function num(value, fallback = 0) {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function rowsOf(items) {
  return items
}

export const LongitudinalManeuvers = {
  name: "LongitudinalManeuvers",
  data() {
    return { loading: true, busy: false, error: "", data: null }
  },
  created() {
    this.poll = usePolling(() => this.refresh(), { interval: 3000 })
    this.poll.start()
  },
  beforeUnmount() { this.poll?.destroy() },
  computed: {
    fmt() {
      const data = this.data
      if (!data) return null
      const support = data.support && typeof data.support === "object" ? data.support : {}
      const yes = (k) => (support[k] ? "Yes" : "No")
      const number = (k, unit) => {
        const v = Number(support[k])
        return Number.isFinite(v) ? `${v.toFixed(2)} ${unit}` : "n/a"
      }
      const rows = [
        { label: "Mode Enabled", value: data.modeEnabled ? "Yes" : "No" },
        { label: "State", value: data.state || "idle" },
        { label: "Onroad", value: data.isOnroad ? "Yes" : "No" },
        { label: "Engaged", value: data.isEngaged ? "Yes" : "No" },
        { label: "Phase", value: data.phase || "n/a" },
        { label: "Paddle Mode", value: data.paddleMode || "auto" },
        { label: "Step", value: `${num(data.stepIndex, 0)} / ${num(data.stepTotal, 0)}` },
        { label: "Run", value: `${num(data.runIndex, 0)} / ${num(data.runTotal, 0)}` },
        { label: "Updated", value: formatAgeSeconds(data.updatedAgeSec) },
      ]
      const supportRows = [
        { label: "openpilot Longitudinal", value: yes("openpilotLongitudinalControl") },
        { label: "Full Stop + Go", value: yes("fullStopAndGo") },
        { label: "Auto Resume from Stop", value: yes("autoResumeFromStop") },
        { label: "Requires Resume Assist", value: yes("requiresResumeAssist") },
        { label: "Expected to Reach Zero", value: yes("expectedToReachZero") },
        { label: "Minimum Enable Speed", value: number("minEnableSpeed", "m/s") },
        { label: "Stop Acceleration", value: number("stopAccel", "m/s²") },
      ]
      return {
        rows: rowsOf(rows),
        supportRows: rowsOf(supportRows),
        popup: `${data.uiText1 || ""}${data.uiText2 ? ` | ${data.uiText2}` : ""}`,
        caveats: Array.isArray(data.caveats) ? data.caveats : [],
        skipped: Array.isArray(data.skippedManeuvers) ? data.skippedManeuvers : [],
        history: Array.isArray(data.history) ? data.history : [],
      }
    },
  },
  methods: {
    async refresh() {
      try {
        const payload = await api.longitudinalManeuversStatus()
        this.data = payload && typeof payload === "object" ? payload : null
        this.error = ""
        this.loading = false
      } catch (e) {
        this.error = e?.message || "Failed to load maneuver status"
        this.loading = false
        throw e
      }
    },
    async run(action) {
      if (this.busy) return
      this.busy = true
      try {
        const payload = await api.longitudinalManeuvers(action)
        this.data = payload && typeof payload === "object" ? payload : this.data
        this.error = ""
        showSnackbar(payload?.message || "Action complete.")
      } catch (e) {
        this.error = e?.message || `Failed to ${action} maneuvers`
        showSnackbar(this.error, "error")
      } finally {
        this.busy = false
      }
    },
  },
  template: `
    <section class="gx-card">
      <div class="gx-section__header">
        <i class="bi bi-forward-fill"></i>
        <span class="gx-section__title">Long Maneuvers</span>
      </div>
      <div style="padding: var(--sp-4);">
        <p style="color: var(--text-muted); line-height:1.6; margin:0 0 var(--sp-3);">Run the longitudinal maneuver suite from your phone and monitor progress live.</p>

        <div style="display:flex; gap:8px; margin-bottom: var(--sp-3); flex-wrap:wrap;">
          <button type="button" class="gx-btn" :disabled="busy" @click="run('start')">
            <i class="bi bi-play-fill"></i> Start / Arm
          </button>
          <button type="button" class="gx-btn gx-btn--danger" :disabled="busy" @click="run('stop')">
            <i class="bi bi-stop-fill"></i> Stop
          </button>
        </div>

        <p v-if="error" class="gx-alert gx-alert--warn" style="border:none;">{{ error }}</p>
        <div v-if="loading" class="gx-loading">Loading status...</div>

        <template v-if="!loading && fmt">
          <div class="gx-section__header" style="padding:0 0 6px;"><i class="bi bi-activity"></i><span class="gx-section__title">Live status</span></div>
          <div>
            <div v-for="row in fmt.rows" style="border-top:none;" :key="row.label" class="gx-row">
              <span class="gx-row__label">{{ row.label }}</span>
              <span class="gx-row__value">{{ row.value }}</span>
            </div>
          </div>

          <div class="gx-section__header" style="padding: var(--sp-4) 0 6px; margin-top: var(--sp-3);"><i class="bi bi-flag"></i><span class="gx-section__title">Current maneuver</span></div>
          <p style="margin:0; font-weight:var(--fw-bold);">{{ data?.maneuver || 'n/a' }}</p>
          <p v-if="fmt.popup" style="color:var(--text-muted); margin:4px 0 0;">{{ fmt.popup }}</p>

          <div class="gx-section__header" style="padding: var(--sp-4) 0 6px; margin-top: var(--sp-3);"><i class="bi bi-check2-circle"></i><span class="gx-section__title">Longitudinal support</span></div>
          <div>
            <div v-for="row in fmt.supportRows" style="border-top:none;" :key="row.label" class="gx-row">
              <span class="gx-row__label">{{ row.label }}</span>
              <span class="gx-row__value">{{ row.value }}</span>
            </div>
          </div>

          <div v-if="fmt.caveats.length" class="gx-alert gx-alert--warn" style="margin: var(--sp-3) 0 0;">
            <i class="bi bi-exclamation-triangle gx-alert__icon"></i>
            <div class="gx-alert__body"><strong>Platform caveats</strong><ul style="margin:4px 0 0; padding-left:18px;"><li v-for="c in fmt.caveats" :key="c">{{ c }}</li></ul></div>
          </div>
          <div v-if="fmt.skipped.length" class="gx-alert gx-alert--info" style="margin: var(--sp-2) 0 0;">
            <i class="bi bi-skip-forward gx-alert__icon"></i>
            <div class="gx-alert__body"><strong>Expected skips</strong><ul style="margin:4px 0 0; padding-left:18px;"><li v-for="s in fmt.skipped" :key="s">{{ s }}</li></ul></div>
          </div>

          <div class="gx-section__header" style="padding: var(--sp-4) 0 6px; margin-top: var(--sp-3);"><i class="bi bi-book"></i><span class="gx-section__title">Quick guide</span></div>
          <ol style="margin:0; padding:0 0 0 18px; line-height:1.8; color:var(--text-muted);">
            <li>Find a large, empty, straight road or lot with no traffic.</li>
            <li>Press <strong>Start / Arm</strong>, then engage openpilot with SET.</li>
            <li>Keep full supervision and be ready to disengage at all times.</li>
            <li>Review the platform caveats first. Low-speed maneuvers can be skipped automatically on cars that do not fully stop.</li>
            <li>When the status says complete, collect the logs and generate your HTML report.</li>
          </ol>

          <div v-if="fmt.history.length" style="margin-top: var(--sp-3);">
            <div class="gx-section__header" style="padding:0 0 6px;"><i class="bi bi-list-ol"></i><span class="gx-section__title">Progress chain</span></div>
            <ol style="margin:0; padding: var(--sp-3) var(--sp-4); border:1px solid var(--glass-border); border-radius:var(--radius-lg); line-height:1.7;">
              <li v-for="line in [...fmt.history].reverse()" :key="line">{{ line }}</li>
            </ol>
          </div>
        </template>
      </div>
    </section>
  `,
}
