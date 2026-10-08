import { GxNotice } from "./notice.js"
export const channels = ["webPush", "discord", "webhook", "ntfy"]
export const labels = { webPush: "Browser push", discord: "Discord", webhook: "General webhook", ntfy: "ntfy" }

export function validNotifications(value) {
  return value?.schemaVersion === 1 && typeof value.queueFull === "boolean" &&
    Number.isInteger(value.subscriptionCount) && value.subscriptionCount >= 0 && value.subscriptionCount <= 16 &&
    Array.isArray(value.subscriptions) && value.subscriptions.length === value.subscriptionCount &&
    value.subscriptions.every(s => typeof s?.id === "string" && /^[0-9a-f]{32}$/.test(s.id) && Object.keys(s).length === 1) &&
    typeof value.deliverySemantics === "string" && value.deliverySemantics.length < 256 &&
    (value.applicationServerKey === undefined || typeof value.applicationServerKey === "string" && /^[A-Za-z0-9_-]{87}$/.test(value.applicationServerKey)) &&
    channels.every(name => {
      const c = value.channels?.[name]
      return typeof c?.enabled === "boolean" && typeof c.configured === "boolean" && Number.isInteger(c.pending) && c.pending >= 0 && c.pending <= 512 &&
        ["idle", "queued", "sending", "sent", "failed", "cancelled"].includes(c.lastState) &&
        ["", "http", "expired", "timeout", "transport", "delivery_unknown", "stale"].includes(c.lastError)
    })
}

export class NotificationClient {
  constructor({ publish, unauthorized, fetcher = (...args) => fetch(...args) }) {
    this.publish = publish; this.unauthorized = unauthorized; this.fetcher = fetcher
    this.revision = 0; this.controller = null; this.pending = false; this.hasStatus = false; this.timer = null
  }
  stop() { this.revision++; this.controller?.abort(); this.controller = null; this.pending = false; clearTimeout(this.timer); this.timer = null }
  async run(payload = null) {
    this.stop()
    const revision = this.revision
    this.controller = new AbortController()
    this.pending = true
    const foreground = payload !== null || !this.hasStatus
    if (foreground) this.publish({ notificationBusy: true, notificationError: "" })
    this.timer = setTimeout(() => {
      if (revision !== this.revision) return
      this.stop()
      this.publish({ notificationBusy: false, notificationError: "Notification request timed out. Refresh status before repeating a test." })
    }, 4000)
    try {
      const response = await this.fetcher("./api/sentry/notifications", { credentials: "same-origin", cache: "no-store",
        signal: this.controller.signal, ...(payload === null ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }) })
      if (revision !== this.revision) return false
      if (response.status === 401) { this.unauthorized(); return false }
      const value = await response.json()
      if (revision !== this.revision) return false
      if (!response.ok) throw new Error(value?.error || "Sentry notifications are unavailable.")
      if (!validNotifications(value)) throw new Error("Notification status is unavailable.")
      this.hasStatus = true
      this.publish({ notifications: value, notificationBusy: false, notificationError: "" })
      return true
    } catch (error) {
      if (revision === this.revision && error.name !== "AbortError") this.publish({ notificationBusy: false, notificationError: error.message || "Notification request failed." })
      return false
    } finally {
      if (revision === this.revision) { clearTimeout(this.timer); this.timer = null; this.pending = false; if (foreground) this.publish({ notificationBusy: false }) }
    }
  }
}

