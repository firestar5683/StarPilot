import { html, reactive } from "/assets/vendor/arrow-core.js"

const MAX_RENDERED_ROUTES = 250
const ROUTE_FLUSH_INTERVAL_MS = 120
const STATUS_POLL_MS = 3000

const state = reactive({
  loadingRoutes: true,
  loadingWorkspace: true,
  runningAction: false,
  error: "",
  routes: [],
  selectedRoutes: [],
  segmentRanges: {},
  truncatedRoutes: false,
  routeProgress: 0,
  routeTotal: 0,
  connectDongleId: "",
  workspace: { reports: [], savedTunes: [], activeTrial: null, status: {} },
  status: {},
  report: null,
  feedbackAccepted: [],
  feedbackIgnored: [],
  feedbackNotes: "",
})

let routesAbortController = null
let routesRequestToken = 0
let pendingRoutes = []
let flushTimerId = null
let seenRouteNames = new Set()
let initialized = false
let statusPollHandle = null

function isTuningRouteActive() {
  return window.location.pathname === "/tuning" || window.location.pathname === "/lateral_maneuvers"
}

function formatTimestamp(value) {
  if (!value) return "Unknown Route"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return parsed.toLocaleString()
}

function formatReportSegmentRanges(report) {
  const ranges = report?.segmentRanges || {}
  const entries = Object.entries(ranges)
  if (!entries.length) return "Whole selected routes"
  return entries
    .map(([route, range]) => `${route}: ${range?.start ?? "first"}-${range?.end ?? "last"}`)
    .join(", ")
}

function safeCount(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function formatRouteLength(route) {
  const segmentCount = Math.max(0, Math.round(safeCount(route?.segmentCount)))
  if (!segmentCount) return "Length unavailable"
  const approximateMinutes = Math.max(1, Math.round(safeCount(route?.approxDurationSeconds) / 60) || segmentCount)
  const duration = approximateMinutes >= 60
    ? `~${Math.floor(approximateMinutes / 60)}h ${approximateMinutes % 60}m`
    : `~${approximateMinutes} min`
  return `${segmentCount} segment${segmentCount === 1 ? "" : "s"} (${duration})`
}

function connectRouteUrl(routeName) {
  const dongleId = String(state.connectDongleId || "").trim()
  const routeId = String(routeName || "").trim()
  if (!dongleId || !routeId) return ""
  return `https://connect.comma.ai/${encodeURIComponent(dongleId)}/${encodeURIComponent(routeId)}`
}

function formatStatusAge(updatedAt) {
  const updated = Number(updatedAt)
  if (!Number.isFinite(updated) || updated <= 0) return "unknown"
  const ageSec = Math.max(0, Math.round(Date.now() / 1000 - updated))
  if (ageSec < 5) return "just now"
  if (ageSec < 60) return `${ageSec}s ago`
  if (ageSec < 3600) return `${Math.round(ageSec / 60)}m ago`
  return `${Math.round(ageSec / 3600)}h ago`
}

function resetRouteStreamState() {
  pendingRoutes = []
  seenRouteNames = new Set()
  if (flushTimerId !== null) {
    clearTimeout(flushTimerId)
    flushTimerId = null
  }
}

function sortedRoutes() {
  return [...state.routes].sort((a, b) => {
    const aTime = Date.parse(a.timestamp)
    const bTime = Date.parse(b.timestamp)
    if (Number.isFinite(aTime) && Number.isFinite(bTime)) return bTime - aTime
    return String(b.timestamp || "").localeCompare(String(a.timestamp || ""))
  })
}

function flushPendingRoutes() {
  if (!pendingRoutes.length) return

  const availableSlots = Math.max(MAX_RENDERED_ROUTES - state.routes.length, 0)
  if (availableSlots <= 0) {
    pendingRoutes = []
    state.truncatedRoutes = true
    return
  }

  const toAppend = pendingRoutes.slice(0, availableSlots)
  pendingRoutes = []
  if (toAppend.length > 0) {
    state.routes = [...state.routes, ...toAppend]
  }
  if (state.routes.length >= MAX_RENDERED_ROUTES) {
    state.truncatedRoutes = true
  }
}

function enqueueRoutes(rawRoutes) {
  if (!Array.isArray(rawRoutes) || rawRoutes.length === 0) return
  const nextRoutes = []
  for (const route of rawRoutes) {
    const name = String(route?.name || "")
    if (!name || seenRouteNames.has(name)) continue
    seenRouteNames.add(name)
    nextRoutes.push({
      ...route,
      timestampLabel: formatTimestamp(route.timestamp),
    })
  }
  if (!nextRoutes.length) return

  pendingRoutes.push(...nextRoutes)
  if (flushTimerId === null) {
    flushTimerId = setTimeout(() => {
      flushTimerId = null
      flushPendingRoutes()
    }, ROUTE_FLUSH_INTERVAL_MS)
  }
}

async function fetchRoutes() {
  const requestToken = ++routesRequestToken
  if (routesAbortController) routesAbortController.abort()
  const controller = new AbortController()
  routesAbortController = controller

  try {
    state.loadingRoutes = true
    state.error = ""
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone
    const response = await fetch(`/api/routes?timezone=${encodeURIComponent(userTimezone)}`, { signal: controller.signal })
    if (!response.ok) throw new Error("Failed to load local routes.")

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      if (requestToken !== routesRequestToken) return

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split(/\r?\n\r?\n/)
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (!line.startsWith("data:")) continue
        try {
          const data = JSON.parse(line.substring(5).trim())
          if (data.progress !== undefined && data.total !== undefined) {
            state.routeProgress = safeCount(data.progress)
            state.routeTotal = safeCount(data.total)
          }
          if (typeof data.connectDongleId === "string") {
            state.connectDongleId = data.connectDongleId
          }
          if (Array.isArray(data.routes)) {
            enqueueRoutes(data.routes)
          }
        } catch (error) {
          console.error("[flm] failed to parse route payload", error)
        }
      }
    }

    flushPendingRoutes()
  } catch (error) {
    if (error?.name !== "AbortError") {
      state.error = error?.message || "Failed to load local routes."
    }
  } finally {
    if (requestToken === routesRequestToken) {
      flushPendingRoutes()
      state.loadingRoutes = false
      if (routesAbortController === controller) {
        routesAbortController = null
      }
    }
  }
}

async function fetchWorkspace() {
  try {
    state.loadingWorkspace = true
    const response = await fetch("/api/flm/workspace")
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to load tuning workspace.")
    state.workspace = payload
    state.status = payload.status || {}
  } catch (error) {
    state.error = error?.message || "Failed to load tuning workspace."
  } finally {
    state.loadingWorkspace = false
  }
}

