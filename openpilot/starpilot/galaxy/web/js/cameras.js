import { GxNotice } from "./notice.js"
import { GalaxySelect } from "./galaxy-select.js"

export class CameraSnapshotFeed {
  constructor({ publish, unauthorized, fetcher = (...args) => fetch(...args),
                createURL = (blob) => URL.createObjectURL(blob), revokeURL = (url) => URL.revokeObjectURL(url),
                later = (fn, ms) => setTimeout(fn, ms), cancelTimer = id => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, createURL, revokeURL, later, cancelTimer })
    this.request = null
    this.url = ""
    this.timer = null
  }
  stop() {
    this.rejectRequest?.(new Error("Snapshot canceled"))
    this.rejectRequest = null
    this.request?.abort()
    this.request = null
    if (this.timer !== null) this.cancelTimer(this.timer)
    this.timer = null
    if (this.url) this.revokeURL(this.url)
    this.url = ""
    this.publish({ image: "", capturing: false, error: "" })
  }
  async capture(camera) {
    this.stop()
    const request = new AbortController()
    this.request = request
    this.publish({ image: "", capturing: true, error: "" })
    let expire
    const deadline = new Promise((_, reject) => { this.rejectRequest = expire = reject })
    this.timer = this.later(() => {
      if (this.request !== request) return
      expire(new Error("Snapshot timed out. Turn off the vehicle and try again."))
    }, 13500)
    try {
      const response = await Promise.race([this.fetcher("./api/cameras/snapshot", { method: "POST", credentials: "same-origin",
        cache: "no-store", signal: request.signal, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ camera }) }), deadline])
      if (this.request !== request || request.signal.aborted) return
      if (response.status === 401) { this.stop(); this.unauthorized(); return }
      if (!response.ok) throw new Error(response.status === 409 ? "Turn the vehicle off before taking a snapshot." :
        "Turn off the vehicle and open its camera preview, then try again.")
      if (response.headers.get("Content-Type")?.split(";")[0].trim().toLowerCase() !== "image/jpeg") throw new Error("Camera image is unavailable.")
      const blob = await Promise.race([response.blob(), deadline])
      if (this.request !== request || request.signal.aborted) return
      if (!blob.size || blob.size > 1000000) throw new Error("Camera image is unavailable.")
      this.url = this.createURL(blob)
      this.publish({ image: this.url, capturing: false, error: "" })
    } catch (error) {
      if (this.request === request && !request.signal.aborted)
        this.publish({ image: "", capturing: false, error: error.message || "Camera image is unavailable." })
    } finally {
      if (this.request === request) {
        request.abort()
        this.request = null
        this.rejectRequest = null
        this.cancelTimer(this.timer)
        this.timer = null
      }
    }
  }
}

