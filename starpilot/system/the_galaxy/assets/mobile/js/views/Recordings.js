import { api, showSnackbar } from "../api.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"
import { GalaxyTabs } from "../components/GalaxyTabs.js"
import { GxNotice } from "../components/GxNotice.js"
import { isFirestarOrigin } from "../components/PwaInstallSection.js"

function fmtDuration(seconds) {
  seconds = Number(seconds) || 0
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function formatBytes(bytes) {
  if (!bytes) return "0 MB"
  const mb = bytes / 1e6
  return mb >= 1000 ? `${(mb / 1000).toFixed(2)} GB` : `${mb.toFixed(1)} MB`
}

function getOrdinalSuffix(n) {
  const s = ["th", "st", "nd", "rd"]
  const v = n % 100
  return s[(v - 20) % 10] || s[v] || s[0]
}

function formatScreenDate(dateString) {
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return String(dateString || "Unknown date")
  const month = date.toLocaleString("en-US", { month: "long" })
  const day = date.getDate()
  const year = date.getFullYear()
  let hour = date.getHours()
  const minute = date.getMinutes()
  const ampm = hour >= 12 ? "pm" : "am"
  hour = hour % 12 || 12
  const minuteStr = minute < 10 ? "0" + minute : minute
  return `${month} ${day}${getOrdinalSuffix(day)}, ${year} - ${hour}:${minuteStr}${ampm}`
}

function normalizeRoute(r) {
  const name = String(r?.name || "")
  const isCustomName = !!r?.isCustomName
  return {
    name,
    displayName: r?.displayName || name.split("--").pop() || name,
    displayDate: r?.displayDate || "",
    approxDurationSeconds: Number(r?.approxDurationSeconds || 0),
    segmentCount: Number(r?.segmentCount || r?.numSegments || 0),
    is_preserved: !!r?.is_preserved,
    isCustomName,
    png: r?.png || "",
  }
}

export const Recordings = {
  name: "Recordings",
  components: { GalaxyTabs, GxNotice },
  data() {
    return {
      sub: "routes",
      loading: true,
      error: "",
      routes: [],
      progress: 0,
      searchQuery: "",
      sortOrder: "newest",
      showPreservedOnly: false,
      playerRoute: null,
      playerLoading: false,
      playerError: "",
      segments: [],
      current: 0,
      cameras: [],
      selectedCamera: "",
      logsRoute: null,
      logsData: null,
      onFirestar: isFirestarOrigin(),
      // Screen recordings subtab
      screenLoading: false,
      screenError: "",
      screenProgress: 0,
      recordings: [],
      recPlay: null,
    }
  },
  computed: {
    stats() {
      return {
        count: this.routes.length,
        formattedDuration: fmtDuration(this.routes.reduce((n, r) => n + r.approxDurationSeconds, 0)),
        preservedCount: this.routes.filter((r) => r.is_preserved).length,
      }
    },
    visibleRoutes() {
      let list = this.routes.slice()
      if (this.showPreservedOnly) list = list.filter((r) => r.is_preserved)
      if (this.searchQuery.trim()) {
        const q = this.searchQuery.toLowerCase()
        list = list.filter((r) => [r.displayName, r.displayDate, r.name].some((v) => String(v || "").toLowerCase().includes(q)))
      }
      const sorters = {
        newest: (a, b) => (b.name > a.name ? 1 : -1),
        oldest: (a, b) => (a.name > b.name ? 1 : -1),
        longest: (a, b) => b.approxDurationSeconds - a.approxDurationSeconds,
        shortest: (a, b) => a.approxDurationSeconds - b.approxDurationSeconds,
      }
      return list.sort(sorters[this.sortOrder] || sorters.newest)
    },
  },
  methods: {
    fmtDuration,
    formatBytes,
    setSub(key) {
      this.sub = key === "screen" ? "screen" : "routes"
      if (this.sub === "screen" && !this.recordings.length && !this.screenLoading) this.loadScreenRecordings()
    },
    screenDisplayName(rec) {
      return rec.is_custom_name ? rec.filename.replace(/\.mp4$/i, "").replace(/_/g, " ") : formatScreenDate(rec.timestamp)
    },
    async loadRoutes() {
      this.loading = true
      this.error = ""
      this.routes = []
      this.progress = 0
      const seen = new Set()
      try {
        this.controller?.abort()
        this.controller = new AbortController()
        await api.getRoutesStream({
          signal: this.controller.signal,
          onProgress: (p) => { this.progress = p },
          onRoutes: (raw) => {
            for (const r of raw) {
              if (seen.has(r.name)) continue
              seen.add(r.name)
              this.routes.push(normalizeRoute(r))
            }
          },
        })
      } catch (e) {
        if (e?.name !== "AbortError") this.error = "Couldn't load routes. Try refreshing."
      } finally {
        this.loading = false
      }
    },
    async loadScreenRecordings() {
      this.screenLoading = true
      this.screenError = ""
      this.recordings = []
      this.screenProgress = 0
      const seen = new Set()
      try {
        this.recController?.abort()
        this.recController = new AbortController()
        await api.screenRecordingsStream({
          signal: this.recController.signal,
          onProgress: (p) => { this.screenProgress = p },
          onRecordings: (raw) => {
            for (const r of raw) {
              if (seen.has(r.filename)) continue
              seen.add(r.filename)
              this.recordings.push(r)
            }
          },
        })
      } catch (e) {
        if (e?.name !== "AbortError") this.screenError = "Couldn't load recordings."
      } finally {
        this.screenLoading = false
      }
    },
    refreshScreenRecordings() {
      this.loadScreenRecordings()
    },
    async deleteRoute(route) {
      if (!(await GalaxyConfirm({ title: "Delete route?", message: `Delete “${route.displayName}”?`, confirmLabel: "Delete", danger: true }))) return
      try {
        await api.deleteRoute(route.name)
        this.routes = this.routes.filter((r) => r.name !== route.name)
        showSnackbar("Route deleted!")
      } catch (e) {
        showSnackbar("Delete failed.", "error")
      }
    },
    setPreservedFilter(key) {
      this.showPreservedOnly = key === "preserved"
    },
    async togglePreserved(route) {
      try {
        await api.setRoutePreserved(route.name, !route.is_preserved)
        route.is_preserved = !route.is_preserved
      } catch (e) {
        showSnackbar("Failed to update preserved state.", "error")
      }
    },
    async renameRoute(route) {
      const newName = prompt("Rename route:", route.displayName)
      if (!newName || newName === route.displayName) return
      try {
        const payload = await api.renameRoute(route.name, newName)
        Object.assign(route, normalizeRoute({ ...route, name: payload.name || newName, isCustomName: true }))
        route.displayName = payload.name || newName
        showSnackbar("Route renamed!")
      } catch (e) {
        showSnackbar("Rename failed.", "error")
      }
    },
    async deleteAllRoutes(includePreserved) {
      const label = includePreserved ? "Delete all routes, including preserved?" : "Delete all non-preserved routes?"
      if (!(await GalaxyConfirm({ title: label, message: "This action cannot be undone.", confirmLabel: includePreserved ? "Delete Everything" : "Delete Non-Preserved", danger: true }))) return
      try {
        const payload = await api.deleteAllRoutes(includePreserved)
        this.routes = []
        showSnackbar(payload?.message || "Routes deleted!")
      } catch (e) {
        showSnackbar(e?.message || "Failed to delete routes.", "error")
      }
    },
    async openPlayer(route) {
      this.playerRoute = route
      this.playerLoading = true
      this.playerError = ""
      this._playRetries = 0
      try {
        const data = await api.getRoute(route.name)
        const segments = Array.isArray(data.segment_urls) ? data.segment_urls.filter((u) => typeof u === "string") : []
        const cameras = ["forward", "wide", "driver"].filter((c) => data.available_cameras?.includes(c))
        if (!segments.length) throw new Error("No video segments for this route.")
        if (!cameras.length) throw new Error("No camera video for this route.")
        this.segments = segments
        this.current = 0
        this.cameras = cameras
        this.selectedCamera = cameras.includes("forward") ? "forward" : cameras[0]
        this.$nextTick(() => this.playSegment())
      } catch (e) {
        this.playerError = e?.message || "Could not load route."
      } finally {
        this.playerLoading = false
      }
    },
    cameraUrl(url, low) {
      if (this.selectedCamera === "forward") return low && !url.includes("?") ? `${url}?quality=low` : url
      const sep = url.includes("?") ? "&" : "?"
      return `${url}${sep}camera=${encodeURIComponent(this.selectedCamera)}${low ? "&quality=low" : ""}`
    },
    playSegment() {
      const video = this.$refs.player
      if (!this.segments[this.current]) return
      // The player mounts inside a Teleport + transition after openPlayer clears
      // playerLoading, so the video element may not exist on the very first call.
      if (!video) {
        this._playRetries = (this._playRetries || 0) + 1
        if (this._playRetries <= 15) {
          requestAnimationFrame(() => this.playSegment())
        }
        return
      }
      this._playRetries = 0
      video.src = this.cameraUrl(this.segments[this.current])
      video.load()
      video.play().catch(() => {})
    },
    downloadRoute() {
      if (!this.playerRoute) return
      const a = document.createElement("a")
      a.href = `/video/${this.playerRoute.name}/combined?camera=${encodeURIComponent(this.selectedCamera)}`
      a.download = `${this.playerRoute.displayName}-${this.selectedCamera}.mp4`
      a.click()
    },
    closePlayer() {
      this._playRetries = 0
      if (this.$refs.player) { this.$refs.player.pause(); this.$refs.player.removeAttribute("src") }
      this.playerRoute = null
      this.playerLoading = false
      this.playerError = ""
      this.segments = []
      this.cameras = []
    },
    async openLogs(route) {
      try {
        this.logsData = await api.getRouteLogs(route.name)
        this.logsRoute = route
      } catch (e) {
        showSnackbar("Could not read logs.", "error")
      }
    },
    closeRecPlayer() {
      this.recPlay = null
    },
    screenUrl(filename) {
      return api.screenRecordingVideoUrl(filename)
    },
    playRec(rec) {
      this.recPlay = rec
    },
    downloadRec(rec) {
      const a = document.createElement("a")
      a.href = api.screenRecordingVideoUrl(rec.filename)
      a.download = rec.filename
      a.click()
    },
    async renameRec(rec) {
      const base = rec.filename.replace(/\.mp4$/i, "")
      const val = prompt("Rename recording:", base)
      if (!val || val === base) return
      try {
        await api.renameScreenRecording(rec.filename, val + ".mp4")
        showSnackbar("Recording renamed!")
        this.refreshScreenRecordings()
      } catch (e) {
        showSnackbar("Rename failed.", "error")
      }
    },
    async deleteRec(rec) {
      if (!(await GalaxyConfirm({ title: "Delete recording?", message: `Delete “${rec.filename}”?`, confirmLabel: "Delete", danger: true }))) return
      try {
        await api.deleteScreenRecording(rec.filename)
        this.recordings = this.recordings.filter((r) => r.filename !== rec.filename)
        if (this.recPlay?.filename === rec.filename) this.recPlay = null
        showSnackbar("Recording deleted!")
      } catch (e) {
        showSnackbar("Delete failed.", "error")
      }
    },
    async deleteAllRecs() {
      if (!(await GalaxyConfirm({ title: "Delete all recordings?", message: "This permanently deletes every screen recording.", confirmLabel: "Delete All", danger: true }))) return
      try {
        const payload = await api.deleteAllScreenRecordings()
        this.recordings = []
        this.recPlay = null
        showSnackbar(payload?.message || "All screen recordings deleted!")
      } catch (e) {
        showSnackbar(e?.message || "Delete failed.", "error")
      }
    },
  },
  async mounted() {
    if (!this.onFirestar) await this.loadRoutes()
  },
  beforeUnmount() {
    this.controller?.abort()
    this.recController?.abort()
  },
  template: `
    <div>
      <template v-if="!onFirestar">
      <h2 style="margin-top:0;">Recordings</h2>

      <GalaxyTabs :items="{ routes: 'Dashcam Routes', screen: 'Screen Recordings' }" :active="sub" @select="setSub" />

      <template v-if="sub === 'routes'">
      <section class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-camera-reels"></i>
          <span class="gx-section__title">Dashcam Routes</span>
          <span class="gx-section__count">{{ stats.count }} drives · {{ stats.formattedDuration }}</span>
        </div>
        <div style="padding: var(--sp-3); display:flex; gap:8px; flex-wrap:wrap;">
          <input class="gx-field" style="flex:1; min-width:160px;" type="search" placeholder="Search routes..." v-model="searchQuery" />
          <select class="gx-field" v-model="sortOrder">
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="longest">Longest duration</option>
            <option value="shortest">Shortest duration</option>
          </select>
        </div>
        <div style="padding: 0 var(--sp-3) var(--sp-3);">
          <GalaxyTabs :items="{ all: 'All', preserved: 'Preserved' }" :active="showPreservedOnly ? 'preserved' : 'all'" @select="setPreservedFilter" />
        </div>
      </section>

      <div v-if="loading" class="gx-loading">Finding local routes... ({{ Math.round(progress) }}%)</div>
      <div v-if="error" class="gx-empty" style="color: var(--error);">{{ error }}</div>
      <section class="gx-card">
        <div v-if="!visibleRoutes.length && !loading" class="gx-empty">No routes found.</div>
        <article v-for="r in visibleRoutes" :key="r.name" class="gx-row" style="cursor:pointer;" @click="openPlayer(r)">
          <div class="gx-row__info">
            <span class="gx-row__label">{{ r.displayName }} <span v-if="r.is_preserved" class="gx-chip gx-chip--dev">Preserved</span></span>
            <span class="gx-row__desc">{{ fmtDuration(r.approxDurationSeconds) }} · {{ r.segmentCount }} segments</span>
          </div>
          <div style="display:flex; gap:6px;">
            <button type="button" class="gx-btn gx-btn--tonal" title="Preserve" @click.stop="togglePreserved(r)"><i class="bi" :class="r.is_preserved ? 'bi-heart-fill' : 'bi-heart'"></i></button>
            <button type="button" class="gx-btn gx-btn--tonal" title="Logs" @click.stop="openLogs(r)"><i class="bi bi-file-earmark-arrow-down"></i></button>
            <button type="button" class="gx-btn gx-btn--tonal" title="Rename" @click.stop="renameRoute(r)"><i class="bi bi-pencil"></i></button>
            <button type="button" class="gx-btn gx-btn--danger" title="Delete" @click.stop="deleteRoute(r)"><i class="bi bi-trash"></i></button>
          </div>
        </article>
      </section>

      <section class="gx-card" v-if="routes.length">
        <div class="gx-section__header">
          <i class="bi bi-exclamation-triangle"></i>
          <span class="gx-section__title">Delete local routes</span>
        </div>
        <div style="display:flex; gap:8px; padding: var(--sp-3); flex-wrap:wrap;">
          <button type="button" class="gx-btn gx-btn--tonal" @click="deleteAllRoutes(false)">Delete Non-Preserved</button>
          <button type="button" class="gx-btn gx-btn--danger" @click="deleteAllRoutes(true)">Delete All Including Preserved</button>
        </div>
      </section>

      <div v-if="logsRoute && logsData" class="gx-card" style="margin-top:12px;">
        <div class="gx-section__header">
          <i class="bi bi-file-earmark-arrow-down"></i>
          <span class="gx-section__title">{{ logsData.segments?.length || 0 }} segments · {{ formatBytes(logsData.totalBytes) }}</span>
          <a class="gx-btn gx-btn--tonal" :href="'/api/routes/' + logsRoute.name + '/logs/download'" download>Download all (.tar)</a>
        </div>
        <div v-for="seg in logsData.segments || []" :key="seg.segmentNum" class="gx-row">
          <div class="gx-row__info">
            <span class="gx-row__label">Segment {{ seg.segmentNum }}</span>
            <span class="gx-row__desc">{{ seg.filename }} · {{ formatBytes(seg.bytes) }}</span>
          </div>
          <a class="gx-btn gx-btn--tonal" :href="seg.url" download>Download</a>
        </div>
      </div>
      </template>

      <template v-else>
      <section class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-record-circle"></i>
          <span class="gx-section__title">Screen Recordings</span>
          <span class="gx-section__count">{{ recordings.length }}</span>
        </div>
        <div v-if="screenLoading && !recordings.length" class="gx-loading">Loading screen recordings...</div>
        <div v-else-if="screenError" class="gx-empty" style="color: var(--error);">{{ screenError }}</div>
        <div v-else-if="!recordings.length" class="gx-empty">No screen recordings found.</div>
        <article v-for="r in recordings" :key="r.filename" class="gx-row" style="cursor:pointer;" @click="playRec(r)">
          <img :src="r.png" alt="" loading="lazy" style="width:84px; height:auto; border-radius:var(--radius-sm); object-fit:cover; flex:none;">
          <div class="gx-row__info">
            <span class="gx-row__label">{{ screenDisplayName(r) }}</span>
            <span class="gx-row__desc">{{ r.filename }}</span>
          </div>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button type="button" class="gx-btn gx-btn--tonal" title="Play" @click.stop="playRec(r)"><i class="bi bi-play-fill"></i></button>
            <button type="button" class="gx-btn gx-btn--tonal" title="Rename" @click.stop="renameRec(r)"><i class="bi bi-pencil"></i></button>
            <button type="button" class="gx-btn gx-btn--tonal" title="Download" @click.stop="downloadRec(r)"><i class="bi bi-download"></i></button>
            <button type="button" class="gx-btn gx-btn--danger" title="Delete" @click.stop="deleteRec(r)"><i class="bi bi-trash"></i></button>
          </div>
        </article>
      </section>

      <section class="gx-card" v-if="recordings.length">
        <div class="gx-section__header">
          <i class="bi bi-exclamation-triangle"></i>
          <span class="gx-section__title">Delete recordings</span>
        </div>
        <div style="display:flex; gap:8px; padding: var(--sp-3); flex-wrap:wrap;">
          <button type="button" class="gx-btn gx-btn--danger" @click="deleteAllRecs">Delete All Recordings</button>
        </div>
      </section>
      </template>

      <Teleport to="body">
        <transition name="gx-fade">
          <div v-if="sub === 'routes' && playerRoute" class="gx-scrim gx-scrim--bottomsheet" @click.self="closePlayer">
            <div class="gx-sheet" role="dialog" aria-label="Route video player">
              <div class="gx-section__header" style="cursor:default;">
                <i class="bi bi-camera-video"></i>
                <span class="gx-section__title">{{ playerRoute.displayName }}</span>
                <button type="button" class="gx-icon-btn" aria-label="Close player" @click="closePlayer"><i class="bi bi-x-lg"></i></button>
              </div>
              <div style="padding: var(--sp-3);">
                <div v-if="playerError" class="gx-empty" style="color: var(--error);">{{ playerError }}</div>
                <div v-else-if="playerLoading" class="gx-loading"><i class="bi bi-hourglass-split"></i> Loading video...</div>
                <template v-else-if="segments.length">
                  <video ref="player" class="gx-video" controls muted playsinline preload="metadata"></video>
                  <div style="display:flex; gap:8px; padding: var(--sp-3) 0 0; flex-wrap:wrap; align-items:center;">
                    <button type="button" class="gx-btn gx-btn--tonal" :disabled="current<=0" @click="current--; playSegment()"><i class="bi bi-skip-start-fill"></i></button>
                    <select class="gx-field" :value="current" @change="current = Number($event.target.value); playSegment()">
                      <option v-for="(s,i) in segments" :key="i" :value="i">Segment {{ i + 1 }}</option>
                    </select>
                    <button type="button" class="gx-btn gx-btn--tonal" :disabled="current>=segments.length-1" @click="current++; playSegment()"><i class="bi bi-skip-end-fill"></i></button>
                    <button v-for="c in cameras" :key="c" type="button" class="gx-chip" :style="selectedCamera===c?'background:var(--primary);color:var(--on-primary);':''" @click="selectedCamera=c; playSegment()">{{ c }}</button>
                    <button type="button" class="gx-btn" @click="downloadRoute"><i class="bi bi-download"></i> Download</button>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </transition>
      </Teleport>

      <Teleport to="body">
        <transition name="gx-fade">
          <div v-if="recPlay" class="gx-scrim gx-scrim--bottomsheet" @click.self="closeRecPlayer">
            <div class="gx-sheet" role="dialog" aria-label="Screen recording player">
              <div class="gx-section__header" style="cursor:default;">
                <i class="bi bi-record-circle"></i>
                <span class="gx-section__title">{{ screenDisplayName(recPlay) }}</span>
                <button type="button" class="gx-icon-btn" aria-label="Close player" @click="closeRecPlayer"><i class="bi bi-x-lg"></i></button>
              </div>
              <div style="padding: var(--sp-3);">
                <video class="gx-video" controls autoplay playsinline :src="screenUrl(recPlay.filename)"></video>
                <div style="display:flex; gap:8px; padding: var(--sp-3) 0 0; flex-wrap:wrap;">
                  <button type="button" class="gx-btn" @click="downloadRec(recPlay)"><i class="bi bi-download"></i> Download</button>
                  <button type="button" class="gx-btn gx-btn--tonal" @click="renameRec(recPlay)"><i class="bi bi-pencil"></i> Rename</button>
                  <button type="button" class="gx-btn gx-btn--danger" @click="deleteRec(recPlay)"><i class="bi bi-trash"></i> Delete</button>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </Teleport>
      </template>

      <GxNotice v-else tone="info" icon="bi-satellite" title="Recordings Unavailable via Galaxy"
                text="Loading recordings requires a direct connection. Connect to your device's local network to use this feature." />
    </div>
  `,
}
