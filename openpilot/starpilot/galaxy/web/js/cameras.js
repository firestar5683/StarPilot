import { GalaxySelect } from "./galaxy-select.js"

export class CameraSnapshotFeed {
  constructor({ publish, unauthorized, fetcher = (...args) => fetch(...args),
                createURL = (blob) => URL.createObjectURL(blob), revokeURL = (url) => URL.revokeObjectURL(url),
                later = setTimeout, cancelTimer = clearTimeout }) {
    Object.assign(this, { publish, unauthorized, fetcher, createURL, revokeURL, later, cancelTimer })
    this.request = null
    this.url = ""
    this.timer = null
  }
  stop() {
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
    this.timer = this.later(() => {
      if (this.request !== request) return
      this.stop()
      this.publish({ image: "", capturing: false, error: "Snapshot timed out. Turn off the vehicle and try again." })
    }, 13500)
    try {
      const response = await this.fetcher("./api/cameras/snapshot", { method: "POST", credentials: "same-origin",
        cache: "no-store", signal: request.signal, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ camera }) })
      if (this.request !== request || request.signal.aborted) return
      if (response.status === 401) { this.stop(); this.unauthorized(); return }
      if (!response.ok) throw new Error(response.status === 409 ? "Turn the vehicle off before taking a snapshot." :
        "Turn off the vehicle and open its camera preview, then try again.")
      if (response.headers.get("Content-Type")?.split(";")[0].trim().toLowerCase() !== "image/jpeg") throw new Error("Camera image is unavailable.")
      const blob = await response.blob()
      if (this.request !== request || request.signal.aborted) return
      if (!blob.size || blob.size > 1000000) throw new Error("Camera image is unavailable.")
      this.url = this.createURL(blob)
      this.publish({ image: this.url, capturing: false, error: "" })
    } catch (error) {
      if (this.request === request && !request.signal.aborted)
        this.publish({ image: "", capturing: false, error: error.message || "Camera image is unavailable." })
    } finally {
      if (this.request === request) {
        this.request = null
        this.cancelTimer(this.timer)
        this.timer = null
      }
    }
  }
}

export const CamerasPage = {
  name: "CamerasPage",
  components: { GalaxySelect },
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
          <p>Draw saved camera window regions and adjust visual warning choices. A live camera image and current warning status are unavailable here.</p>
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
          <p v-if="error" role="alert">{{ error }}</p>
          <img v-if="image" :src="image" :alt="camera + ' camera snapshot'" style="display:block;max-width:100%;height:auto;margin-top:1rem;" />
        </template>
        <p v-else>Camera snapshots are available on the connected device.</p>
        <small>Snapshots are not saved.</small></section>
    </div>`,
}