export const CamerasPage = {
  name: "CamerasPage",
  components: { GxNotice, GalaxySelect },
  props: { mode: { type: String, required: true }, go: { type: Function, required: true },
    unauthorized: { type: Function, required: true } },
  data: () => ({ camera: "cabin", image: "", capturing: false, error: "" }),
  created() { this.snapshots = new CameraSnapshotFeed({ publish: (state) => Object.assign(this.$data, state), unauthorized: this.unauthorized }) },
  methods: {
    chooseCamera(event) { this.camera = event.target.value; this.snapshots.stop() },
  },
  mounted() {
    this.visibility = () => { if (document.hidden) this.snapshots.stop() }
    document.addEventListener("visibilitychange", this.visibility)
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibility); this.snapshots.stop() },
  watch: { mode() { this.snapshots.stop() } },
  template: `
    <div class="gx-view gx-home" aria-label="Cameras and Monitoring">
      <div class="gx-home__hero"><div><h1>Cameras &amp; Monitoring</h1>
        <p class="gx-note">Camera preferences and availability</p></div></div>
      <div class="gx-home__grid">
        <section class="gx-card gx-home__card"><h2><i class="bi bi-camera-video"></i> Blind Spot Camera and Preview</h2>
          <p>Adjust the camera crop with a live cabin preview.</p>
          <button v-if="mode === 'local'" type="button" class="gx-home__link" @click="go('/cameras/pip')">Open saved preferences <i class="bi bi-arrow-right"></i></button>
          <small v-else>Saved preferences are unavailable in preview.</small></section>
        <section class="gx-card gx-home__card"><h2><i class="bi bi-shield"></i> Sentry</h2>
          <p>View captured motion events and configure Sentry notifications.</p>
          <button v-if="mode === 'local'" type="button" class="gx-home__link" @click="go('/cameras/events')">View motion events <i class="bi bi-arrow-right"></i></button>
          <button v-if="mode === 'local'" type="button" class="gx-home__link" @click="go('/cameras/sentry-settings')">Saved motion settings <i class="bi bi-arrow-right"></i></button>
          <small v-else>Motion events are unavailable in preview.</small></section>
        <section class="gx-card gx-home__card"><h2><i class="bi bi-eye"></i> V-ASM</h2>
          <p>Preview the cabin camera, draw window regions, and adjust visual spot-monitoring choices.</p>
          <button v-if="mode === 'local'" type="button" class="gx-home__link" @click="go('/cameras/vasm')">Open saved settings <i class="bi bi-arrow-right"></i></button>
          <small v-else>Saved settings are unavailable in preview.</small></section>
      </div>
      <section class="gx-card gx-home__card"><h2>Camera Snapshot</h2>
        <p>Turn off the vehicle, choose a camera, then take a snapshot.</p>
        <template v-if="mode === 'local'">
          <label>Camera
            <GalaxySelect class="gx-field gx-field--full" aria-label="Camera" :value="camera" :disabled="capturing" @change="chooseCamera">
              <option value="cabin">Cabin</option><option value="wide">Wide road</option><option value="narrow">Road</option>
            </GalaxySelect></label>
          <button class="gx-btn" type="button" :disabled="capturing" @click="snapshots.capture(camera)">{{ capturing ? 'Capturing…' : 'Take snapshot' }}</button>
          <button v-if="image || capturing" class="gx-btn gx-btn--tonal" type="button" @click="snapshots.stop()">{{ capturing ? 'Cancel' : 'Clear snapshot' }}</button>
          <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
          <img v-if="image" :src="image" :alt="camera + ' camera snapshot'" style="display:block;max-width:100%;height:auto;margin-top:1rem;" />
        </template>
        <p v-else>Camera snapshots are available on the connected device.</p>
        <small>Snapshots are not saved.</small></section>
    </div>`,
}

// Shared owner for live editor frames, including bounded capture and image decode.
export class LiveCameraPreview {
  constructor({ publish, unauthorized, redraw, enabled, imageFactory = () => new Image() }) {
    Object.assign(this, { publish, redraw, enabled, imageFactory })
    this.image = null
    this.generation = 0
    this.stopped = true
    this.snapshots = new CameraSnapshotFeed({ unauthorized, publish: update => this.receive(update) })
    this.visibility = () => {
      if (document.hidden) this.clear()
      else { clearTimeout(this.timer); this.poll() }
    }
  }
  clear() {
    this.generation++
    clearTimeout(this.decodeTimer)
    this.snapshots.stop()
    if (this.image) this.image.src = ""
    this.image = null
    this.publish({ imageName: "" })
    this.redraw()
  }
  receive(update) {
    if (update.error) {
      this.generation++
      clearTimeout(this.decodeTimer)
      this.image = null
      this.publish({ imageName: "", cameraError: update.error })
      this.redraw()
    }
    if (!update.image) return
    const generation = ++this.generation
    const image = this.imageFactory()
    const failed = () => {
      if (this.stopped || generation !== this.generation) return
      clearTimeout(this.decodeTimer)
      this.generation++
      this.image = null
      this.publish({ imageName: "", cameraError: "Camera frame could not be displayed." })
      this.redraw()
    }
    image.onload = () => {
      if (this.stopped || generation !== this.generation) return
      clearTimeout(this.decodeTimer)
      this.image = image
      this.publish({ imageName: "Live cabin camera", cameraError: "" })
      this.redraw()
    }
    image.onerror = failed
    clearTimeout(this.decodeTimer)
    this.decodeTimer = setTimeout(failed, 4000)
    image.src = update.image
  }
  start() {
    this.stopped = false
    document.addEventListener("visibilitychange", this.visibility)
    this.poll()
  }
  async poll() {
    if (this.stopped) return
    const generation = this.pollGeneration = (this.pollGeneration || 0) + 1
    if (this.enabled() && !document.hidden) await this.snapshots.capture("cabin")
    if (!this.stopped && generation === this.pollGeneration) this.timer = setTimeout(() => this.poll(), 1500)
  }
  stop() {
    this.stopped = true
    clearTimeout(this.timer)
    document.removeEventListener("visibilitychange", this.visibility)
    this.clear()
  }
}
