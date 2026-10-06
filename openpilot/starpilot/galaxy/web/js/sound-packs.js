import { GxNotice } from "./notice.js"
import { connectionError } from "./polling.js"
import { reactive } from "../vendor/vue/vue.esm-browser.js"

const RUNNING = new Set(["downloading", "verifying"])

export class SoundPacksFeed {
  constructor({ publish, installed = () => {}, unauthorized = () => {},
                fetcher = (...args) => fetch(...args), later = (fn, ms) => setTimeout(fn, ms),
                cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, installed, unauthorized, fetcher, later, cancelTimer })
    this.active = false
    this.generation = 0
    this.request = null
    this.timeout = null
    this.pollTimer = null
    this.snapshot = null
    this.seenComplete = new Set()
    this.busy = false
    this.blocked = false
    this.error = ""
  }

  stop() {
    this.active = false
    this.generation++
    this.request?.abort()
    if (this.timeout !== null) this.cancelTimer(this.timeout)
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    this.request = this.timeout = this.pollTimer = null
    this.busy = false
    this.blocked = false
    this.snapshot = null
    this.publish({ status: "idle", snapshot: null, busy: false, error: "" })
  }

  start() {
    this.stop()
    this.active = true
    return this.refresh()
  }

  async run(path, body = null) {
    if (!this.active || this.request) return
    const generation = ++this.generation
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    this.pollTimer = null
    const request = new AbortController()
    this.request = request
    this.busy = body !== null
    this.publish({ status: this.snapshot ? "ready" : this.error ? "unavailable" : "loading", snapshot: this.snapshot, busy: this.busy, error: this.error })
    this.timeout = this.later(() => {
      if (!this.active || generation !== this.generation || this.request !== request) return
      request.abort()
      this.generation++
      this.request = this.timeout = null
      this.busy = false
      this.blocked = true
      this.publish({ status: this.snapshot ? "ready" : "unavailable", snapshot: this.snapshot, busy: false,
        error: this.error = body ? "The request timed out. Its result is unknown; checking automatically…" :
          "The sound catalog timed out. Reconnecting automatically…" })
      this.pollTimer = this.later(() => { this.pollTimer = null; this.refresh() }, 5000)
    }, 4000)
    try {
      const response = await this.fetcher(path, body === null
        ? { credentials: "same-origin", cache: "no-store", signal: request.signal }
        : { method: "POST", credentials: "same-origin", cache: "no-store", signal: request.signal,
            headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      if (!this.active || generation !== this.generation || request.signal.aborted) return
      const payload = await response.json().catch(() => null)
      if (!this.active || generation !== this.generation || request.signal.aborted) return
      if (response.status === 401 || (response.status === 503 &&
          ["access_unavailable", "setup_required"].includes(payload?.code))) {
        this.stop()
        this.unauthorized()
        return
      }
      if (!response.ok) throw new Error(payload?.error || payload?.message || "Sound request failed.")
      if (!payload || !Array.isArray(payload.packs) || typeof payload.parked !== "boolean" ||
          (payload.job !== null && typeof payload.job !== "object")) throw new Error("Sound catalog is unavailable.")
      this.snapshot = payload
      this.blocked = false
      this.error = ""
      this.publish({ status: "ready", snapshot: payload, busy: false, error: "" })
      if (payload.job?.state === "complete" && payload.job.id != null && !this.seenComplete.has(payload.job.id)) {
        this.seenComplete.add(payload.job.id)
        this.installed(payload.job.pack)
      }
      this.pollTimer = this.later(() => {
        this.pollTimer = null
        this.refresh()
      }, RUNNING.has(payload.job?.state) ? 1000 : 5000)
    } catch (error) {
      if (this.active && generation === this.generation && !request.signal.aborted) {
        this.blocked = true
        this.publish({ status: this.snapshot ? "ready" : "unavailable", snapshot: this.snapshot, busy: false,
          error: this.error = connectionError(error) })
      }
    } finally {
      if (this.request === request) {
        if (this.timeout !== null) this.cancelTimer(this.timeout)
        this.request = this.timeout = null
        this.busy = false
        if (this.active && this.pollTimer === null) this.pollTimer = this.later(() => { this.pollTimer = null; this.refresh() }, 5000)
      }
    }
  }

  refresh() { return this.run("./api/sounds") }

  download(pack) {
    if (!this.active || this.busy || this.blocked || !this.snapshot?.parked || !Array.isArray(this.snapshot.packs) ||
        !this.snapshot.packs.some((item) => item.id === pack && item.installed === false) ||
        RUNNING.has(this.snapshot.job?.state)) return
    return this.run("./api/sounds/download", { pack })
  }

  cancel() {
    const job = this.snapshot?.job
    if (!this.active || this.busy || this.blocked || !this.snapshot?.parked || !RUNNING.has(job?.state) || job.id == null) return
    return this.run("./api/sounds/cancel", { job: job.id })
  }
}

export const SoundPacks = {
  components: { GxNotice },
  props: { unauthorized: { type: Function, required: true }, disabled: { type: Boolean, default: false } },
  emits: ["installed"],
  setup(props, { emit }) {
    const state = reactive({ status: "idle", snapshot: null, busy: false, error: "" })
    const feed = new SoundPacksFeed({ publish: (update) => Object.assign(state, update),
      installed: (pack) => emit("installed", pack), unauthorized: props.unauthorized })
    return { state, feed }
  },
  computed: {
    job() { return this.state.snapshot?.job },
    running() { return RUNNING.has(this.job?.state) },
    progress() {
      const bytes = Number(this.job?.bytes), total = Number(this.job?.total)
      return Number.isFinite(bytes) && Number.isFinite(total) && total > 0
        ? Math.min(100, Math.max(0, Math.round(bytes / total * 100))) : null
    },
  },
  mounted() { this.feed.start() },
  beforeUnmount() { this.feed.stop() },
  methods: {
    canDownload(pack) { return !this.disabled && !this.state.busy && !this.state.error && this.state.status === "ready" &&
      this.state.snapshot?.parked === true && !this.running && pack.installed === false },
  },
  template: `
    <section class="gx-card gx-settings__section" aria-label="Sound pack catalog">
      <div class="gx-section__header"><i class="bi bi-music-note-list" aria-hidden="true"></i>
        <span class="gx-section__title">Sound pack catalog</span>
        <span v-if="state.snapshot && !state.snapshot.parked" class="gx-note gx-settings__hint">Park the vehicle to download sound packs.</span>

      </div>
      <div class="gx-settings__grid" style="padding: 16px">
        <p v-if="state.status === 'loading'" role="status">Loading sound packs…</p>
        <GxNotice tone="danger" v-else-if="state.status === 'unavailable'">Sound packs are unavailable.</GxNotice>
        <GxNotice tone="danger" v-if="state.error">{{ state.error }}</GxNotice>
        <p v-if="state.snapshot && !state.snapshot.packs.length" class="gx-note">No sound packs are available.</p>
        <div v-for="pack in state.snapshot?.packs || []" :key="pack.id" class="gx-card gx-settings__row">
          <strong>{{ pack.name }}</strong>
          <div class="gx-settings__controls">
            <span v-if="pack.installed" class="gx-chip">Installed</span>
            <button v-else type="button" class="gx-btn gx-btn--tonal" :disabled="!canDownload(pack)" @click="feed.download(pack.id)">Download</button>
          </div>
        </div>
        <div v-if="job" role="status">
          <p v-if="running">{{ job.state === 'verifying' ? 'Verifying' : 'Downloading' }} {{ state.snapshot.packs.find(pack => pack.id === job.pack)?.name || 'sound pack' }}<span v-if="progress !== null"> · {{ progress }}%</span></p>
          <p v-else-if="job.state === 'complete'">Sound pack installed. Choose it from the pack selector above when ready.</p>
          <p v-else-if="job.state === 'cancelled'">Download cancelled.</p>
          <GxNotice tone="danger" v-else-if="job.state === 'failed'">Download failed: {{ job.error || 'Unknown error.' }}</GxNotice>
          <progress v-if="running && progress !== null" :value="progress" max="100" :aria-label="'Sound pack download ' + progress + '%'">{{ progress }}%</progress>
          <button v-if="running" type="button" class="gx-btn gx-btn--tonal" :disabled="disabled || state.busy || !!state.error || !state.snapshot.parked" @click="feed.cancel()">Cancel download</button>
        </div>
      </div>
    </section>`,
}
