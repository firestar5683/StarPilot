import { requestJson } from "./startup.js"
import { GxDialog } from "./dialog.js"
import { GxNotice } from "./notice.js"
import { GxState } from "./state.js"
import { GxIconButton } from "./icon-button.js"
import { markRaw } from "../vendor/vue/vue.esm-browser.js"

const ID = /^[a-f0-9]{32}$/
const STATES = new Set(["idle", "preparing", "buffering", "playing", "paused", "seeking", "stopping", "ended", "failed"])
const TERMINAL = new Set(["idle", "failed"])
const number = value => typeof value === "number" && Number.isFinite(value)
const integer = value => Number.isSafeInteger(value) && value >= 0
const token = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), value => value.toString(16).padStart(2, "0")).join("")
const mediaSources = () => [globalThis.MediaSource, globalThis.ManagedMediaSource].filter(Source => typeof Source === "function")
const STREAMING_UNAVAILABLE = "Replay video streaming is unavailable in this browser. Update your browser or try another browser."
const PLAY_BUFFER = .5, MAX_BUFFER_AHEAD = 1, MEDIA_INTERVAL = 50
export const replayableSegment = segment => !!((segment.files.rlog || segment.files.qlog) && (segment.files.fcamera || segment.files.qcamera))
export function validReplayStatus(value) {
  const ranges = value?.seekRanges
  return value?.schemaVersion === 1 && ID.test(value.ownerId) && STATES.has(value.state) &&
    (value.sessionId === null || ID.test(value.sessionId)) && integer(value.revision) && integer(value.epoch) &&
    [value.position, value.start, value.end].every(number) && value.start <= value.end &&
    [.5, 1, 2].includes(value.rate) && typeof value.paused === "boolean" && typeof value.offroad === "boolean" && typeof value.owned === "boolean" &&
    (value.codec == null || typeof value.codec === "string" && value.codec.length <= 128) &&
    (ranges === undefined || Array.isArray(ranges) && ranges.length <= 512 && ranges.every((range, i) =>
      Array.isArray(range) && range.length === 2 && range.every(number) && value.start <= range[0] && range[0] <= range[1] &&
      range[1] <= value.end && (i === 0 || ranges[i-1][1] <= range[0])))
}
export function replaySeekPosition(status, position) {
  const bounded = Math.min(status.end, Math.max(status.start, position)), ranges = status.seekRanges || []
  if (!ranges.length || ranges.some(([start, end]) => start <= bounded && bounded <= end)) return bounded
  let nearest = ranges[0][0]
  for (const range of ranges) for (const boundary of range) if (Math.abs(boundary - bounded) < Math.abs(nearest - bounded)) nearest = boundary
  return nearest
}
export function replaySeekGaps(status) {
  const gaps = [], ranges = status?.seekRanges || []
  let after = status?.start
  for (const [start, end] of ranges) { if (start > after) gaps.push([after, start]); after = end }
  if (ranges.length && after < status.end) gaps.push([after, status.end])
  return gaps
}
export function replayBufferTime(buffered, paused = false) {
  const last = buffered.length - 1, start = buffered.start(last), end = buffered.end(last)
  return Math.max(start, end - (paused ? .001 : Math.min(.2, end - start)))
}
export const replayTime = seconds => `${Math.floor(Math.max(0, seconds) / 60)}:${String(Math.floor(Math.max(0, seconds) % 60)).padStart(2, "0")}`

