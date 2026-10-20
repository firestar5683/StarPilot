import { GxNotice } from "./notice.js"
import { GxState } from "./state.js"
import { recordingUrl } from "./recording-data.js"

export const CameraViewer = {
  components: { GxNotice, GxState },
  props: { segment: { type: Object, required: true }, camera: { type: String, required: true },
    unauthorized: { type: Function, required: true } },
  emits: ["ended"],
  data: () => ({ generation: 0, error: "", hidden: globalThis.document?.hidden === true }),
  computed: { url() { return !this.hidden && this.segment.files[this.camera] ? recordingUrl(this.segment.segmentName, this.camera) : null } },
  watch: { url() { this.retire() } },
  mounted() {
    this.visibility = () => { this.hidden = document.hidden }
    document.addEventListener("visibilitychange", this.visibility)
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibility); this.retire() },
  methods: {
    pause() { this.$refs.video?.pause() },
    retire() {
      this.generation++
      this.sessionProbe?.abort(); this.sessionProbe = null
      this.pause(); this.$refs.video?.removeAttribute("src"); this.$refs.video?.load()
      this.error = ""
    },
    async videoError(event) {
      if (!this.url || event.currentTarget !== this.$refs.video ||
          Number(event.currentTarget.dataset.playerGeneration) !== this.generation) return
      const generation = this.generation
      this.error = "This camera recording could not play in this browser. Download the video to watch it in a compatible player."
      const controller = new AbortController()
      this.sessionProbe?.abort()
      this.sessionProbe = controller
      const deadline = setTimeout(() => controller.abort(), 4000)
      let revoke = false
      try {
        const response = await fetch("./api/auth/session", { credentials: "same-origin", cache: "no-store", signal: controller.signal })
        if (!this.url || generation !== this.generation || controller.signal.aborted) return
        const state = await response.json()
        if (!this.url || generation !== this.generation || controller.signal.aborted) return
        revoke = response.status === 401 || state.authenticated === false
      } catch { /* A media or session request may fail; keep the explicit playback error. */ }
      finally { clearTimeout(deadline); if (this.sessionProbe === controller) this.sessionProbe = null }
      if (revoke && this.url && generation === this.generation) { this.retire(); this.unauthorized() }
    },
  },
  template: `<div class="gx-route-workspace__camera">
    <video v-if="url" :key="generation" ref="video" :data-player-generation="generation" controls playsinline autoplay preload="metadata" :src="url" aria-label="Recorded camera footage" @error="videoError($event)" @ended="$emit('ended')"></video>
    <GxState v-else class="gx-route-workspace__empty">{{ hidden ? 'Playback paused while Galaxy is in the background.' : 'This camera is not saved for this segment. Choose another camera or segment.' }}</GxState>
    <GxNotice v-if="error" tone="danger">{{ error }}</GxNotice>
  </div>`,
}