export const SentryNotifications = {
  components: { GxNotice },
  name: "SentryNotifications",
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ channels, labels, notifications: null, notificationBusy: false, notificationError: "",
    drafts: Object.fromEntries(channels.map(name => [name, { url: "", token: "" }])) }),
  created() { this.client = new NotificationClient({ publish: update => Object.assign(this.$data, update), unauthorized: this.unauthorized }) },
  mounted() {
    this.visibility = () => { if (document.hidden) { this.client.stop(); clearInterval(this.poll) } else this.start() }
    document.addEventListener("visibilitychange", this.visibility)
    this.start()
  },
  beforeUnmount() { this.client.stop(); clearInterval(this.poll); document.removeEventListener("visibilitychange", this.visibility) },
  methods: {
    start() {
      clearInterval(this.poll)
      if (this.mode !== "local" || document.hidden) return
      this.client.run()
      this.poll = setInterval(() => { if (!this.notificationBusy && !this.client.pending) this.client.run() }, 5000)
    },
    async save(name, enabled) {
      const draft = this.drafts[name]
      if (await this.client.run({ action: "configure", channel: name, enabled, url: draft.url, token: draft.token })) {
        draft.url = ""; draft.token = ""
      }
    },
    test(name) { return this.client.run({ action: "test", channel: name }) },
    async forget(name) { if (await this.client.run({ action: "forget", channel: name })) { this.drafts[name].url = ""; this.drafts[name].token = "" } },
    remove(id) { return this.client.run({ action: "unsubscribe", id }) },
    async subscribe() {
      if (!isSecureContext || !("serviceWorker" in navigator) || !("PushManager" in window)) {
        this.notificationError = "Browser push needs HTTPS and a browser with Push API support."
        return
      }
      try {
        const permission = await Notification.requestPermission()
        if (permission !== "granted") throw new Error("Allow browser notifications to subscribe.")
        if (!await this.client.run({ action: "pushKey" })) return
        const key = this.notifications.applicationServerKey
        const bytes = Uint8Array.from(atob(key.replace(/-/g, "+").replace(/_/g, "/") + "="), c => c.charCodeAt(0))
        const registration = await navigator.serviceWorker.register("./sentry-push-worker.js")
        await navigator.serviceWorker.ready
        const subscription = await registration.pushManager.getSubscription() || await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: bytes })
        const value = subscription.toJSON()
        if (!await this.client.run({ action: "subscribe", subscription: { endpoint: value.endpoint, keys: value.keys } })) return
        await this.save("webPush", true)
      } catch (error) { this.notificationError = error.message || "Browser push subscription failed." }
    },
  },
  template: `
    <section class="gx-card gx-home__card" aria-label="Sentry notifications">
      <h2>Notifications</h2>
      <p class="gx-note">Receive new locally recorded motion events. Notification channels work independently.</p>
      <p v-if="mode !== 'local'">Notification configuration is available on your connected device.</p>
      <template v-else>
        <GxNotice tone="danger" v-if="notificationError">{{ notificationError }}</GxNotice>
        <p v-if="notificationBusy" role="status">Updating notifications…</p>
        <GxNotice tone="danger" v-if="notifications?.queueFull">The notification queue is full. Some events could not be queued.</GxNotice>
        <template v-if="notifications">
          <p class="gx-note">{{ notifications.deliverySemantics }}</p>
          <section v-for="name in channels" :key="name" class="gx-card gx-sentry-channel">
            <h3>{{ labels[name] }}</h3>
            <p>{{ notifications.channels[name].enabled ? 'Enabled' : 'Disabled' }} · {{ notifications.channels[name].configured ? 'Configured' : 'Not configured' }}</p>
            <p role="status">Delivery: {{ notifications.channels[name].lastState }} · Pending: {{ notifications.channels[name].pending }}</p>
            <GxNotice tone="danger" v-if="notifications.channels[name].lastError">Delivery status: {{ notifications.channels[name].lastError.replaceAll('_', ' ') }}</GxNotice>
            <div v-if="name !== 'webPush'" class="gx-sentry-channel__fields">
              <label>HTTPS URL <input v-model="drafts[name].url" class="gx-field" type="password" autocomplete="off" placeholder="Leave blank to keep saved URL"></label>
              <label>Bearer token (optional) <input v-model="drafts[name].token" class="gx-field" type="password" autocomplete="off" placeholder="Leave blank to keep saved token"></label>
            </div>
            <div class="gx-sentry-channel__actions gx-actions">
            <button v-if="name !== 'webPush'" class="gx-btn gx-btn--tonal" type="button" :disabled="notificationBusy" @click="save(name, true)">Save and enable</button>
            <button v-else class="gx-btn gx-btn--tonal" type="button" :disabled="notificationBusy" @click="subscribe">Subscribe this browser</button>
            <button class="gx-btn gx-btn--tonal" type="button" :disabled="notificationBusy || !notifications.channels[name].configured" @click="save(name, !notifications.channels[name].enabled)">{{ notifications.channels[name].enabled ? 'Disable' : 'Enable' }}</button>
            <button class="gx-btn gx-btn--tonal" type="button" :disabled="notificationBusy || !notifications.channels[name].enabled || !notifications.channels[name].configured" @click="test(name)">Send test</button>
            <button class="gx-btn gx-btn--tonal" type="button" :disabled="notificationBusy" @click="forget(name)">Forget configuration</button>
            </div>
          </section>
          <p v-if="notifications.subscriptionCount">Subscribed browsers: {{ notifications.subscriptionCount }}</p>
          <button v-for="(subscription, index) in notifications.subscriptions" :key="subscription.id" class="gx-btn gx-btn--tonal" type="button" :disabled="notificationBusy" @click="remove(subscription.id)">Remove browser {{ index + 1 }}</button>
        </template>
      </template>
    </section>`,
}
