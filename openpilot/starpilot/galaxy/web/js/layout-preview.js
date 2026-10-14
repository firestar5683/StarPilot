import { widgetArtMetadata } from "./widget-art.js"
export const PREVIEW_SCENES = [
  { id: "engaged", label: "Engaged" },
  { id: "aol", label: "Lateral only" },
  { id: "long_only", label: "Longitudinal only" },
  { id: "experimental", label: "Manual experimental" },
  { id: "braking", label: "Braking" },
  { id: "stopped", label: "Stopped timer" },
  { id: "cem_stop_light", label: "CEM · Traffic light" },
  { id: "cem_lead", label: "CEM · Stopped lead" },
  { id: "cem_curve", label: "CEM · Curve" },
  { id: "slc_pending", label: "Pending speed limit" },
  { id: "slc_max", label: "Using set speed" },
  { id: "slc_equal", label: "Equal speed limits" },
  { id: "slc_pedal", label: "Using accelerator" },
  { id: "slc_retained", label: "Set-speed override" },
  { id: "slc_disengaged", label: "Cruise off" },
  { id: "slc_unavailable", label: "Unavailable speed limit" },
  { id: "slc_display", label: "Display-only speed limit" },
]
const SCENES = PREVIEW_SCENES.map(({ id }) => id)

export class LayoutPreviewFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id),
                urls = URL, art = false, backdrop = false }) {
    Object.assign(this, { publish, unauthorized, fetcher, later, cancelTimer, urls, art, backdrop })
    this.active = false
    this.version = 0
    this.timer = null
    this.request = null
    this.currentUrl = null
    this.pending = null
    // Keep one native sheet per profile while switching views or refreshing it.
    this.artCache = new Map()
    this.failureKey = null
    this.failures = 0
  }

  pause() {
    this.active = false
    this.version++
    if (this.timer !== null) this.cancelTimer(this.timer)
    this.timer = null
    this.pending = null
    this.inputKey = null
    this.request?.abort()
    this.request = null
    this.last = null
  }

  stop() {
    this.pause()
    this.clearImage()
    this.failureKey = null
    this.failures = 0
  }

  clearImage() {
    const urls = new Set([...this.artCache.values()].map(item => item.url))
    if (this.currentUrl) urls.add(this.currentUrl)
    for (const url of urls) this.urls.revokeObjectURL(url)
    this.artCache.clear()
    this.currentUrl = null
    this.publish({ url: null, ...(this.art ? {sprites: null} : {}) })
  }

  start() { if (this.art) this.pause(); else this.stop(); this.active = true }

  // `key` stands in for the document when only part of it changes the image (the backdrop ignores positions).
  update(document, profile, scene, dragging = false, key = document) {
    if (!this.active || !document || !["large", "compact", "projection"].includes(profile) || !SCENES.includes(scene)) return
    const inputKey = JSON.stringify({ key, profile, scene, dragging })
    if (inputKey === this.inputKey) return
    this.inputKey = inputKey
    this.version++
    if (this.timer !== null) this.cancelTimer(this.timer)
    this.timer = null
    this.pending = null
    this.request?.abort()
    if (dragging) { this.publish({ status: "editing", error: "" }); return }
    const renderKey = JSON.stringify({ key, profile, scene })
    if (renderKey !== this.failureKey) { this.failureKey = renderKey; this.failures = 0 }
    if (this.art) {
      const cached = this.artCache.get(profile)
      this.currentUrl = cached?.url || null
      this.publish({ url: this.currentUrl, sprites: cached?.sprites || null })
      if (cached?.key === renderKey) {
        this.publish({ status: "ready", error: "" })
        return
      }
    }
    this.pending = { document: JSON.parse(JSON.stringify(document)), key, profile, scene, version: this.version, renderKey }
    // Once a real outage is reported, keep the message stable through retries.
    if (!this.art || this.failures < 2) this.publish({ status: "updating", error: "" })
    this.timer = this.later(() => { this.timer = null; this.dispatch() }, 200)
  }

  retry() {
    if (!this.active || !this.last) return
    this.inputKey = null
    this.update(this.last.document, this.last.profile, this.last.scene, false, this.last.key)
  }

  async dispatch() {
    if (!this.active || this.request || !this.pending) return
    const item = this.pending
    this.pending = null
    this.last = item
    const request = new AbortController()
    this.request = request
    const timeout = this.later(() => request.abort(), 7000)
    let rejectAborted
    const aborted = new Promise((_, reject) => { rejectAborted = () => reject(new Error("Preview request cancelled")) })
    request.signal.addEventListener("abort", rejectAborted, { once: true })
    let failure = "Preview is unavailable. Reconnecting automatically…"
    let denied = false
    try {
      await Promise.race([aborted, (async () => {
        const response = await this.fetcher("./api/ui/layout/preview", { method: "POST", credentials: "same-origin",
          cache: "no-store", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ document: item.document, profile: item.profile, scene: item.scene, ...(this.art ? {art: true} : this.backdrop ? {art: "backdrop"} : {}) }), signal: request.signal })
        if (!this.active || item.version !== this.version || request.signal.aborted) return
        if (response.status === 401) { this.stop(); this.unauthorized(); return }
        if (response.status === 403) { denied = true; failure = "Turn off the vehicle to preview this layout."; throw new Error() }
        if (response.status === 429) { failure = "Preview is busy. Retrying automatically…"; throw new Error() }
        if (!response.ok) { const detail = await response.json().catch(() => null); failure = detail?.error || failure; throw new Error() }
        if (!response.headers.get("Content-Type")?.toLowerCase().startsWith("image/png")) throw new Error("Preview is unavailable. Reconnecting automatically…")
        const blob = await response.blob()
        if (!this.active || item.version !== this.version || request.signal.aborted) return
        if (!blob.size || blob.size > 4 * 1024 * 1024) throw new Error("Preview is unavailable. Reconnecting automatically…")
        const sprites = this.art ? await widgetArtMetadata(blob) : null
        if (!this.active || item.version !== this.version || request.signal.aborted) return
        const previousUrl = this.art ? this.artCache.get(item.profile)?.url : this.currentUrl
        this.currentUrl = this.urls.createObjectURL(blob)
        if (this.art) this.artCache.set(item.profile, { key: item.renderKey, url: this.currentUrl, sprites })
        this.failures = 0
        this.publish({ status: "ready", error: "", url: this.currentUrl, ...(this.art ? {sprites} : {}) })
        if (previousUrl) this.urls.revokeObjectURL(previousUrl)
      })()])
    } catch {
      if (this.active && item.version === this.version) {
        this.inputKey = null
        this.failures = denied ? 2 : this.failures + 1
        if (this.art && denied) this.clearImage()
        const recovering = this.art && this.failures < 2
        this.publish({ status: recovering ? "updating" : "unavailable", error: recovering ? "" : failure })
        this.timer = this.later(() => { this.timer = null; this.retry() }, recovering ? 600 : 5000)
      }
    } finally {
      this.cancelTimer(timeout)
      request.signal.removeEventListener("abort", rejectAborted)
      if (this.request === request) this.request = null
      if (this.active && this.pending && this.timer === null) this.dispatch()
    }
  }
}
