import { MenuTile } from "./menu-tile.js"
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
  components: { GxNotice, GalaxySelect, MenuTile },
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
    <div class="gx-view" aria-label="Cameras and Monitoring">
      <h2>Cameras &amp; Monitoring</h2>
      <div class="gx-grid">
        <MenuTile icon="bi-camera-video" title="Blind Spot Camera and Preview" description="Adjust the camera crop with a live cabin preview." :disabled="mode !== 'local'" @select="go('/cameras/pip')" />
        <MenuTile icon="bi-shield" title="Sentry" description="View motion events, configure saved motion settings, and manage notifications." :disabled="mode !== 'local'" @select="go('/cameras/events')" />
        <MenuTile icon="bi-eye" title="V-ASM" description="Preview the cabin camera, draw window regions, and adjust visual spot-monitoring choices." :disabled="mode !== 'local'" @select="go('/cameras/vasm')" />
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
  constructor({ publish, unauthorized, redraw, enabled, imageFactory = () => new Image(), later = (fn, ms) => setTimeout(fn, ms), cancelTimer = id => clearTimeout(id) }) {
    Object.assign(this, { publish, redraw, enabled, imageFactory, later, cancelTimer })
    this.image = null
    this.generation = 0
    this.stopped = true
    this.snapshots = new CameraSnapshotFeed({ unauthorized, publish: update => this.receive(update) })
    this.visibility = () => {
      this.cancelTimer(this.timer)
      this.snapshots.stop()
      if (!document.hidden && this.warming) this.poll()
    }
  }
  clear() {
    this.generation++
    this.cancelTimer(this.decodeTimer)
    this.snapshots.stop()
    if (this.image) this.image.src = ""
    this.image = null
    this.publish({ imageName: "" })
    this.redraw()
  }
  receive(update) {
    if (update.error) {
      this.lastError = update.error
      return
    }
    if (!update.image) return
    const generation = ++this.generation
    const image = this.imageFactory()
    const failed = () => {
      if (this.stopped || generation !== this.generation) return
      this.cancelTimer(this.decodeTimer)
      this.generation++
      this.lastError = "Camera frame could not be displayed."
      if (!this.image && !this.warming) this.publish({ cameraError: this.lastError })
      this.redraw()
    }
    image.onload = () => {
      if (this.stopped || generation !== this.generation) return
      this.cancelTimer(this.decodeTimer)
      this.image = image
      this.publish({ imageName: "Live cabin camera", cameraError: "" })
      this.redraw()
    }
    image.onerror = failed
    this.cancelTimer(this.decodeTimer)
    this.decodeTimer = this.later(failed, 4000)
    image.src = update.image
  }
  start() {
    this.stopped = false
    document.addEventListener("visibilitychange", this.visibility)
    this.refresh()
  }
  refresh() {
    this.cancelTimer(this.warmupTimer)
    this.cancelTimer(this.timer)
    this.warming = true
    this.lastError = ""
    this.publish({ cameraWarming: true, cameraError: "" })
    this.warmupTimer = this.later(() => this.freeze(), 5000)
    this.poll()
  }
  freeze() {
    this.generation++
    this.cancelTimer(this.decodeTimer)
    this.warming = false
    this.pollGeneration = (this.pollGeneration || 0) + 1
    this.cancelTimer(this.timer)
    this.snapshots.stop()
    this.publish({ cameraWarming: false, cameraError: this.image ? "" : this.lastError || "No cabin frame was available. Turn off the vehicle and take a new snapshot." })
  }
  async poll() {
    if (this.stopped || !this.warming) return
    const generation = this.pollGeneration = (this.pollGeneration || 0) + 1
    if (this.enabled() && !document.hidden) await this.snapshots.capture("cabin")
    if (!this.stopped && this.warming && generation === this.pollGeneration) this.timer = this.later(() => this.poll(), 1000)
  }
  stop() {
    this.stopped = true
    this.warming = false
    this.cancelTimer(this.warmupTimer)
    this.cancelTimer(this.timer)
    document.removeEventListener("visibilitychange", this.visibility)
    this.clear()
  }
}
