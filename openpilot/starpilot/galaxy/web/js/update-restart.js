import { requestJson } from "./startup.js"

export const UPDATE_RESTART_KEY = "galaxy-update-restart"
export const UPDATE_RESTART_MESSAGE = "StarPilot is restarting after an update. Galaxy is waiting for your device to come online and will reconnect automatically."

export function savedUpdateRestart(storage = globalThis.sessionStorage) {
  try {
    const value = JSON.parse(storage.getItem(UPDATE_RESTART_KEY))
    return typeof value?.commit === "string" && typeof value?.branch === "string" ? value : null
  } catch { return null }
}

// Keep restart recovery outside the page so authentication changes cannot dismiss it.
export class UpdateRestart {
  constructor({ publish, storage = globalThis.sessionStorage, request = requestJson,
    later = (fn, ms) => setTimeout(fn, ms), cancel = id => clearTimeout(id), reload = () => location.reload() }) {
    Object.assign(this, { publish, storage, request, later, cancel, reload })
    this.baseline = savedUpdateRestart(storage)
    this.offline = !!this.baseline
    this.polling = false
    this.retry = null
    this.publish(!!this.baseline)
    if (this.baseline) this.poll()
  }

  start(baseline) {
    if (this.baseline) {
      this.baseline = { ...this.baseline, ...baseline }
      try { this.storage.setItem(UPDATE_RESTART_KEY, JSON.stringify(this.baseline)) } catch {}
      return
    }
    this.baseline = baseline
    try { this.storage.setItem(UPDATE_RESTART_KEY, JSON.stringify(baseline)) } catch {}
    this.publish(true)
    this.poll()
  }

  async poll() {
    if (this.polling || !this.baseline) return
    this.polling = true
    try {
      const data = await this.request("./api/software/status?history=0")
      const installed = data?.installed, request = data?.operations?.request
      if (data?.schemaVersion !== 1 || !installed || !data.operations) throw new Error("Status unavailable")
      const changed = installed.commit && (installed.commit !== this.baseline.commit || installed.branch !== this.baseline.branch)
      const finished = request?.state === "failed" || request?.outcome === "up_to_date"
      const returned = !request && data.updater?.state === "idle" && changed
      if (finished || returned) {
        this.baseline = null
        if (this.retry !== null) this.cancel(this.retry)
        this.retry = null
        try { this.storage.removeItem(UPDATE_RESTART_KEY) } catch {}
        this.publish(false)
        this.reload() // Preserve the current hash and load the newly installed Galaxy assets.
      }
    } catch {
      this.offline = true
    } finally {
      this.polling = false
      if (this.baseline && this.retry === null) this.retry = this.later(() => {
        this.retry = null
        this.poll()
      }, 2000)
    }
  }
}
