import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"
import { GalaxySection } from "../components/GalaxySection.js"
import { GalaxySelect } from "../components/GalaxySelect.js"
import { GalaxySheet } from "../components/GalaxySheet.js"
import { SentryScrubber, isCaptureEvent } from "../components/SentryScrubber.js"

function b64ToBytes(value) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4)
  const normalized = (value + padding).replace(/-/g, "+").replace(/_/g, "/")
  const raw = window.atob(normalized)
  return Uint8Array.from(raw, (ch) => ch.charCodeAt(0))
}

// Local calendar day (YYYY-MM-DD), `daysAgo` days back from today.
function localDay(daysAgo = 0) {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  const pad = (n) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export const Sentry = {
  name: "Sentry",
  components: { GalaxySection, GalaxySelect, GalaxySheet, SentryScrubber },
  data() {
    return {
      loading: true,
      savingKey: "",
      params: {},
      status: {},
      event: {},
      dateFrom: "",
      dateTo: "",
      historyVisible: false,
      newEvents: false,
      liveCapture: {},
      testBusy: false,
      liveBusy: false,
      deleteBusy: false,
      viewerBusy: false,
      viewerEvents: [],
      viewerKey: 0,
      viewerCamera: "both",
      timelapseBusy: false,
      pushBusy: false,
      selectedImage: null,
    }
  },
  created() {
    this.viewerRequestId = 0
    this.viewerLatestId = ""
    this.poll = usePolling(() => this.loadStatus(), { interval: 5000 })
    this.poll.start()
  },
  mounted() {
    this.loadParams()
    this._onKeydown = (event) => {
      if (event.key === "Escape" && this.selectedImage) this.closeImage()
    }
    window.addEventListener("keydown", this._onKeydown)
  },
  beforeUnmount() {
    this.poll?.destroy()
    window.removeEventListener("keydown", this._onKeydown)
  },
  computed: {
    captureEvents() { return this.viewerEvents.filter(isCaptureEvent) },
    alertEvents() { return this.viewerEvents.filter((e) => !isCaptureEvent(e)) },
    statusText() { return String(this.status?.state || "unknown") },
    hasEvent() { return !!(this.event && this.event.eventId) },
    filterActive() { return !!(this.dateFrom || this.dateTo) },
    activePreset() {
      if (!this.dateFrom && !this.dateTo) return "all"
      if (this.dateFrom === localDay(1) && this.dateTo === localDay(1)) return "yesterday"
      if (this.dateTo !== localDay()) return ""
      if (this.dateFrom === localDay()) return "today"
      if (this.dateFrom === localDay(6)) return "week"
      return ""
    },
    // A new event can only show up in the viewer if the range still reaches today.
    rangeIncludesNow() { return !this.dateTo || this.dateTo >= localDay() },
  },
  methods: {
    async loadParams() {
      try {
        this.params = (await api.getParams()) || {}
      } catch (e) {
        showSnackbar("Failed to load Sentry settings.", "error")
      } finally {
        this.loading = false
      }
    },
    async loadStatus() {
      try {
        const payload = await api.getSentryStatus()
        this.status = payload?.status || {}
        this.event = payload?.lastEvent || {}
        // Never rebuild the viewer from the poll; just flag that it is stale. Compare against the
        // latest event seen when the viewer last loaded, so an empty or past range does not false-flag.
        if (this.historyVisible && this.rangeIncludesNow && this.hasEvent
          && String(this.event.eventId) !== this.viewerLatestId) {
          this.newEvents = true
        }
      } catch (e) {
        if (!this.loading) showSnackbar("Failed to load Sentry status.", "error")
      }
    },
    // Local calendar days -> UTC instants; "until" is exclusive so the end date is inclusive.
    historyRange() {
      const range = {}
      if (this.dateFrom) range.since = new Date(`${this.dateFrom}T00:00:00`).toISOString()
      if (this.dateTo) {
        const end = new Date(`${this.dateTo}T00:00:00`)
        end.setDate(end.getDate() + 1)
        range.until = end.toISOString()
      }
      return range
    },
    applyFilter() {
      if (this.dateFrom && this.dateTo && this.dateFrom > this.dateTo) {
        showSnackbar("The start date is after the end date.", "error")
        return
      }
      this.viewerKey += 1
      this.loadViewerEvents()
    },
    clearFilter() {
      this.dateFrom = ""
      this.dateTo = ""
      this.applyFilter()
    },
    showToday() {
      this.dateFrom = localDay()
      this.dateTo = localDay()
      this.applyFilter()
    },
    showYesterday() {
      this.dateFrom = localDay(1)
      this.dateTo = localDay(1)
      this.applyFilter()
    },
    showLastWeek() {
      this.dateFrom = localDay(6)
      this.dateTo = localDay()
      this.applyFilter()
    },
    onPresetChange(preset) {
      if (preset === "today") return this.showToday()
      if (preset === "yesterday") return this.showYesterday()
      if (preset === "week") return this.showLastWeek()
      return this.clearFilter()
    },
    async makeTimelapse() {
      if (this.timelapseBusy) return
      this.timelapseBusy = true
      try {
        const { blob, frames, seconds } = await api.getSentryTimelapse({
          ...this.historyRange(),
          camera: this.viewerCamera,
          timing: "gap",
        })
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = "sentry-timelapse.mp4"
        a.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
        showSnackbar(`Timelapse ready (${frames} frame${frames === 1 ? "" : "s"}, ${Math.round(seconds)}s).`)
      } catch (e) {
        showSnackbar(e?.data?.error || e?.message || "Timelapse failed.", "error")
      } finally {
        this.timelapseBusy = false
      }
    },
    // The viewer needs every event in range (not one page), so it asks for the unpaginated list.
    // The default range is today, which keeps this small.
    async loadViewerEvents() {
      const requestId = ++this.viewerRequestId
      this.viewerBusy = true
      try {
        const payload = await api.getSentryEvents(this.historyRange())
        if (requestId !== this.viewerRequestId) return
        this.viewerEvents = Array.isArray(payload?.events) ? payload.events : []
        this.newEvents = false
        this.viewerLatestId = String(this.event?.eventId || "")
      } catch (e) {
        if (requestId !== this.viewerRequestId) return
        showSnackbar("Failed to load Sentry events for the viewer.", "error")
      } finally {
        if (requestId === this.viewerRequestId) this.viewerBusy = false
      }
    },
    refreshAll() {
      this.loadViewerEvents()
    },
    async deleteAllHistory() {
      const total = this.viewerEvents.length
      if (this.deleteBusy || !total) return
      const range = this.historyRange()
      const scoped = this.filterActive
      const captures = this.captureEvents.length
      const alerts = this.alertEvents.length
      const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`
      const what = alerts ? `${plural(captures, "capture")} and ${plural(alerts, "alert")}` : plural(total, "Sentry event")
      const imagesClause = captures ? " and their camera images" : ""
      if (!(await GalaxyConfirm({
        title: scoped ? "Delete events in this range?" : "Delete ALL Sentry events?",
        message: scoped
          ? `Delete ${what} in this date range${imagesClause}? This cannot be undone.`
          : `Delete all ${what}${imagesClause}? This cannot be undone.`,
        confirmLabel: scoped ? "Delete matching" : "Delete all",
        danger: true,
      }))) return
      this.deleteBusy = true
      try {
        const result = await api.deleteSentryEvents({ ...range, all: !scoped })
        const failed = result?.failed ? ` ${result.failed} could not be removed.` : ""
        showSnackbar(`Deleted ${result?.deleted ?? 0} Sentry event${result?.deleted === 1 ? "" : "s"}.${failed}`)
        await this.loadViewerEvents()
        this.loadStatus()
      } catch (e) {
        showSnackbar(e?.data?.error || e?.message || "Sentry event deletion failed.", "error")
      } finally {
        this.deleteBusy = false
      }
    },
    // Opening history always starts on today; most reviews are of the current day.
    toggleHistory() {
      this.historyVisible = !this.historyVisible
      if (!this.historyVisible) return
      this.dateFrom = localDay()
      this.dateTo = localDay()
      this.viewerEvents = []
      this.viewerKey += 1
      this.loadViewerEvents()
    },
    numeric(key, fallback) {
      const n = Number(this.params[key])
      return Number.isFinite(n) ? n : fallback
    },
    async saveParam(key, value) {
      this.savingKey = key
      try {
        const payload = await api.updateParam({ key, value })
        this.params = { ...this.params, ...(payload?.updated || {}), [key]: value }
        showSnackbar(payload?.message || "Sentry setting saved.")
      } catch (e) {
        showSnackbar(e?.data?.error || e?.message || `Failed to update ${key}.`, "error")
      } finally {
        this.savingKey = ""
      }
    },
    async sendTestEvent() {
      if (this.testBusy) return
      this.testBusy = true
      try {
        await api.postAction("/api/sentry/test")
        showSnackbar("Test capture started. The images will appear here shortly.")
      } catch (e) {
        showSnackbar(e?.data?.error || "Sentry test failed.", "error")
      } finally {
        this.testBusy = false
      }
    },
    async viewLive() {
      if (this.liveBusy) return
      this.liveBusy = true
      try {
        this.liveCapture = await api.getSentryLive()
        showSnackbar("Live camera snapshot captured.")
      } catch (e) {
        showSnackbar(e?.message || "Live camera capture failed.", "error")
      } finally {
        this.liveBusy = false
      }
    },
    // ISO instants from the backend are UTC; show them in the viewer's local time.
    formatWhen(value) {
      const ms = Date.parse(value || "")
      return Number.isFinite(ms) ? new Date(ms).toLocaleString() : String(value || "")
    },
    kindLabel(kind) {
      return String(kind || "event").toUpperCase()
    },
    kindColor(kind) {
      const k = String(kind || "")
      if (k === "alarm") return "var(--error)"
      if (k === "warning") return "var(--warning)"
      if (k === "selfie") return "var(--primary)"
      return "var(--text-muted)"
    },
    liveImageUrl(url) {
      const cacheKey = encodeURIComponent(this.liveCapture?.capturedAt || "")
      return cacheKey ? `${url}?t=${cacheKey}` : url
    },
    openImage(src, alt) {
      if (!src) return
      this.selectedImage = { src: String(src), alt: String(alt || "Sentry capture") }
    },
    closeImage() {
      this.selectedImage = null
    },
    async enablePush() {
      if (this.pushBusy) return
      this.pushBusy = true
      try {
        if (typeof Notification === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
          showSnackbar("This browser does not support Web Push notifications.", "error")
          return
        }
        if (!window.isSecureContext) {
          showSnackbar("Browser notifications require Galaxy over HTTPS.", "error")
          return
        }
        const permission = await Notification.requestPermission()
        if (permission !== "granted") {
          showSnackbar("Browser notification permission was not granted.", "error")
          return
        }
        const config = await api.getSentryPushConfig()
        if (!config?.enabled || !config?.publicKey) {
          showSnackbar(config?.error || "Galaxy Web Push is unavailable.", "error")
          return
        }
        await navigator.serviceWorker.register("/service-worker.js", { scope: "/" })
        const registration = await navigator.serviceWorker.ready
        let subscription = await registration.pushManager.getSubscription()
        if (!subscription) {
          subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: b64ToBytes(config.publicKey),
          })
        }
        const body = typeof subscription.toJSON === "function"
          ? subscription.toJSON()
          : {
            endpoint: subscription.endpoint,
            expirationTime: subscription.expirationTime,
            keys: {
              p256dh: subscription.getKey ? btoa(String.fromCharCode(...new Uint8Array(subscription.getKey("p256dh")))) : "",
              auth: subscription.getKey ? btoa(String.fromCharCode(...new Uint8Array(subscription.getKey("auth")))) : "",
            },
          }
        await api.sentryPushSubscribe(body)
        showSnackbar("Browser notifications enabled for this device.")
      } catch (e) {
        showSnackbar(e?.message || "Could not enable browser notifications.", "error")
      } finally {
        this.pushBusy = false
      }
    },
    async sendTestNotification() {
      if (this.pushBusy) return
      this.pushBusy = true
      try {
        const payload = await api.postAction("/api/sentry/test-notification")
        const channels = Object.entries(payload?.channels || {})
          .filter(([, configured]) => configured)
          .map(([channel]) => channel === "webPush" ? "browser" : channel)
        showSnackbar(channels.length ? `Test notification sent through ${channels.join(", ")}.` : "Test notification sent.")
      } catch (e) {
        showSnackbar(e?.message || "Could not send the test notification.", "error")
      } finally {
        this.pushBusy = false
      }
    },
    async deleteEvent(eventId) {
      eventId = String(eventId || "")
      if (!eventId || this.deleteBusy) return
      const matched = this.viewerEvents.find((e) => String(e?.eventId || "") === eventId)
        || (String(this.event?.eventId || "") === eventId ? this.event : null)
      const hasImages = Array.isArray(matched?.imageUrls) && matched.imageUrls.length > 0
      if (!(await GalaxyConfirm({
        title: "Delete Sentry event?",
        message: hasImages
          ? "Delete this Sentry event and its camera images? This cannot be undone."
          : "Delete this Sentry event? This cannot be undone.",
        confirmLabel: "Delete",
        danger: true,
      }))) return
      this.deleteBusy = true
      try {
        await api.deleteSentryEvent(eventId)
        this.viewerEvents = this.viewerEvents.filter((e) => String(e?.eventId || "") !== eventId)
        if (String(this.event?.eventId || "") === eventId) {
          this.event = {}
          this.loadStatus()
        }
        showSnackbar("Sentry event deleted.")
      } catch (e) {
        showSnackbar(e?.data?.error || e?.message || "Sentry event deletion failed.", "error")
      } finally {
        this.deleteBusy = false
      }
    },
  },
  template: `
    <div>
      <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap;">
        <div>
          <h2 style="margin-top:0; margin-bottom:4px;">Sentry Mode</h2>
          <p style="margin:0; color:var(--text-muted);">Monitor the parked vehicle and review movement captures.</p>
        </div>
        <span class="gx-chip">{{ statusText }}</span>
      </div>

      <GalaxySection title="Configuration" icon="bi-sliders" :collapsible="false">
        <div style="padding: var(--sp-3);">
          <div v-if="loading" class="gx-loading">Loading Sentry settings...</div>
          <template v-else>
            <div class="gx-row" style="border-top:none;">
              <div class="gx-row__info">
                <span class="gx-row__label"><strong>Enable Sentry Mode</strong></span>
                <span class="gx-row__desc">Detect sustained movement while the vehicle is parked.</span>
              </div>
              <label class="gx-switch">
                <input type="checkbox" :checked="!!params.SentryModeEnabled" :disabled="savingKey === 'SentryModeEnabled'"
                  @change="saveParam('SentryModeEnabled', $event.target.checked)" />
                <span class="gx-switch__track"></span>
                <span class="gx-switch__thumb"></span>
              </label>
            </div>

            <div style="padding: var(--sp-2) 0;">
              <div class="gx-row__label">Webhook URL</div>
              <input class="gx-field gx-field--full" type="url" :value="params.SentryModeWebhook || ''"
                placeholder="https://..." :disabled="savingKey === 'SentryModeWebhook'"
                @change="saveParam('SentryModeWebhook', $event.target.value.trim())" />
              <div class="gx-row__desc">Optional Discord-compatible or custom webhook.</div>
            </div>

            <div style="padding: var(--sp-2) 0;">
              <div class="gx-row__label">ntfy URL</div>
              <input class="gx-field gx-field--full" type="url" :value="params.SentryModeNtfyUrl || ''"
                placeholder="https://ntfy.sh/..." :disabled="savingKey === 'SentryModeNtfyUrl'"
                @change="saveParam('SentryModeNtfyUrl', $event.target.value.trim())" />
              <div class="gx-row__desc">Optional ntfy topic URL for phone notifications.</div>
            </div>

            <div class="gx-row" style="border-top:none; align-items:stretch; flex-direction:column; gap:var(--sp-2);">
              <div class="gx-row__label"><strong>Motion sensitivity</strong></div>
              <div class="gx-slider-row">
                <span class="gx-row__value">{{ numeric('SentryModeSensitivity', 0.04).toFixed(3) }}</span>
                <input type="range" class="gx-slider" min="0.005" max="1" step="0.001" :value="numeric('SentryModeSensitivity', 0.04)"
                  :disabled="savingKey === 'SentryModeSensitivity'" aria-label="Motion sensitivity"
                  @change="saveParam('SentryModeSensitivity', Number($event.target.value))" />
              </div>
              <div class="gx-row__desc">Lower values detect smaller acceleration changes. Default: 0.04.</div>
            </div>

            <div class="gx-row" style="border-top:none; align-items:stretch; flex-direction:column; gap:var(--sp-2);">
              <div class="gx-row__label"><strong>Warning persistence</strong></div>
              <div class="gx-slider-row">
                <span class="gx-row__value">{{ numeric('SentryModeWarningTime', 1).toFixed(1) }} seconds</span>
                <input type="range" class="gx-slider" min="0.1" max="10" step="0.1" :value="numeric('SentryModeWarningTime', 1)"
                  :disabled="savingKey === 'SentryModeWarningTime'" aria-label="Warning persistence"
                  @change="saveParam('SentryModeWarningTime', Number($event.target.value))" />
              </div>
              <div class="gx-row__desc">How long movement must continue before the first alert. Default: 1 second.</div>
            </div>

            <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:var(--sp-2);">
              <button type="button" class="gx-btn" :disabled="pushBusy" @click="enablePush">
                <i class="bi bi-bell"></i> {{ pushBusy ? 'Enabling...' : 'Enable browser notifications' }}
              </button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="pushBusy" @click="sendTestNotification">
                {{ pushBusy ? 'Sending...' : 'Send test notification' }}
              </button>
            </div>
            <p class="gx-note">The test notification uses every configured channel: browser Web Push, ntfy, and webhook.</p>
            <p class="gx-note">iPhone users: add Galaxy to your Home Screen as a web app before enabling notifications.</p>
          </template>
        </div>
      </GalaxySection>

      <GalaxySection title="Live view" icon="bi-camera" :collapsible="false">
        <div style="padding: var(--sp-3);">
          <div class="gx-row" style="border-top:none;">
            <span class="gx-row__label">Capture one still from both cameras while parked.</span>
            <span class="gx-row__value">
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="liveBusy" @click="viewLive">
                <i class="bi bi-camera"></i> {{ liveBusy ? 'Capturing...' : 'View live' }}
              </button>
            </span>
          </div>
          <template v-if="Array.isArray(liveCapture.imageUrls) && liveCapture.imageUrls.length">
            <p class="gx-row__desc">Captured {{ liveCapture.capturedAt ? formatWhen(liveCapture.capturedAt) : 'just now' }}.</p>
            <div class="gx-sentry-images">
              <button v-for="(u, i) in liveCapture.imageUrls" :key="u + i" type="button" class="gx-sentry-image-button"
                :aria-label="'Open Live Sentry camera ' + (i + 1)" @click="openImage(liveImageUrl(u), 'Live Sentry camera ' + (i + 1))">
                <img :src="liveImageUrl(u)" :alt="'Live Sentry camera ' + (i + 1)" />
              </button>
            </div>
          </template>
          <p v-else class="gx-empty">No live snapshot captured yet.</p>
        </div>
      </GalaxySection>

      <GalaxySection title="Latest Event" icon="bi-shield-exclamation" :collapsible="false">
        <div style="padding: var(--sp-3);">
          <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:var(--sp-2);">
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="viewerBusy" @click="toggleHistory">
              {{ viewerBusy && !historyVisible ? 'Loading...' : (historyVisible ? 'Hide history' : 'View history') }}
            </button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="testBusy" @click="sendTestEvent">
              {{ testBusy ? 'Capturing...' : 'Send test capture' }}
            </button>
            <button v-if="hasEvent" type="button" class="gx-btn gx-btn--danger" :disabled="deleteBusy" @click="deleteEvent(event.eventId)">
              {{ deleteBusy ? 'Deleting...' : 'Delete event' }}
            </button>
          </div>
          <p class="gx-row__desc">The latest event refreshes every five seconds. History updates when you refresh it.</p>

          <template v-if="hasEvent">
            <div style="display:flex; align-items:center; gap:8px; margin-top:var(--sp-2);">
              <span class="gx-chip" :style="{ color: kindColor(event.kind) }">{{ kindLabel(event.kind) }}</span>
              <span class="gx-row__desc" style="margin:0;">{{ formatWhen(event.detectedAt) }}</span>
            </div>
            <p style="margin:8px 0;"><strong>{{ event.message || 'Movement detected while parked.' }}</strong></p>
            <template v-if="Array.isArray(event.imageUrls) && event.imageUrls.length">
              <div class="gx-sentry-images">
                <button v-for="(u, i) in event.imageUrls" :key="u + i" type="button" class="gx-sentry-image-button"
                  :aria-label="'Open Sentry capture ' + (i + 1)" @click="openImage(u, 'Sentry capture ' + (i + 1))">
                  <img :src="u" :alt="'Sentry capture ' + (i + 1)" loading="lazy" />
                </button>
              </div>
            </template>
            <p v-else-if="event.kind === 'power_off'" class="gx-empty">Power-off alerts do not include camera captures because the device is shutting down.</p>
            <p v-else class="gx-empty">No camera images were available for this event.</p>
          </template>
          <p v-else-if="!loading" class="gx-empty">No Sentry events recorded yet.</p>

          <div v-if="historyVisible" style="margin-top:var(--sp-3); border-top:1px solid var(--border-color, rgba(255,255,255,.08)); padding-top:var(--sp-2);">
            <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:flex-end; margin-bottom:var(--sp-2);">
              <label style="flex:1 1 140px;">
                <div class="gx-row__desc" style="margin:0 0 4px;">From</div>
                <input class="gx-field gx-field--full" type="date" :value="dateFrom" :max="dateTo || null"
                  @change="dateFrom = $event.target.value; applyFilter()" />
              </label>
              <label style="flex:1 1 140px;">
                <div class="gx-row__desc" style="margin:0 0 4px;">To</div>
                <input class="gx-field gx-field--full" type="date" :value="dateTo" :min="dateFrom || null"
                  @change="dateTo = $event.target.value; applyFilter()" />
              </label>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:flex-end; margin-bottom:var(--sp-2);">
              <label style="flex:1 1 140px;">
                <div class="gx-row__desc" style="margin:0 0 4px;">Preset</div>
                <GalaxySelect class="gx-field gx-field--full" aria-label="Date range preset" :value="activePreset || 'custom'" :disabled="viewerBusy" @change="onPresetChange($event.target.value)">
                  <option value="today">Today</option>
                  <option value="yesterday">Yesterday</option>
                  <option value="week">Last 7 days</option>
                  <option value="all">All</option>
                  <option v-if="!activePreset" value="custom" disabled>Custom range</option>
                </GalaxySelect>
              </label>
              <button v-if="viewerEvents.length" type="button" class="gx-btn gx-btn--danger" :disabled="deleteBusy || viewerBusy" @click="deleteAllHistory">
                <i class="bi bi-trash"></i> {{ deleteBusy ? 'Deleting...' : (filterActive ? 'Delete matching' : 'Delete all') }}
              </button>
            </div>
            <button v-if="newEvents" type="button" class="gx-btn gx-btn--tonal" :disabled="viewerBusy" style="margin-bottom:var(--sp-2);" @click="refreshAll">New event - refresh</button>
            <div v-if="viewerBusy && !viewerEvents.length" class="gx-loading">Loading Sentry events...</div>
            <template v-else-if="viewerEvents.length">
              <SentryScrubber v-if="captureEvents.length" :key="viewerKey" :events="viewerEvents" :delete-busy="deleteBusy" v-model:camera="viewerCamera" @delete="deleteEvent" @close="toggleHistory" @open-image="openImage">
                <template #actions>
                  <button type="button" class="gx-btn gx-btn--tonal" :disabled="timelapseBusy || deleteBusy"
                    title="Create a timelapse video of the events in the selected date range" aria-label="Create timelapse video" @click="makeTimelapse">
                    <i class="bi bi-film"></i> {{ timelapseBusy ? 'Encoding...' : 'Timelapse video' }}
                  </button>
                </template>
              </SentryScrubber>
              <p v-else class="gx-empty">No captures in this range.</p>
              <div v-if="alertEvents.length" data-testid="sentry-alerts" style="margin-top:var(--sp-2);">
                <div class="gx-row__desc" style="margin:0 0 4px;">Alerts without photos</div>
                <div v-for="alert in alertEvents" :key="alert.eventId" style="display:flex; align-items:center; gap:8px; padding:6px 0; border-top:1px solid var(--border-color, rgba(255,255,255,.08));">
                  <span class="gx-chip" :style="{ color: kindColor(alert.kind) }">{{ kindLabel(alert.kind) }}</span>
                  <div style="flex:1; min-width:0;">
                    <div>{{ alert.message || 'Sentry alert' }}</div>
                    <div class="gx-row__desc" style="margin:0;">{{ formatWhen(alert.detectedAt) }}</div>
                  </div>
                  <button type="button" class="gx-btn gx-btn--danger" :disabled="deleteBusy" @click="deleteEvent(alert.eventId)">
                    <i class="bi bi-trash"></i> Delete
                  </button>
                </div>
              </div>
            </template>
            <div v-else>
              <p class="gx-empty">{{ filterActive ? 'No Sentry events in this date range.' : 'No retained Sentry events.' }}</p>
            </div>
          </div>
        </div>
      </GalaxySection>

      <GalaxySheet :open="!!selectedImage" :title="selectedImage?.alt || ''" icon="bi-camera"
        scrim-class="gx-scrim--image-viewer" sheet-class="gx-image-viewer" @close="closeImage">
        <img class="gx-image-viewer__image" :src="selectedImage?.src" :alt="selectedImage?.alt || ''" />
      </GalaxySheet>
    </div>
  `,
}
