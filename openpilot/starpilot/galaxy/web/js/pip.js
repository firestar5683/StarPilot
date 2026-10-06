import { GxNotice } from "./notice.js"
import { reactive } from "../vendor/vue/vue.esm-browser.js"
import { LiveCameraPreview } from "./cameras.js"
import { SettingsFeed, isPipCropRow } from "./settings.js"
import { GalaxySettingRow } from "./galaxy-setting-row.js"
import { displayPoint, FORMATS, maskDraft, sourcePoint } from "./pip-geometry.js"

const SIDES = [
  { key: "centerRight", label: "Left camera", color: "#5ee5ee" },
  { key: "centerLeft", label: "Right camera", color: "#ffb865" },
]

export const PipPage = {
  name: "PipPage",
  components: { GxNotice, GalaxySettingRow },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true },
    go: { type: Function, required: true } },
  setup(props) {
    const state = reactive({ status: "idle", data: null, pending: null, error: "", width: 1928, height: 1208,
      cropSize: 580, centerLeft: null, centerRight: null, invert: null, activeSide: "centerRight",
      localNote: "", cameraWarming: false, cameraError: "", imageName: "", reviewing: false })
    let lastEditor = null
    const feed = new SettingsFeed({ unauthorized: props.unauthorized, publish: (update) => {
      Object.assign(state, update)
      if (update.status === "ready" && update.data?.view && JSON.stringify(update.data.editor) !== lastEditor) {
        lastEditor = JSON.stringify(update.data.editor)
        const editor = update.data.editor
        if (editor) {
          state.width = editor.width
          state.height = editor.height
          state.cropSize = editor.cropSize
          state.centerLeft = editor.centerLeft === null ? null : [...editor.centerLeft]
          state.centerRight = editor.centerRight === null ? null : [...editor.centerRight]
          state.invert = editor.invert
          state.localNote = ""
        } else {
          state.invert = null
          state.localNote = "Restore the invalid saved crop or mirror choice before editing."
        }
      }
    } })
    return { state, feed, FORMATS, SIDES }
  },
  mounted() {
    this._dragIndex = -1
    this._dragSide = null
    this.liveCamera = new LiveCameraPreview({
      unauthorized: this.unauthorized, enabled: () => this.mode === "local",
      publish: update => Object.assign(this.state, update), redraw: () => this.redraw(),
    })
    if (this.mode === "local") this.feed.start("pip")
    this.liveCamera.start()
    this.$nextTick(() => this.redraw())
  },
  updated() { this.$nextTick(() => this.redraw()) },
  beforeUnmount() { this.liveCamera.stop(); this.feed.stop() },
  computed: {
    controls() { return (this.state.data?.rows || []).map((row, index) => ({ row, index }))
      .filter(({ row }) => !isPipCropRow(row) && !/camera availability/i.test(row.label)) },
    canEdit() { return !!this.state.imageName && this.mode === "local" && !!this.state.data?.parked && this.state.data?.editorRow >= 0 &&
      !!this.state.data.rows[this.state.data.editorRow]?.available && this.state.status === "ready" &&
      !this.state.pending && !this.state.reviewing && typeof this.state.invert === "boolean" &&
      FORMATS.some(([w, h]) => w === this.state.width && h === this.state.height) },
  },
  methods: {
    pointerDown(event) {
      if (!this.canEdit) return
      const canvas = this.$refs.canvas
      const point = sourcePoint(event.clientX, event.clientY, canvas.getBoundingClientRect(), this.state.width, this.state.height, this.state.invert)
      if (!point) return
      const tolerance = 16 * this.state.width / canvas.getBoundingClientRect().width
      const side = SIDES.find(side => this.state[side.key] && Math.hypot(point[0] - this.state[side.key][0], point[1] - this.state[side.key][1]) <= this.state.cropSize / 2 + tolerance)
      if (side) this.state.activeSide = side.key
      const center = this.state[this.state.activeSide]
      this._gesture = { pointerId: event.pointerId, resize: !!center && Math.abs(Math.hypot(point[0] - center[0], point[1] - center[1]) - this.state.cropSize / 2) <= tolerance }
      canvas.setPointerCapture(event.pointerId)
      this.pointerMove(event)
    },
    pointerMove(event) {
      if (!this._gesture || this._gesture.pointerId !== event.pointerId || !this.canEdit) return
      if (!this._gesture.resize) { this.place(event); return }
      const point = sourcePoint(event.clientX, event.clientY, this.$refs.canvas.getBoundingClientRect(), this.state.width, this.state.height, this.state.invert)
      const center = this.state[this.state.activeSide]
      if (point && center) this.resizeCrop(Math.round(2 * Math.hypot(point[0] - center[0], point[1] - center[1])))
    },
    pointerUp() { this._gesture = null },
    choose(side) { if (this.canEdit) this.state.activeSide = side },
    place(event) {
      if (!this.canEdit) return
      const canvas = this.$refs.canvas
      const point = sourcePoint(event.clientX, event.clientY, canvas?.getBoundingClientRect(),
                                this.state.width, this.state.height, this.state.invert)
      if (!point) return
      const nextLeft = this.state.activeSide === "centerLeft" ? point : this.state.centerLeft
      const nextRight = this.state.activeSide === "centerRight" ? point : this.state.centerRight
      if (!maskDraft(this.state.width, this.state.height, this.state.cropSize, nextLeft, nextRight)) {
        this.state.localNote = "Place the center far enough from the frame edge for the whole crop."
        return
      }
      this.state.centerLeft = nextLeft
      this.state.centerRight = nextRight
      this.state.localNote = "Draft only; review both centers and crop size before saving."
      this.redraw()
    },
    clear(side) {
      if (!this.canEdit) return
      this.state[side] = null
      this.redraw()
    },
    resizeCrop(value) {
      if (!this.canEdit) return
      if (!maskDraft(this.state.width, this.state.height, value, this.state.centerLeft, this.state.centerRight)) {
        this.state.localNote = "That crop size would cross the image edge or leave no configured side."
        return
      }
      this.state.cropSize = value
      this.redraw()
    },
    async saveCrop() {
      if (!this.canEdit) return
      const draft = maskDraft(this.state.width, this.state.height, this.state.cropSize,
                              this.state.centerLeft, this.state.centerRight)
      if (!draft) { this.state.localNote = "Keep at least one complete crop inside the image."; return }
      this.state.reviewing = true
      try { await this.feed.preview(this.state.data.editorRow, 0, draft) }
      finally { this.state.reviewing = false }
    },
    redraw() {
      const canvas = this.$refs.canvas
      if (!canvas || !FORMATS.some(([w, h]) => w === this.state.width && h === this.state.height)) return
      if (canvas.width !== this.state.width) canvas.width = this.state.width
      if (canvas.height !== this.state.height) canvas.height = this.state.height
      const ctx = canvas.getContext("2d")
      if (!ctx) return
      const w = canvas.width, h = canvas.height
      ctx.fillStyle = "#151821"
      ctx.fillRect(0, 0, w, h)
      if (this.liveCamera?.image) {
        if (this.state.invert) { ctx.save(); ctx.translate(w, 0); ctx.scale(-1, 1) }
        ctx.drawImage(this.liveCamera.image, 0, 0, w, h)
        if (this.state.invert) ctx.restore()
      } else {
        ctx.strokeStyle = "#38404e"
        ctx.beginPath(); ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h); ctx.stroke()
      }
      const preview = this.$refs.preview
      const center = this.state[this.state.activeSide]
      if (preview && this.liveCamera?.image && center) {
        if (preview.width !== 300 || preview.height !== 300) preview.width = preview.height = 300
        const crop = preview.getContext("2d")
        crop.save()
        if (this.state.invert) { crop.translate(300, 0); crop.scale(-1, 1) }
        const size = this.state.cropSize
        crop.drawImage(this.liveCamera.image, (center[0] - size / 2) * this.liveCamera.image.naturalWidth / w,
          (center[1] - size / 2) * this.liveCamera.image.naturalHeight / h,
          size * this.liveCamera.image.naturalWidth / w, size * this.liveCamera.image.naturalHeight / h, 0, 0, 300, 300)
        crop.restore()
      }
      if (preview && (!center || !this.liveCamera?.image)) preview.getContext("2d")?.clearRect(0, 0, preview.width, preview.height)
      for (const side of SIDES) {
        const center = this.state[side.key]
        if (!center) continue
        const [x, y] = displayPoint(center, w, this.state.invert)
        const half = this.state.cropSize / 2
        ctx.strokeStyle = side.color
        ctx.lineWidth = Math.max(2, w / 640)
        ctx.beginPath(); ctx.arc(x, y, half, 0, Math.PI * 2); ctx.stroke()
        ctx.beginPath(); ctx.arc(x + half, y, Math.max(6, w / 160), 0, Math.PI * 2); ctx.fillStyle = side.color; ctx.fill()
        ctx.beginPath(); ctx.arc(x, y, Math.max(4, w / 320), 0, Math.PI * 2); ctx.fillStyle = side.color; ctx.fill()
      }
    },
  },
  template: `
    <section class="gx-settings gx-pip" aria-label="Blind Spot Camera and Preview saved settings">
      <header class="gx-settings__header"><div><h2>Blind Spot Camera and Preview</h2>
        <p>Adjust the native Blind Spot Camera crop on a cabin snapshot.</p></div>
        <button type="button" class="gx-icon-btn" :disabled="state.cameraWarming" aria-label="Take a new cabin snapshot" title="New snapshot" @click="liveCamera.refresh()"><i class="bi bi-camera"></i></button></header>
      <div v-if="mode !== 'local'" class="gx-card gx-message" role="status">Local saved settings are unavailable in preview.</div>
      <template v-else>
        <GxNotice v-if="state.data && !state.data.parked" tone="warn">Turn the vehicle off to change these settings.</GxNotice>
        <div v-if="state.status === 'loading'" class="gx-card gx-message" role="status">Reading blind-spot camera preferences and crop positions…</div>
        <GxNotice tone="danger" v-else-if="state.status === 'unavailable' && !state.error">The device could not read blind-spot camera preferences or crop positions. Reconnecting automatically…</GxNotice>
        <GxNotice tone="danger" v-if="state.error">{{ state.error }}
          </GxNotice>
        <div v-if="state.data" class="gx-settings__body">

          <section class="gx-card gx-vasm__editor" aria-label="Blind Spot Camera crop editor">
            <h3>Camera Crop</h3>
            <p class="gx-note">Drag a circle to position it. Drag its edge to resize both crops.</p>
            <p class="gx-note gx-camera-status" role="status">{{ state.cameraWarming ? "Warming up the camera · 5 seconds…" : state.imageName ? "Snapshot ready" : "Turn off the vehicle to take a snapshot." }}</p>
            <GxNotice tone="danger" v-if="state.cameraError">{{ state.cameraError }}</GxNotice>
            <p v-if="state.localNote" class="gx-note" role="status">{{ state.localNote }}</p>
            <div class="gx-actions">
              <button v-for="side in SIDES" :key="side.key" type="button" class="gx-btn gx-btn--tonal" :disabled="!canEdit" :aria-pressed="state.activeSide === side.key" :aria-label="side.label" @click="choose(side.key)">{{ side.key === "centerRight" ? "Left" : "Right" }}</button>
              <button type="button" class="gx-icon-btn" :disabled="!canEdit || !state[state.activeSide]" aria-label="Clear selected camera crop" title="Clear selected crop" @click="clear(state.activeSide)"><i class="bi bi-eraser"></i></button>
              <button type="button" class="gx-btn" :disabled="!canEdit" aria-label="Save Crop" @click="saveCrop">Save</button>
            </div>
            <canvas ref="canvas" class="gx-vasm__canvas" :aria-label="'Cabin source crop canvas, editing ' + (state.activeSide === 'centerRight' ? 'vehicle left' : 'vehicle right')" @pointerdown="pointerDown" @pointermove="pointerMove" @pointerup="pointerUp" @pointercancel="pointerUp" @lostpointercapture="pointerUp"></canvas>
            <div class="gx-pip__preview"><canvas ref="preview" aria-label="Live selected crop preview"></canvas><small>Selected circle · {{ state.cropSize }} px</small></div>
          </section>
          <section class="gx-card gx-settings__section" aria-label="Saved settings">
            <GalaxySettingRow v-for="{ row, index } in controls" :key="state.data.page + ':' + index" :row="row" :index="index"
              :disabled="!state.data.parked || state.status !== 'ready' || state.reviewing || !!state.pending"
              :save-value="(index, value) => feed.previewValue(index, value)"
              @review="(index, direction) => feed.preview(index, direction)" @reset-default="index => feed.resetDefault(index)" />
          </section>
        </div>
        <Teleport to="body"><div v-if="state.pending" class="gx-settings__modal" role="dialog" aria-modal="true" aria-label="Confirm Blind Spot Camera preference">
          <div class="gx-card gx-settings__dialog"><h3>Confirm Saved Preference</h3><p>{{ state.pending.question }}</p>
            <div class="gx-settings__controls"><button type="button" class="gx-btn gx-btn--tonal" @click="feed.cancel()">Cancel</button>
              <button type="button" class="gx-btn" @click="feed.confirm()">Save</button></div></div></div></Teleport>
      </template>
    </section>`,
}
