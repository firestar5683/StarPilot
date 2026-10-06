import { SnapshotFeed } from "./snapshot-feed.js"

const STATES = Object.freeze({ parked: "Parked", driving: "Driving", standby: "Standby" })

export const validDeviceState = (value) => value &&
  (value.state === null || Object.hasOwn(STATES, value.state)) &&
  Number.isFinite(value.maxAgeMs) && value.maxAgeMs >= (value.state === null ? 0 : 1) && value.maxAgeMs <= 3000

// Reuse the authenticated request/deadline boundary; this lightweight endpoint
// does not scan processes or start any device services.
export class DeviceStateFeed extends SnapshotFeed {
  static interval = 0
  static endpoint = "./api/device/state"
  static valid = validDeviceState
  static subject = "device state"
  static unavailable = "Device state is unavailable."
  static invalid = "Device state is unavailable."

  constructor(options) {
    super(options)
    this.clock = options.clock || (() => performance.now())
    this.poll = this.expiry = null
    this.lastState = null
    this.validUntil = this.retainUntil = 0
    this.presented = ""
  }
  stop() {
    this.cancelTimer(this.poll)
    this.cancelTimer(this.expiry)
    this.poll = this.expiry = null
    this.lastState = null
    this.validUntil = this.retainUntil = 0
    super.stop()
  }
  present() {
    const now = this.clock()
    const state = now < this.retainUntil ? this.lastState : null
    const stale = state !== null && now >= this.validUntil
    const key = `${state}:${stale}`
    if (key !== this.presented) {
      this.presented = key
      this.publish({ state, stale })
    }
    this.cancelTimer(this.expiry)
    this.expiry = null
    const next = now < this.validUntil ? this.validUntil : this.retainUntil
    if (state !== null) this.expiry = this.later(() => this.present(), Math.max(1, next - now))
  }
  emit() {
    if (this.status === "loading") return
    const now = this.clock()
    const elapsed = now - this.startedAt
    if (this.status === "ready" && this.data?.state !== null && elapsed >= 0 && this.data.maxAgeMs > elapsed) {
      this.lastState = this.data.state
      this.validUntil = this.startedAt + this.data.maxAgeMs
      // Display continuity only. A missed poll never extends driving authority or this deadline.
      this.retainUntil = this.validUntil + 5000
    }
    this.present()
    if (this.active && this.poll === null) {
      const delay = Math.max(500, Math.min(1500, (this.validUntil - now) / 2))
      this.poll = this.later(() => { this.poll = null; this.load() }, delay)
    }
  }
  load() {
    if (!this.active || this.request !== null) return
    this.startedAt = this.clock()
    return super.load()
  }

}

export const DeviceState = {
  props: { unauthorized: { type: Function, required: true }, connection: { type: String, default: "" } },
  data: () => ({ state: null, stale: false }),
  computed: { label() { return STATES[this.state] || "State unavailable" } },
  created() { this.feed = new DeviceStateFeed({ publish: (update) => Object.assign(this.$data, update), unauthorized: this.unauthorized }) },
  mounted() {
    this.visibility = () => document.hidden ? this.feed.stop() : this.feed.start()
    document.addEventListener("visibilitychange", this.visibility)
    if (!document.hidden) this.feed.start()
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibility); this.feed.stop() },
  template: `<span class="gx-status-pill gx-device-state" role="status" :title="stale ? 'Reconnecting; showing last reported state' : connection">
    <span class="gx-status-dot" :class="state && !stale ? 'online' : 'offline'" aria-hidden="true"></span>{{ label }}
  </span>`,
}
