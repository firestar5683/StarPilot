import { html, reactive } from "/assets/vendor/arrow-core.js"
import { escapeHtml, isGalaxyTunnel } from "/assets/js/utils.js"
import { Modal } from "/assets/components/modal.js"
import {
  buildRouteView,
  cameraVideoUrl,
  computeRouteStats,
  formatApproxDuration,
  getSegmentOptions,
  shouldUpgradeFromHeight,
  supportsLowQuality,
  groupRoutesForView,
  MAX_RENDERED_ROUTES,
  normalizeRoute,
  routeMetadataErrorMessage,
  routeViewRenderKey,
} from "/assets/components/recordings/dashcam_routes_helpers.js"

const state = reactive({
  loading: true,
  error: null,
  routes: [],
  selectedRoute: null,
  searchQuery: "",
  sortOrder: "newest",
  showPreservedOnly: false,
  viewMode: "list",
  progress: 0,
  total: 0,
  deleteMode: null,
  isDeletingAll: false,
})

let routesAbortController = null
let routesRequestToken = 0
let seenRouteNames = new Set()
let overlay = null
const routeLogsCache = new Map()
const FULL_QUALITY_RETRIES = 2
const FULL_QUALITY_RETRY_MS = 1000
// Only ask for the full stream once the viewer settles, so scrubbing queues no remuxes.
const FULL_QUALITY_SETTLE_MS = 1200

function routeLabel(route) {
  return route.displayName || route.displayDate || route.name
}

function mergeRoutes(rawRoutes) {
  if (!Array.isArray(rawRoutes) || rawRoutes.length === 0) return
  const additions = []
  for (const rawRoute of rawRoutes) {
    const name = String(rawRoute?.name || "")
    if (!name || seenRouteNames.has(name)) continue
    seenRouteNames.add(name)
    additions.push(normalizeRoute(rawRoute))
  }
  // Worker completion order is irrelevant: buildRouteView sorts the list at render time.
  if (additions.length) state.routes = [...state.routes, ...additions]
}

async function fetchRoutes() {
  const requestToken = ++routesRequestToken
  routesAbortController?.abort()
  const controller = new AbortController()
  routesAbortController = controller

  try {
    const response = await fetch("/api/routes", { signal: controller.signal })
    if (!response.ok || !response.body) throw new Error(`Route request failed (${response.status})`)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      if (requestToken !== routesRequestToken) return

      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split(/\r?\n\r?\n/)
      buffer = events.pop() || ""
      for (const event of events) {
        const dataLines = event.split(/\r?\n/).filter(line => line.startsWith("data:"))
        if (!dataLines.length) continue
        try {
          const payload = JSON.parse(dataLines.map(line => line.slice(5).trimStart()).join("\n"))
          if (Number.isFinite(payload.progress)) state.progress = payload.progress
          if (Number.isFinite(payload.total)) state.total = payload.total
          mergeRoutes(payload.routes)
        } catch (error) {
          console.error("Failed to parse route stream event:", error)
        }
      }
    }
  } catch (error) {
    if (error?.name !== "AbortError") state.error = "Couldn't load routes. Try refreshing."
  } finally {
    if (requestToken === routesRequestToken) {
      state.loading = false
      if (routesAbortController === controller) routesAbortController = null
    }
  }
}

function refresh() {
  state.loading = true
  state.error = null
  state.routes = []
  state.progress = 0
  state.total = 0
  seenRouteNames = new Set()
  return fetchRoutes()
}

function changeSortOrder(event) {
  const sortOrder = String(event.target.value || "")
  if (!["newest", "oldest", "longest", "shortest"].includes(sortOrder)) return
  state.sortOrder = sortOrder
}

if (!isGalaxyTunnel()) refresh()

function openDialog(htmlString) {
  const dialog = document.createElement("div")
  dialog.className = "dialog-overlay"
  dialog.innerHTML = htmlString
  document.body.appendChild(dialog)
  return dialog
}

function closeDialog(dialog) {
  dialog?.remove()
}

function replaceRoute(updatedRoute) {
  // Rows bind to this exact object, so replacing it would strand them on the stale one.
  const existing = state.routes.find(route => route.name === updatedRoute.name)
  if (existing) Object.assign(existing, updatedRoute)
  const selected = state.selectedRoute
  if (selected?.name === updatedRoute.name && selected !== existing) {
    Object.assign(selected, updatedRoute)
  }
  // Reassigning state.routes notifies ArrowJS to re-render views that depend on the routes array
  state.routes = [...state.routes]
}

async function deleteRoute(route) {
  const dialog = openDialog(`
    <div class="dialog-box">
      <p>Delete “${escapeHtml(routeLabel(route))}”?</p>
      <div class="dialog-buttons">
        <button class="btn-cancel" type="button">Cancel</button>
        <button class="btn-del" type="button">Delete</button>
      </div>
    </div>`)
  dialog.querySelector(".btn-cancel").onclick = () => closeDialog(dialog)
  dialog.querySelector(".btn-del").onclick = async () => {
    const response = await fetch(`/api/routes/${route.name}`, { method: "DELETE" })
    if (!response.ok) {
      showSnackbar("Delete failed...", "error")
      return
    }
    closeDialog(dialog)
    closeOverlay()
    await refresh()
    showSnackbar("Route deleted!")
  }
}