function syncFeedbackState(report) {
  const feedback = report?.feedback || {}
  state.feedbackAccepted = Array.isArray(feedback.acceptedDimensions) ? [...feedback.acceptedDimensions] : []
  state.feedbackIgnored = Array.isArray(feedback.ignoredDimensions) ? [...feedback.ignoredDimensions] : []
  state.feedbackNotes = typeof feedback.notes === "string" ? feedback.notes : ""
}

async function loadReport(reportId) {
  if (!reportId) return
  try {
    const response = await fetch(`/api/flm/report/${encodeURIComponent(reportId)}`)
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to load tuning report.")
    state.report = payload
    syncFeedbackState(payload)
    await fetchWorkspace()
  } catch (error) {
    state.error = error?.message || "Failed to load tuning report."
  }
}

async function deleteReport(reportId) {
  if (!reportId || state.runningAction) return
  if (!window.confirm("Delete this saved tuning report and its generated trial data?")) return

  state.runningAction = true
  try {
    const response = await fetch(`/api/flm/report/${encodeURIComponent(reportId)}`, { method: "DELETE" })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to delete tuning report.")

    if (state.report?.reportId === reportId) {
      state.report = null
      syncFeedbackState(null)
    }
    state.workspace = payload.workspace || state.workspace
    state.status = { ...state.status, ...(payload.workspace?.status || {}) }
    showSnackbar(payload.message || "Deleted tuning report.")
  } catch (error) {
    state.error = error?.message || "Failed to delete tuning report."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function fetchStatus() {
  try {
    const response = await fetch("/api/flm/status")
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to load tuning status.")
    state.status = {
      ...(payload.status || {}),
      isOnroad: !!payload.isOnroad,
      laneCentering: !!payload.laneCentering,
    }
    if (payload.activeTrial !== undefined) {
      state.workspace = {
        ...state.workspace,
        activeTrial: payload.activeTrial,
        reports: payload.reports || state.workspace.reports,
        savedTunes: payload.savedTunes || state.workspace.savedTunes,
      }
    }
    const reportId = state.status.reportId
    if (reportId && state.report?.reportId !== reportId) {
      await loadReport(reportId)
    }
  } catch (error) {
    state.error = error?.message || "Failed to load tuning status."
  }
}

function stopPolling() {
  if (statusPollHandle) {
    clearTimeout(statusPollHandle)
    statusPollHandle = null
  }
}

function ensurePolling() {
  if (statusPollHandle) return

  const poll = async () => {
    if (!isTuningRouteActive()) {
      stopPolling()
      return
    }
    if (document.visibilityState === "visible") {
      await fetchStatus()
    }
    statusPollHandle = setTimeout(poll, STATUS_POLL_MS)
  }

  statusPollHandle = setTimeout(poll, STATUS_POLL_MS)
}

function toggleRouteSelection(routeName) {
  const current = new Set(state.selectedRoutes)
  if (current.has(routeName)) {
    current.delete(routeName)
  } else {
    current.add(routeName)
  }
  state.selectedRoutes = [...current]
}

function setSegmentRange(routeName, key, value) {
  const cleaned = String(value ?? "").replace(/[^\d]/g, "")
  state.segmentRanges = {
    ...state.segmentRanges,
    [routeName]: {
      ...(state.segmentRanges[routeName] || {}),
      [key]: cleaned,
    },
  }
}

function selectedSegmentRanges() {
  const ranges = {}
  for (const routeName of state.selectedRoutes) {
    const selected = state.segmentRanges[routeName] || {}
    const start = String(selected.start ?? "").trim()
    const end = String(selected.end ?? "").trim()
    if (start || end) {
      ranges[routeName] = {
        start: start || null,
        end: end || null,
      }
    }
  }
  return ranges
}

function clearSelections() {
  state.selectedRoutes = []
  state.segmentRanges = {}
}

async function runAnalyze() {
  if (!state.selectedRoutes.length || state.runningAction) return
  state.runningAction = true
  try {
    const response = await fetch("/api/flm/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        routes: state.selectedRoutes,
        segmentRanges: selectedSegmentRanges(),
      }),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to start tuning analysis.")
    state.status = payload.status || {}
    showSnackbar(payload.message || "FLM analysis started.")
  } catch (error) {
    state.error = error?.message || "Failed to start tuning analysis."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function stopAnalyze() {
  if (state.runningAction) return
  state.runningAction = true
  try {
    const response = await fetch("/api/flm/analyze/stop", { method: "POST" })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to stop tuning analysis.")
    state.status = payload.status || {}
    showSnackbar(payload.message || "FLM analysis stopped.")
  } catch (error) {
    state.error = error?.message || "Failed to stop tuning analysis."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function applyProfile(profileId) {
  if (!state.report?.reportId || !profileId || state.runningAction) return
  state.runningAction = true
  try {
    const response = await fetch("/api/flm/trials/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reportId: state.report.reportId, profileId }),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to apply trial profile.")
    state.error = ""
    await fetchWorkspace()
    showSnackbar(payload.message || "Trial profile applied.")
  } catch (error) {
    state.error = error?.message || "Failed to apply trial profile."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function saveCurrentTune() {
  if (state.runningAction || !state.workspace?.activeTrial) return
  const defaultName = state.workspace.activeTrial.profileLabel || state.workspace.currentCarFingerprint || "Saved Tune"
  const name = window.prompt("Name this tune", defaultName)
  if (name === null) return

  state.runningAction = true
  try {
    const response = await fetch("/api/flm/saved-tunes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to save the active tune.")
    state.error = ""
    state.workspace = payload.workspace || state.workspace
    showSnackbar(payload.message || "Saved the active tune.")
  } catch (error) {
    state.error = error?.message || "Failed to save the active tune."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function applySavedTune(tuneId) {
  if (!tuneId || state.runningAction) return
  state.runningAction = true
  try {
    const response = await fetch(`/api/flm/saved-tunes/${encodeURIComponent(tuneId)}/apply`, { method: "POST" })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to apply saved tune.")
    state.error = ""
    state.workspace = payload.workspace || state.workspace
    showSnackbar(payload.message || "Saved tune applied.")
  } catch (error) {
    state.error = error?.message || "Failed to apply saved tune."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function renameSavedTune(tune) {
  if (!tune?.tuneId || state.runningAction) return
  const name = window.prompt("Rename saved tune", tune.name || "Saved Tune")
  if (name === null) return

  state.runningAction = true
  try {
    const response = await fetch(`/api/flm/saved-tunes/${encodeURIComponent(tune.tuneId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to rename saved tune.")
    state.error = ""
    state.workspace = payload.workspace || state.workspace
    showSnackbar(payload.message || "Saved tune renamed.")
  } catch (error) {
    state.error = error?.message || "Failed to rename saved tune."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function deleteSavedTune(tune) {
  if (!tune?.tuneId || state.runningAction) return
  if (!window.confirm(`Delete saved tune "${tune.name || "Saved Tune"}"?`)) return

  state.runningAction = true
  try {
    const response = await fetch(`/api/flm/saved-tunes/${encodeURIComponent(tune.tuneId)}`, { method: "DELETE" })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to delete saved tune.")
    state.error = ""
    state.workspace = payload.workspace || state.workspace
    showSnackbar(payload.message || "Saved tune deleted.")
  } catch (error) {
    state.error = error?.message || "Failed to delete saved tune."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function submitSavedTune(tune) {
  if (!tune?.tuneId || state.runningAction) return
  const approved = window.confirm(
    "Think this FLM tune is genuinely good and worth sharing? Send it to Firestar for review and possible inclusion in future tuning. Only the tune values, car identity, and your Discord username are sent; routes and driving logs are not included."
  )
  if (!approved) return

  const discordUsername = window.prompt("Enter your Discord username so Firestar can credit you.", "")
  if (discordUsername === null || !discordUsername.trim()) return

  state.runningAction = true
  try {
    const response = await fetch(`/api/flm/saved-tunes/${encodeURIComponent(tune.tuneId)}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ discordUsername: discordUsername.trim() }),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to submit saved tune.")
    state.error = ""
    showSnackbar(payload.message || "Tune submitted to Firestar for review.")
  } catch (error) {
    state.error = error?.message || "Failed to submit saved tune."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function selectPath(pathKey) {
  if (!state.report?.reportId || !pathKey || state.runningAction) return
  if (pathKey === (state.report.selectedPathKey || state.report.primaryPathKey)) return

  state.runningAction = true
  try {
    const response = await fetch(`/api/flm/report/${encodeURIComponent(state.report.reportId)}/path`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pathKey }),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to select tuning path.")
    state.report = payload.report
    syncFeedbackState(state.report)
    showSnackbar(payload.message || "Tuning path selected.")
  } catch (error) {
    state.error = error?.message || "Failed to select tuning path."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function revertProfile() {
  if (state.runningAction) return
  state.runningAction = true
  try {
    const response = await fetch("/api/flm/trials/revert", { method: "POST" })
    const body = await response.text()
    let payload
    try { payload = body ? JSON.parse(body) : {} } catch (_) {
      payload = { error: body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim() }
    }
    if (!response.ok) throw new Error(payload.error || "Failed to revert trial profile.")
    state.error = ""
    await fetchWorkspace()
    showSnackbar(payload.message || "Trial profile reverted.")
  } catch (error) {
    state.error = error?.message || "Failed to revert trial profile."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

async function acceptCurrentAsBaseline() {
  if (state.runningAction || !state.workspace?.activeTrial) return
  if (!window.confirm("Keep the currently applied tuning values and end this trial? This does not restore the previous tune.")) return

  state.runningAction = true
  try {
    const response = await fetch("/api/flm/trials/accept", { method: "POST" })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to keep the current tune.")
    state.error = ""
    state.workspace = payload.workspace || state.workspace
    showSnackbar(payload.message || "Current tune kept as the new baseline.")
  } catch (error) {
    state.error = error?.message || "Failed to keep the current tune."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

function setDimensionFeedback(dimensionId, mode) {
  const accepted = new Set(state.feedbackAccepted)
  const ignored = new Set(state.feedbackIgnored)
  accepted.delete(dimensionId)
  ignored.delete(dimensionId)
  if (mode === "accepted") accepted.add(dimensionId)
  if (mode === "ignored") ignored.add(dimensionId)
  state.feedbackAccepted = [...accepted]
  state.feedbackIgnored = [...ignored]
}

async function updateDimensionFeedback(dimensionId, mode) {
  if (state.runningAction) return
  const current = feedbackStateFor(dimensionId)
  setDimensionFeedback(dimensionId, current === mode ? "unset" : mode)
  await saveFeedback()
}

async function saveFeedback() {
  if (!state.report?.reportId || state.runningAction) return
  state.runningAction = true
  try {
    const response = await fetch("/api/flm/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reportId: state.report.reportId,
        acceptedDimensions: state.feedbackAccepted,
        ignoredDimensions: state.feedbackIgnored,
        notes: state.feedbackNotes,
      }),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || "Failed to save tuning feedback.")
    state.report = payload.report || {
      ...state.report,
      feedback: payload.feedback,
      profiles: payload.profiles || state.report.profiles,
    }
    syncFeedbackState(state.report)
    await fetchWorkspace()
    showSnackbar(payload.message || "Feedback saved.")
  } catch (error) {
    state.error = error?.message || "Failed to save tuning feedback."
    showSnackbar(state.error, "error")
  } finally {
    state.runningAction = false
  }
}

function feedbackStateFor(dimensionId) {
  if (state.feedbackAccepted.includes(dimensionId)) return "accepted"
  if (state.feedbackIgnored.includes(dimensionId)) return "ignored"
  return "unset"
}

function initialize() {
  if (initialized) return
  initialized = true
  resetRouteStreamState()
  fetchRoutes()
  fetchWorkspace().then(() => {
    const latestReport = state.workspace?.reports?.[0]?.reportId
    if (latestReport) loadReport(latestReport)
  })
  fetchStatus()
  ensurePolling()
}

function renderCurve(values) {
  return `[${(values || []).map((value) => Number(value).toFixed(3)).join(", ")}]`
}

function reportPaths() {
  if (Array.isArray(state.report?.paths) && state.report.paths.length) {
    return state.report.paths
  }
  if (!state.report) return []
  return [{
    key: state.report.primaryPathKey || "cleanup_pass",
    title: "Recommendations",
    description: "",
    whenToUse: "",
    whySelected: "",
    isPrimary: true,
    suggestions: state.report.suggestions || [],
    profiles: state.report.profiles || [],
  }]
}

function primaryPath() {
  const paths = reportPaths()
  const selectedPathKey = state.report?.selectedPathKey || state.report?.primaryPathKey
  return paths.find((path) => path.key === selectedPathKey) || paths.find((path) => path.isPrimary) || paths[0] || null
}

function allReportProfiles() {
  const pathProfiles = reportPaths().flatMap((path) => path.profiles || [])
  return pathProfiles.length ? pathProfiles : (state.report?.profiles || [])
}

function activeTrialProfile() {
  const activeTrial = state.workspace?.activeTrial
  if (!activeTrial) return null
  if (activeTrial.reportId === state.report?.reportId) {
    const reportProfile = allReportProfiles().find((profile) => profile.id === activeTrial.profileId)
    if (reportProfile) return reportProfile
  }
  return {
    id: activeTrial.profileId,
    genericParams: activeTrial.appliedGenericParams || {},
    flmOverrides: {
      baseFrictionThresholds: activeTrial.appliedFrictionThresholds || {},
      vehicleKnobs: activeTrial.appliedVehicleKnobs || {},
    },
  }
}

function mergedFlmOverrides() {
  const current = state.report?.currentParams?.FLMActiveOverrides || {}
  const trial = activeTrialProfile()?.flmOverrides || {}
  return {
    baseFrictionThresholds: {
      ...(current.baseFrictionThresholds || {}),
      ...(trial.baseFrictionThresholds || {}),
    },
    vehicleKnobs: {
      ...(current.vehicleKnobs || {}),
      ...(trial.vehicleKnobs || {}),
    },
  }
}

function formatTuneComparisonValue(value) {
  if (Array.isArray(value)) return renderCurve(value)
  if (typeof value === "boolean") return value ? "On" : "Off"
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(3) : String(value ?? "-")
}

function tuneComparisonRows() {
  const stock = state.report?.stockParams
  const current = state.report?.currentParams
  if (!stock || !current) return []

  const trialGeneric = activeTrialProfile()?.genericParams || {}
  const angleControl = state.report?.car?.controlPath === "angle"
  const genericParams = angleControl ? [
    ["Auto steer delay", "UseAutoSteerDelay"],
    ["Steer delay", "SteerDelay"],
    ["Steer ratio", "SteerRatio"],
  ] : [
    ["Lat accel", "SteerLatAccel"],
    ["Friction", "SteerFriction"],
    ["Auto steer delay", "UseAutoSteerDelay"],
    ["Steer delay", "SteerDelay"],
    ["Steer ratio", "SteerRatio"],
    ["KP", "SteerKP"],
  ]
  const rows = genericParams.map(([label, key]) => ({
    key,
    label,
    stock: stock[key],
    current: Object.hasOwn(trialGeneric, key) ? trialGeneric[key] : current[key],
  }))

  if (angleControl) return rows

  const overrides = mergedFlmOverrides()
  for (const [family, payload] of Object.entries(stock.FLMBaseFrictionThresholds || {})) {
    rows.push({
      key: `friction-threshold-${family}`,
      label: `${family} friction threshold`,
      stock: payload?.values || [],
      current: overrides.baseFrictionThresholds?.[family]?.values || payload?.values || [],
    })
  }

  for (const [symbol, currentValue] of Object.entries(overrides.vehicleKnobs || {})) {
    if (!Object.hasOwn(stock.FLMVehicleKnobs || {}, symbol)) continue
    rows.push({
      key: symbol,
      label: symbol.split(".").slice(1).join("."),
      stock: stock.FLMVehicleKnobs[symbol],
      current: currentValue,
      codeLabel: symbol,
    })
  }
  return rows
}

function comparisonValueChanged(row) {
  if (Array.isArray(row.stock) || Array.isArray(row.current)) {
    return JSON.stringify(row.stock || []) !== JSON.stringify(row.current || [])
  }
  return Math.abs(Number(row.stock) - Number(row.current)) > 0.0005
}

function renderTuneComparison() {
  const rows = tuneComparisonRows()
  if (!rows.length) return ""
  const profile = activeTrialProfile()
  const angleControl = state.report?.car?.controlPath === "angle"
  return html`
    <div class="flmCardSubsection flmTuneComparison">
      <div class="flmCardHeader">
        <div>
          <h4>${angleControl ? "Applicable Angle Settings" : "Stock vs Current FLM"}</h4>
          <p class="longManeuverMuted">
            ${angleControl
              ? "Current applicable values captured when this route was analyzed."
              : profile
                ? `Includes active trial: ${profile.pathLabel || "FLM"} / ${profile.label}`
                : "Current values captured when this route was analyzed."}
          </p>
          ${angleControl ? html`
            <p class="longManeuverMuted">Torque-only lateral acceleration, friction, and KP values do not apply to this angle-control car.</p>
          ` : ""}
        </div>
      </div>
      <div class="flmTuneComparisonTable">
        <div class="flmTuneComparisonHeader">Parameter</div>
        <div class="flmTuneComparisonHeader">Stock</div>
        <div class="flmTuneComparisonArrow"></div>
        <div class="flmTuneComparisonHeader">${angleControl ? "Current" : "FLM"}</div>
        ${rows.map((row) => html`
          <div class="flmTuneComparisonLabel" title="${row.codeLabel || row.key}">${row.label}</div>
          <div>${formatTuneComparisonValue(row.stock)}</div>
          <div class="flmTuneComparisonArrow">&gt;</div>
          <div class="${comparisonValueChanged(row) ? "flmTuneComparisonChanged" : ""}">${formatTuneComparisonValue(row.current)}</div>
        `)}
      </div>
    </div>
  `
}

const TRACKING_OVERVIEW_GROUPS = [
  { title: "Straight Tracking", buckets: new Set(["center_chatter"]) },
  {
    title: "Curve Response",
    buckets: new Set([
      "understeer", "oversteer", "early_turn_in", "late_turn_in",
      "notchy_mid_curve", "low_speed_unwillingness", "saturation_limited",
    ]),
  },
  { title: "Unwind Response", buckets: new Set(["unwind_too_slow", "unwind_too_fast"]) },
]

function hasUsablePlotData(suggestion) {
  const plot = suggestion?.plotData
  return !!(
    plot?.driverOverrideFree !== false &&
    Array.isArray(plot?.times) && plot.times.length > 1 &&
    Array.isArray(plot?.desired) && plot.desired.length === plot.times.length &&
    Array.isArray(plot?.actual) && plot.actual.length === plot.times.length
  )
}

function trackingOverviewItems() {
  const suggestions = [...(primaryPath()?.suggestions || [])]
    .filter(hasUsablePlotData)
    .sort((left, right) => Number(right.severity || 0) - Number(left.severity || 0))
  const selected = []
  const selectedDimensions = new Set()

  for (const group of TRACKING_OVERVIEW_GROUPS) {
    const match = suggestions.find((suggestion) => (
      group.buckets.has(suggestion.bucket) && !selectedDimensions.has(suggestion.dimensionId)
    ))
    if (!match) continue
    selected.push({ ...match, overviewTitle: group.title })
    selectedDimensions.add(match.dimensionId)
  }

  for (const suggestion of suggestions) {
    if (selected.length >= 3) break
    if (selectedDimensions.has(suggestion.dimensionId)) continue
    selected.push({ ...suggestion, overviewTitle: "Additional Evidence" })
    selectedDimensions.add(suggestion.dimensionId)
  }

  return selected.slice(0, 3)
}

function plotPoints(times, values, duration, yMin, yMax) {
  const xStart = 34
  const xEnd = 410
  const yStart = 12
  const yEnd = 136
  const ySpan = Math.max(yMax - yMin, 0.001)
  return times.map((time, index) => {
    const x = xStart + (Math.max(0, Number(time)) / duration) * (xEnd - xStart)
    const y = yEnd - ((Number(values[index]) - yMin) / ySpan) * (yEnd - yStart)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(" ")
}

function renderTrackingPlot(plot) {
  const times = plot.times.map(Number)
  const desired = plot.desired.map(Number)
  const actual = plot.actual.map(Number)
  const duration = Math.max(Number(plot.windowDurationSec), times[times.length - 1] || 0, 0.1)
  const allValues = [...desired, ...actual, 0].filter(Number.isFinite)
  const rawMin = Math.min(...allValues)
  const rawMax = Math.max(...allValues)
  const padding = Math.max((rawMax - rawMin) * 0.12, 0.08)
  const yMin = rawMin - padding
  const yMax = rawMax + padding
  const desiredPoints = plotPoints(times, desired, duration, yMin, yMax)
  const actualPoints = plotPoints(times, actual, duration, yMin, yMax)
  const eventStart = Math.max(0, Math.min(Number(plot.eventStartSec) || 0, duration))
  const eventEnd = Math.max(eventStart, Math.min(Number(plot.eventEndSec) || eventStart, duration))
  const eventX = 34 + (eventStart / duration) * 376
  const eventWidth = Math.max(((eventEnd - eventStart) / duration) * 376, 2)
  const zeroY = 136 - ((0 - yMin) / Math.max(yMax - yMin, 0.001)) * 124

  return html`
    <svg class="flmTrackingPlot" viewBox="0 0 420 158" role="img" aria-label="Desired versus actual lateral acceleration">
      <rect class="flmTrackingPlotBackground" x="0" y="0" width="420" height="158" rx="10"></rect>
      <rect class="flmTrackingEventRegion" x="${eventX}" y="12" width="${eventWidth}" height="124"></rect>
      <line class="flmTrackingZero" x1="34" y1="${zeroY}" x2="410" y2="${zeroY}"></line>
      <line class="flmTrackingAxis" x1="34" y1="12" x2="34" y2="136"></line>
      <line class="flmTrackingAxis" x1="34" y1="136" x2="410" y2="136"></line>
      <polyline class="flmTrackingDesired" points="${desiredPoints}"></polyline>
      <polyline class="flmTrackingActual" points="${actualPoints}"></polyline>
      <text class="flmTrackingAxisLabel" x="2" y="18">${yMax.toFixed(1)}</text>
      <text class="flmTrackingAxisLabel" x="2" y="138">${yMin.toFixed(1)}</text>
      <text class="flmTrackingAxisLabel" x="34" y="152">0s</text>
      <text class="flmTrackingAxisLabel" x="384" y="152">${duration.toFixed(1)}s</text>
    </svg>
  `
}

function renderTrackingOverview() {
  const items = trackingOverviewItems()
  if (!items.length) return ""

  return html`
    <div class="flmCardSubsection flmTrackingOverview">
      <div class="flmCardHeader">
        <div>
          <h4>Tracking Overview</h4>
          <p class="longManeuverMuted">
            Desired vs actual lateral acceleration (m/s^2) in representative intervention-free windows. The shaded area is the classified event.
          </p>
        </div>
        <div class="flmTrackingLegend" aria-label="Plot legend">
          <span><i class="desired"></i>Desired</span>
          <span><i class="actual"></i>Actual</span>
        </div>
      </div>

      <div class="flmTrackingNotice">
        No fit score by design. Small phase separation is normal, and closer traces do not automatically mean the steering feels better.
      </div>

      <div class="flmTrackingGrid">
        ${items.map((item) => html`
          <article class="flmTrackingCard">
            <div class="flmTrackingCardHeader">
              <div>
                <strong>${item.overviewTitle}</strong>
                <span>${String(item.bucket || "event").replace(/_/g, " ")}</span>
              </div>
              <span>${Number(item.plotData.meanSpeedMph || 0).toFixed(1)} mph</span>
            </div>
            ${renderTrackingPlot(item.plotData)}
            <div class="flmTrackingMeta">
              <span>${item.evidence?.directionBias || item.plotData.direction || "center"}</span>
              <span>${item.evidence?.speedBand || item.plotData.speedBand || "mixed"}</span>
              <span>${Number(item.plotData.eventDurationSec || 0).toFixed(1)}s event</span>
            </div>
            <small title="${item.plotData.segmentLabel || ""}">${item.plotData.segmentLabel || "Unknown segment"}</small>
          </article>
        `)}
      </div>
    </div>
  `
}

function renderProfile(profile) {
  const genericEntries = Object.entries(profile.genericParams || {}).filter(([key]) => key !== "AdvancedLateralTune")
  const frictionEntries = Object.entries(profile.flmOverrides?.baseFrictionThresholds || {})
  const vehicleKnobEntries = Object.entries(profile.flmOverrides?.vehicleKnobs || {})
  return html`
    <div class="flmCard">
      <div class="flmCardHeader">
        <div>
          <h4>${profile.label}</h4>
          <p class="longManeuverMuted">${profile.description}</p>
        </div>
        <button
          class="longManeuverButton"
          disabled="${() => state.runningAction || state.workspace?.activeTrial?.rollbackAvailable === false}"
          @click="${() => applyProfile(profile.id)}">
          Apply Trial
        </button>
      </div>

      <div class="flmProfileGrid">
        <div>
          <h5>Generic Params</h5>
          <ul>
            ${genericEntries.length
              ? genericEntries.map(([key, value]) => html`<li><code>${key}</code>: ${String(value)}</li>`)
              : html`<li>None</li>`}
          </ul>
        </div>
        <div>
          <h5>FLM Overrides</h5>
          <ul>
            ${frictionEntries.map(([family, payload]) => html`<li><code>${family}</code>: ${renderCurve(payload?.values || [])}</li>`)}
            ${vehicleKnobEntries.map(([key, value]) => html`<li><code>${key}</code>: ${Number(value).toFixed(3)}</li>`)}
            ${!frictionEntries.length && !vehicleKnobEntries.length ? html`<li>None</li>` : ""}
          </ul>
        </div>
      </div>
    </div>
  `
}

function renderSuggestion(suggestion) {
  const currentVsSuggested = suggestion.currentVsSuggested
  return html`
    <div class="flmCard">
      <div class="flmCardHeader">
        <div>
          <h4>${suggestion.bucket.replace(/_/g, " ")}</h4>
          <p class="longManeuverMuted">
            ${suggestion.evidence?.speedBand || "mixed"} |
            ${suggestion.evidence?.directionBias || "center"} |
            ${safeCount(suggestion.evidence?.eventCount)} event(s)
          </p>
        </div>
        <div class="flmFeedbackButtons">
          <button
            class="${() => `longManeuverButton ${feedbackStateFor(suggestion.dimensionId) === "accepted" ? "selected" : ""}`}"
            aria-pressed="${() => feedbackStateFor(suggestion.dimensionId) === "accepted" ? "true" : "false"}"
            disabled="${() => state.runningAction}"
            @click="${() => updateDimensionFeedback(suggestion.dimensionId, "accepted")}">
            ${() => feedbackStateFor(suggestion.dimensionId) === "accepted" ? "Matched" : "Matches Experience"}
          </button>
          <button
            class="${() => `longManeuverButton danger ${feedbackStateFor(suggestion.dimensionId) === "ignored" ? "selected" : ""}`}"
            aria-pressed="${() => feedbackStateFor(suggestion.dimensionId) === "ignored" ? "true" : "false"}"
            disabled="${() => state.runningAction}"
            @click="${() => updateDimensionFeedback(suggestion.dimensionId, "ignored")}">
            ${() => feedbackStateFor(suggestion.dimensionId) === "ignored" ? "Ignored" : "Ignore"}
          </button>
        </div>
      </div>

      <p><strong>Observed behavior:</strong> ${suggestion.observedBehavior}</p>
      <p><strong>Likely interpretation:</strong> ${suggestion.likelyInterpretation}</p>
      <p><strong>Primary adjustment:</strong> ${suggestion.primaryAdjustment}</p>
      <p><strong>What not to touch yet:</strong> ${suggestion.whatNotToTouchYet}</p>
      <p><strong>If that was wrong, next thing to try:</strong> ${suggestion.ifThatWasWrong}</p>
      <p><strong>Strongest segments:</strong> ${(suggestion.evidence?.segments || []).map((segment) => segment.label).join(", ") || "none"}</p>

      ${currentVsSuggested
        ? html`
          <div class="flmDeltaBox">
            <strong>Current vs suggested:</strong>
            ${currentVsSuggested.type === "friction_curve"
              ? html`
                <p><code>${currentVsSuggested.family}</code> current: ${renderCurve(currentVsSuggested.current)}</p>
                <p><code>${currentVsSuggested.family}</code> suggested: ${renderCurve(currentVsSuggested.suggested)}</p>
              `
              : html`
                <p>
                  <code>${currentVsSuggested.paramKey || currentVsSuggested.symbol}</code>:
                  ${Number(currentVsSuggested.current).toFixed(3)} -> ${Number(currentVsSuggested.suggested).toFixed(3)}
                </p>
              `}
          </div>
        `
        : html`<p class="longManeuverMuted">No trial adjustment suggested for this dimension.</p>`}

    </div>
  `
}

function renderPathSummary(path) {
  const selected = path.key === (state.report?.selectedPathKey || state.report?.primaryPathKey)
  return html`
    <div class="flmCard">
      <div class="flmCardHeader">
        <div>
          <h4>${path.title}</h4>
          <p class="longManeuverMuted">
            ${path.isPrimary ? "Analyzer recommended" : "Alternate path"}${selected ? " / Active" : ""}
          </p>
        </div>
        <button
          class="longManeuverButton"
          disabled="${() => state.runningAction || selected}"
          @click="${() => selectPath(path.key)}">
          ${selected ? "Active Path" : `Use ${path.title}`}
        </button>
      </div>
      <p>${path.description || ""}</p>
      <p><strong>Why this path:</strong> ${path.whySelected || "No path note available."}</p>
      <p><strong>When to use it:</strong> ${path.whenToUse || "Use the path that best matches the spread of the problem."}</p>
    </div>
  `
}

export function Tuning() {
  initialize()

  return html`
    <div class="longManeuverPage">
      <h2>Lateral Tuning</h2>

      <div class="longManeuverCard">
        <p class="longManeuverIntro">
          Analyze one or more local routes, review deterministic lateral findings, apply a bounded trial, drive, then revert or refine.
        </p>
        <p class="longManeuverError">
          <strong>Before using FLM:</strong> turn Lane Centering off. FLM must analyze the model's unmodified lateral request; routes recorded with Lane Centering enabled are excluded.
        </p>

        <div class="longManeuverActions">
          <button
            class="longManeuverButton"
            disabled="${() => state.runningAction || state.selectedRoutes.length === 0 || !!state.status?.isOnroad || !!state.status?.laneCentering}"
            @click="${runAnalyze}">
            Analyze Selected Routes
          </button>
          <button
            class="longManeuverButton danger"
            disabled="${() => state.runningAction || !state.status?.running}"
            @click="${stopAnalyze}">
            Stop Analysis
          </button>
          <button
            class="longManeuverButton"
            disabled="${() => state.runningAction || !state.workspace?.activeTrial || state.workspace.activeTrial.rollbackAvailable === false}"
            @click="${revertProfile}">
            Revert Trial
          </button>
          <button
            class="longManeuverButton"
            disabled="${() => state.runningAction || !state.workspace?.activeTrial}"
            @click="${saveCurrentTune}">
            Save Tune
          </button>
          ${() => state.workspace?.activeTrial?.rollbackAvailable === false ? html`
            <button
              class="longManeuverButton"
              disabled="${() => state.runningAction}"
              @click="${acceptCurrentAsBaseline}">
              Keep Current as Baseline
            </button>
          ` : ""}
          <button
            class="longManeuverButton"
            disabled="${() => state.runningAction}"
            @click="${() => {
              state.routes = []
              state.routeProgress = 0
              state.routeTotal = 0
              state.truncatedRoutes = false
              resetRouteStreamState()
              fetchRoutes()
              fetchWorkspace()
              fetchStatus()
            }}">
            Refresh
          </button>
        </div>

        ${() => state.error ? html`<p class="longManeuverError">${state.error}</p>` : ""}

        <div class="longManeuverStatusGrid">
          <p><strong>Status:</strong> ${() => state.status?.state || "idle"}</p>
          <p><strong>Running:</strong> ${() => state.status?.running ? "Yes" : "No"}</p>
          <p><strong>Onroad:</strong> ${() => state.status?.isOnroad ? "Yes" : "No"}</p>
          <p><strong>Updated:</strong> ${() => formatStatusAge(state.status?.updatedAt)}</p>
          <p><strong>Selected Routes:</strong> ${() => state.selectedRoutes.length}</p>
          <p><strong>Progress:</strong> ${() => `${safeCount(state.status?.progress)}/${safeCount(state.status?.total)}`}</p>
          <p><strong>Active Trial:</strong> ${() => state.workspace?.activeTrial?.profileLabel || state.workspace?.activeTrial?.profileId || "None"}</p>
        </div>

        ${() => state.status?.isOnroad ? html`
          <p class="longManeuverError">FLM analysis is offroad-only. Stop the car and go offroad before starting a run.</p>
        ` : ""}

        ${() => state.status?.laneCentering ? html`
          <p class="longManeuverError">FLM is blocked while Lane Centering is enabled. Turn it off before starting analysis.</p>
        ` : ""}

        ${() => state.workspace?.activeTrial?.rollbackAvailable === false ? html`
          <p class="longManeuverError">
            The original rollback data is unavailable. Keep the current tune as the new baseline before applying another trial.
          </p>
        ` : ""}

        ${() => state.status?.currentSegment ? html`
          <div class="longManeuverCurrent">
            <p><strong>Current Segment:</strong> ${state.status.currentSegment}</p>
            ${state.status.segmentTimeoutSeconds ? html`
              <p class="longManeuverMuted">Segments that take longer than ${safeCount(state.status.segmentTimeoutSeconds)} seconds are skipped automatically.</p>
            ` : ""}
          </div>
        ` : ""}

        ${() => state.status?.lastSkippedSegment ? html`
          <p class="longManeuverMuted">Skipped ${state.status.lastSkippedSegment} after it exceeded the read limit.</p>
        ` : ""}

        <div class="flmTwoColumn">
          <section class="flmCard">
            <div class="flmCardHeader">
              <div>
                <h3>Local Routes</h3>
                <p class="longManeuverMuted">
                  Pick up to 8 routes from the device. Optionally limit each route to a segment range. The analyzer prefers rlogs and falls back to qlogs when needed.
                </p>
              </div>
              <button class="longManeuverButton" @click="${clearSelections}">Clear</button>
            </div>

            ${() => state.loadingRoutes ? html`<p class="longManeuverMuted">Loading local routes...</p>` : ""}
            ${() => state.routeTotal ? html`<p class="longManeuverMuted">Route index: ${state.routeProgress}/${state.routeTotal}</p>` : ""}
            ${() => state.truncatedRoutes ? html`<p class="longManeuverMuted">Showing the first ${MAX_RENDERED_ROUTES} routes only.</p>` : ""}

            <div class="flmRouteList">
              ${() => sortedRoutes().map((route) => html`
                <div class="flmRouteSelection">
                  <div class="flmRouteRow">
                    <label class="flmRouteItem">
                      <input
                        type="checkbox"
                        checked="${() => state.selectedRoutes.includes(route.name)}"
                        @change="${() => toggleRouteSelection(route.name)}" />
                      <span>
                        <strong>${route.timestampLabel}</strong>
                        <small>${route.name}</small>
                        <small>${formatRouteLength(route)}</small>
                      </span>
                    </label>
                    ${() => connectRouteUrl(route.name) ? html`
                      <a
                        class="flmConnectLink"
                        href="${connectRouteUrl(route.name)}"
                        target="_blank"
                        rel="noopener noreferrer">Connect</a>
                    ` : ""}
                  </div>
                  ${() => state.selectedRoutes.includes(route.name) ? html`
                    <div class="flmSegmentRange">
                      <span>Segments</span>
                      <input
                        type="number"
                        min="0"
                        inputmode="numeric"
                        placeholder="First"
                        value="${() => state.segmentRanges[route.name]?.start || ""}"
                        @input="${event => setSegmentRange(route.name, "start", event.target.value)}" />
                      <span>to</span>
                      <input
                        type="number"
                        min="0"
                        inputmode="numeric"
                        placeholder="Last"
                        value="${() => state.segmentRanges[route.name]?.end || ""}"
                        @input="${event => setSegmentRange(route.name, "end", event.target.value)}" />
                      <small>Blank analyzes the whole route.</small>
                    </div>
                  ` : ""}
                </div>
              `)}
            </div>
          </section>

          <section class="flmCard">
            <div class="flmCardHeader">
              <div>
                <h3>Saved Tunes</h3>
              </div>
              <button
                class="longManeuverButton"
                disabled="${() => state.runningAction || !state.workspace?.activeTrial}"
                @click="${saveCurrentTune}">
                Save Current
              </button>
            </div>
            ${() => state.loadingWorkspace ? html`<p class="longManeuverMuted">Loading saved tunes...</p>` : ""}
            <p class="longManeuverMuted">
              Save a working FLM trial, switch between vehicle or trailer setups, then use Revert Trial to return to the exact manual settings from before FLM.
            </p>
            <p class="longManeuverMuted">
              Think a tune is genuinely excellent? Send it to Firestar for review and possible community sharing. Submission includes only tune values, car identity, and your Discord username, not routes or driving logs.
            </p>
            <div class="flmWorkspaceList">
              ${() => (state.workspace?.savedTunes || []).length
                ? state.workspace.savedTunes.map((tune) => html`
                  <div class="flmWorkspaceRow">
                    <div class="flmWorkspaceItem">
                      <strong>${tune.name || "Saved Tune"}${tune.active ? " (Active)" : ""}</strong>
                      <span>${tune.carFingerprint || "Unknown car"}${tune.pathLabel ? ` / ${tune.pathLabel}` : ""}</span>
                      <small>
                        ${tune.genericParamCount} generic, ${tune.frictionCurveCount} friction curve, ${tune.vehicleKnobCount} vehicle knobs
                      </small>
                      <small>${formatTimestamp(tune.updatedAt ? new Date(tune.updatedAt * 1000).toISOString() : "")}</small>
                    </div>
                    <div class="flmSavedTuneActions">
                      <button
                        class="longManeuverButton"
                        disabled="${() => state.runningAction || tune.active}"
                        @click="${() => applySavedTune(tune.tuneId)}">
                        ${tune.active ? "Active" : "Apply"}
                      </button>
                      <button
                        class="longManeuverButton"
                        disabled="${() => state.runningAction}"
                        @click="${() => renameSavedTune(tune)}">
                        Rename
                      </button>
                      <button
                        class="longManeuverButton danger"
                        disabled="${() => state.runningAction || tune.active}"
                        @click="${() => deleteSavedTune(tune)}">
                        Delete
                      </button>
                      <button
                        class="longManeuverButton"
                        disabled="${() => state.runningAction}"
                        @click="${() => submitSavedTune(tune)}">
                        Send to Firestar
                      </button>
                    </div>
                  </div>
                `)
                : html`<p class="longManeuverMuted">No saved tunes yet. Apply a trial, then save it here.</p>`}
            </div>
          </section>
        </div>

        ${() => state.report ? html`
          <section class="flmCard">
            <div class="flmCardHeader">
              <div>
                <h3>Report Summary</h3>
              </div>
              <button
                class="longManeuverButton danger"
                disabled="${() => state.runningAction || !state.report?.reportId}"
                @click="${() => deleteReport(state.report.reportId)}">
                Delete Report
              </button>
            </div>
            <div class="longManeuverStatusGrid">
              <p><strong>Car:</strong> ${state.report.car?.carFingerprint || "Unknown"}</p>
              <p><strong>Control Path:</strong> ${state.report.car?.controlPath || "unknown"}</p>
              <p><strong>Friction Family:</strong> ${state.report.capabilities?.frictionFamily || "standard"}</p>
              <p><strong>Analyzer Recommended:</strong> ${reportPaths().find((path) => path.isPrimary)?.title || "Recommendations"}</p>
              <p><strong>Active Path:</strong> ${primaryPath()?.title || "Recommendations"}</p>
              <p><strong>Path Choice:</strong> ${state.report.pathSelectionSource === "manual" ? "Manual override" : "Automatic"}</p>
              <p><strong>Nonlinear Torque Map:</strong> ${state.report.capabilities?.nonlinearTorqueMap?.type === "siglin" ? (state.report.capabilities.nonlinearTorqueMap.asymmetric ? "Asymmetric left/right siglin" : "Symmetric siglin") : "Not detected"}</p>
              <p><strong>Live Learner Refits Map:</strong> ${state.report.capabilities?.nonlinearTorqueMap?.type === "siglin" ? "No" : "Not applicable"}</p>
              <p><strong>Segment Selection:</strong> ${formatReportSegmentRanges(state.report)}</p>
              <p><strong>Processed Segments:</strong> ${safeCount(state.report.summary?.processedSegments)}</p>
              <p><strong>Skipped Segments:</strong> ${safeCount(state.report.summary?.skippedSegments)}</p>
              <p><strong>Driver-Override Samples Excluded:</strong> ${safeCount(state.report.summary?.excludedDriverOverrideSamples)}</p>
              <p><strong>Lane Centering Segments Excluded:</strong> ${safeCount(state.report.summary?.laneCenteringExcludedSegments)}</p>
              <p><strong>qlog Fallback:</strong> ${state.report.summary?.usedQlogFallback ? "Yes" : "No"}</p>
              <p><strong>Samples:</strong> ${safeCount(state.report.summary?.sampleCount)}</p>
            </div>

            ${() => renderTrackingOverview()}

            ${() => renderTuneComparison()}

            <div class="flmFindings">
              ${reportPaths().map((path) => renderPathSummary(path))}
            </div>

            ${() => (state.report.warnings || []).length ? html`
              <div class="flmCardSubsection">
                <h4>Warnings</h4>
                <ul>
                  ${(state.report.warnings || []).map((warning) => html`<li>${warning}</li>`)}
                </ul>
              </div>
            ` : ""}

            ${() => (state.report.addTheseParametersAndStartHere || []).length ? html`
              <div class="flmCardSubsection">
                <h4>Add These Parameters And Start Here</h4>
                <ul>
                  ${(state.report.addTheseParametersAndStartHere || []).map((line) => html`<li>${line}</li>`)}
                </ul>
              </div>
            ` : ""}
          </section>

          <section class="flmCard">
            <div class="flmCardHeader">
              <div>
                <h3>Active Findings: ${primaryPath()?.title || "Recommendations"}</h3>
                <p class="longManeuverMuted">
                  ${primaryPath()?.whySelected || "Mark the dimensions that match what the driver felt."}
                </p>
                <p class="longManeuverMuted">Finding decisions save immediately and regenerate the trial profiles below.</p>
              </div>
              <button
                class="longManeuverButton"
                disabled="${() => state.runningAction || !state.report}"
                @click="${saveFeedback}">
                Save Notes
              </button>
            </div>

            <textarea
              class="flmNotes"
              placeholder="Optional tuning notes"
              @input="${(event) => { state.feedbackNotes = event.target.value }}">${() => state.feedbackNotes}</textarea>

            <div class="flmFindings">
              ${((primaryPath()?.suggestions) || []).map((suggestion) => renderSuggestion(suggestion))}
            </div>
          </section>

          <section class="flmCard">
            <h3>Trial Profiles</h3>
            <p class="longManeuverMuted">
              Apply one bounded profile at a time. Revert restores the exact advanced-lateral and FLM state that existed before the trial.
            </p>
            <div class="flmFindings">
              ${reportPaths().length
                ? reportPaths().map((path) => html`
                  <div>
                    <h4>${path.title} Profiles</h4>
                    <p class="longManeuverMuted">${path.whenToUse || ""}</p>
                    ${(path.profiles || []).length
                      ? (path.profiles || []).map((profile) => renderProfile(profile))
                      : html`<p class="longManeuverMuted">No trial profiles generated for this path.</p>`}
                  </div>
                `)
                : html`<p class="longManeuverMuted">No trial profiles generated for this report.</p>`}
            </div>
          </section>
        ` : html`
          <section class="flmCard">
            <h3>No Active Report</h3>
            <p class="longManeuverMuted">
              Select local routes, run analysis, or open one of the saved reports from the workspace panel.
            </p>
          </section>
        `}
      </div>
    </div>
  `
}
