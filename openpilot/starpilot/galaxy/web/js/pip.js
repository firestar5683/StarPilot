import { reactive } from "../vendor/vue/vue.esm-browser.js"
import { CameraSnapshotFeed } from "./cameras.js"
import { SettingsFeed, isPipCropRow } from "./settings.js"
import { GalaxySettingRow } from "./galaxy-setting-row.js"
import { displayPoint, FORMATS, maskDraft, sourcePoint } from "./pip-geometry.js"

const SIDES = [
  { key: "centerRight", label: "Vehicle left / camera right", color: "#5ee5ee" },
  { key: "centerLeft", label: "Vehicle right / camera left", color: "#ffb865" },
]

export const PipPage = {
  name: "PipPage",
  components: { GalaxySettingRow },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true },
    go: { type: Function, required: true } },
  setup(props) {
    const state = reactive({ status: "idle", data: null, pending: null, error: "", width: 1928, height: 1208,
      cropSize: 580, centerLeft: null, centerRight: null, invert: null, activeSide: "centerRight",
      localNote: "", imageName: "", reviewing: false })
    let lastView = null
    const feed = new SettingsFeed({ unauthorized: props.unauthorized, publish: (update) => {
      Object.assign(state, update)
      if (update.status === "ready" && update.data?.view && update.data.view !== lastView) {
        lastView = update.data.view
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
    this._image = null
    this._imageGeneration = 0
    if (this.mode === "local") this.feed.start("pip")
    this._liveStopped = false
    this.snapshots = new CameraSnapshotFeed({ unauthorized: this.unauthorized, publish: (update) => {
      if (update.error) { this.state.localNote = update.error; this._image = null; this.state.imageName = "" }
      if (!update.image) return
      const generation = ++this._imageGeneration
      const image = new Image()
      image.onload = () => {
        if (this._liveStopped || generation !== this._imageGeneration) return
        this._image = image
        this.state.imageName = "Live cabin camera"
        this.state.localNote = ""
        this.redraw()
      }
      image.onerror = () => { this.state.localNote = "Camera frame could not be displayed."; this._image = null }
      image.src = update.image
    } })
    const refresh = async () => {
      if (this._liveStopped) return
      if (this.mode === "local" && !document.hidden) await this.snapshots.capture("cabin")
      if (!this._liveStopped) this._liveTimer = setTimeout(refresh, 1500)
    }
    this.visibility = () => { if (document.hidden) { this.snapshots.stop(); this._image = null; this.state.imageName = "" } }
    document.addEventListener("visibilitychange", this.visibility)
    refresh()
    this.$nextTick(() => this.redraw())
  },
  updated() {
    this.$nextTick(() => this.redraw())
  },
  beforeUnmount() {
    this._liveStopped = true
    clearTimeout(this._liveTimer)
    document.removeEventListener("visibilitychange", this.visibility)
    this.snapshots?.stop()
    this.feed.stop()
    this.dropImage()
  },
  computed: {
    controls() { return (this.state.data?.rows || []).map((row, index) => ({ row, index }))
      .filter(({ row }) => !isPipCropRow(row)) },
    canEdit() { return !!this.state.imageName && this.mode === "local" && !!this.state.data?.parked && this.state.data?.editorRow >= 0 &&
      !!this.state.data.rows[this.state.data.editorRow]?.available && this.state.status === "ready" &&
      !this.state.pending && !this.state.reviewing && typeof this.state.invert === "boolean" &&
      FORMATS.some(([w, h]) => w === this.state.width && h === this.state.height) },
  },
  methods: {
    dropImage() {
      this._imageGeneration++
      if (this._image) this._image.src = ""
      this._image = null
      this.state.imageName = ""
    },
    position(axis, event) {
      if (!this.canEdit) return
      const center = [...(this.state[this.state.activeSide] || [this.state.width / 2, this.state.height / 2])]
      center[axis] = Number(event.target.value)
      const left = this.state.activeSide === "centerLeft" ? center : this.state.centerLeft
      const right = this.state.activeSide === "centerRight" ? center : this.state.centerRight
      if (!maskDraft(this.state.width, this.state.height, this.state.cropSize, left, right)) return
      this.state[this.state.activeSide] = center
      this.redraw()
    },
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
    size(event) {
      if (!this.canEdit) return
      const value = Number(event.target.value)
      if (!maskDraft(this.state.width, this.state.height, value, this.state.centerLeft, this.state.centerRight)) {
        this.state.localNote = "That crop size would cross the image edge or leave no configured side."
        event.target.value = String(this.state.cropSize)
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
      if (this._image) {
        if (this.state.invert) { ctx.save(); ctx.translate(w, 0); ctx.scale(-1, 1) }
        ctx.drawImage(this._image, 0, 0, w, h)
        if (this.state.invert) ctx.restore()
      } else {
        ctx.strokeStyle = "#38404e"
        ctx.beginPath(); ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h); ctx.stroke()
      }
      const preview = this.$refs.preview
      const center = this.state[this.state.activeSide]
      if (preview && this._image && center) {
        preview.width = preview.height = 300
        const crop = preview.getContext("2d")
        crop.save()
        if (this.state.invert) { crop.translate(300, 0); crop.scale(-1, 1) }
        const size = this.state.cropSize
        crop.drawImage(this._image, (center[0] - size / 2) * this._image.naturalWidth / w,
          (center[1] - size / 2) * this._image.naturalHeight / h,
          size * this._image.naturalWidth / w, size * this._image.naturalHeight / h, 0, 0, 300, 300)
        crop.restore()
      }
      for (const side of SIDES) {
        const center = this.state[side.key]
        if (!center) continue
        const [x, y] = displayPoint(center, w, this.state.invert)
        const half = this.state.cropSize / 2
        ctx.strokeStyle = side.color
        ctx.lineWidth = Math.max(2, w / 640)
        ctx.strokeRect(x - half, y - half, this.state.cropSize, this.state.cropSize)
        ctx.beginPath(); ctx.arc(x, y, Math.max(4, w / 320), 0, Math.PI * 2); ctx.fillStyle = side.color; ctx.fill()
      }
    },
  },
  template: `
    <section class="gx-settings gx-pip" aria-label="Blind Spot Camera and Preview saved settings">
      <header class="gx-card gx-settings__header"><div><h2>Blind Spot Camera and Preview</h2>
        <p>Adjust the native Blind Spot Camera crop using a live cabin preview.</p></div>
        </header>
      <div v-if="mode !== 'local'" class="gx-card gx-message" role="status">Local saved settings are unavailable in preview.</div>
      <template v-else>
        <div v-if="state.status === 'loading'" class="gx-card gx-message" role="status">Loading saved settings…</div>
        <div v-else-if="state.status === 'unavailable'" class="gx-card gx-message" role="alert">Saved settings are unavailable.</div>
        <div v-if="state.error" class="gx-card gx-message" role="alert">{{ state.error }}
          <button type="button" class="gx-btn gx-btn--tonal" @click="feed.load()">Refresh</button></div>
        <div v-if="state.data" class="gx-settings__body">
          <div class="gx-settings__subhead"><p>{{ state.data.subtitle }} <span v-if="!state.data.parked">Turn the vehicle off to change these settings.</span></p>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="state.status === 'saving'" @click="feed.load()">Refresh</button></div>
          <section class="gx-card gx-settings__section" aria-label="Saved settings">
            <GalaxySettingRow v-for="{ row, index } in controls" :key="state.data.view + ':' + index" :row="row" :index="index"
              :disabled="!state.data.parked || state.status !== 'ready' || state.reviewing || !!state.pending"
              :save-value="(index, value) => feed.previewValue(index, value)"
              @review="(index, direction) => feed.preview(index, direction)" />
          </section>
          <section class="gx-card gx-vasm__editor" aria-label="Blind Spot Camera crop editor">
            <h3>Live Camera Crop</h3>
            <p>Choose a vehicle side and adjust horizontal position, vertical position, and crop size.</p>
            <p v-if="!state.imageName" role="status">Waiting for a fresh cabin frame. Turn off the vehicle to preview and edit the crop.</p>
            <p v-if="state.localNote" class="gx-note" role="status">{{ state.localNote }}</p>
            <div class="gx-vasm__sides"><div v-for="side in SIDES" :key="side.key" class="gx-vasm__side">
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!canEdit" :aria-pressed="state.activeSide === side.key" @click="choose(side.key)">{{ side.label }}</button>
              <span>{{ state[side.key] ? state[side.key].join(', ') + ' px' : 'Not configured' }}</span>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!canEdit || !state[side.key]" :aria-label="'Clear ' + side.label" @click="clear(side.key)">Clear</button>
            </div></div>
            <canvas v-show="state.imageName" ref="canvas" class="gx-vasm__canvas" :aria-label="'Cabin source crop canvas, editing ' + (state.activeSide === 'centerRight' ? 'vehicle left' : 'vehicle right')" @pointerdown="place"></canvas>
            <canvas v-show="state.imageName" ref="preview" aria-label="Live selected crop preview" style="max-width:300px;width:100%"></canvas>
            <label>Horizontal position
              <input type="range" :min="Math.ceil(state.cropSize / 2)" :max="state.width - Math.ceil(state.cropSize / 2)" :value="state[state.activeSide]?.[0] || state.width / 2" :disabled="!canEdit" @input="position(0, $event)" /></label>
            <label>Vertical position
              <input type="range" :min="Math.ceil(state.cropSize / 2)" :max="state.height - Math.ceil(state.cropSize / 2)" :value="state[state.activeSide]?.[1] || state.height / 2" :disabled="!canEdit" @input="position(1, $event)" /></label>
            <label>Shared square crop size: {{ state.cropSize }} px
              <input type="range" min="20" :max="Math.min(state.width, state.height)" step="1" :value="state.cropSize" :disabled="!canEdit" @input="size" /></label>
            <div class="gx-settings__controls"><button type="button" class="gx-btn" :disabled="!canEdit" @click="saveCrop">Save Crop</button></div>
            <p class="gx-note">The C3 bubble and C4 panel use this saved crop.</p>
          </section>
        </div>
        <Teleport to="body"><div v-if="state.pending" class="gx-settings__modal" role="dialog" aria-modal="true" aria-label="Confirm Blind Spot Camera preference">
          <div class="gx-card gx-settings__dialog"><h3>Confirm Saved Preference</h3><p>{{ state.pending.question }}</p>
            <div class="gx-settings__controls"><button type="button" class="gx-btn gx-btn--tonal" @click="feed.cancel()">Cancel</button>
              <button type="button" class="gx-btn" @click="feed.confirm()">Save</button></div></div></div></Teleport>
      </template>
    </section>`,
}
