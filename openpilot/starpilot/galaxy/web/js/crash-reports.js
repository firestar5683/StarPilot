import { PollTimer, connectionError } from "./polling.js"
import { requestJson } from "./startup.js"
// Read-only local crash reports. State is cleared on navigation and sign-out.
export class CrashReportsFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args), later = (fn, ms) => setTimeout(fn, ms), cancel = id => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher })
    Object.assign(this, { later, cancel })
    this.poller = new PollTimer({ read: () => this.load(true), interval: 30000, later, cancel })
    this.active = false
    this.generation = 0
    this.request = null
    this.reports = []
  }

  clear() {
    this.reports = []
    this.publish({ reports: [], scanIncomplete: false, listLimited: false, status: "idle", error: "", selected: null, preview: null, previewStatus: "idle" })
  }

  stop() {
    this.poller.stop()
    this.active = false
    this.generation++
    this.request?.abort()
    this.request = null
    this.clear()
  }

  start() {
    this.stop()
    this.active = true
    this.poller.start()
    return this.load()
  }

  async requestJson(url, generation, request) {
    try {
      const body = await requestJson(url, { fetcher: this.fetcher, later: this.later, cancel: this.cancel, request: { signal: request.signal } })
      return this.active && generation === this.generation && !request.signal.aborted ? body : null
    } catch (error) {
      if (!this.active || generation !== this.generation) return null
      if (error.status === 401 || ["access_unavailable", "setup_required"].includes(error.code)) { this.stop(); this.unauthorized(); return null }
      throw error
    }
  }

  async load(background = false) {
    if (!this.active || background && this.request) return
    const generation = ++this.generation
    this.request?.abort()
    const request = new AbortController()
    this.request = request
    if (!background) this.publish({ status: "loading" })
    try {
      const data = await this.requestJson("./api/crash-reports", generation, request)
      if (!data) return
      if (data.schemaVersion !== 1 || !Array.isArray(data.reports) || data.reports.length > 200 ||
          typeof data.scanIncomplete !== "boolean" || typeof data.listLimited !== "boolean" ||
          data.reports.some((item) => typeof item.id !== "string" || !item.id ||
            typeof item.name !== "string" || !item.name ||
            typeof item.size !== "number" || !Number.isFinite(item.size) || item.size < 0 ||
            typeof item.modifiedAt !== "number" || !Number.isFinite(item.modifiedAt))) {
        throw new Error("Invalid crash report list")
      }
      this.reports = data.reports
      this.publish({ reports: data.reports, scanIncomplete: data.scanIncomplete, listLimited: data.listLimited, status: "ready", error: "" })
    } catch (error) {
      if (this.active && generation === this.generation) this.publish({ reports: [], scanIncomplete: false, listLimited: false, status: "unavailable", error: connectionError(error), selected: null, preview: null, previewStatus: "idle" })
    } finally {
      if (generation === this.generation) this.request = null
    }
  }

  async open(report) {
    if (!this.active || !this.reports.some((item) => item.id === report?.id)) return
    const generation = ++this.generation
    this.request?.abort()
    const request = new AbortController()
    this.request = request
    this.publish({ selected: report.id, preview: null, previewStatus: "loading", error: "" })
    try {
      const data = await this.requestJson(`./api/crash-reports/${encodeURIComponent(report.id)}`, generation, request)
      if (!data) return
      if (data.schemaVersion !== 1 || data.name !== report.name || typeof data.text !== "string" || typeof data.truncated !== "boolean") {
        throw new Error("Invalid crash report")
      }
      this.publish({ selected: report.id, preview: data, previewStatus: "ready", error: "" })
    } catch (error) {
      if (this.active && generation === this.generation) this.publish({ selected: null, preview: null, previewStatus: "unavailable", error: connectionError(error) })
    } finally {
      if (generation === this.generation) this.request = null
    }
  }
}
