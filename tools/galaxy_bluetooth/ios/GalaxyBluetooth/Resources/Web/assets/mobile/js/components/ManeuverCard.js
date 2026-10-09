import { usePolling, formatAgeSeconds } from "../composables.js"
import { showSnackbar } from "../api.js"

function safeNumber(value, fallback = 0) {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

export const ManeuverCard = {
  name: "ManeuverCard",
  props: {
    title: { type: String, required: true },
    icon: { type: String, default: "bi-sign-turn-right" },
    intro: { type: String, default: "" },
    start: { type: Function, required: true },
    stop: { type: Function, required: true },
    status: { type: Function, required: true },
    interval: { type: Number, default: 3000 },
  },
  data() {
    return { loading: true, busy: false, data: null }
  },
  created() {
    this.poll = usePolling(() => this.refreshStatus(), { interval: this.interval })
    this.poll.start()
  },
  beforeUnmount() { this.poll?.destroy() },
  methods: {
    formatAgeSeconds,
    safeNumber,
    async refreshStatus() {
      try {
        const payload = await this.status()
        this.data = payload && typeof payload === "object" ? { ...payload, history: Array.isArray(payload.history) ? payload.history : [] } : null
        this.loading = false
      } catch (e) {
        this.loading = false
        throw e
      }
    },
    async run(action) {
      if (this.busy) return
      this.busy = true
      try {
        const fn = action === "start" ? this.start : this.stop
        const payload = await fn()
        this.data = payload && typeof payload === "object" ? { ...payload, history: Array.isArray(payload.history) ? payload.history : [] } : this.data
        showSnackbar(payload?.message || "Action complete.")
      } catch (e) {
        showSnackbar(e?.message || "Action failed.", "error")
      } finally {
        this.busy = false
      }
    },
  },
  template: `
    <section class="gx-card">
      <div class="gx-section__header">
        <i class="bi" :class="icon"></i>
        <span class="gx-section__title">{{ title }}</span>
      </div>
      <div style="padding: var(--sp-3);">
        <p style="color: var(--text-muted); line-height:1.5;">{{ intro }}</p>
        <div style="display:flex; gap:8px; margin: 12px 0;">
          <button type="button" class="gx-btn" :disabled="busy" @click="run('start')">Start / Arm</button>
          <button type="button" class="gx-btn gx-btn--danger" :disabled="busy" @click="run('stop')">Stop</button>
        </div>
        <div v-if="loading" class="gx-loading">Loading status...</div>
        <dl v-else-if="data" class="gx-stat-grid" style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
          <div><strong>Mode</strong><span>{{ data.modeEnabled ? 'Yes' : 'No' }}</span></div>
          <div><strong>State</strong><span>{{ data.state || 'idle' }}</span></div>
          <div><strong>Onroad</strong><span>{{ data.isOnroad ? 'Yes' : 'No' }}</span></div>
          <div><strong>Engaged</strong><span>{{ data.isEngaged ? 'Yes' : 'No' }}</span></div>
          <div><strong>Phase</strong><span>{{ data.phase || 'n/a' }}</span></div>
          <div><strong>Step</strong><span>{{ safeNumber(data.stepIndex, 0) }}/{{ safeNumber(data.stepTotal, 0) }}</span></div>
          <div><strong>Run</strong><span>{{ safeNumber(data.runIndex, 0) }}/{{ safeNumber(data.runTotal, 0) }}</span></div>
          <div><strong>Updated</strong><span>{{ formatAgeSeconds(data.updatedAgeSec) }}</span></div>
          <div style="grid-column:1/-1;"><strong>Current</strong><span>{{ data.maneuver || 'n/a' }}</span></div>
        </dl>
        <div v-if="data && data.history?.length" class="gx-card" style="margin-top:12px;">
          <div class="gx-section__header"><i class="bi bi-list-ol"></i><span class="gx-section__title">Progress Chain</span></div>
          <ol style="margin:0; padding: var(--sp-3) var(--sp-4);">
            <li v-for="line in [...data.history].reverse()" :key="line">{{ line }}</li>
          </ol>
        </div>
      </div>
    </section>
  `,
}
