import { computed, reactive } from "vue"
import { showSnackbar } from "./api.js"
import { navigate, store } from "./store.js"

export function useTabRouting(basePath, tabs) {
  const tab = computed(() => {
    const prefix = basePath + "/"
    const slug = store.route.startsWith(prefix)
      ? store.route.slice(prefix.length).split("/")[0]
      : ""
    for (const [key, s] of Object.entries(tabs)) {
      if (s === slug) return key
    }
    return Object.keys(tabs)[0]
  })

  function selectTab(key) {
    const slug = tabs[key]
    if (slug === undefined) return
    const href = slug ? `${basePath}/${slug}` : basePath
    if (href !== store.route) navigate(href)
  }

  return { tab, selectTab }
}

export function usePolling(fn, { interval = 3000, enabled = () => true } = {}) {
  const state = reactive({ running: false, lastError: "", lastErrorAt: 0 })
  let timer = null
  let destroyed = false

  const stop = () => { if (timer) { clearTimeout(timer); timer = null } }
  const scrolling = () => typeof document !== "undefined" && !!document.body?.classList?.contains("is-scrolling")
  const tick = async () => {
    if (destroyed || !enabled() || document.visibilityState !== "visible" || scrolling()) {
      timer = setTimeout(tick, interval)
      return
    }
    try {
      await fn()
      state.lastError = ""
    } catch (e) {
      state.lastError = e?.message || String(e)
      state.lastErrorAt = Date.now()
    }
    if (!destroyed) timer = setTimeout(tick, interval)
  }
  const start = () => { stop(); timer = setTimeout(tick, 0) }
  const destroy = () => { destroyed = true; stop() }
  return { state, start, stop, destroy }
}

export function useLogStream({ endpoint, snapshotFn, interval = 2000 } = {}) {
  const state = reactive({ log: "", latest: "", paused: false, transport: "idle" })
  let es = null
  let timer = null
  let destroyed = false

  const apply = (data) => {
    state.latest = data || ""
    if (!state.paused) state.log = state.latest
  }
  const snapshotFetch = async () => {
    if (!snapshotFn) return
    try { apply((await snapshotFn())?.data || "") } catch (e) {  }
  }
  const stopStream = () => { if (es) { es.close(); es = null } }
  const stopPolling = () => { if (timer) { clearInterval(timer); timer = null } }
  const startPolling = () => {
    stopStream()
    state.transport = "polling"
    snapshotFetch()
    timer = setInterval(() => { if (!destroyed) snapshotFetch() }, interval)
  }
  const startStream = () => {
    stopPolling()
    if (!endpoint) return startPolling()
    state.transport = "streaming"
    es = new EventSource(endpoint)
    es.onmessage = (e) => apply(e.data)
    es.onerror = () => { if (snapshotFn) startPolling() }
  }
  const start = () => (snapshotFn ? startPolling() : startStream())
  const destroy = () => { destroyed = true; stopStream(); stopPolling() }
  const togglePause = () => {
    state.paused = !state.paused
    if (!state.paused) state.log = state.latest
  }
  const notify = (message, level) => showSnackbar(message, level)
  return { state, start, destroy, togglePause, notify }
}

export function formatAgeSeconds(value) {
  const sec = Number(value)
  if (!Number.isFinite(sec) || sec < 0) return "unknown"
  if (sec < 1) return "just now"
  if (sec < 60) return `${Math.round(sec)}s ago`
  const min = sec / 60
  if (min < 60) return `${Math.round(min)}m ago`
  return `${Math.round(min / 60)}h ago`
}