async function resetRouteName(route, dialog) {
  const response = await fetch("/api/routes/reset_name", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: route.name }),
  })
  if (!response.ok) {
    showSnackbar("Resetting name failed...", "error")
    return
  }

  const { timestamp } = await response.json()
  const updatedRoute = normalizeRoute({ ...route, timestamp, isCustomName: false })
  replaceRoute(updatedRoute)
  closeDialog(dialog)
  const title = overlay?.querySelector(".media-player-title-text")
  if (title) title.textContent = routeLabel(updatedRoute)
  showSnackbar("Route name reset!")
}

async function renameRoute(route) {
  const dialog = openDialog(`
    <div class="dialog-box">
      <p>Rename “${escapeHtml(routeLabel(route))}”</p>
      <input class="rn-input" value="${escapeHtml(routeLabel(route))}" aria-label="New route name">
      <div class="dialog-buttons">
        <button class="btn-cancel" type="button">Cancel</button>
        <button class="btn-reset" type="button">Reset</button>
        <button class="btn-save" type="button">Save</button>
      </div>
    </div>`)
  dialog.querySelector(".btn-cancel").onclick = () => closeDialog(dialog)
  dialog.querySelector(".btn-reset").onclick = () => resetRouteName(route, dialog)
  dialog.querySelector(".btn-save").onclick = async () => {
    const newName = dialog.querySelector(".rn-input").value.trim()
    if (!newName) return
    const response = await fetch("/api/routes/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ old: route.name, new: newName }),
    })
    if (!response.ok) {
      showSnackbar("Rename failed...", "error")
      return
    }

    const payload = await response.json().catch(() => ({}))
    const savedName = payload.name || newName
    const updatedRoute = normalizeRoute({ ...route, timestamp: savedName, isCustomName: true })
    replaceRoute(updatedRoute)
    closeDialog(dialog)
    const title = overlay?.querySelector(".media-player-title-text")
    if (title) title.textContent = savedName
    showSnackbar("Route renamed!")
  }
}

function formatBytes(bytes) {
  if (!bytes) return "0 MB"
  const megabytes = bytes / 1e6
  return megabytes >= 1000 ? `${(megabytes / 1000).toFixed(2)} GB` : `${megabytes.toFixed(1)} MB`
}

function openLogsDialog(route, logsButton, getCachedLogs, setCachedLogs) {
  const logsDialog = openDialog(`
    <section class="dialog-box route-logs-dialog" role="dialog" aria-modal="true" aria-labelledby="route-logs-title">
      <header class="route-logs-toolbar">
        <div><p class="route-logs-eyebrow">Route data</p><h2 id="route-logs-title">Full logs</h2></div>
        <button class="route-logs-close" type="button" aria-label="Close full logs">&times;</button>
      </header>
      <div class="route-logs-content" aria-live="polite"><p class="route-logs-message">Looking for full logs&hellip;</p></div>
    </section>`)
  const content = logsDialog.querySelector(".route-logs-content")
  const closeButton = logsDialog.querySelector(".route-logs-close")
  const closeLogsDialog = () => {
    document.removeEventListener("keydown", handleKeydown)
    closeDialog(logsDialog)
    logsButton?.focus()
  }
  const handleKeydown = event => { if (event.key === "Escape") closeLogsDialog() }
  closeButton.onclick = closeLogsDialog
  logsDialog.addEventListener("click", event => { if (event.target === logsDialog) closeLogsDialog() })
  document.addEventListener("keydown", handleKeydown)
  closeButton.focus()

  const renderLogs = data => {
    content.innerHTML = `
      <div class="route-logs-summary">
        <div><strong>${data.segments.length} segment${data.segments.length === 1 ? "" : "s"}</strong><span>${formatBytes(data.totalBytes)} total download</span></div>
        <a class="route-logs-download-all" href="/api/routes/${route.name}/logs/download" download>Download all <span>.tar</span></a>
      </div>
      <ul class="route-logs-list">
        ${data.segments.map(segment => `<li>
          <div class="route-log-details"><strong>Segment ${Number(segment.segmentNum)}</strong><span>${formatBytes(segment.bytes)} &middot; ${escapeHtml(segment.filename)}</span></div>
          <a class="route-log-download" href="${escapeHtml(segment.url)}" download>Download</a>
        </li>`).join("")}
      </ul>`
  }

  const cachedLogs = getCachedLogs?.()
  if (cachedLogs) {
    renderLogs(cachedLogs)
    return
  }

  fetch(`/api/routes/${route.name}/logs`)
    .then(async response => ({ response, data: await response.json() }))
    .then(({ response, data }) => {
      if (!response.ok) {
        if (content.isConnected) content.innerHTML = `<p class="route-logs-message route-logs-error">${escapeHtml(data.error || "Could not read logs.")}</p>`
        return
      }
      setCachedLogs?.(data)
      if (content.isConnected) renderLogs(data)
    })
    .catch(error => {
      if (content.isConnected) content.innerHTML = `<p class="route-logs-message route-logs-error">Could not reach the device: ${escapeHtml(error.message)}</p>`
    })
}

function openLogsFromRow(route, event) {
  const button = event.currentTarget
  openLogsDialog(
    route,
    button,
    () => routeLogsCache.get(route.name) || null,
    value => { routeLogsCache.set(route.name, value) },
  )
}

