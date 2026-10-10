import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"
import { GxNotice } from "./GxNotice.js"

export const SpeedLimitsPanel = {
  name: "SpeedLimitsPanel",
  components: { GxNotice },
  data() {
    return {
      loading: true,
      canProcessNow: false,
      processing: false,
      reason: "",
      status: "Idle",
      submitting: false,
      vision: {
        bookmarkCount: 0, confidence: 0, debugSession: "", displaySpeed: 0,
        enabled: false, lastEvent: "", speedUnit: "mph", status: "Disabled", stream: "",
      },
    }
  },
  created() {
    this.poll = usePolling(() => this.load(), { interval: 3000 })
    this.poll.start()
  },
  beforeUnmount() { this.poll?.destroy() },
  methods: {
    async load() {
      try {
        const d = await api.getSpeedLimitsStatus()
        this.canProcessNow = Boolean(d?.canProcessNow)
        this.processing = Boolean(d?.processing)
        this.reason = d?.reason || ""
        this.status = d?.status || "Idle"
        this.vision = {
          bookmarkCount: Number(d?.visionBookmarkCount || 0),
          confidence: Number(d?.visionConfidence || 0),
          debugSession: d?.visionDebugSession || "",
          displaySpeed: Number(d?.visionDisplaySpeed || 0),
          enabled: Boolean(d?.visionEnabled),
          lastEvent: d?.visionLastEvent || "",
          speedUnit: d?.visionSpeedUnit || "mph",
          status: d?.visionStatus || (d?.visionEnabled ? "Idle" : "Disabled"),
          stream: d?.visionStream || "",
        }
      } catch (e) {
        this.status = "Unavailable"
        this.vision.status = "Unavailable"
        this.canProcessNow = false
        this.processing = false
      } finally {
        this.loading = false
      }
    },
    download() {
      const a = document.createElement("a")
      a.href = "/api/speed_limits"
      a.download = "speed_limits.json"
      a.click()
      showSnackbar("Download started...")
    },
    async processNow() {
      if (this.submitting || this.processing || !this.canProcessNow) return
      this.submitting = true
      try {
        const payload = await api.processSpeedLimits()
        showSnackbar(payload?.message || "Speed limit processing started.")
        await this.load()
      } catch (e) {
        showSnackbar(e?.message || "Failed to start speed limit processing.", "error")
      } finally {
        this.submitting = false
      }
    },
    visionSuffix() {
      const v = this.vision
      let out = `${v.status}`
      if (v.stream) out += ` on ${v.stream}`
      if (v.displaySpeed > 0) {
        out += ` (${v.displaySpeed} ${v.speedUnit}`
        if (v.confidence > 0) out += `, ${Math.round(v.confidence * 100)}%`
        out += ")"
      }
      return out
    },
  },
  template: `
    <section class="gx-card">
      <div class="gx-section__header">
        <i class="bi bi-sign-stop-fill"></i>
        <span class="gx-section__title">Download Speed Limits</span>
      </div>
      <div style="padding: var(--sp-3); display:grid; gap:6px;">
        <p style="margin:0; color:var(--text-muted);">
          Enable "Speed Limit Filler" on the device, drive to collect data, then process and download it here when parked.
        </p>
        <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
          <span class="gx-row__label">Processor Status</span>
          <span class="gx-row__value">{{ loading ? 'Checking...' : status }}</span>
        </div>
        <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
          <span class="gx-row__label">Vision Detector</span>
          <span class="gx-row__value">{{ loading ? 'Checking...' : visionSuffix() }}</span>
        </div>
        <div v-if="!loading && vision.enabled" class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
          <span class="gx-row__label">Vision Debug</span>
          <span class="gx-row__value">{{ vision.debugSession || 'No active session' }}<template v-if="vision.bookmarkCount">, {{ vision.bookmarkCount }} bookmark{{ vision.bookmarkCount === 1 ? '' : 's' }}</template></span>
        </div>
        <div v-if="!loading && vision.enabled && vision.lastEvent" class="gx-row__desc">{{ vision.lastEvent }}</div>
        <GxNotice v-if="!loading && reason && reason !== status" :text="reason" style="margin:0;" />
        <div style="display:flex; gap:8px; margin-top:8px; flex-wrap:wrap; align-items:center;">
          <a class="gx-btn" :href="'/api/speed_limits'" download="speed_limits.json" @click="showSnackbar('Download started...')"><i class="bi bi-download"></i> Download</a>
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="submitting || processing || !canProcessNow" @click="processNow">
            {{ processing || submitting ? 'Processing...' : 'Process Now' }}
          </button>
          <a class="gx-btn gx-btn--text" href="https://nerf.077769.xyz/" target="_blank" rel="noopener noreferrer">Submit speed limits here</a>
        </div>
      </div>
    </section>
  `,
}
