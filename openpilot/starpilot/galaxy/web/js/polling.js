// Shared background synchronization. Reads never replay a user's mutation.
export class PollTimer {
  constructor({ read, interval = 10000, later = (fn, ms) => setTimeout(fn, ms), cancel = id => clearTimeout(id) }) {
    Object.assign(this, { read, interval, later, cancel })
    this.active = false
    this.generation = 0
    this.timer = null
  }
  start() { this.stop(); this.active = true; this.schedule() }
  stop() { this.generation++; this.active = false; this.cancel(this.timer); this.timer = null }
  schedule() {
    if (!this.active || this.timer !== null) return
    const generation = this.generation
    this.timer = this.later(async () => {
      if (!this.active || generation !== this.generation) return
      this.timer = null
      try { if (typeof document === "undefined" || !document.hidden) await this.read() }
      finally { if (generation === this.generation) this.schedule() }
    }, this.interval)
  }
}

export const connectionError = (error, fallback = "Galaxy could not connect. Reconnecting automatically…") =>
  error instanceof TypeError || error?.name === "NetworkError" || error?.name === "AbortError" || error?.name === "TimeoutError" ? fallback : error?.message || fallback
