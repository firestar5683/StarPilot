import { GxIconButton } from "./icon-button.js"
import { GxNotice } from "./notice.js"
import { SnapshotFeed } from "./snapshot-feed.js"
import { RecordingActions } from "./recording-actions.js"
import { GalaxySelect } from "./galaxy-select.js"

// Local recording inventory and closed camera playback.
const LOCAL = /^(?:[a-f0-9]{8}--[a-f0-9]{10}|[0-9]{4}-[0-9]{2}-[0-9]{2}--[0-9]{2}-[0-9]{2}-[0-9]{2}|[a-f0-9]{16}\|(?:[a-f0-9]{8}--[a-f0-9]{10}|[0-9]{4}-[0-9]{2}-[0-9]{2}--[0-9]{2}-[0-9]{2}-[0-9]{2}))$/
const SEGMENT = /^(?:[a-f0-9]{8}--[a-f0-9]{10}|[0-9]{4}-[0-9]{2}-[0-9]{2}--[0-9]{2}-[0-9]{2}-[0-9]{2}|[a-f0-9]{16}[|_](?:[a-f0-9]{8}--[a-f0-9]{10}|[0-9]{4}-[0-9]{2}-[0-9]{2}--[0-9]{2}-[0-9]{2}-[0-9]{2}))--[0-9]{1,6}$/
const FILES = ["rlog", "qlog", "fcamera", "dcamera", "ecamera", "qcamera"]
const LABELS = { rlog: "Full log", qlog: "Quick log", fcamera: "Road video", dcamera: "Driver video",
  ecamera: "Wide video", qcamera: "Quick video" }

export function validLocalHistory(value) {
  if (value?.schemaVersion !== 1 || value.source !== "local" || value.partialHistory !== true ||
      typeof value.scanIncomplete !== "boolean" || !Array.isArray(value.routes) || value.routes.length > 100) return false
  let count = 0
  const routes = new Set()
  return value.routes.every((route) => {
    if (typeof route?.routeId !== "string" || !LOCAL.test(route.routeId) || routes.has(route.routeId) ||
        !Array.isArray(route.segments) || route.segments.length > 64 ||
        !Number.isSafeInteger(route.segmentCount) || route.segmentCount !== route.segments.length) return false
    routes.add(route.routeId)
    const numbers = new Set()
    count += route.segmentCount
    return count <= 512 && route.segments.every((segment) => {
      if (!Number.isSafeInteger(segment?.number) || segment.number < 0 || segment.number > 999999 ||
          typeof segment.segmentName !== "string" || !SEGMENT.test(segment.segmentName) ||
          (!segment.segmentName.startsWith(route.routeId.replace('|', '_') + '--') &&
           !segment.segmentName.startsWith(route.routeId + '--')) ||
          Number(segment.segmentName.slice(segment.segmentName.lastIndexOf('--') + 2)) !== segment.number ||
          numbers.has(segment.number) || segment.files === null || typeof segment.files !== "object" ||
          Object.keys(segment.files).length !== FILES.length ||
          !FILES.every((key) => typeof segment.files[key] === "boolean") ||
          !FILES.some((key) => segment.files[key])) return false
      numbers.add(segment.number)
      return true
    })
  })
}

const VIDEOS = ["fcamera", "dcamera", "ecamera", "qcamera"]
export const hasVideo = (files) => VIDEOS.some((key) => files?.[key])
export const availableFiles = (files) => FILES.filter((key) => files?.[key]).map((key) => LABELS[key])
export const routeFiles = (route) => availableFiles(Object.fromEntries(FILES.map((key) =>
  [key, route.segments.some((segment) => segment.files[key])])))
