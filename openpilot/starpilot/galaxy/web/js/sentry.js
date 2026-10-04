import { SentryNotifications } from "./sentry-notifications.js"
import { LocalHistoryFeed } from "./record-history.js"

// Historical motion records and independently configured notifications.
const ID = /^[0-9a-f]{32}$/

export function validSentryEvents(value) {
  if (value?.schemaVersion !== 1 || value.source !== "local" || typeof value.scanIncomplete !== "boolean" ||
      value.capacity !== 512 || !Array.isArray(value.events) || value.events.length > 512) return false
  const seen = new Set()
  return value.events.every((event) => {
    if (event === null || typeof event !== "object" || Object.keys(event).some((key) => !["eventId", "kind", "systemTimeMs", "images"].includes(key)) ||
        (event.images !== undefined && (!Array.isArray(event.images) || event.images.length > 2 ||
          new Set(event.images).size !== event.images.length || event.images.some((camera) => !["wide", "cabin"].includes(camera)))) ||
        typeof event.eventId !== "string" || !ID.test(event.eventId) || seen.has(event.eventId) ||
        !["warning", "alarm", "selfie"].includes(event.kind) || !Number.isSafeInteger(event.systemTimeMs) ||
        event.systemTimeMs <= 0 || event.systemTimeMs > 8_640_000_000_000_000) return false
    seen.add(event.eventId)
    return true
  })
}

export const systemTime = (milliseconds) => Number.isSafeInteger(milliseconds) && milliseconds > 0 && milliseconds <= 8_640_000_000_000_000
  ? new Date(milliseconds).toLocaleString() : "Unavailable"

export class SentryEventsFeed extends LocalHistoryFeed {
  static endpoint = "./api/sentry/events"
  static valid = validSentryEvents
  static subject = "local motion events"
  static unavailable = "Local motion events are unavailable."
  static invalid = "Local motion records are unavailable."
}

export const SentryEventsPage = {
  name: "SentryEventsPage",
  components: { SentryNotifications },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true },
    go: { type: Function, required: true } },
  data: () => ({ status: "idle", data: null, error: "" }),
  created() { this.feed = new SentryEventsFeed({ publish: (update) => Object.assign(this.$data, update), unauthorized: this.unauthorized }) },
  mounted() {
    this.visibility = () => { if (document.hidden) this.feed.stop(); else if (this.mode === "local") this.feed.start() }
    document.addEventListener("visibilitychange", this.visibility)
    if (this.mode === "local" && !document.hidden) this.feed.start()
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibility); this.feed.stop() },
  methods: { systemTime },
  template: `
    <div class="gx-view gx-home" aria-label="Sentry motion events">
      <div class="gx-home__hero"><div><h1>Motion Events</h1>
        <p class="gx-note">Local motion records only · System clock times may be inaccurate</p></div>
        </div>

      <SentryNotifications :mode="mode" :unauthorized="unauthorized" />
      <p v-if="mode !== 'local'" class="gx-card gx-message">Local motion records are unavailable in preview.</p>
      <template v-else>
        <button type="button" class="gx-btn gx-btn--tonal" :disabled="status === 'loading'" @click="feed.load()">Refresh events</button>
        <p v-if="status === 'loading'" role="status">Reading local motion events…</p>
        <p v-if="status === 'unavailable'" role="alert">{{ error }}</p>
        <template v-if="status === 'ready' && data">
          <p v-if="data.scanIncomplete" role="status">This scan was incomplete. More local motion events may exist.</p>
          <p v-if="!data.events.length" role="status">No local motion events found in this scan.</p>
          <section v-for="event in data.events" :key="event.eventId" class="gx-card gx-home__card">
            <h2>{{ event.kind === 'selfie' ? 'Selfie' : event.kind === 'alarm' ? 'Alarm' : 'Warning' }}</h2>
            <p>System time: {{ systemTime(event.systemTimeMs) }}</p>
            <small>Event ID: {{ event.eventId }}</small>
            <img v-for="camera in (event.images || [])" :key="camera" :src="'./api/sentry/image/' + event.eventId + '/' + camera" :alt="camera + ' camera at motion event'" style="max-width:100%;height:auto" />
          </section>
        </template>
      </template>
    </div>`,
}