// The browser owns viewing; every route action still goes through the parked replay owner.
export class ReplayClient {
  constructor({ publish, unauthorized, video, fetcher = (...args) => fetch(...args),
    mediaSource = Source => new Source(), createURL = value => URL.createObjectURL(value), revokeURL = value => URL.revokeObjectURL(value),
    later = (fn, ms) => setTimeout(fn, ms), cancelTimer = id => clearTimeout(id), clientId = token() }) {
    Object.assign(this, { publish, unauthorized, video, fetcher, mediaSource, createURL, revokeURL, later, cancelTimer, clientId })
    this.active = false
    this.generation = this.mediaGeneration = 0
    this.requests = new Set()
    this.status = null
    this.busy = false
    this.pendingAction = null
    this.error = ""
    this.detail = null
    this.ownedSession = null
  }
  emit() { this.publish({ replay: this.status, replayBusy: this.busy, replayError: this.error, replayDetail: this.detail,
    replayVideoReady: !!this.buffer?.buffered.length, replayBuffering: this.needsBuffer() }) }
  async json(path, body = null) {
    const request = new AbortController(), generation = this.generation
    this.requests.add(request)
    if (path === "start") this.startRequest = request
    try {
      const data = await requestJson(`./api/replay/${path}`, { fetcher: this.fetcher, timeout: 6000,
        later: this.later, cancel: this.cancelTimer, request: { signal: request.signal,
          ...(body === null ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }) } })
      return path === "start" || this.active && generation === this.generation ? data : null
    } catch (error) {
      if (!this.active || generation !== this.generation) return null
      if (error.status === 401 || ["setup_required", "access_unavailable"].includes(error.code)) { this.close(false); this.unauthorized(); return null }
      throw error
    } finally { this.requests.delete(request); if (this.startRequest === request) this.startRequest = null }
  }
  async open(routeId, startSegment = null) {
    this.close(false)
    this.active = true
    this.status = this.detail = null; this.error = ""
    this.routeId = routeId
    this.startSegment = startSegment
    this.emit()
    const generation = this.generation
    try {
      const [detail] = await Promise.all([this.json(`detail?routeId=${encodeURIComponent(routeId)}`), this.refresh()])
      if (!this.active || generation !== this.generation) return
      this.detail = detail; this.emit()
      if (!this.error && detail?.playable && this.status?.offroad && TERMINAL.has(this.status.state)) await this.start()
    } catch (error) { if (this.active) { this.error = error.message; this.emit() } }
  }
  async refresh() {
    if (!this.active || this.reading) return
    const generation = this.generation
    this.reading = true
    try {
      const status = await this.json(`status?clientId=${this.clientId}`)
      if (!status) return
      if (!validReplayStatus(status)) throw new Error("Replay returned an unsupported status.")
      this.receive(status)
    } catch (error) {
      if (this.active) { this.retireMedia(); this.status = null; this.error = error.message || "Replay disconnected. Refresh before continuing."; this.emit() }
    } finally {
      if (generation === this.generation) {
        this.reading = false
        if (this.active) { this.cancelTimer(this.timer); this.timer = this.later(() => this.refresh(), 500) }
      }
    }
  }
  receive(status) {
    const prior = this.status
    if (prior?.ownerId === status.ownerId && prior.sessionId === status.sessionId && status.revision < prior.revision) return
    if (!this.ownedSession && this.startAttempted && status.owned && ID.test(status.sessionId) && status.routeId === this.routeId) { this.ownedSession = status.sessionId; this.error = "" }
    this.status = status
    if (status.lastRequestId === this.pendingAction || TERMINAL.has(status.state) || !status.offroad) { this.pendingAction = null; this.busy = false }
    if (this.ownedSession && (status.sessionId !== this.ownedSession || !status.owned)) { this.ownedSession = null; this.retireMedia() }
    if (!status.offroad || TERMINAL.has(status.state) || ["preparing", "seeking", "stopping"].includes(status.state) || status.mediaReady === false) this.retireMedia()
    else if (status.sessionId === this.ownedSession && status.codec &&
      ((!this.source && !this.videoFailed) || prior?.epoch !== status.epoch)) this.beginMedia(status)
    const video = this.video()
    if (video && this.source) {
      if (status.paused && status.state !== "ended") {
        video.pause()
        if (this.buffer?.buffered.length) {
          const position = replayBufferTime(this.buffer.buffered, true)
          if (Math.abs(video.currentTime - position) > .001) video.currentTime = position
        }
      }
      else this.playVideo()
    }
    if (this.source && this.buffer && (prior?.paused && !status.paused || status.state === "ended" && this.sequence <= status.media?.lastSequence)) {
      this.mediaDemand = true; this.cancelTimer(this.mediaTimer); this.loadMedia(this.mediaGeneration, status.sessionId, status.epoch)
    }
    this.emit()
  }
  playVideo() {
    const generation = this.mediaGeneration, video = this.video()
    const ended = this.status?.state === "ended"
    if (ended && this.sequence > this.status.media?.lastSequence && this.source?.readyState === "open" && !this.buffer?.updating) {
      this.cancelTimer(this.mediaTimer)
      this.source.endOfStream()
    }
    if (!video?.paused || this.status?.paused && !ended || this.needsBuffer() || this.bufferAhead() <= 0) return
    video.play()?.catch(error => {
      if (!this.active || generation !== this.mediaGeneration || error.name === "AbortError") return
      this.error = error.name === "NotAllowedError" ? "Select Play to allow video playback in this browser." : "Replay video could not play. Retry the video or stop replay."
      this.emit()
    })
  }
  bufferAhead() {
    const video = this.video(), ranges = this.buffer?.buffered
    for (let i = 0; video && i < (ranges?.length || 0); i++) {
      if (ranges.start(i) <= video.currentTime && video.currentTime < ranges.end(i)) return ranges.end(i) - video.currentTime
    }
    return 0
  }
  needsBuffer() {
    return !!this.source && !this.status?.paused && this.status?.state !== "ended" && !!this.video()?.paused && this.bufferAhead() < PLAY_BUFFER
  }
  videoWaiting() {
    if (!this.active || !this.source || this.status?.paused || this.status?.state === "ended") return
    this.video().pause()
    this.mediaDemand = true
    this.cancelTimer(this.mediaTimer)
    this.loadMedia(this.mediaGeneration, this.status.sessionId, this.status.epoch)
    this.emit()
  }
  async action(operation, extra = {}) {
    if (!this.active || operation !== "stop" && (this.busy || !this.status)) return
    const generation = this.generation, requestId = token()
    this.pendingAction = operation === "control" ? requestId : null
    this.busy = true; this.error = ""; this.emit()
    try {
      const status = await this.json(operation, { clientId: this.clientId, requestId, ...extra })
      if (!status) return
      if (operation === "start" && ID.test(status.sessionId)) {
        if (!this.active || generation !== this.generation) { this.sendStop(status.sessionId); return }
        this.ownedSession = status.sessionId
      }
      if (!validReplayStatus(status)) throw new Error("Replay returned an unsupported status.")
      this.receive(status)
    } catch (error) {
      this.pendingAction = null
      if (this.active) { this.error = error.message || "Replay action could not complete."; await this.refresh() }
    } finally { this.busy = this.pendingAction !== null; if (this.active) this.emit() }
  }
  start() {
    if (!this.active || this.busy || !this.status) return
    if (!mediaSources().length) { this.error = STREAMING_UNAVAILABLE; this.emit(); return }
    this.startAttempted = true; this.videoFailed = false; this.autoplay = true
    return this.action("start", { routeId: this.routeId, target: "web", expectedOwnerId: this.status.ownerId,
      ...(this.startSegment == null ? {} : { segment: this.startSegment }) })
  }
  control(action, value) {
    this.autoplay = false
    if (!this.ownedSession || this.status?.sessionId !== this.ownedSession) return
    if (action === "seek") { if (!number(value)) return; value = replaySeekPosition(this.status, value) }
    return this.action("control", { sessionId: this.ownedSession, expectedRevision: this.status.revision, action,
      ...(action === "pause" ? { paused: value } : action === "seek" ? { position: value } : { rate: value }) })
  }
  stop() { return this.ownedSession && this.action("stop", { sessionId: this.ownedSession }) }
  retireMedia() {
    this.mediaGeneration++
    this.mediaRequest?.abort(); this.mediaRequest = null
    this.cancelTimer(this.mediaTimer)
    this.rejectAppend?.(new Error("Replay video retired")); this.rejectAppend = null
    this.source = this.buffer = null
    const video = this.video()
    if (video) {
      if (this.mediaSeeking) video.removeEventListener("seeking", this.mediaSeeking)
      video.pause(); video.removeAttribute("src"); video.load()
    }
    this.mediaSeeking = null
    if (this.url) this.revokeURL(this.url)
    this.url = null
  }
  beginMedia(status) {
    this.retireMedia()
    this.videoFailed = false; this.error = ""
    if (!status.offroad || !status.codec || status.mediaReady === false) return
    const mime = `video/mp4; codecs="${status.codec}"`
    const sources = mediaSources(), Source = sources.find(Source => Source.isTypeSupported(mime))
    if (!Source) {
      this.videoFailed = true
      this.error = sources.length ? "This browser does not support this replay's H.264 video. Update your browser or try another browser." : STREAMING_UNAVAILABLE
      if (this.ownedSession === status.sessionId) this.sendStop(status.sessionId)
      this.emit(); return
    }
    const generation = this.mediaGeneration
    try {
      const video = this.video(), source = this.source = this.mediaSource(Source)
      const load = () => this.loadMedia(generation, status.sessionId, status.epoch)
      this.mediaDemand = true
      if (Source === globalThis.ManagedMediaSource) {
        video.disableRemotePlayback = true
        const resume = () => {
          if (!this.active || generation !== this.mediaGeneration) return
          this.mediaDemand = true
          if (this.buffer) { this.cancelTimer(this.mediaTimer); load() }
        }
        source.addEventListener("startstreaming", resume)
        source.addEventListener("endstreaming", () => {
          if (!this.active || generation !== this.mediaGeneration || video.seeking) return
          this.mediaDemand = false
          if (this.buffer && !this.needsBuffer()) this.cancelTimer(this.mediaTimer)
        })
        // Safari can omit startstreaming after a seek; resume the existing loader explicitly.
        video.addEventListener("seeking", this.mediaSeeking = resume)
      }
      source.addEventListener("sourceopen", () => {
        if (!this.active || generation !== this.mediaGeneration) return
        this.cancelTimer(this.mediaTimer)
        try {
          const buffer = this.buffer = source.addSourceBuffer(mime)
          buffer.addEventListener("bufferedchange", event => {
            if (!this.active || generation !== this.mediaGeneration || !event.removedRanges.length) return
            for (let i = 0; i < event.removedRanges.length; i++) {
              if (!buffer.buffered.length || event.removedRanges.start(i) <= video.currentTime && video.currentTime < event.removedRanges.end(i)) {
                this.beginMedia(this.status); return
              }
            }
          })
          this.sequence = 0
          this.nextFragment = status.media?.firstSequence || 1
          load()
        } catch (error) { this.videoFailed = true; this.mediaFailed(error, generation) }
      }, { once: true })
      this.url = this.createURL(source)
      video.src = this.url
      this.mediaTimer = this.later(() => {
        if (!this.active || generation !== this.mediaGeneration) return
        this.videoFailed = true
        this.mediaFailed(new Error("Replay video could not open. Retry video or stop replay."), generation)
      }, 4000)
    } catch (error) { this.videoFailed = true; this.mediaFailed(error, generation) }
  }
  append(bytes, generation) { return this.updateBuffer(buffer => buffer.appendBuffer(bytes), generation) }
  updateBuffer(change, generation) {
    return new Promise((resolve, reject) => {
      if (!this.buffer || generation !== this.mediaGeneration) { reject(new Error("Replay video retired")); return }
      const buffer = this.buffer
      const cleanup = () => { buffer.removeEventListener("updateend", done); buffer.removeEventListener("error", failed); if (this.rejectAppend === failed) this.rejectAppend = null }
      const done = () => { cleanup(); resolve() }
      const failed = () => { cleanup(); reject(new Error("Replay video could not decode.")) }
      this.rejectAppend = failed
      buffer.addEventListener("updateend", done, { once: true })
      buffer.addEventListener("error", failed, { once: true })
      try { change(buffer) } catch (error) { cleanup(); reject(error) }
    })
  }
  async loadMedia(generation, sessionId, epoch) {
    if (!this.active || generation !== this.mediaGeneration || !this.buffer || this.mediaRequest ||
      this.source?.readyState === "ended" || this.mediaDemand === false && this.buffer.buffered.length && !this.needsBuffer()) return
    const load = () => this.loadMedia(generation, sessionId, epoch)
    this.cancelTimer(this.mediaTimer)
    if (this.bufferAhead() >= MAX_BUFFER_AHEAD) { this.mediaTimer = this.later(load, MEDIA_INTERVAL); return }
    const request = this.mediaRequest = new AbortController()
    const timeout = this.later(() => request.abort(), 4000)
    try {
      const response = await this.fetcher(`./api/replay/media?sessionId=${sessionId}&clientId=${this.clientId}&epoch=${epoch}&sequence=${this.sequence}`, { credentials: "same-origin", cache: "no-store", signal: request.signal })
      if (!this.active || generation !== this.mediaGeneration || this.source?.readyState === "ended") return
      if (response.status === 401) { this.close(false); this.unauthorized(); return }
      if (response.status === 202) { this.mediaTimer = this.later(load, this.status?.paused || this.status?.state === "ended" ? 500 : MEDIA_INTERVAL); return }
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        if (error.code === "media_evicted") { await this.refresh(); if (generation === this.mediaGeneration && this.status) this.beginMedia(this.status); return }
        throw new Error(error.error || "Replay video is unavailable.")
      }
      if (response.headers.get("Content-Type")?.split(";")[0] !== "video/mp4" || Number(response.headers.get("X-Replay-Epoch")) !== epoch) throw new Error("Replay video epoch changed.")
      const length = Number(response.headers.get("Content-Length"))
      if (!integer(length) || length < 1 || length > 1024 * 1024) throw new Error("Replay video exceeded its media budget.")
      const bytes = await response.arrayBuffer()
      if (!this.active || generation !== this.mediaGeneration) return
      if (bytes.byteLength !== length) throw new Error("Replay video was incomplete.")
      await this.append(bytes, generation)
      if (!this.active || generation !== this.mediaGeneration) return
      const next = Number(response.headers.get("X-Replay-Next-Sequence"))
      if (!integer(next) || next <= this.sequence) throw new Error("Replay video sequence is invalid.")
      this.sequence = this.sequence === 0 ? this.nextFragment : next
      const video = this.video(), buffer = this.buffer
      if (buffer.buffered.length) {
        // The owner starts paused so its first composed frame can reach the viewer.
        if (this.autoplay) {
          this.autoplay = false
          if (this.status.paused && this.status.state !== "ended") await this.control("pause", false)
          if (!this.active || generation !== this.mediaGeneration) return
        }
        const start = buffer.buffered.start(0), end = buffer.buffered.end(buffer.buffered.length - 1)
        if (this.status.paused && this.status.state !== "ended" || this.bufferAhead() === 0 && video.currentTime < end) {
          const position = replayBufferTime(buffer.buffered, this.status.paused && this.status.state !== "ended")
          if (Math.abs(video.currentTime - position) > .001) video.currentTime = position
        }
        if (video.currentTime - start > 3) {
          await this.updateBuffer(buffer => buffer.remove(start, video.currentTime - 2), generation)
        }
      }
      this.playVideo()
      this.emit()
      if (this.source?.readyState !== "ended") this.mediaTimer = this.later(load, !this.buffer.buffered.length || this.needsBuffer() ? 0 : MEDIA_INTERVAL)
    } catch (error) { this.mediaFailed(error, generation) }
    finally { this.cancelTimer(timeout); if (this.mediaRequest === request) this.mediaRequest = null }
  }
  videoError() { this.videoFailed = true; this.mediaFailed(new Error("Replay video could not decode. Retry the video or stop replay."), this.mediaGeneration) }
  mediaFailed(error, generation) {
    if (!this.active || generation !== this.mediaGeneration) return
    this.retireMedia(); this.error = error.message || "Replay video disconnected. Stop or retry the video."; this.emit()
  }
  sendStop(sessionId) {
    this.fetcher("./api/replay/stop", { method: "POST", credentials: "same-origin", keepalive: true,
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sessionId, clientId: this.clientId, requestId: token() }) }).catch(() => {})
  }
  close(stop = true) {
    if (stop && this.active && this.ownedSession) this.sendStop(this.ownedSession)
    this.active = this.reading = this.autoplay = this.startAttempted = false; this.generation++
    this.cancelTimer(this.timer)
    for (const request of this.requests) if (request !== this.startRequest) request.abort()
    this.requests.clear(); this.retireMedia(); this.ownedSession = null
  }
}