async function openOverlay(route) {
  if (overlay) return
  overlay = document.createElement("div")
  overlay.className = "media-player-overlay dashcam-player-overlay"
  overlay.innerHTML = `
    <section class="media-player-content dashcam-player" role="dialog" aria-modal="true" aria-label="Route player">
      <header class="dashcam-player-header">
        <div class="dashcam-player-heading">
          <p class="dashcam-player-eyebrow">Dashcam route</p>
          <div class="dashcam-player-title-row">
            <h2 class="media-player-title-text">${escapeHtml(routeLabel(route))}</h2>
            <button class="dashcam-title-rename action-rename" type="button" title="Rename route" aria-label="Rename route"><i class="bi bi-pencil"></i></button>
          </div>
        </div>
        <button class="dashcam-player-close" type="button" aria-label="Close player">&times;</button>
      </header>
      <div class="dashcam-video-shell">
        <video class="dashcam-video active" controls muted playsinline preload="metadata"></video>
        <video class="dashcam-video staging" muted playsinline preload="none"></video>
        <div class="dashcam-player-state" role="status">Loading route metadata&hellip;</div>
      </div>
      <div class="dashcam-player-toolbar">
        <div class="dashcam-camera-selector" aria-label="Camera selector">
          <button class="camera-button" data-camera="forward" type="button" disabled hidden>Forward</button>
          <button class="camera-button" data-camera="wide" type="button" disabled hidden>Wide</button>
          <button class="camera-button" data-camera="driver" type="button" disabled hidden>Driver</button>
        </div>
        <div class="dashcam-segment-bar" hidden>
          <button class="segment-step action-prev-segment" type="button" title="Previous segment (Shift + \u2190)" aria-label="Previous segment"><i class="bi bi-skip-start-fill"></i></button>
          <select class="segment-select" aria-label="Jump to segment"></select>
          <button class="segment-step action-next-segment" type="button" title="Next segment (Shift + \u2192)" aria-label="Next segment"><i class="bi bi-skip-end-fill"></i></button>
        </div>
        <div class="dashcam-player-actions">
          <button class="action-download" type="button" disabled title="Download route" aria-label="Download route"><i class="bi bi-download"></i></button>
          <button class="action-logs" type="button" title="View &amp; download logs" aria-label="View and download logs"><i class="bi bi-file-earmark-arrow-down"></i></button>
          <button class="action-delete" type="button" title="Delete route" aria-label="Delete route"><i class="bi bi-trash"></i></button>
        </div>
      </div>
    </section>`
  document.body.appendChild(overlay)

  const [videoA, videoB] = overlay.querySelectorAll(".dashcam-video")
  let activeVideo = videoA
  let stagingVideo = videoB
  const videoShell = overlay.querySelector(".dashcam-video-shell")
  const playerState = overlay.querySelector(".dashcam-player-state")
  const segmentBar = overlay.querySelector(".dashcam-segment-bar")
  const segmentSelect = overlay.querySelector(".segment-select")
  const prevSegmentButton = overlay.querySelector(".action-prev-segment")
  const nextSegmentButton = overlay.querySelector(".action-next-segment")
  const downloadButton = overlay.querySelector(".action-download")
  const logsButton = overlay.querySelector(".action-logs")
  const cameraButtons = [...overlay.querySelectorAll(".camera-button")]
  let segments = []
  let current = 0
  let selectedCamera = null
  let logsData = null
  let showingPreview = false
  let wantsPlayback = true
  let qualityToken = 0
  let upgradeController = null
  let upgradeTimer = null
  let isUpgrading = false

  const setPlayerMessage = (message, isError = false) => {
    playerState.textContent = message
    playerState.hidden = !message
    playerState.classList.toggle("error", isError)
  }
  const syncSegmentControls = () => {
    segmentSelect.value = String(current)
    segmentSelect.disabled = segments.length < 2
    prevSegmentButton.disabled = current <= 0
    nextSegmentButton.disabled = current >= segments.length - 1
  }
  const buildSegmentPicker = () => {
    segmentSelect.innerHTML = getSegmentOptions(segments)
      .map(option => `<option value="${option.index}">${escapeHtml(option.label)}</option>`)
      .join("")
    segmentBar.hidden = !segments.length
  }

  const cancelUpgrade = () => {
    qualityToken += 1
    isUpgrading = false
    clearTimeout(upgradeTimer)
    upgradeTimer = null
    upgradeController?.abort()
    upgradeController = null
    stagingVideo.pause()
    stagingVideo.removeAttribute("src")
    stagingVideo.controls = false
    stagingVideo.load()
  }

  const performSeamlessUpgrade = (fullUrl, token) => {
    if (token !== qualityToken || !showingPreview || !overlay) return
    isUpgrading = true

    stagingVideo.muted = activeVideo.muted
    stagingVideo.volume = activeVideo.volume
    stagingVideo.playbackRate = activeVideo.playbackRate
    stagingVideo.src = fullUrl
    stagingVideo.preload = "auto"
    stagingVideo.load()

    const cleanupStaging = () => {
      stagingVideo.removeEventListener("loadedmetadata", onMetadata)
      stagingVideo.removeEventListener("error", onStagingError)
    }

    const onStagingError = () => {
      cleanupStaging()
      if (token !== qualityToken) return
      isUpgrading = false
      showingPreview = false
    }

    const onMetadata = () => {
      if (token !== qualityToken || !showingPreview || !overlay) {
        cleanupStaging()
        return
      }

      const syncAndSwap = () => {
        if (token !== qualityToken || !showingPreview || !overlay) {
          cleanupStaging()
          return
        }

        const applySwap = () => {
          if (token !== qualityToken || !showingPreview || !overlay) {
            cleanupStaging()
            return
          }
          cleanupStaging()

          const targetTime = Number.isFinite(activeVideo.currentTime) ? activeVideo.currentTime : 0
          const isPlaying = !activeVideo.paused && !activeVideo.ended

          stagingVideo.muted = activeVideo.muted
          stagingVideo.volume = activeVideo.volume
          stagingVideo.playbackRate = activeVideo.playbackRate

          if (Math.abs(stagingVideo.currentTime - targetTime) > 0.15) {
            try {
              stagingVideo.currentTime = targetTime
            } catch (_) {}
          }

          if (isPlaying && stagingVideo.paused) {
            stagingVideo.play().catch(() => {})
          } else if (!isPlaying && !stagingVideo.paused) {
            stagingVideo.pause()
          }

          activeVideo.classList.remove("active")
          activeVideo.classList.add("staging")
          activeVideo.controls = false

          stagingVideo.classList.remove("staging")
          stagingVideo.classList.add("active")
          // Keep native controls enabled across the quality swap so touch browsers
          // can reveal them again after their normal auto-hide.
          stagingVideo.controls = true

          const oldActive = activeVideo
          activeVideo = stagingVideo
          stagingVideo = oldActive

          stagingVideo.pause()
          stagingVideo.removeAttribute("src")
          stagingVideo.load()

          showingPreview = false
          isUpgrading = false
          setPlayerMessage("")
        }

        const isPlaying = !activeVideo.paused && !activeVideo.ended
        if (isPlaying) {
          stagingVideo.play().then(() => {
            if ("requestVideoFrameCallback" in stagingVideo) {
              stagingVideo.requestVideoFrameCallback(() => applySwap())
            } else {
              stagingVideo.addEventListener("timeupdate", applySwap, { once: true })
            }
          }).catch(() => {
            applySwap()
          })
        } else {
          if ("requestVideoFrameCallback" in stagingVideo) {
            stagingVideo.requestVideoFrameCallback(() => applySwap())
          } else {
            applySwap()
          }
        }
      }

      const playbackTime = Number.isFinite(activeVideo.currentTime) ? activeVideo.currentTime : 0
      if (playbackTime > 0) {
        stagingVideo.addEventListener("seeked", syncAndSwap, { once: true })
        try {
          stagingVideo.currentTime = Math.min(playbackTime, Number.isFinite(stagingVideo.duration) ? stagingVideo.duration : playbackTime)
        } catch (_) {
          syncAndSwap()
        }
      } else {
        syncAndSwap()
      }
    }

    stagingVideo.addEventListener("loadedmetadata", onMetadata, { once: true })
    stagingVideo.addEventListener("error", onStagingError, { once: true })
  }

  // Request the real stream behind the playing preview without interrupting playback.
  const requestFullQuality = (segmentUrl, camera, attempt = 0) => {
    const token = ++qualityToken
    upgradeController?.abort()
    const controller = new AbortController()
    upgradeController = controller
    const fullUrl = cameraVideoUrl(segmentUrl, camera)
    const stillCurrent = () =>
      token === qualityToken && showingPreview && segments[current] === segmentUrl && selectedCamera === camera && Boolean(overlay)

    fetch(fullUrl, { method: "HEAD", signal: controller.signal })
      .then(response => {
        if (!stillCurrent()) return
        if (upgradeController === controller) upgradeController = null
        if (response.ok) {
          performSeamlessUpgrade(fullUrl, token)
          return
        }
        if (response.status === 503 && attempt < FULL_QUALITY_RETRIES) {
          upgradeTimer = setTimeout(() => {
            if (stillCurrent()) requestFullQuality(segmentUrl, camera, attempt + 1)
          }, FULL_QUALITY_RETRY_MS)
        }
      })
      .catch(error => {
        if (upgradeController === controller) upgradeController = null
        if (error?.name !== "AbortError") console.error("Could not prepare full-quality route video:", error)
      })
  }

  const scheduleUpgrade = (segmentUrl, camera) => {
    cancelUpgrade()
    upgradeTimer = setTimeout(() => {
      if (!showingPreview || segments[current] !== segmentUrl || selectedCamera !== camera) return
      requestFullQuality(segmentUrl, camera)
    }, FULL_QUALITY_SETTLE_MS)
  }

  const loadSegment = (autoplay, { message, preview } = {}) => {
    const segmentUrl = segments[current]
    const camera = selectedCamera
    if (!segmentUrl || !camera) return
    cancelUpgrade()
    wantsPlayback = autoplay
    showingPreview = preview === undefined ? supportsLowQuality(camera) : preview
    // qcamera.ts scales the complete road frame to 526x330. Keep that same mapping
    // after the full stream arrives so its slightly wider aspect ratio is not cropped.
    videoShell.classList.toggle("qcamera-framing", showingPreview)
    if (message) setPlayerMessage(message)

    stagingVideo.pause()
    stagingVideo.removeAttribute("src")
    stagingVideo.classList.remove("active")
    stagingVideo.classList.add("staging")
    stagingVideo.controls = false

    activeVideo.classList.remove("staging")
    activeVideo.classList.add("active")
    activeVideo.controls = true
    activeVideo.src = cameraVideoUrl(segmentUrl, camera, showingPreview ? "low" : undefined)
    activeVideo.load()
    if (autoplay) activeVideo.play().catch(() => {})
  }

  const playCurrentSegment = (autoplay = true) => {
    if (!segments[current] || !selectedCamera) return
    syncSegmentControls()
    loadSegment(autoplay)
  }
  const goToSegment = index => {
    if (!segments.length) return
    const target = Math.min(Math.max(index, 0), segments.length - 1)
    if (target === current) {
      syncSegmentControls()
      return
    }
    const keepPlaying = activeVideo.ended || (!activeVideo.paused && !activeVideo.error)
    current = target
    playCurrentSegment(keepPlaying)
  }
  overlay._cancelUpgrade = cancelUpgrade

  const closeOnEscape = event => {
    if (document.querySelector(".route-logs-dialog")) return
    if (event.key === "Escape") {
      closeOverlay()
      return
    }
    if (!event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return
    if (event.key === "ArrowLeft") {
      event.preventDefault()
      goToSegment(current - 1)
    } else if (event.key === "ArrowRight") {
      event.preventDefault()
      goToSegment(current + 1)
    }
  }

  overlay.addEventListener("click", event => { if (event.target === overlay) closeOverlay() })
  document.addEventListener("keydown", closeOnEscape)
  overlay._closeOnEscape = closeOnEscape
  overlay.querySelector(".dashcam-player-close").onclick = closeOverlay
  overlay.querySelector(".action-delete").onclick = () => deleteRoute(state.selectedRoute || route)
  overlay.querySelector(".action-rename").onclick = () => renameRoute(state.selectedRoute || route)

  logsButton.onclick = () => openLogsDialog(route, logsButton, () => logsData, value => { logsData = value })
  downloadButton.onclick = () => {
    if (!selectedCamera) return
    const link = document.createElement("a")
    link.href = `/video/${route.name}/combined?camera=${encodeURIComponent(selectedCamera)}`
    link.download = `${routeLabel(state.selectedRoute || route)}-${selectedCamera}.mp4`
    document.body.appendChild(link)
    link.click()
    link.remove()
  }

  const handleLoadedMetadata = event => {
    if (event.target !== activeVideo) return
    if (!showingPreview) return
    if (shouldUpgradeFromHeight(activeVideo.videoHeight)) {
      scheduleUpgrade(segments[current], selectedCamera)
    } else {
      showingPreview = false
    }
  }
  const handleLoadedData = event => {
    if (event.target === activeVideo) setPlayerMessage("")
  }
  const handlePlaying = event => {
    if (event.target === activeVideo) setPlayerMessage("")
  }
  const handleWaiting = () => {}
  const handleError = event => {
    if (event.target !== activeVideo) return
    // A dead preview drops through to the real stream rather than showing an error.
    if (showingPreview) {
      showingPreview = false
      cancelUpgrade()
      loadSegment(wantsPlayback, { preview: false })
      return
    }
    setPlayerMessage("This segment could not be played.", true)
  }
  const handleEnded = event => {
    if (event.target === activeVideo) goToSegment(current + 1)
  }
  const handleSeeking = event => {
    if (event.target !== activeVideo) return
    if (isUpgrading && stagingVideo.readyState >= 1) {
      try {
        stagingVideo.currentTime = activeVideo.currentTime
      } catch (_) {}
    }
  }
  const handlePause = event => {
    if (event.target !== activeVideo) return
    if (isUpgrading && !stagingVideo.paused) stagingVideo.pause()
  }
  const handlePlay = event => {
    if (event.target !== activeVideo) return
    if (isUpgrading && stagingVideo.paused && stagingVideo.readyState >= 3) {
      stagingVideo.play().catch(() => {})
    }
  }

  const bindVideoEvents = el => {
    el.addEventListener("loadedmetadata", handleLoadedMetadata)
    el.addEventListener("loadeddata", handleLoadedData)
    el.addEventListener("playing", handlePlaying)
    el.addEventListener("waiting", handleWaiting)
    el.addEventListener("error", handleError)
    el.addEventListener("ended", handleEnded)
    el.addEventListener("seeking", handleSeeking)
    el.addEventListener("pause", handlePause)
    el.addEventListener("play", handlePlay)
  }
  bindVideoEvents(videoA)
  bindVideoEvents(videoB)

  prevSegmentButton.onclick = () => goToSegment(current - 1)
  nextSegmentButton.onclick = () => goToSegment(current + 1)
  segmentSelect.onchange = () => goToSegment(Number(segmentSelect.value))

  for (const button of cameraButtons) {
    button.addEventListener("click", () => {
      if (button.disabled || button.dataset.camera === selectedCamera || !segments[current]) return
      selectedCamera = button.dataset.camera
      cameraButtons.forEach(candidate => candidate.classList.toggle("active", candidate === button))
      const playbackTime = Number.isFinite(activeVideo.currentTime) ? activeVideo.currentTime : 0
      const shouldResume = !activeVideo.paused && !activeVideo.ended
      activeVideo.addEventListener("loadedmetadata", () => {
        if (playbackTime > 0) {
          try {
            activeVideo.currentTime = Math.min(playbackTime, Number.isFinite(activeVideo.duration) ? activeVideo.duration : playbackTime)
          } catch (_) {}
        }
      }, { once: true })
      loadSegment(shouldResume, { message: "Switching camera…" })
    })
  }

  try {
    const response = await fetch(`/api/routes/${route.name}`)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(routeMetadataErrorMessage(response.status, data?.error))
    segments = Array.isArray(data.segment_urls) ? data.segment_urls.filter(url => typeof url === "string") : []
    const availableCameras = ["forward", "wide", "driver"].filter(camera => data.available_cameras?.includes(camera))
    if (!segments.length) throw new Error("No video segments are stored for this route")
    if (!availableCameras.length) throw new Error("No camera video is stored for this route")

    selectedCamera = availableCameras.includes("forward") ? "forward" : availableCameras[0]
    for (const button of cameraButtons) {
      const available = availableCameras.includes(button.dataset.camera)
      button.hidden = !available
      button.disabled = !available
      button.classList.toggle("active", button.dataset.camera === selectedCamera)
    }
    downloadButton.disabled = false
    buildSegmentPicker()
    playCurrentSegment()
  } catch (error) {
    cameraButtons.forEach(button => { button.disabled = true })
    setPlayerMessage(error.message || "Could not load this route.", true)
  }
}

function closeOverlay() {
  if (!overlay) return
  overlay._cancelUpgrade?.()
  document.removeEventListener("keydown", overlay._closeOnEscape)
  const videos = overlay.querySelectorAll("video")
  videos.forEach(v => {
    v.pause()
    v.removeAttribute("src")
    v.load()
  })
  overlay.remove()
  overlay = null
  state.selectedRoute = null
}

async function togglePreserved(route, event) {
  event?.stopPropagation?.()
  const isPreserved = !route.is_preserved
  try {
    const response = await fetch(`/api/routes/${route.name}/preserve`, { method: isPreserved ? "POST" : "DELETE" })
    if (!response.ok) {
      const errorData = await response.json()
      showSnackbar(errorData.error || "Failed to update preserved state...", "error")
      return
    }
    replaceRoute({ ...route, is_preserved: isPreserved })
  } catch (_) {
    showSnackbar("An error occurred...", "error")
  }
}

async function deleteAllRoutes(includePreserved) {
  state.deleteMode = null
  state.isDeletingAll = true
  try {
    const response = await fetch(`/api/routes/delete_all?include_preserved=${includePreserved}`, { method: "DELETE" })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || "Route deletion failed")
    await refresh()
    showSnackbar(payload.message || "Routes deleted!")
  } catch (error) {
    showSnackbar(error?.message || "An error occurred while deleting routes...", "error")
  } finally {
    state.isDeletingAll = false
  }
}

