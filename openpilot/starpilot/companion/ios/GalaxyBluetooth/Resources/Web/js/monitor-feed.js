import { normalizeSnapshot } from "./system-monitor-data.js"

// One request at a time. The deadline starts before the request so slow replies
// never obtain a fresh lease merely by arriving late.
export class MonitorFeed {
  constructor({ mode, publish, fetcher = (...args) => fetch(...args), clock = () => performance.now(),
    schedule = (fn, delay) => setTimeout(fn, delay), cancel = (timer) => clearTimeout(timer), unauthorized = () => {} }) {
    if (!["sample", "local"].includes(mode)) throw new Error("Unsupported monitor source")
    Object.assign(this, { mode, publish, fetcher, clock, schedule, cancel, unauthorized })
    this.generation = 0
    this.stopped = true
    this.timer = this.deadline = this.expiry = this.request = null
  }

  start() { this.stop(); this.stopped = false; this.refresh() }
  stop() {
    this.stopped = true
    this.generation++
    this.cancel(this.timer)
    this.cancel(this.deadline)
    this.cancel(this.expiry)
    this.request?.abort()
    this.request = null
  }

  async refresh() {
    if (this.stopped || this.request) return
    const generation = ++this.generation
    const started = this.clock()
    const request = new AbortController()
    this.request = request
    this.deadline = this.schedule(() => {
      if (this.stopped || this.generation !== generation) return
      this.publish({ snapshot: null, status: "unavailable", error: "System activity could not be refreshed." })
      this.cancel(this.expiry)
      // Retire it even if a stalled response body ignores cancellation.
      this.generation++
      this.request = null
      request.abort()
      if (this.mode === "local") this.timer = this.schedule(() => this.refresh(), 2000)
    }, 4000)
    try {
      const url = this.mode === "local" ? "./api/system/monitor" : "./data/system-monitor.sample.json"
      const response = await this.fetcher(url, { signal: request.signal, cache: "no-store" })
      if (this.stopped || this.generation !== generation || request.signal.aborted) return
      if (this.mode === "local" && response.status === 401) {
        this.stop()
        this.publish({ snapshot: null, status: "unavailable", error: "" })
        this.unauthorized()
        return
      }
      if (this.mode === "local" && response.status === 503) {
        const body = await response.json().catch(() => null)
        if (this.stopped || this.generation !== generation || request.signal.aborted) return
        if (["access_unavailable", "setup_required"].includes(body?.code)) {
          this.stop()
          this.publish({ snapshot: null, status: "unavailable", error: "" })
          this.unauthorized()
          return
        }
      }
      if (!response.ok) throw new Error("Monitor unavailable")
      const snapshot = normalizeSnapshot(await response.json(), this.mode === "local" ? "local-runtime" : "synthetic-preview")
      if (this.stopped || this.generation !== generation || request.signal.aborted) return
      const elapsed = this.clock() - started
      if (elapsed < 0 || elapsed >= 4000) throw new Error("Expired monitor response")
      this.publish({ snapshot, status: this.mode === "local" ? "current" : "sample", error: "" })
      this.cancel(this.deadline)
      this.cancel(this.expiry)
      if (this.mode === "local") {
        this.expiry = this.schedule(() => {
          if (!this.stopped) this.publish({ snapshot: null, status: "unavailable", error: "System activity is out of date." })
        }, 4000 - elapsed)
      }
    } catch {
      if (!this.stopped && this.generation === generation) {
        this.cancel(this.expiry)
        this.publish({ snapshot: null, status: "unavailable", error: "System activity is unavailable." })
      }
    } finally {
      if (!this.stopped && this.generation === generation) {
        this.cancel(this.deadline)
        this.request = null
        if (this.mode === "local") this.timer = this.schedule(() => this.refresh(), 2000)
      }
    }
  }
}
