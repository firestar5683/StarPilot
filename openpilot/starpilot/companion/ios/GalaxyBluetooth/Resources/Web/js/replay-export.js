import { requestJson } from "./startup.js"
import { LOCAL } from "./recording-data.js"
import { ReplayClient, replayToken, validReplayStatus } from "./replay.js"

export function replayClientId() {
  try {
    let id = sessionStorage.getItem("galaxy-replay-client")
    if (!/^[a-f0-9]{32}$/.test(id || "")) { id = replayToken(); sessionStorage.setItem("galaxy-replay-client", id) }
    return id
  } catch { return replayToken() }
}
export function validReplayExport(job) {
  return job == null || /^[a-f0-9]{32}$/.test(job.id) && LOCAL.test(job.routeId) &&
    (job.segment === null || Number.isSafeInteger(job.segment) && job.segment >= 0) &&
    ["rendering", "finalizing", "ready", "failed", "cancelled"].includes(job.state) &&
    typeof job.owned === "boolean" && Number.isFinite(job.progress) && job.progress >= 0 && job.progress <= 1 &&
    Number.isSafeInteger(job.bytes) && job.bytes >= 0 &&
    (job.expiresInSeconds === undefined || Number.isFinite(job.expiresInSeconds) && job.expiresInSeconds >= 0 && job.expiresInSeconds <= 1800) && /^[a-zA-Z0-9_-]+\.mp4$/.test(job.filename)
}

// This receipt outlives a viewer. Closing the page stops polling, never the export.
export class ReplayExportClient {
  constructor({ unauthorized, clientId = replayClientId(), fetcher = (...args) => fetch(...args),
    later = (fn, ms) => setTimeout(fn, ms), cancelTimer = id => clearTimeout(id) }) {
    Object.assign(this, { unauthorized, clientId, fetcher, later, cancelTimer })
    this.job = this.status = null
    this.busy = this.active = false
    this.error = ""
    this.generation = 0
  }
  get running() { return ["rendering", "finalizing"].includes(this.job?.state) }
  get downloadUrl() { return this.job?.owned && this.job.state === "ready" ? `./api/replay/export-download?exportId=${this.job.id}&clientId=${this.clientId}` : null }
  async request(path, body) {
    const result = await requestJson(`./api/replay/${path}`, { fetcher: this.fetcher, timeout: 6000,
      request: { ...(body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}) } })
    if (!validReplayStatus(result) || !validReplayExport(result.export)) throw new Error("Replay returned an unsupported export status.")
    return result
  }
  receive(status) { this.status = status; this.job = status.export?.state === "ready" && status.export.expiresInSeconds === 0 ? null : status.export || null }
  open() { this.close(); this.active = true; return this.refresh() }
  async refresh() {
    if (this.busy) return
    const generation = this.generation
    let retry = false
    this.cancelTimer(this.timer)
    try {
      const status = await this.request(`status?clientId=${this.clientId}`)
      if (this.active && generation === this.generation) { this.receive(status); this.error = "" }
    } catch (error) {
      if (this.active && generation === this.generation) {
        if (error.status === 401 || ["setup_required", "access_unavailable"].includes(error.code)) { this.close(); this.unauthorized() }
        else { retry = true; this.error = error.message || "Export status is unavailable. Retrying…" }
      }
    } finally {
      if (this.active && generation === this.generation && (retry || this.running || this.job?.state === "ready"))
        this.timer = this.later(() => this.refresh(), retry || this.running ? 1000 : Math.max(1000, (this.job.expiresInSeconds ?? 1800) * 1000))
    }
  }
  async start(routeId, segment = null, prepare = async () => {}) {
    if (this.busy || this.running) return
    this.generation++; this.cancelTimer(this.timer)
    this.busy = true; this.error = ""
    try {
      await prepare()
      let status = await this.request(`status?clientId=${this.clientId}`)
      if (status.owned && status.sessionId && status.purpose !== "export") {
        const preview = new ReplayClient({ clientId: this.clientId, fetcher: this.fetcher, later: this.later, cancelTimer: this.cancelTimer,
          publish() {}, unauthorized: this.unauthorized, video: () => null })
        preview.active = true; preview.status = status; preview.ownedSession = status.sessionId
        try { await preview.stopAndWait(); status = preview.status }
        finally { preview.close() }
      }
      const job = await this.request("export-start", { routeId, clientId: this.clientId, requestId: replayToken(),
        expectedOwnerId: status.ownerId, ...(segment === null ? {} : { segment }) })
      this.receive(job)
    } catch (error) {
      if (error.status === 401 || ["setup_required", "access_unavailable"].includes(error.code)) this.unauthorized()
      else this.error = error.message || "Replay export could not start. Try again."
    } finally { this.busy = false; if (this.active) this.refresh() }
  }
  async cancel() {
    if (this.busy || !this.running || !this.job.owned) return
    this.generation++; this.cancelTimer(this.timer)
    this.busy = true; this.error = ""
    try { this.receive(await this.request("stop", { clientId: this.clientId, sessionId: this.job.id, requestId: replayToken() })) }
    catch (error) { if (error.status === 401) this.unauthorized(); else this.error = error.message || "Cancel could not complete. Try again." }
    finally { this.busy = false; if (this.active) this.refresh() }
  }
  close() { this.active = false; this.generation++; this.cancelTimer(this.timer) }
}
