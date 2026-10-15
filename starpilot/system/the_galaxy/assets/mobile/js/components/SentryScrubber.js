// Interactive Sentry event viewer: scrub, step or play through retained events using the images the
// Galaxy already serves. The parent supplies the events and handles deletes.

const PRELOAD_BEHIND = 3
const PRELOAD_AHEAD = 8
const PRELOAD_WAIT_MS = 3000
// Shares its pacing curve with the timelapse renderer: a burst stays readable, a long lull still pauses.
const GAP_BASE_S = 0.15
const GAP_SCALE_S = 0.25
const GAP_MAX_S = 1.5
const LAST_FRAME_S = 1.0

function eventTime(event) {
  const ms = Date.parse(event?.detectedAt || "")
  return Number.isFinite(ms) ? ms : null
}

function formatGap(ms) {
  const seconds = Math.max(0, Math.floor(ms / 1000))
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ${minutes % 60}m`
  return `${Math.floor(hours / 24)}d ${hours % 24}h`
}

// Events the scrubber can show: anything with photos and a time, test captures included. The rest (power-off, low-voltage) are alerts.
export function isCaptureEvent(event) {
  return !!(event && event.eventId && Array.isArray(event.imageUrls) && event.imageUrls.length && eventTime(event) !== null)
}

export const SentryScrubber = {
  name: "SentryScrubber",
  props: {
    events: { type: Array, default: () => [] },
    deleteBusy: { type: Boolean, default: false },
    // Selected camera ("wide" | "driver" | "both"); owned by the parent so the timelapse can follow it.
    camera: { type: String, default: "both" },
  },
  emits: ["delete", "close", "update:camera", "open-image"],
  data() {
    return {
      index: 0,
      playing: false,
      speed: 1,
      dragging: false,
    }
  },
  created() {
    // Deliberately not reactive, and only ever holds the frames near the cursor: decoded 1344x760 bitmaps
    // are about 4MB each, so keeping every viewed frame would exhaust a phone on a long history.
    this.preloaded = new Map()
    this.timer = null
    this.initialized = false
  },
  mounted() {
    this.index = Math.max(0, this.frames.length - 1)
    this.initialized = this.frames.length > 0
    this.preload()
  },
  beforeUnmount() {
    this.clearTimer()
    this.preloaded.clear()
  },
  computed: {
    frames() {
      return this.events
        .filter(isCaptureEvent)
        .slice()
        .sort((a, b) => eventTime(a) - eventTime(b))
    },
    current() { return this.frames[this.index] || null },
    hasFrames() { return this.frames.length > 0 },
    span() {
      if (this.frames.length < 2) return 0
      return eventTime(this.frames[this.frames.length - 1]) - eventTime(this.frames[0])
    },
    positions() {
      const start = this.frames.length ? eventTime(this.frames[0]) : 0
      return this.frames.map((event) => (this.span > 0 ? (eventTime(event) - start) / this.span : 0.5))
    },
    currentUrls() { return this.urlsFor(this.current) },
    nextGapText() {
      if (this.index >= this.frames.length - 1) return "last event"
      return `next event in ${formatGap(eventTime(this.frames[this.index + 1]) - eventTime(this.current))}`
    },
    currentTimeText() {
      const ms = this.current ? eventTime(this.current) : null
      return ms === null ? "" : new Date(ms).toLocaleString()
    },
  },
  watch: {
    frames(next, previous) {
      if (!next.length) {
        this.pause()
        this.index = 0
        this.initialized = false
        return
      }
      if (!this.initialized) {
        this.index = next.length - 1
        this.initialized = true
      } else {
        // Keep the same event selected when the list changes underneath us (e.g. after a delete).
        const previousId = previous?.[this.index]?.eventId
        const kept = previousId ? next.findIndex((event) => event.eventId === previousId) : -1
        this.index = kept >= 0 ? kept : Math.min(this.index, next.length - 1)
      }
      this.preload()
    },
    index() { this.preload() },
    camera() { this.preload() },
  },
  methods: {
    // A plain click opens the capture in the page's image viewer; modified/middle clicks keep the link's
    // default so "open in new tab" still works.
    openCapture(event, entry) {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
      event.preventDefault()
      this.$emit("open-image", entry.url, entry.label + " camera capture")
    },
    kindLabel(kind) { return String(kind || "event").toUpperCase() },
    kindColor(kind) {
      const k = String(kind || "")
      if (k === "alarm") return "var(--error)"
      if (k === "warning") return "var(--warning)"
      if (k === "selfie") return "var(--primary)"
      return "var(--text-muted)"
    },
    urlFor(event, name) {
      return (event?.imageUrls || []).find((url) => {
        try { return decodeURIComponent(String(url)).split("?")[0].endsWith(`/${name}`) } catch { return false }
      }) || ""
    },
    // One entry per camera shown; url is "" when the event has no image for that camera.
    urlsFor(event) {
      if (!event) return []
      const wide = { label: "Road", url: this.urlFor(event, "wide.jpg") }
      const driver = { label: "Driver", url: this.urlFor(event, "driver.jpg") }
      if (this.camera === "driver") return [driver]
      if (this.camera === "both") return [wide, driver]
      return [wide]
    },
    preload() {
      if (!this.hasFrames) return
      const wanted = new Set()
      for (let offset = -PRELOAD_BEHIND; offset <= PRELOAD_AHEAD; offset++) {
        const frame = this.frames[this.index + offset]
        for (const entry of this.urlsFor(frame)) if (entry.url) wanted.add(entry.url)
      }
      for (const url of wanted) {
        if (this.preloaded.has(url)) continue
        const image = new Image()
        image.decoding = "async"
        image.src = url
        this.preloaded.set(url, image)
      }
      for (const url of Array.from(this.preloaded.keys())) {
        if (!wanted.has(url)) this.preloaded.delete(url)
      }
    },
    go(index) {
      if (!this.hasFrames) return
      this.index = Math.min(Math.max(index, 0), this.frames.length - 1)
    },
    step(delta) {
      this.pause()
      this.go(this.index + delta)
    },
    jumpKind(direction, kind) {
      this.pause()
      for (let i = this.index + direction; i >= 0 && i < this.frames.length; i += direction) {
        if (this.frames[i].kind === kind) {
          this.index = i
          return
        }
      }
    },
    hasKind(direction, kind) {
      for (let i = this.index + direction; i >= 0 && i < this.frames.length; i += direction) {
        if (this.frames[i].kind === kind) return true
      }
      return false
    },
    // --- timeline scrubbing: tap or drag maps the pointer's real-time position to the nearest event ---
    indexAtFraction(fraction) {
      if (this.span <= 0) return this.index
      let best = 0
      let bestDistance = Infinity
      for (let i = 0; i < this.positions.length; i++) {
        const distance = Math.abs(this.positions[i] - fraction)
        if (distance < bestDistance) {
          best = i
          bestDistance = distance
        }
      }
      return best
    },
    scrubTo(pointerEvent) {
      const bar = this.$refs.bar
      if (!bar) return
      const rect = bar.getBoundingClientRect()
      if (rect.width <= 0) return
      const fraction = Math.min(Math.max((pointerEvent.clientX - rect.left) / rect.width, 0), 1)
      this.index = this.indexAtFraction(fraction)
    },
    onPointerDown(pointerEvent) {
      this.pause()
      this.dragging = true
      pointerEvent.currentTarget.setPointerCapture?.(pointerEvent.pointerId)
      this.scrubTo(pointerEvent)
    },
    onPointerMove(pointerEvent) {
      if (this.dragging) this.scrubTo(pointerEvent)
    },
    onPointerUp(pointerEvent) {
      this.dragging = false
      pointerEvent.currentTarget.releasePointerCapture?.(pointerEvent.pointerId)
    },
    onKeydown(keyEvent) {
      const tag = String(keyEvent.target?.tagName || "")
      if (keyEvent.key === "ArrowLeft") { this.step(-1); keyEvent.preventDefault() }
      else if (keyEvent.key === "ArrowRight") { this.step(1); keyEvent.preventDefault() }
      else if (keyEvent.key === "Home") { this.step(-Infinity); keyEvent.preventDefault() }
      else if (keyEvent.key === "End") { this.step(Infinity); keyEvent.preventDefault() }
      else if (keyEvent.key === " " && !["BUTTON", "SELECT", "INPUT"].includes(tag)) {
        this.togglePlay()
        keyEvent.preventDefault()
      }
    },
    // --- playback ---
    frameSeconds(index) {
      if (index >= this.frames.length - 1) return LAST_FRAME_S
      const gapMinutes = (eventTime(this.frames[index + 1]) - eventTime(this.frames[index])) / 60000
      const seconds = GAP_BASE_S + GAP_SCALE_S * Math.log10(1 + Math.max(gapMinutes, 0))
      return Math.min(seconds, GAP_MAX_S)
    },
    clearTimer() {
      if (this.timer !== null) clearTimeout(this.timer)
      this.timer = null
    },
    togglePlay() {
      if (this.playing) this.pause()
      else this.play()
    },
    play() {
      if (!this.hasFrames) return
      if (this.index >= this.frames.length - 1) this.index = 0
      this.playing = true
      this.schedule()
    },
    pause() {
      this.playing = false
      this.clearTimer()
    },
    schedule() {
      this.clearTimer()
      this.timer = setTimeout(() => this.advance(0), (this.frameSeconds(this.index) * 1000) / this.speed)
    },
    // Do not advance onto a frame that has not arrived yet, or playback would flash blank on a slow link.
    advance(waitedMs) {
      if (!this.playing) return
      if (this.index >= this.frames.length - 1) {
        this.pause()
        return
      }
      const ready = this.urlsFor(this.frames[this.index + 1]).every((entry) => {
        const image = entry.url ? this.preloaded.get(entry.url) : null
        return !entry.url || !image || image.complete
      })
      if (!ready && waitedMs < PRELOAD_WAIT_MS) {
        this.timer = setTimeout(() => this.advance(waitedMs + 100), 100)
        return
      }
      this.index += 1
      this.schedule()
    },
  },
  template: `
    <div tabindex="0" @keydown="onKeydown" style="outline:none;">
      <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center; justify-content:space-between; margin-bottom:var(--sp-2);">
        <div role="group" aria-label="Camera" style="display:flex; gap:4px;">
          <button type="button" class="gx-btn" :class="{ 'gx-btn--tonal': camera !== 'wide' }" :aria-pressed="camera === 'wide'" @click="$emit('update:camera', 'wide')">Road</button>
          <button type="button" class="gx-btn" :class="{ 'gx-btn--tonal': camera !== 'driver' }" :aria-pressed="camera === 'driver'" @click="$emit('update:camera', 'driver')">Driver</button>
          <button type="button" class="gx-btn" :class="{ 'gx-btn--tonal': camera !== 'both' }" :aria-pressed="camera === 'both'" @click="$emit('update:camera', 'both')">Both</button>
        </div>
        <button type="button" class="gx-btn gx-btn--tonal" @click="$emit('close')">Close viewer</button>
      </div>

      <p v-if="!hasFrames" class="gx-empty">No Sentry events with images to view.</p>

      <template v-else>
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:var(--sp-2);">
          <span style="display:inline-flex; align-items:center; gap:6px; font-weight:600;" :style="{ color: kindColor(current.kind) }">
            <span style="width:12px; height:12px; border-radius:50%; background:currentColor; display:inline-block;"></span>
            {{ kindLabel(current.kind) }}
          </span>
          <strong>{{ currentTimeText }}</strong>
          <span class="gx-row__desc" style="margin:0;">{{ nextGapText }}</span>
          <span class="gx-row__desc" style="margin:0 0 0 auto;">{{ index + 1 }} / {{ frames.length }}</span>
        </div>

        <div style="display:flex; gap:8px;">
          <div v-for="entry in urlsFor(current)" :key="entry.label"
            :style="{ flex: '1 1 0', minWidth: 0, aspectRatio: '1344 / 760', background: 'rgba(0,0,0,.35)', borderRadius: '8px',
              overflow: 'hidden', position: 'relative', border: '4px solid ' + (current.kind === 'alarm' ? 'var(--error)' : 'transparent'),
              boxSizing: 'border-box' }">
            <a v-if="entry.url" :href="entry.url" @click="openCapture($event, entry)" style="display:block; width:100%; height:100%;">
              <img :src="entry.url" :alt="entry.label + ' camera capture'" decoding="async"
                style="width:100%; height:100%; object-fit:contain; display:block;" />
            </a>
            <div v-else class="gx-row__desc" style="height:100%; display:flex; align-items:center; justify-content:center; margin:0;">
              No {{ entry.label.toLowerCase() }} image for this event
            </div>
          </div>
        </div>
        <p v-if="current.message" style="margin:8px 0 0;"><strong>{{ current.message }}</strong></p>

        <div ref="bar" role="slider" aria-label="Event timeline" :aria-valuemin="1" :aria-valuemax="frames.length" :aria-valuenow="index + 1"
          @pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp" @pointercancel="onPointerUp"
          style="position:relative; height:44px; margin:var(--sp-2) 0; touch-action:none; cursor:pointer; user-select:none;">
          <div style="position:absolute; left:0; right:0; top:50%; height:3px; margin-top:-1px; background:var(--on-surface-variant); opacity:.5; border-radius:2px;"></div>
          <span v-for="(frame, i) in frames" :key="frame.eventId"
            :style="{ position: 'absolute', left: (positions[i] * 100) + '%', top: '10px', bottom: '10px', width: '3px', marginLeft: '-1px',
              borderRadius: '2px', background: kindColor(frame.kind), opacity: i > index ? 0.4 : 1, pointerEvents: 'none' }"></span>
          <span :style="{ position: 'absolute', left: (positions[index] * 100) + '%', top: '2px', bottom: '2px', width: '8px', marginLeft: '-4px',
            borderRadius: '3px', background: '#fff', boxShadow: '0 0 0 1px rgba(0,0,0,.5)', pointerEvents: 'none' }"></span>
        </div>

        <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="index === 0" aria-label="Previous event" @click="step(-1)">
            <i class="bi bi-skip-backward-fill"></i>
          </button>
          <button type="button" class="gx-btn" :aria-label="playing ? 'Pause' : 'Play'" @click="togglePlay">
            <i :class="playing ? 'bi bi-pause-fill' : 'bi bi-play-fill'"></i> {{ playing ? 'Pause' : 'Play' }}
          </button>
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="index >= frames.length - 1" aria-label="Next event" @click="step(1)">
            <i class="bi bi-skip-forward-fill"></i>
          </button>
          <select class="gx-field" v-model.number="speed" aria-label="Playback speed">
            <option :value="0.5">0.5x</option>
            <option :value="1">1x</option>
            <option :value="2">2x</option>
            <option :value="4">4x</option>
          </select>
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="!hasKind(-1, 'alarm')" @click="jumpKind(-1, 'alarm')">Prev alarm</button>
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="!hasKind(1, 'alarm')" @click="jumpKind(1, 'alarm')">Next alarm</button>
          <slot name="actions"></slot>
          <button type="button" class="gx-btn gx-btn--danger" style="margin-left:auto;" :disabled="deleteBusy" @click="$emit('delete', current.eventId)">
            <i class="bi bi-trash"></i> Delete
          </button>
        </div>
        <p class="gx-note">Tap or drag the timeline to jump by real time. Arrow keys step, Home/End jump, Space plays.</p>
      </template>
    </div>
  `,
}
