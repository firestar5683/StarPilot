// Read-only Android Auto session logs. State is cleared on navigation and sign-out.
export const LOGS_URL = "./api/android-auto/logs"
export const BUNDLE_URL = `${LOGS_URL}/bundle`
export const fileUrl = (name) => `${LOGS_URL}/file/${encodeURIComponent(name)}`

// compat_report's outcome is a short phrase: "projected", "failed: <error>", "stopped at rfcomm", "no session".
export const outcomeLabel = (outcome) => (outcome ? outcome[0].toUpperCase() + outcome.slice(1) : "Unknown")

export class AndroidAutoLogsFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args) }) {
    Object.assign(this, { publish, unauthorized, fetcher })
    this.active = false
    this.generation = 0
    this.request = null
  }

  clear() {
    this.publish({ sessions: [], others: [], status: "idle", error: "" })
  }

  stop() {
    this.active = false
    this.generation++
    this.request?.abort()
    this.request = null
    this.clear()
  }

  start() {
    this.stop()
    this.active = true
    return this.load()
  }

  async load() {
    if (!this.active) return
    const generation = ++this.generation
    this.request?.abort()
    const request = new AbortController()
    this.request = request
    const current = () => this.active && generation === this.generation && !request.signal.aborted
    this.publish({ status: "loading", error: "" })
    try {
      const response = await this.fetcher(LOGS_URL, { signal: request.signal, cache: "no-store" })
      if (!current()) return
      if (response.status === 401) {
        this.stop()
        this.unauthorized()
        return
      }
      if (response.status === 503) {
        const body = await response.json().catch(() => null)
        if (!current()) return
        if (["access_unavailable", "setup_required"].includes(body?.code)) {
          this.stop()
          this.unauthorized()
          return
        }
        throw new Error("Android Auto logs are unavailable")
      }
      if (!response.ok) throw new Error("Android Auto logs are unavailable")
      const body = await response.json()
      if (!current()) return
      this.publish({ sessions: body.sessions ?? [], others: body.others ?? [], status: "ready", error: "" })
    } catch (error) {
      if (!current() || error?.name === "AbortError") return
      this.publish({ sessions: [], others: [], status: "unavailable", error: error?.message || "Android Auto logs are unavailable" })
    }
  }
}
