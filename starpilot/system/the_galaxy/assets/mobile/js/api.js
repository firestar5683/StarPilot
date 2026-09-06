export const LAYOUT_URL = "/assets/components/tools/device_settings_layout.json?v=settings-tier-1"

async function parse(res) {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = new Error(data?.error || data?.message || res.statusText || "Request failed")
    err.data = data
    throw err
  }
  return data
}

function initFor({ method = "GET", data, form, headers, cache, signal } = {}) {
  const init = { method }
  if (cache) init.cache = cache
  if (signal) init.signal = signal
  if (data !== undefined) {
    init.headers = { "Content-Type": "application/json", ...(headers || {}) }
    init.body = JSON.stringify(data)
  } else if (form !== undefined) {
    if (headers) init.headers = headers
    init.body = form
  } else if (headers) init.headers = headers
  return init
}

function request(url, opts) {
  return fetch(url, initFor(opts)).then(parse)
}

async function requestOk(url, opts) {
  const res = await fetch(url, initFor(opts))
  return res.ok ? parse(res) : null
}

async function delOk(url) {
  return (await fetch(url, { method: "DELETE" })).ok
}

function postOk(url, opts = {}) {
  return fetch(url, initFor({ ...opts, method: "POST" })).then((res) => res.ok)
}

export const api = {
  postAction(endpoint) { return request(endpoint, { method: "POST" }) },
  getOptions(endpoint) { return request(endpoint) },

  async getLayout() {
    const data = await request(LAYOUT_URL, { cache: "no-store" })
    return (data || [])
      .map((section) => ({ ...section, params: (section.params || []).filter((p) => p.key !== "Model") }))
      .filter((section) => (section.params || []).length > 0)
  },

  getParams() { return request("/api/params/all") },
  async getDefaults() {
    const res = await fetch("/api/params/defaults")
    return res.ok ? parse(res) : {}
  },

  updateParam({ key, value, label }) {
    const data = { key, value }
    if (label) data.label = label
    return request("/api/params", { method: "PUT", data })
  },

  getFlmWorkspace() { return requestOk("/api/flm/workspace", { cache: "no-store" }) },
  getFavoritesSlots() { return request("/api/favorites/slots", { cache: "no-store" }) },
  saveFavoritesSlots(slots) { return request("/api/favorites/slots", { method: "PUT", data: { slots } }) },
  activateFavoriteAction(key) { return request("/api/favorites/action", { method: "POST", data: { key } }) },

  getDeviceStatus() { return requestOk("/api/device/status") },
  getStats() { return requestOk("/api/stats") },
  setDriveStats(action, routeNames) { return request(`/api/stats/${action}_drive`, { method: "POST", data: { routeNames } }) },

  async getRoutesStream({ onProgress, onRoutes, signal } = {}) {
    const res = await fetch("/api/routes", { signal })
    if (!res.ok || !res.body) throw new Error(`Route request failed (${res.status})`)
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split(/\r?\n\r?\n/)
      buffer = events.pop() || ""
      for (const event of events) {
        const lines = event.split(/\r?\n/).filter((l) => l.startsWith("data:"))
        if (!lines.length) continue
        try {
          const payload = JSON.parse(lines.map((l) => l.slice(5).trimStart()).join("\n"))
          if (Number.isFinite(payload.progress)) onProgress?.(payload.progress)
          onRoutes?.(Array.isArray(payload.routes) ? payload.routes : [])
        } catch (e) {  }
      }
    }
  },

  getRoute(name) { return request(`/api/routes/${encodeURIComponent(name)}`) },
  deleteRoute(name) { return request(`/api/routes/${encodeURIComponent(name)}`, { method: "DELETE" }) },
  renameRoute(oldName, newName) { return request("/api/routes/rename", { method: "POST", data: { old: oldName, new: newName } }) },
  resetRouteName(name) { return request("/api/routes/reset_name", { method: "POST", data: { name } }) },
  setRoutePreserved(name, preserved) { return request(`/api/routes/${encodeURIComponent(name)}/preserve`, { method: preserved ? "POST" : "DELETE" }) },
  deleteAllRoutes(includePreserved) { return request(`/api/routes/delete_all?include_preserved=${includePreserved}`, { method: "DELETE" }) },
  getRouteLogs(name) { return request(`/api/routes/${encodeURIComponent(name)}/logs`) },

  async screenRecordingsStream({ onProgress, onRecordings, signal } = {}) {
    const res = await fetch("/api/screen_recordings/list", { signal })
    if (!res.ok || !res.body) throw new Error(`Screen recordings request failed (${res.status})`)
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split(/\r?\n\r?\n/)
      buffer = events.pop() || ""
      for (const event of events) {
        const lines = event.split(/\r?\n/).filter((l) => l.startsWith("data:"))
        if (!lines.length) continue
        try {
          const payload = JSON.parse(lines.map((l) => l.slice(5).trimStart()).join("\n"))
          if (Number.isFinite(payload.progress)) onProgress?.(payload.progress)
          onRecordings?.(Array.isArray(payload.recordings) ? payload.recordings : [])
        } catch (e) {  }
      }
    }
  },
  screenRecordingVideoUrl(filename) { return `/api/screen_recordings/download/${encodeURIComponent(filename)}` },
  deleteScreenRecording(filename) { return request(`/api/screen_recordings/delete/${encodeURIComponent(filename)}`, { method: "DELETE" }) },
  deleteAllScreenRecordings() { return request("/api/screen_recordings/delete_all", { method: "DELETE" }) },
  renameScreenRecording(oldName, newName) { return request("/api/screen_recordings/rename", { method: "POST", data: { old: oldName, new: newName } }) },

  getModelLab() { return request("/api/model-laboratory", { cache: "no-store" }) },
  saveModelLab(config) { return request("/api/model-laboratory", { method: "PUT", data: config }) },
  prepareModelLabArtifact(model) { return request("/api/model-laboratory/download", { method: "POST", data: { model } }) },

  getErrorLogs() { return request("/api/error_logs", { headers: { Accept: "application/json" } }) },
  getErrorLog(filename) { return fetch(`/api/error_logs/${encodeURIComponent(filename)}`).then((r) => r.text()) },
  deleteErrorLog(filename) { return delOk(`/api/error_logs/${encodeURIComponent(filename)}`) },
  deleteAllErrorLogs() { return delOk("/api/error_logs/delete_all") },

  getTmuxLogs() { return request("/api/tmux_log/list") },
  tmuxCapture() { return postOk("/api/tmux_log/capture") },
  tmuxSnapshot() { return request("/api/tmux_log/snapshot") },
  deleteTmuxLog(filename) { return delOk(`/api/tmux_log/delete/${encodeURIComponent(filename)}`) },
  deleteAllTmuxLogs() { return delOk("/api/tmux_log/delete_all") },
  async renameTmuxLog(oldName, newName) {
    const res = await fetch(`/api/tmux_log/rename/${encodeURIComponent(oldName)}/${encodeURIComponent(newName)}`, { method: "PUT" })
    return res.ok
  },

  runTroubleshoot() { return request("/api/troubleshoot", { method: "POST" }) },
  getTroubleshoot() { return requestOk("/api/troubleshoot") },
  resetTroubleshoot() { return postOk("/api/troubleshoot/reset") },
  resetTroubleshootSection(sectionId) { return request("/api/troubleshoot/reset", { method: "POST", data: { sectionId } }) },

  getWheelControlsStatus() { return request("/api/wheel-controls/status", { cache: "no-store" }) },
  wheelControlsOp(operation, body = {}) { return request(`/api/wheel-controls/${operation}`, { method: "POST", data: body }) },

  getBluetoothStatus() { return request("/api/bluetooth/status") },
  bluetoothOp(operation, body = {}) { return request(`/api/bluetooth/${operation}`, { method: "POST", data: body }) },

  carFeaturesCheck(tool = "") {
    const query = tool ? `?tool=${encodeURIComponent(tool)}` : ""
    return requestOk(`/api/car_features_check${query}`)
  },

  lateralManeuvers(action) { return request(`/api/lateral_maneuvers/${action}`, { method: "POST" }) },
  lateralManeuversStatus() { return request("/api/lateral_maneuvers/status") },
  longitudinalManeuvers(action) { return request(`/api/longitudinal_maneuvers/${action}`, { method: "POST" }) },
  longitudinalManeuversStatus() { return request("/api/longitudinal_maneuvers/status") },

  getMapsStatus() { return request("/api/maps/status") },
  getMapsCatalog() { return request("/api/maps/catalog") },
  mapsOp(operation, body = {}) { return request(`/api/maps/${operation}`, { method: "POST", data: body }) },

  getNavigation() { return request("/api/navigation") },
  setNavigation(body) { return request("/api/navigation", { method: "POST", data: body }) },
  getNavigationKeys() { return request("/api/navigation_key") },
  setNavigationKey(body) { return request("/api/navigation_key", { method: "POST", data: body }) },
  navigationFavorite(body) { return request("/api/navigation/favorite", { method: "POST", data: body }) },
  deleteNavigationKey(type) { return request(`/api/navigation_key?type=${encodeURIComponent(type)}`, { method: "DELETE" }) },

  async backupToggles() {
    const res = await fetch("/api/toggles/backup", { method: "POST" })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data?.message || "Failed to create toggle backup.")
    }
    return res.blob()
  },
  restoreToggles(data) { return request("/api/toggles/restore", { method: "POST", data }) },
  resetTogglesDefault() { return request("/api/toggles/reset_default", { method: "POST" }) },

  getUpdateBranches() { return request("/api/update/branches") },
  getUpdateBranch() { return request("/api/update/branch") },
  setUpdateBranch(branch) { return request("/api/update/branch", { method: "POST", data: { branch } }) },
  updateFast() { return request("/api/update/fast", { method: "POST" }) },
  getUpdateFastStatus() { return request("/api/update/fast/status") },
  updateRecover() { return request("/api/update/recover", { method: "POST" }) },
  updateRollback() { return request("/api/update/rollback", { method: "POST" }) },
  factoryReset() { return request("/api/update/factory_reset", { method: "POST" }) },
  getAgnosStatus() { return requestOk("/api/update/agnos_status") },

  getVasmConfig() { return request("/api/v_asm/config") },
  setVasmConfig(body) { return request("/api/v_asm/config", { method: "POST", data: body }) },
  vasmSnapshot() { return requestOk("/api/v_asm/snapshot", { cache: "no-store" }) },

  getPipConfig() { return request("/api/pip_preview/config") },
  setPipConfig(body) { return request("/api/pip_preview/config", { method: "POST", data: body }) },
  pipSnapshot() { return requestOk("/api/pip_preview/snapshot", { cache: "no-store" }) },

  getGalaxyStatus() { return requestOk("/api/galaxy/status") },
  getSpeedLimitsStatus() { return request("/api/speed_limits/status") },
  processSpeedLimits() { return request("/api/speed_limits/process", { method: "POST" }) },

  getTskKeys() { return request("/api/tsk_keys") },
  saveTskKeys(keys) { return request("/api/tsk_keys", { method: "POST", data: keys }) },
  deleteTskKey(name) { return request(`/api/tsk_keys?name=${encodeURIComponent(name)}`, { method: "DELETE" }) },
  tskKeySet(name, value) { return request("/api/tsk_key_set", { method: "POST", data: { name, value } }) },

  async galaxyPair(password) {
    const res = await fetch("/api/galaxy/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    })
    const data = await parse(res).catch(() => ({}))
    if (!res.ok) throw new Error(data?.error || data?.message || "Pairing failed.")
    return data
  },

  async galaxyUnpair() {
    const res = await fetch("/api/galaxy/unpair", { method: "POST" })
    const data = await parse(res).catch(() => ({}))
    if (!res.ok) throw new Error(data?.error || data?.message || "Unpairing failed.")
    return data
  },

  getToggleProfiles() { return request("/api/toggles/profiles", { cache: "no-store" }) },
  saveToggleProfile(slot) { return request(`/api/toggles/profiles/${encodeURIComponent(slot)}/save`, { method: "POST" }) },
  loadToggleProfile(slot) { return request(`/api/toggles/profiles/${encodeURIComponent(slot)}/load`, { method: "POST" }) },

  selectTestingGround(body) { return request("/api/testing_grounds/select", { method: "POST", data: body }) },

  getSentryStatus() { return requestOk("/api/sentry/status", { cache: "no-store" }) },
  getSentryEvents() { return request("/api/sentry/events", { cache: "no-store" }) },
  getSentryLive() { return request("/api/sentry/live", { cache: "no-store" }) },
  deleteSentryEvent(eventId) { return request(`/api/sentry/events/${encodeURIComponent(eventId)}`, { method: "DELETE" }) },

  async getSentryPushConfig() {
    const res = await fetch("/api/sentry/push/config", { cache: "no-store" })
    const data = await parse(res).catch(() => ({}))
    if (!res.ok) return { enabled: false, error: data?.error || "Galaxy Web Push is unavailable." }
    return data
  },
  sentryPushSubscribe(body) { return request("/api/sentry/push/subscribe", { method: "POST", data: body }) },

  getModelStatus() { return requestOk("/api/models/status", { cache: "no-store" }) },
  startModelDownload(modelKey, allowGpuWithoutGpu = false) { return request("/api/models/download", { method: "POST", data: { model: modelKey, allowGpuWithoutGpu } }) },
  downloadAllModels(allowGpuWithoutGpu = false) { return request("/api/models/download_all", { method: "POST", data: { allowGpuWithoutGpu } }) },
  deleteModel(modelKey) { return request("/api/models/delete", { method: "POST", data: { model: modelKey } }) },
  saveModelPreferences(prefs = {}) { return request("/api/models/preferences", { method: "PUT", data: prefs }) },

  getPlotsLive() { return request("/api/plots/live") },
  getGalaxySession() { return request("/api/galaxy/session") },

  getThemeList() { return request("/api/themes/list") },
  getThemeDefault() { return request("/api/themes/default") },
  loadTheme(path, type) {
    const qs = type ? `?type=${encodeURIComponent(type)}` : ""
    return request(`/api/themes/load/${encodeURIComponent(path)}${qs}`)
  },
  saveTheme(formData) { return request("/api/themes", { method: "POST", form: formData }) },
  applyTheme(formData) { return request("/api/themes/apply", { method: "POST", form: formData }) },
  deleteTheme(path, type) {
    const qs = type ? `?type=${encodeURIComponent(type)}` : "?type=user"
    return request(`/api/themes/delete/${encodeURIComponent(path)}${qs}`, { method: "DELETE" })
  },
  async downloadTheme(formData) {
    const res = await fetch("/api/themes/download", { method: "POST", body: formData })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data?.message || data?.error || "Failed to export theme.")
    }
    return res.blob()
  },
  async getThemeAssetBlob(path, type, assetPath) {
    const encodedAsset = String(assetPath || "").split("/").map((seg) => encodeURIComponent(seg)).join("/")
    const qs = type ? `?type=${encodeURIComponent(type)}` : ""
    const res = await fetch(`/api/themes/asset/${encodeURIComponent(path)}/${encodedAsset}${qs}`)
    if (!res.ok) throw new Error("Failed to load theme asset.")
    return res.blob()
  },

  getFlmStatus() { return requestOk("/api/flm/status", { cache: "no-store" }) },
  getFlmReport(reportId) { return requestOk(`/api/flm/report/${encodeURIComponent(reportId)}`, { cache: "no-store" }) },
  flmDeleteReport(reportId) { return request(`/api/flm/report/${encodeURIComponent(reportId)}`, { method: "DELETE" }) },
  flmSelectPath(reportId, pathKey) { return request(`/api/flm/report/${encodeURIComponent(reportId)}/path`, { method: "POST", data: { pathKey } }) },
  flmAnalyze(routes, segmentRanges) { return request("/api/flm/analyze", { method: "POST", data: { routes, segmentRanges: segmentRanges || {} } }) },
  flmStopAnalyze() { return request("/api/flm/analyze/stop", { method: "POST" }) },
  flmApplyTrial(reportId, profileId) { return request("/api/flm/trials/apply", { method: "POST", data: { reportId, profileId } }) },
  flmRevertTrial() { return request("/api/flm/trials/revert", { method: "POST" }) },
  flmAcceptTrial() { return request("/api/flm/trials/accept", { method: "POST" }) },
  flmSaveFeedback(reportId, feedback) { return request("/api/flm/feedback", { method: "POST", data: { reportId, ...feedback } }) },
  flmSaveTune(name) { return request("/api/flm/saved-tunes", { method: "POST", data: { name } }) },
  flmApplySavedTune(tuneId) { return request(`/api/flm/saved-tunes/${encodeURIComponent(tuneId)}/apply`, { method: "POST" }) },
  flmRenameSavedTune(tuneId, name) { return request(`/api/flm/saved-tunes/${encodeURIComponent(tuneId)}`, { method: "PATCH", data: { name } }) },
  flmDeleteSavedTune(tuneId) { return request(`/api/flm/saved-tunes/${encodeURIComponent(tuneId)}`, { method: "DELETE" }) },
  flmSubmitTune(tuneId, discordUsername) { return request(`/api/flm/saved-tunes/${encodeURIComponent(tuneId)}/submit`, { method: "POST", data: { discordUsername } }) },

  async getVasmSnapshotBlob() {
    const res = await fetch("/api/v_asm/snapshot", { cache: "no-store" })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data?.error || res.statusText || "Failed to load snapshot")
    }
    return res.blob()
  },

  deleteVasmConfig() { return request("/api/v_asm/config", { method: "DELETE" }) },

  async getMemoryParam(key) {
    const res = await fetch(`/api/params_memory?key=${encodeURIComponent(key)}`, { cache: "no-store" })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data?.error || res.statusText || "Request failed")
    }
    return res.text()
  },

  deletePipConfig() { return request("/api/pip_preview/config", { method: "DELETE" }) },

  async pipSnapshotSource() {
    const res = await fetch("/api/pip_preview/snapshot")
    if (!res.ok) return parse(res)
    const contentType = res.headers.get("content-type") || ""
    if (contentType.includes("application/json")) {
      const data = await parse(res)
      if (!data.jpeg) throw new Error("Snapshot missing image data")
      return { src: `data:image/jpeg;base64,${data.jpeg}`, cleanup: null }
    }
    const src = URL.createObjectURL(await res.blob())
    return { src, cleanup: () => URL.revokeObjectURL(src) }
  },
}

export function showSnackbar(message, level = "info") {
  const wrapper = document.getElementById("snackbar_wrapper")
  if (!wrapper) return
  for (const el of Array.from(wrapper.children)) {
    el.classList.remove("show")
    el.remove()
  }
  const el = document.createElement("div")
  el.className = "snackbar show"
  el.setAttribute("role", level === "error" ? "alert" : "status")
  el.setAttribute("aria-live", level === "error" ? "assertive" : "polite")
  el.setAttribute("aria-atomic", "true")
  el.style.background = level === "error" ? "var(--error)" : "var(--color-confirm, #8b6cc5)"
  el.style.borderRadius = "var(--border-radius-base, 5px)"
  el.style.color = "var(--text-color, #fff)"
  el.style.margin = "0 auto var(--margin-base, 1rem)"
  el.style.padding = "var(--padding-base, 1rem)"
  el.style.textAlign = "center"
  el.textContent = message
  wrapper.appendChild(el)
  setTimeout(() => {
    el.classList.remove("show")
    setTimeout(() => el.remove(), 500)
  }, 2400)
}
