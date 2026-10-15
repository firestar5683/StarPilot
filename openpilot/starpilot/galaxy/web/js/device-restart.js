import { requestJson } from "./startup.js"

export class DeviceRestartWatch {
  constructor({ request = requestJson, interval = 5000, later = (fn, ms) => setTimeout(fn, ms), cancel = id => clearTimeout(id),
    reload = () => location.reload(), hidden = () => typeof document !== "undefined" && document.hidden, paused = () => false }) {
    Object.assign(this, { request, interval, later, cancel, reload, hidden, paused })
    this.instance = null
    this.timer = null
    this.checking = false
    this.reloading = false
  }

  track(instance) {
    if (typeof instance !== "string" || !instance) return
    if (this.instance === null) {
      this.instance = instance
      this.schedule()
    } else if (instance !== this.instance) this.restarted()
  }

  restarted() {
    if (this.reloading || this.paused()) return
    this.reloading = true
    this.stop()
    this.reload()
  }

  schedule() {
    if (this.instance === null || this.reloading || this.timer !== null) return
    this.timer = this.later(() => { this.timer = null; this.check() }, this.interval)
  }

  wake() {
    if (this.timer !== null) this.cancel(this.timer)
    this.timer = null
    this.check()
  }

  async check() {
    if (this.instance === null || this.checking || this.reloading) return
    if (this.hidden()) { this.schedule(); return }
    this.checking = true
    try {
      const runtime = await this.request("./data/runtime.json")
      this.track(runtime?.instance)
    } catch {
      // Offline while rebooting; keep checking until Galaxy answers again.
    } finally {
      this.checking = false
      this.schedule()
    }
  }

  stop() {
    if (this.timer !== null) this.cancel(this.timer)
    this.timer = null
  }
}
