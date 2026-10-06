import { PollTimer, connectionError } from "./polling.js"

export class SnapshotFeed {
  static interval = 10000
  static unavailable = "This information is unavailable."
  static invalid = "This response is unavailable."
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, later, cancelTimer })
    this.active = false
    this.generation = 0
    this.request = null
    this.timer = null
    this.status = "idle"
    this.data = null
    this.error = ""
    this.poller = new PollTimer({ read: () => this.load(), interval: this.constructor.interval, later, cancel: cancelTimer })
  }

  emit() { this.publish({ status: this.status, data: this.data, error: this.error }) }
  stop() {
    this.poller.stop()
    this.active = false
    this.generation++
    this.request?.abort()
    if (this.timer !== null) this.cancelTimer(this.timer)
    this.request = this.timer = null
    this.status = "idle"
    this.data = null
    this.error = ""
    this.emit()
  }
  start() { this.stop(); this.active = true; if (this.constructor.interval) this.poller.start(); return this.load() }

  async load() {
    if (!this.active || this.request !== null) return
    const generation = this.generation
    const request = new AbortController()
    this.request = request
    if (!this.data && !this.error) { this.status = "loading"; this.emit() }
    this.timer = this.later(() => {
      if (!this.active || generation !== this.generation || this.request !== request) return
      request.abort()
      this.generation++
      this.request = this.timer = null
      this.data = null
      this.status = "unavailable"
      this.error = `Reading ${this.constructor.subject} timed out. Reconnecting automatically…`
      this.emit()
    }, 4000)
    try {
      const response = await this.fetcher(this.constructor.endpoint, { credentials: "same-origin", cache: "no-store", signal: request.signal })
      if (!this.active || generation !== this.generation || request.signal.aborted) return
      if (response.status === 401) { this.stop(); this.unauthorized(); return }
      if (response.status === 503) {
        const body = await response.json().catch(() => null)
        if (!this.active || generation !== this.generation || request.signal.aborted) return
        if (["setup_required", "access_unavailable"].includes(body?.code)) { this.stop(); this.unauthorized(); return }
        throw new Error(this.constructor.unavailable)
      }
      if (!response.ok) throw new Error(this.constructor.unavailable)
      const data = await response.json()
      if (!this.active || generation !== this.generation || request.signal.aborted) return
      if (!this.constructor.valid(data)) throw new Error(this.constructor.invalid)
      this.data = data
      this.status = "ready"
      this.error = ""
      this.emit()
    } catch (error) {
      if (this.active && generation === this.generation) {
        this.data = null
        this.status = "unavailable"
        this.error = connectionError(error, this.constructor.unavailable + " Reconnecting automatically…")
        this.emit()
      }
    } finally {
      if (generation === this.generation) {
        if (this.timer !== null) this.cancelTimer(this.timer)
        this.timer = null
        this.request = null
      }
    }
  }
}