export const firstQuickVideo = (route) => route.segments.find((segment) => segment.files.qcamera) || null
export function routeDate(route, locale = undefined, timeZone = undefined) {
  const validTime = (value) => typeof value === "number" && Number.isFinite(value) && value > 0 && Number.isFinite(new Date(value * 1000).getTime())
  const captured = validTime(route.startTime)
  const value = captured ? route.startTime : validTime(route.fileTime) ? route.fileTime : null
  if (value === null) return { label: "Date unavailable", source: "", datetime: null }
  const date = new Date(value * 1000)
  return { label: new Intl.DateTimeFormat(locale, { year: "numeric", month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit", ...(timeZone ? { timeZone } : {}) }).format(date),
    source: captured ? "" : "File date", datetime: date.toISOString() }
}
export function connectRouteUrl(route) {
  if (typeof route?.routeId !== "string" || !LOCAL.test(route.routeId) || typeof route.connectUrl !== "string") return null
  const host = route.provider === "konik" ? "stable.konik.ai" : route.provider === undefined || route.provider === "comma" ? "connect.comma.ai" : null
  if (host === null) return null
  const match = /^https:\/\/(connect\.comma\.ai|stable\.konik\.ai)\/([a-f0-9]{16})\/([^/?#]+)$/.exec(route.connectUrl)
  const [device, identifier] = route.routeId.includes('|') ? route.routeId.split('|') : [null, route.routeId]
  return match && match[1] === host && match[3] === identifier && (device === null || match[2] === device) ? route.connectUrl : null
}
export const recordingUrl = (segmentName, camera = "qcamera") => SEGMENT.test(segmentName) &&
  ["qcamera", "fcamera", "dcamera", "ecamera"].includes(camera) ?
  `./api/recordings/media/${encodeURIComponent(segmentName)}${camera === "qcamera" ? "" : "/" + camera}` : null
export const quickRoadUrl = (segmentName) => recordingUrl(segmentName)
export const segmentSummaryUrl = (segmentName) => SEGMENT.test(segmentName) ?
  `./api/recordings/segment-summary?segmentName=${encodeURIComponent(segmentName)}` : null

export function validSegmentSummary(value, segmentName) {
  const metric = (v) => v === null || (typeof v === "number" && Number.isFinite(v) && v >= 0)
  return value?.schemaVersion === 1 && value.source === "closed_local_rlog" &&
    value.segmentName === segmentName && typeof value.sourceSha256 === "string" &&
    /^[a-f0-9]{64}$/.test(value.sourceSha256) &&
    [value.observedCarSpanSeconds, value.estimatedDistanceMeters,
      value.observedLatActiveSeconds, value.observedLongActiveSeconds].every(metric) &&
    value.gaps && Number.isSafeInteger(value.gaps.carState) && value.gaps.carState >= 0 &&
    Number.isSafeInteger(value.gaps.carControl) && value.gaps.carControl >= 0 &&
    typeof value.sampleCoverageComplete === "boolean"
}

export const detailMetric = (seconds, unit = "s") => seconds === null ? "Unavailable" :
  `${seconds.toFixed(unit === "m" ? 1 : 2)} ${unit}`



const searchText = value => String(value || "").normalize("NFKD").replace(/\p{M}/gu, "")
  .toLocaleLowerCase().replace(/(\d+)(?:st|nd|rd|th)\b/g, "$1").replace(/[^\p{L}\p{N}]+/gu, " ").trim()

export function routeMatchesSearch(route, query) {
  const date = routeDate(route)
  const index = searchText(`${route.displayName || ""} ${route.routeId} ${date.label} ${date.datetime || ""}`)
  return searchText(query).split(" ").every(word => index.includes(word))
}

export class LocalHistoryFeed extends SnapshotFeed {
  static endpoint = "./api/recordings/local"
  static valid = validLocalHistory
  static subject = "local recordings"
  static unavailable = "Local recordings are unavailable."
  static invalid = "Local recording inventory is unavailable."
}

export const LocalRecordingsPage = {
  name: "LocalRecordingsPage",
  components: { GxIconButton, GxNotice, RecordingActions, GalaxySelect },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ sortOrder: "newest", logsRoute: null, query: "", preservedOnly: false, status: "idle", data: null, error: "", playing: null, playerError: "", playerGeneration: 0,
    details: null, detailsName: null, detailsStatus: "idle", detailsError: "", detailsGeneration: 0,
    deleting: null, deleteError: "" }),
  computed: {
    stats() { const routes = this.data?.routes || []; return { count: routes.length, minutes: routes.reduce((sum, route) => sum + route.segmentCount, 0), preserved: routes.filter(route => route.preserved).length } },
    playerCameras() { return ["fcamera", "ecamera", "dcamera", "qcamera"].filter(camera =>
      this.playing?.route.segments.some(segment => segment.files[camera])) },
    routeCards() {
      const ordered = (this.data?.routes || []).slice().sort((a, b) => {
        if (["longest", "shortest"].includes(this.sortOrder)) return (b.segmentCount - a.segmentCount) * (this.sortOrder === "shortest" ? -1 : 1)
        return ((b.startTime || b.fileTime || 0) - (a.startTime || a.fileTime || 0)) * (this.sortOrder === "oldest" ? -1 : 1)
      })
      return ordered.filter(route => (!this.preservedOnly || route.preserved) &&
        routeMatchesSearch(route, this.query)).map((route) => ({ ...route, date: routeDate(route),
        connect: connectRouteUrl(route), fileLabels: routeFiles(route), firstQuick: firstQuickVideo(route), firstFull: route.segments.find(segment => segment.files.fcamera) }))
    },
  },
  created() { this.feed = new LocalHistoryFeed({ publish: (update) => Object.assign(this.$data, update), unauthorized: this.unauthorized }) },
  mounted() {
    this.visibility = () => { if (document.hidden) { this.closePlayer(); this.closeDetails(); this.logsRoute = null; this.feed.stop() } else if (this.mode === "local") this.feed.start() }
    document.addEventListener("visibilitychange", this.visibility)
    if (this.mode === "local" && !document.hidden) this.feed.start()
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibility); this.closePlayer(); this.closeDetails(); this.logsRoute = null; this.feed.stop() },
  watch: { mode(value) { if (value !== "local") { this.closePlayer(); this.closeDetails() } } },
  methods: {
    availableFiles,
    hasVideo,
    quickRoadUrl,
    recordingUrl,
    driveVideoUrl: (routeId, camera) => LOCAL.test(routeId) && ["qcamera", "fcamera", "dcamera", "ecamera"].includes(camera) ?
      `./api/recordings/route/${encodeURIComponent(routeId)}/${camera}` : null,
    cameraLabel: camera => LABELS[camera],
    logUrl: (segmentName, filename) => SEGMENT.test(segmentName) && /^(rlog|qlog)\.(zst|bz2)$/.test(filename) ?
      `./api/recordings/files/${encodeURIComponent(segmentName)}/${filename}` : null,
    detailMetric,
    refresh() { this.closePlayer(); this.closeDetails(); this.logsRoute = null; return this.feed.load() },
    watchRoute(route) {
      const camera = ["fcamera", "ecamera", "dcamera", "qcamera"].find(camera => route.segments.some(segment => segment.files[camera]))
      if (camera) this.openPlayer(route, route.segments.find(segment => segment.files[camera]), camera)
    },
    openLogs(route) { this.logsRoute = route; this.$nextTick?.(() => this.$refs.logsPanel?.scrollIntoView?.({ behavior: "smooth", block: "nearest" })) },
    logArchiveUrl(routeId) { return LOCAL.test(routeId) ? `./api/recordings/logs/${encodeURIComponent(routeId)}` : null },
    formatDuration(minutes) { return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes} min` },
    formatBytes(bytes) { return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(2)} GB` : `${((bytes || 0) / 1e6).toFixed(1)} MB` },
    async deleteVideos(segment) {
      if (this.mode !== "local" || this.status !== "ready" || this.deleting !== null || !hasVideo(segment?.files)) return
      if (!window.confirm(`Delete the videos for segment ${segment.number}? Its logs stay on the device. This cannot be undone.`)) return
      if (this.playing?.segments.some((item) => item.segmentName === segment.segmentName)) this.closePlayer()
      this.deleting = segment.segmentName
      this.deleteError = ""
      const controller = new AbortController()
      const deadline = setTimeout(() => controller.abort(), 10000)
      try {
        const response = await fetch("./api/recordings/delete-videos", { method: "POST", credentials: "same-origin", cache: "no-store",
          headers: { "Content-Type": "application/json" }, body: JSON.stringify({ segmentName: segment.segmentName }), signal: controller.signal })
        if (response.status === 401) { this.feed.stop(); this.unauthorized(); return }
        if (!response.ok && response.status !== 404) {
          const body = await response.json().catch(() => null)
          throw new Error(typeof body?.error === "string" ? body.error : "Videos could not be deleted.")
        }
      } catch (error) {
        this.deleteError = controller.signal.aborted ? "Deleting videos timed out. Refresh to check what remains." :
          error instanceof Error ? error.message : "Videos could not be deleted."
      } finally {
        clearTimeout(deadline)
        this.deleting = null
      }
      if (this.deleteError) return
      await this.feed.load()
      if (this.logsRoute) this.logsRoute = this.routeCards.find(route => route.routeId === this.logsRoute.routeId) || null
    },
    closeDetails() {
      this.detailsRequest?.abort()
      if (this.detailsTimer !== undefined) clearTimeout(this.detailsTimer)
      this.detailsRequest = null
      this.detailsTimer = undefined
      this.detailsGeneration++
      this.details = null
      this.detailsName = null
      this.detailsStatus = "idle"
      this.detailsError = ""
    },
    async openDetails(segment) {
      if (this.mode !== "local" || this.status !== "ready" || !segment?.files?.rlog || document.hidden) return
      const url = segmentSummaryUrl(segment.segmentName)
      if (!url) return
      this.closeDetails()
      const generation = this.detailsGeneration
      const controller = new AbortController()
      this.detailsRequest = controller
      this.detailsName = segment.segmentName
      this.detailsStatus = "loading"
      this.detailsTimer = setTimeout(() => {
        if (generation !== this.detailsGeneration || this.detailsRequest !== controller) return
        controller.abort()
        this.detailsRequest = null
        this.detailsGeneration++
        this.detailsTimer = undefined
        this.detailsStatus = "unavailable"
        this.detailsError = "Reading this segment timed out. Select Details to try again."
      }, 10000)
      try {
        const response = await fetch(url, { credentials: "same-origin", cache: "no-store", signal: controller.signal })
        if (generation !== this.detailsGeneration || controller.signal.aborted) return
        if (response.status === 401) { this.closeDetails(); this.unauthorized(); return }
        if (response.status === 503) {
          const body = await response.json().catch(() => null)
          if (generation !== this.detailsGeneration || controller.signal.aborted) return
          if (["setup_required", "access_unavailable"].includes(body?.code)) { this.closeDetails(); this.unauthorized(); return }
        }
        if (!response.ok) throw new Error("Recorded segment details are unavailable.")
        const result = await response.json()
        if (generation !== this.detailsGeneration || controller.signal.aborted) return
        if (!validSegmentSummary(result, segment.segmentName)) throw new Error("Recorded segment details are unavailable.")
        this.details = result
        this.detailsStatus = "ready"
        this.$nextTick?.(() => this.$refs.detailsPanel?.scrollIntoView?.({ block: "nearest", behavior: "smooth" }))
      } catch (error) {
        if (generation === this.detailsGeneration) {
          this.detailsStatus = "unavailable"
          this.detailsError = error instanceof Error ? error.message : "Recorded segment details are unavailable."
        }
      } finally {
        if (generation === this.detailsGeneration) {
          if (this.detailsTimer !== undefined) clearTimeout(this.detailsTimer)
          this.detailsTimer = undefined
          this.detailsRequest = null
        }
      }
    },
    openPlayer(route, segment, camera = "qcamera") {
      if (this.mode !== "local" || this.status !== "ready" || !segment.files[camera]) return
      const segments = route.segments.filter((item) => item.files[camera] && recordingUrl(item.segmentName, camera))
      const index = segments.findIndex((item) => item.segmentName === segment.segmentName)
      if (index < 0) return
      this.closePlayer()
      this.playing = { route, routeId: route.routeId, segments, index, camera, url: recordingUrl(segment.segmentName, camera) }
      this.playerGeneration++
      this.$nextTick?.(() => { if (this.$refs.playerPanel && !this.$refs.playerPanel.open) this.$refs.playerPanel.showModal() })
    },
    selectCamera(camera) {
      if (!this.playing) return
      const { route, segments, index } = this.playing
      const segment = route.segments.find(item => item.number === segments[index].number && item.files[camera]) ||
        route.segments.find(item => item.files[camera])
      if (segment) this.openPlayer(route, segment, camera)
    },
    chooseSegment(offset) {
      if (!this.playing) return
      const index = this.playing.index + offset
      if (index < 0 || index >= this.playing.segments.length) return
      this.sessionProbe?.abort()
      this.sessionProbe = null
      this.$refs.quickVideo?.pause()
      this.$refs.quickVideo?.removeAttribute("src")
      this.playing = { ...this.playing, index, url: recordingUrl(this.playing.segments[index].segmentName, this.playing.camera) }
      this.playerError = ""
      this.playerGeneration++
    },
    closePlayer() {
      this.$refs.playerPanel?.close?.()
      this.sessionProbe?.abort()
      this.sessionProbe = null
      this.$refs.quickVideo?.pause()
      this.$refs.quickVideo?.removeAttribute("src")
      this.$refs.quickVideo?.load()
      this.playing = null
      this.playerError = ""
      this.playerGeneration++
    },
    async videoError(event) {
      if (!this.playing || event.currentTarget !== this.$refs.quickVideo ||
          Number(event.currentTarget.dataset.playerGeneration) !== this.playerGeneration) return
      const generation = this.playerGeneration
      this.playerError = "This camera recording could not play in this browser. Download the video to watch it in a compatible player."
      const controller = new AbortController()
      this.sessionProbe?.abort()
      this.sessionProbe = controller
      const deadline = setTimeout(() => controller.abort(), 4000)
      let revoke = false
      try {
        const response = await fetch("./api/auth/session", { credentials: "same-origin", cache: "no-store", signal: controller.signal })
        if (!this.playing || generation !== this.playerGeneration || controller.signal.aborted) return
        const state = await response.json()
        if (!this.playing || generation !== this.playerGeneration || controller.signal.aborted) return
        revoke = response.status === 401 || state.authenticated === false
      } catch { /* A media or session request may fail; keep the explicit playback error. */ }
      finally { clearTimeout(deadline); if (this.sessionProbe === controller) this.sessionProbe = null }
      if (revoke && this.playing && generation === this.playerGeneration) { this.closePlayer(); this.unauthorized() }
    },
  },
  template: `
    <div class="gx-view gx-recordings">
      <h2>Recordings</h2>
      <p v-if="mode !== 'local'" class="gx-card gx-message">Local recordings are unavailable in the offline preview.</p>
      <template v-else>
        <section class="gx-card gx-recordings__library">
          <header class="gx-section__header"><i class="bi bi-camera-reels" aria-hidden="true"></i><span class="gx-section__title">Dashcam drives</span>
            <span class="gx-section__count">{{ stats.count }} drives · ~{{ formatDuration(stats.minutes) }}</span>
            </header>
          <div class="gx-recordings__filters">
            <input class="gx-field" type="search" aria-label="Search recordings" placeholder="Search drives, dates or IDs…" v-model="query" />
            <GalaxySelect class="gx-field" aria-label="Sort recordings" :value="sortOrder" @change="sortOrder=$event.target.value">
              <option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="longest">Longest duration</option><option value="shortest">Shortest duration</option>
            </GalaxySelect>
            <div class="gx-recordings__tabs" aria-label="Filter recordings"><button class="gx-btn gx-btn--tonal" :aria-pressed="!preservedOnly" @click="preservedOnly=false">All</button><button class="gx-btn gx-btn--tonal" :aria-pressed="preservedOnly" @click="preservedOnly=true">Preserved · {{ stats.preserved }}</button></div>
          </div>
        </section>
        <p v-if="status === 'loading'" role="status" class="gx-card gx-message">Finding local drives…</p><GxNotice tone="danger" v-if="status === 'unavailable'">{{ error }}</GxNotice><GxNotice tone="danger" v-if="deleteError">{{ deleteError }}</GxNotice>
        <template v-if="status === 'ready' && data">
          <p v-if="data.scanIncomplete" role="status">This scan was incomplete. More local segments may exist.</p>
          <section class="gx-card gx-recordings__list">
            <p v-if="!routeCards.length" class="gx-recordings__empty">{{ data.routes.length ? 'No drives match your filters.' : 'No saved drives found on this device.' }}</p>
            <article v-for="route in routeCards" :key="route.routeId" class="gx-recordings__row" :class="{'gx-recordings__row--preserved': route.preserved}">
              <button class="gx-recordings__drive" :disabled="!route.segments.some(segment => segment.files.fcamera || segment.files.ecamera || segment.files.dcamera || segment.files.qcamera)" :aria-label="'Watch ' + (route.displayName !== route.routeId ? route.displayName : route.date.label)" @click="watchRoute(route)">
                <span class="gx-row__label">{{ route.displayName !== route.routeId ? route.displayName : route.date.label }}</span>
                <span class="gx-row__desc"><template v-if="route.displayName !== route.routeId">{{ route.date.label }} · </template>~{{ formatDuration(route.segmentCount) }} · {{ route.segmentCount }} saved {{ route.segmentCount === 1 ? "segment" : "segments" }}</span>
                <span v-if="route.preserved" class="gx-chip">Preserved</span>
              </button>
              <RecordingActions :recording="route" :unauthorized="unauthorized" @changed="refresh"><button class="gx-icon-btn" aria-label="View drive logs" title="Logs and files" @click="openLogs(route)"><i class="bi bi-file-earmark-arrow-down"></i></button></RecordingActions>
            </article>
          </section>
          <section v-if="logsRoute" ref="logsPanel" class="gx-card gx-recordings__logs">
            <header class="gx-section__header"><i class="bi bi-file-earmark-arrow-down"></i><span class="gx-section__title">{{ logsRoute.displayName !== logsRoute.routeId ? logsRoute.displayName : logsRoute.date.label }} · Logs and files</span><button class="gx-icon-btn" aria-label="Close logs" @click="logsRoute=null"><i class="bi bi-x-lg"></i></button></header>
            <div class="gx-recordings__actions gx-recordings__log-toolbar"><a v-if="logsRoute.segments.some(segment => segment.logFiles?.length)" class="gx-btn gx-btn--tonal" :href="logArchiveUrl(logsRoute.routeId)" :download="logsRoute.routeId + '-logs.tar'"><i class="bi bi-download"></i>Download all logs (.tar)</a><a class="gx-btn gx-btn--tonal" href="#/tuning/flm">Analyze driving logs</a><a v-if="logsRoute.connect" class="gx-btn gx-btn--tonal" :href="logsRoute.connect" target="_blank" rel="noopener noreferrer">Open in comma connect</a></div>
            <ul class="gx-recordings__segments"><li v-for="segment in logsRoute.segments" :key="segment.number">
              <div class="gx-recordings__segment-info"><strong>Segment {{ segment.number }}</strong><ul class="gx-recordings__files"><li v-for="file in availableFiles(segment.files)" :key="file">{{ file }}</li></ul></div>
              <div class="gx-recordings__actions"><a v-for="filename in segment.logFiles || []" :key="filename" class="gx-btn gx-btn--tonal" :href="logUrl(segment.segmentName, filename)" :download="segment.segmentName + '-' + filename">{{ filename }}<span v-if="segment.logBytes?.[filename]"> · {{ formatBytes(segment.logBytes[filename]) }}</span><i class="bi bi-download"></i></a>
                <button v-if="segment.files.rlog" class="gx-btn gx-btn--tonal" @click="openDetails(segment)">Details</button>
                <button v-for="camera in ['fcamera', 'ecamera', 'dcamera', 'qcamera'].filter(camera => segment.files[camera])" :key="camera" class="gx-btn gx-btn--tonal" @click="openPlayer(logsRoute, segment, camera)">Play {{ cameraLabel(camera) }}</button>
                <button v-if="hasVideo(segment.files)" type="button" class="gx-btn gx-btn--tonal gx-recordings__danger" :disabled="deleting !== null" @click="deleteVideos(segment)"><i aria-hidden="true" class="bi bi-trash"></i> {{ deleting === segment.segmentName ? 'Deleting…' : 'Delete videos' }}</button>
              </div>
            </li></ul>
          </section>
          <section v-if="detailsName" ref="detailsPanel" class="gx-card gx-recordings__details" aria-label="Recorded segment details">
            <div class="gx-recordings__player-head"><h3>Recorded Segment Details</h3><GxIconButton label="Close segment details" icon="bi-x-lg" @click="closeDetails" /></div>
            <p class="gx-note">{{ detailsName }} · For this saved segment only. Distance is estimated from recorded speed.</p>
            <p v-if="detailsStatus === 'loading'" role="status" class="gx-card gx-message">Reading closed full log…</p>
            <GxNotice tone="danger" v-if="detailsStatus === 'unavailable'">{{ detailsError }}</GxNotice>
            <div v-if="detailsStatus === 'ready' && details" class="gx-recordings__metrics">
              <div><strong>{{ detailMetric(details.observedCarSpanSeconds) }}</strong><span>Recorded time span</span></div>
              <div><strong>{{ detailMetric(details.estimatedDistanceMeters, 'm') }}</strong><span>Estimated distance</span></div>
              <div><strong>{{ detailMetric(details.observedLatActiveSeconds) }}</strong><span>Steering active</span></div>
              <div><strong>{{ detailMetric(details.observedLongActiveSeconds) }}</strong><span>Longitudinal active</span></div>
            </div>
            <p v-if="detailsStatus === 'ready' && details && !details.sampleCoverageComplete" class="gx-note">Samples have gaps or a missing source; unavailable values were not inferred.</p>
          </section>

          <section v-if="data.routes.length" class="gx-card gx-recordings__delete">
            <header class="gx-section__header"><i class="bi bi-exclamation-triangle"></i><span class="gx-section__title">Delete local drives</span></header>
            <RecordingActions :recording="{displayName: 'local driving recordings'}" all :unauthorized="unauthorized" @changed="refresh" />
          </section>
          <p class="gx-note">Duration is approximate from saved one-minute segments. Older footage may have been removed to free space.</p>
          <Teleport to="body"><dialog v-if="playing" ref="playerPanel" class="gx-card gx-recordings__player" aria-label="Camera recording player" @cancel.prevent="closePlayer">
            <div class="gx-recordings__player-head"><div><h3>{{ cameraLabel(playing.camera) }}</h3><p class="gx-note">{{ playing.camera === "qcamera" ? "Quick preview" : "Full-resolution recording" }} · {{ playing.routeId }} · segment {{ playing.segments[playing.index].number }}</p></div>
              <GxIconButton label="Close recording player" icon="bi-x-lg" @click="closePlayer" /></div>
            <div class="gx-recordings__actions"><button v-for="camera in playerCameras" :key="camera" class="gx-btn gx-btn--tonal"
              :aria-pressed="playing.camera === camera" @click="selectCamera(camera)">{{ cameraLabel(camera) }}</button></div>
            <video :key="playerGeneration" ref="quickVideo" :data-player-generation="playerGeneration" controls playsinline autoplay preload="metadata" :src="playing.url" @error="videoError($event)" @ended="chooseSegment(1)"></video>
            <GxNotice tone="danger" v-if="playerError">{{ playerError }}</GxNotice>
            <div class="gx-recordings__actions"><a class="gx-btn gx-btn--tonal" :href="playing.url" :download="playing.routeId + '-' + playing.camera + '-' + playing.segments[playing.index].number + '.mp4'">Download segment</a>
            <a class="gx-btn gx-btn--tonal" :href="driveVideoUrl(playing.routeId, playing.camera)" :download="playing.routeId + '-' + playing.camera + '.mp4'">Download drive</a></div>
            <div class="gx-recordings__player-controls"><GxIconButton label="Previous segment" icon="bi-skip-backward-fill" :disabled="playing.index === 0" @click="chooseSegment(-1)" />
              <GalaxySelect class="gx-field" aria-label="Video segment" :value="String(playing.index)" @change="chooseSegment(Number($event.target.value) - playing.index)"><option v-for="(segment, index) in playing.segments" :key="segment.number" :value="String(index)" :data-collapsed-label="'Segment ' + segment.number">Segment {{ segment.number }} · {{ index + 1 }} of {{ playing.segments.length }}</option></GalaxySelect>
              <GxIconButton label="Next segment" icon="bi-skip-forward-fill" :disabled="playing.index === playing.segments.length - 1" @click="chooseSegment(1)" /></div>
          </dialog></Teleport>

        </template>
      </template>
    </div>`,
}