function thumbnailFailed(event) {
  event.currentTarget.hidden = true
  event.currentTarget.parentElement?.classList.add("thumbnail-failed")
}

export function RouteRecordings() {
  if (isGalaxyTunnel()) {
    return html`
      <div class="tunnel-notice">
        <div class="tunnel-notice-icon">🛰️</div>
        <h3 class="tunnel-notice-title">Dashcam Routes Unavailable via Galaxy</h3>
        <p class="tunnel-notice-body">Loading dashcam routes requires a direct connection.<br>Connect to your device's local network to use this feature.</p>
      </div>`
  }

  if (state.selectedRoute && !overlay) openOverlay(state.selectedRoute)

  return html`
    <div class="screen-recordings-wrapper dashcam-routes-wrapper">
      <section class="screen-recordings-widget dashcam-library">
        <header class="dashcam-library-header">
          <div class="dashcam-header-info">
            <p class="dashcam-library-eyebrow">Local recordings</p>
            <h1>Dashcam Routes</h1>
            ${() => {
              const stats = computeRouteStats(state.routes)
              return html`<div class="dashcam-stats-bar"><span class="dashcam-stat-chip"><i class="bi bi-car-front-fill"></i> <strong>${stats.count}</strong> ${stats.count === 1 ? "drive" : "drives"}</span><span class="dashcam-stat-chip"><i class="bi bi-stopwatch-fill"></i> <strong>${stats.formattedDuration}</strong> total</span>${stats.preservedCount > 0 ? html`<span class="dashcam-stat-chip stat-chip-preserved"><i class="bi bi-heart-fill"></i> <strong>${stats.preservedCount}</strong> preserved</span>` : ""}</div>`
            }}
          </div>
          <div class="dashcam-header-controls">
            <button class="dashcam-refresh-button" type="button" @click="${refresh}" disabled="${() => state.loading || false}" title="Refresh routes">
              <i class="bi bi-arrow-clockwise"></i> Refresh
            </button>
          </div>
        </header>

        <div class="dashcam-toolbar">
          <div class="dashcam-search-box">
            <i class="bi bi-search dashcam-search-icon"></i>
            <input type="search" placeholder="Search route names, dates, or hash IDs..." aria-label="Search routes" value="${() => state.searchQuery}" @input="${event => { state.searchQuery = event.target.value }}">
            ${() => state.searchQuery ? html`
              <button class="dashcam-search-clear" type="button" title="Clear search" @click="${() => { state.searchQuery = "" }}"><i class="bi bi-x"></i></button>
            ` : ""}
          </div>
          <div class="dashcam-filter-group">
            <button class="${() => `dashcam-filter-pill ${!state.showPreservedOnly ? "active" : ""}`}" type="button" @click="${() => { state.showPreservedOnly = false }}">
              All Drives
            </button>
            <button class="${() => `dashcam-filter-pill ${state.showPreservedOnly ? "active" : ""}`}" type="button" @click="${() => { state.showPreservedOnly = true }}">
              <i class="bi bi-heart-fill"></i> Preserved
            </button>
          </div>
          <label class="dashcam-sort">
            <span>Sort</span>
            <select value="${() => state.sortOrder}" @input="${changeSortOrder}" @change="${changeSortOrder}">
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
              <option value="longest">Longest duration</option>
              <option value="shortest">Shortest duration</option>
            </select>
          </label>
          <div class="dashcam-view-toggle" aria-label="Layout view mode">
            <button class="${() => `dashcam-view-btn ${state.viewMode === "list" ? "active" : ""}`}" type="button" title="List View" @click="${() => { state.viewMode = "list" }}">
              <i class="bi bi-list-ul"></i>
            </button>
            <button class="${() => `dashcam-view-btn ${state.viewMode === "grid" ? "active" : ""}`}" type="button" title="Grid View" @click="${() => { state.viewMode = "grid" }}">
              <i class="bi bi-grid-fill"></i>
            </button>
          </div>
        </div>

        ${() => {
          const view = buildRouteView(state.routes, { preservedOnly: state.showPreservedOnly, searchQuery: state.searchQuery, sortOrder: state.sortOrder })
          const groups = groupRoutesForView(view.visible, state.sortOrder)
          const renderKey = routeViewRenderKey(view.visible, state.sortOrder, state.viewMode)
          const hasActiveSearch = Boolean(state.searchQuery.trim())

          return html`
            ${state.loading || hasActiveSearch ? html`
              <div class="dashcam-results-summary" aria-live="polite">
                ${hasActiveSearch ? html`<span>${view.matching.length} matching drive${view.matching.length === 1 ? "" : "s"}</span>` : ""}
                ${state.loading ? html`<span>Loading routes</span>` : ""}
              </div>
            ` : ""}
            ${state.error ? html`<p class="screen-recordings-message dashcam-error">${state.error}</p>` : ""}
            ${state.isDeletingAll ? html`<p class="screen-recordings-message">Deleting routes&hellip;</p>` : ""}
            ${!view.visible.length && state.loading ? html`<div class="dashcam-loading"><span></span><p>Finding local routes&hellip;</p></div>` : ""}
            ${!view.visible.length && !state.loading && !state.isDeletingAll ? html`<div class="dashcam-empty-state"><i class="bi bi-camera-reels"></i><p>${state.routes.length ? "No routes match these filters." : "No routes found."}</p></div>` : ""}
            <div class="dashcam-date-groups" data-view-key="${renderKey}">
              ${groups.map(group => html`
                <section class="dashcam-date-group">
                  <div class="dashcam-date-group-header">
                    <h2>${group.label}</h2>
                    <span class="dashcam-date-group-count">${group.routes.length} ${group.routes.length === 1 ? "drive" : "drives"}</span>
                  </div>
                  ${state.viewMode === "grid" ? html`<div class="screen-recordings-grid dashcam-routes-grid">
                      ${group.routes.map(route => html`
                        <article class="${() => `recording-card dashcam-route-card ${route.is_preserved ? "is-preserved" : ""}`}" @click="${() => { state.selectedRoute = route }}">
                          <div class="dashcam-card-top-bar">
                            <button class="${() => `btn-route-action btn-preserve ${route.is_preserved ? "active" : ""}`}" type="button" aria-label="${() => route.is_preserved ? "Remove preservation" : "Preserve route"}" title="${() => route.is_preserved ? "Preserved (click to unpreserve)" : "Click to preserve"}" @click="${event => togglePreserved(route, event)}">
                              <i class="${() => `bi ${route.is_preserved ? "bi-heart-fill" : "bi-heart"}`}"></i>
                            </button>
                            <span class="meta-pill id-pill" title="Route ID: ${route.name}"><i class="bi bi-hash"></i>${route.name.split("--").slice(1).join("--") || route.name}</span>
                          </div>
                          <div class="recording-preview-container dashcam-preview">
                            <span class="dashcam-preview-fallback"><i class="bi bi-camera-video"></i><small>Preview unavailable</small></span>
                            <img src="${route.png}" class="recording-preview" loading="lazy" alt="" @error="${thumbnailFailed}">
                            <span class="dashcam-grid-play-overlay"><i class="bi bi-play-fill"></i></span>
                          </div>
                          <div class="dashcam-card-body">
                            <div class="dashcam-route-title-row">
                              <h3 title="${() => route.displayName}">${() => route.displayName}</h3>
                              ${() => route.isCustomName ? html`<span class="dashcam-custom-badge" title="Custom name"><i class="bi bi-tag-fill"></i></span>` : ""}
                            </div>
                            ${() => route.isCustomName ? html`<p class="dashcam-card-date">${route.displayDate}</p>` : ""}
                            <div class="dashcam-route-meta-pills">
                              <span class="meta-pill duration-pill"><i class="bi bi-clock"></i> ${formatApproxDuration(route.approxDurationSeconds)}</span>
                              <span class="meta-pill segments-pill"><i class="bi bi-collection-play"></i> ${route.segmentCount} seg</span>
                            </div>
                            <div class="dashcam-card-actions" @click="${event => event.stopPropagation()}">
                              <button class="btn-route-action btn-play" type="button" title="Play route" @click="${() => { state.selectedRoute = route }}">
                                <i class="bi bi-play-fill"></i> Play
                              </button>
                              <button class="btn-route-action btn-icon" type="button" title="View logs" @click="${event => openLogsFromRow(route, event)}">
                                <i class="bi bi-file-earmark-arrow-down"></i>
                              </button>
                              <button class="btn-route-action btn-icon" type="button" title="Rename" @click="${() => renameRoute(route)}">
                                <i class="bi bi-pencil"></i>
                              </button>
                              <button class="btn-route-action btn-icon btn-danger-action" type="button" title="Delete" @click="${() => deleteRoute(route)}">
                                <i class="bi bi-trash"></i>
                              </button>
                            </div>
                          </div>
                        </article>`.key(route.name))}
                    </div>` : html`<div class="dashcam-routes-list">
                      ${group.routes.map(route => html`
                        <article class="${() => `dashcam-route-row ${route.is_preserved ? "is-preserved" : ""}`}" @click="${() => { state.selectedRoute = route }}">
                          <div class="dashcam-mini-preview">
                            <span class="dashcam-mini-fallback"><i class="bi bi-camera-video"></i></span>
                            <img src="${route.png}" class="dashcam-mini-img" loading="lazy" alt="" @error="${thumbnailFailed}">
                            <span class="dashcam-mini-play-overlay"><i class="bi bi-play-fill"></i></span>
                          </div>
                          <div class="dashcam-route-info">
                            <div class="dashcam-route-title-row">
                              <h3 class="dashcam-route-title" title="${() => route.displayName}">${() => route.displayName}</h3>
                              ${() => route.isCustomName ? html`<span class="dashcam-custom-badge" title="Custom name"><i class="bi bi-tag-fill"></i> Custom</span>` : ""}
                            </div>
                            ${() => route.isCustomName ? html`<p class="dashcam-route-subdate"><i class="bi bi-calendar3"></i> ${route.displayDate}</p>` : ""}
                            <div class="dashcam-route-meta-pills">
                              <span class="meta-pill duration-pill" title="Estimated duration"><i class="bi bi-clock"></i> ${formatApproxDuration(route.approxDurationSeconds)}</span>
                              <span class="meta-pill segments-pill" title="Segments recorded"><i class="bi bi-collection-play"></i> ${route.segmentCount} segment${route.segmentCount === 1 ? "" : "s"}</span>
                              ${() => route.is_preserved ? html`<span class="meta-pill preserved-pill" title="Preserved from deletion"><i class="bi bi-heart-fill"></i> Preserved</span>` : ""}
                              <span class="meta-pill id-pill" title="Route ID: ${route.name}"><i class="bi bi-hash"></i>${route.name.split("--").slice(1).join("--") || route.name}</span>
                            </div>
                          </div>
                          <div class="dashcam-route-actions" @click="${event => event.stopPropagation()}">
                            <button class="btn-route-action btn-play" type="button" title="Play recording" @click="${() => { state.selectedRoute = route }}">
                              <i class="bi bi-play-fill"></i> <span>Play</span>
                            </button>
                            <button class="${() => `btn-route-action btn-preserve ${route.is_preserved ? "active" : ""}`}" type="button" aria-label="${() => route.is_preserved ? "Remove preservation" : "Preserve route"}" title="${() => route.is_preserved ? "Preserved (click to unpreserve)" : "Click to preserve"}" @click="${event => togglePreserved(route, event)}">
                              <i class="${() => `bi ${route.is_preserved ? "bi-heart-fill" : "bi-heart"}`}"></i>
                            </button>
                            <button class="btn-route-action btn-icon" type="button" title="View & download logs" @click="${event => openLogsFromRow(route, event)}">
                              <i class="bi bi-file-earmark-arrow-down"></i>
                            </button>
                            <button class="btn-route-action btn-icon" type="button" title="Rename route" @click="${() => renameRoute(route)}">
                              <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn-route-action btn-icon btn-danger-action" type="button" title="Delete route" @click="${() => deleteRoute(route)}">
                              <i class="bi bi-trash"></i>
                            </button>
                          </div>
                        </article>`.key(route.name))}
                    </div>`}
                </section>`.key(group.key))}
            </div>
            ${view.truncated ? html`<p class="screen-recordings-message">Showing the first ${MAX_RENDERED_ROUTES} of ${view.matching.length} matching routes.</p>` : ""}`
        }}

        ${() => state.routes.length ? html`
          <footer class="dashcam-danger-zone">
            <div class="dashcam-danger-copy"><strong>Delete local routes</strong><span>Keep preserved routes, or remove everything.</span></div>
            <div class="dashcam-danger-actions">
              <button class="delete-all-button delete-non-preserved-button" type="button" @click="${() => { state.deleteMode = "non-preserved" }}" disabled="${() => state.isDeletingAll || state.routes.every(route => route.is_preserved) || false}">${() => state.isDeletingAll ? "Deleting…" : "Delete Non-Preserved"}</button>
              <button class="delete-all-button" type="button" @click="${() => { state.deleteMode = "all" }}" disabled="${() => state.isDeletingAll || false}">${() => state.isDeletingAll ? "Deleting…" : "Delete All Including Preserved"}</button>
            </div>
          </footer>` : ""}
      </section>
      ${() => state.deleteMode ? Modal({
        title: state.deleteMode === "all" ? "Delete All Routes, Including Preserved?" : "Delete All Non-Preserved Routes?",
        message: state.deleteMode === "all"
          ? "This permanently deletes every local route, including preserved routes. This action cannot be undone."
          : "This permanently deletes every non-preserved local route. Preserved routes will be kept.",
        onConfirm: () => deleteAllRoutes(state.deleteMode === "all"),
        onCancel: () => { state.deleteMode = null },
        confirmText: state.deleteMode === "all" ? "Delete Everything" : "Delete Non-Preserved",
      }) : ""}
    </div>`
}