export const ReplayViewer = {
  components: { GxDialog, GxNotice, GxState, GxIconButton },
  props: { routeId: { type: String, required: true }, startSegment: { type: Number, default: null }, unauthorized: { type: Function, required: true } },
  emits: ["close"],
  data: () => ({ client: null, replay: null, replayBusy: false, replayError: "", replayDetail: null, replayVideoReady: false, replayBuffering: false, seekPosition: null }),
  computed: {
    playing() { return this.client?.ownedSession === this.replay?.sessionId && !!this.replay?.sessionId && !TERMINAL.has(this.replay.state) },
    controlsBusy() { return this.replayBusy || !this.replay?.offroad || ["preparing", "seeking", "stopping"].includes(this.replay.state) },
    seekGaps() { return replaySeekGaps(this.replay) },
    canStart() { return this.replay?.offroad && TERMINAL.has(this.replay.state) && !this.replayBusy && this.replayDetail?.playable === true },
  },
  mounted() {
    this.client = markRaw(new ReplayClient({ video: () => this.$refs.video, unauthorized: this.unauthorized, publish: update => Object.assign(this.$data, update) }))
    this.visibility = () => { if (document.hidden) { this.client.close(); this.$emit("close") } }
    document.addEventListener("visibilitychange", this.visibility)
    this.client.open(this.routeId, this.startSegment)
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibility); this.client.close() },
  methods: {
    replayTime,
    close() { this.client.close(); this.$emit("close") },
    seek(value) { this.seekPosition = null; this.client.control("seek", Number(value)) },
    cycleRate() {
      const rates = [.5, 1, 2]
      this.client.control("rate", rates[(rates.indexOf(this.replay.rate) + 1) % rates.length])
    },
    fullscreen() { return document.fullscreenElement === this.$refs.player ? document.exitFullscreen() : this.$refs.player.requestFullscreen?.() },
  },
  template: `<GxDialog class="gx-replay" labelledby="gx-replay-title" @close="close">
    <div class="gx-recordings__player-head"><div><h3 id="gx-replay-title">Route replay</h3><p class="gx-note">{{ routeId }}<template v-if="startSegment !== null"> · from segment {{ startSegment }}</template> · Recorded driving view · Vehicle offroad only</p></div><GxIconButton label="Close replay" icon="bi-x-lg" @click="close" /></div>
    <div ref="player" class="gx-replay__player">
    <video ref="video" class="gx-replay__video" playsinline muted aria-label="Recorded route with driving interface" @waiting="client?.videoWaiting()" @error="client?.videoError()"></video>
    <GxState class="gx-replay__loading" v-if="!replayError && (!replay || replayBuffering || !replayVideoReady && (playing || replayBusy || !replayDetail) || ['preparing', 'seeking'].includes(replay.state))" loading>{{ replay?.state === 'seeking' ? 'Seeking recorded route…' : replayBuffering ? 'Buffering replay…' : 'Loading replay…' }}</GxState>
    <GxIconButton v-if="playing" class="gx-replay__fullscreen" label="Fullscreen video" icon="bi-fullscreen" @click="fullscreen" />
    <div v-if="playing" class="gx-replay__media-controls">
      <label class="gx-replay__timeline"><span>{{ replayTime((seekPosition ?? replay.position)-replay.start) }} / {{ replayTime(replay.end-replay.start) }}</span><input type="range" aria-label="Replay route position" :min="replay.start" :max="replay.end" step="0.05" :value="seekPosition ?? replay.position" :disabled="controlsBusy" @input="seekPosition=Number($event.target.value)" @change="seek($event.target.value)" /></label>
      <div class="gx-replay__controls">
        <button type="button" class="gx-btn" aria-label="Back ten seconds" :disabled="controlsBusy" @click="seek(replay.position-10)">-10 s</button>
        <button v-if="replay.state === 'ended'" type="button" class="gx-btn" aria-label="Return to start" :disabled="controlsBusy" @click="seek(replay.start)">Restart</button>
        <button v-else type="button" class="gx-btn" :disabled="controlsBusy" @click="client.control('pause', !replay.paused)">{{ replay.paused ? 'Play' : 'Pause' }}</button>
        <button type="button" class="gx-btn" aria-label="Forward ten seconds" :disabled="controlsBusy" @click="seek(replay.position+10)">+10 s</button>
        <button type="button" class="gx-btn" aria-label="Replay speed" :disabled="controlsBusy" @click="cycleRate">{{ replay.rate }}x</button>
        <button type="button" class="gx-btn" :disabled="replayBusy" @click="close">Stop</button>
      </div>
    </div>
    </div>
    <GxNotice v-if="replayError" tone="danger">{{ replayError }}<button v-if="!playing" class="gx-btn gx-btn--tonal" :disabled="replayBusy" @click="client.open(routeId, startSegment)">Retry replay</button><button v-else class="gx-btn gx-btn--tonal" :disabled="controlsBusy || !replay.codec || replay.mediaReady === false" @click="client.beginMedia(replay)">Retry video</button></GxNotice>
    <GxNotice v-if="replay && !replay.offroad" tone="warn">Turn off the vehicle before replaying a drive.</GxNotice>
    <GxNotice v-if="replay?.errorCode" tone="warn">Replay stopped: {{ replay.errorCode.replaceAll('_', ' ') }}</GxNotice>
    <GxNotice v-if="replay?.sessionId && !playing && !canStart" tone="info">Another replay is active. Close it in its viewer before starting this route.</GxNotice>
    <p v-if="replayDetail?.reason" class="gx-note">{{ replayDetail.reason }}</p>
    <p v-if="playing && seekGaps.length" class="gx-note">Missing recordings: <span v-for="(gap, i) in seekGaps" :key="i">{{ i ? ", " : "" }}{{ replayTime(gap[0]-replay.start) }}–{{ replayTime(gap[1]-replay.start) }}</span>. Seeks move to the nearest recorded position.</p>
  </GxDialog>`,
}
