import { reactive } from "../vendor/vue/vue.esm-browser.js"
import { SettingsFeed } from "./settings.js"
import { GalaxySettingRow } from "./galaxy-setting-row.js"
import { LiveCameraPreview } from "./cameras.js"
import { GxNotice } from "./notice.js"
import { FORMATS, annotationDraft, displaySide, sourcePoint } from "./vasm-geometry.js"

export const VasmPage = {
  name: "VasmPage",
  components: { GalaxySettingRow, GxNotice },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true },
    go: { type: Function, required: true } },
  setup(props) {
    const state = reactive({ status: "idle", data: null, pending: null, error: "", width: 1928, height: 1208,
      cameraLeft: [], cameraRight: [], activeSide: "cameraRight", localNote: "", cameraError: "", imageName: "", reviewing: false })
    let lastEditor = null
    const feed = new SettingsFeed({ unauthorized: props.unauthorized, publish: (update) => {
      Object.assign(state, update)
      if (update.status === "ready" && update.data?.view && JSON.stringify(update.data.editor) !== lastEditor) {
        lastEditor = JSON.stringify(update.data.editor)
        const editor = update.data.editor
        if (!editor || !Array.isArray(editor.cameraLeft) || !Array.isArray(editor.cameraRight)) {
          state.localNote = "Camera regions are unavailable. Restore the saved settings before editing."
          return
        }
        state.width = editor.width
        state.height = editor.height
        state.cameraLeft = editor.cameraLeft.map((point) => [...point])
        state.cameraRight = editor.cameraRight.map((point) => [...point])
        state.localNote = FORMATS.some(([w, h]) => w === editor.width && h === editor.height) ? "" :
          "This saved camera size cannot be edited here. Choose a supported size and redraw the regions."
      }
    } })
    return { state, feed, FORMATS, displaySide }
  },
  mounted() {
    this._dragIndex = -1
    this._dragSide = null
    this.liveCamera = new LiveCameraPreview({
      unauthorized: this.unauthorized, enabled: () => this.mode === "local",
      publish: update => Object.assign(this.state, update), redraw: () => this.redraw(),
    })
    if (this.mode === "local") this.feed.start("vasm")
    this.liveCamera.start()
    this.$nextTick(() => this.redraw())
  },
  updated() { this.$nextTick(() => this.redraw()) },
  beforeUnmount() { this.liveCamera.stop(); this.feed.stop() },
  computed: {
    controls() { return (this.state.data?.rows || []).map((row, index) => ({ row, index }))
      .filter(({ index }) => index !== this.state.data?.editorRow && !["Saved spot-monitor settings"].includes(this.state.data.rows[index].label)) },
    canEdit() { return this.mode === "local" && !!this.state.data?.parked && this.state.data?.editorRow >= 0 &&
      !!this.state.data.rows[this.state.data.editorRow]?.available && this.state.status === "ready" &&
      !this.state.pending && !this.state.reviewing },
    supportedFormat() { return FORMATS.some(([w, h]) => w === this.state.width && h === this.state.height) },
    canDraw() { return this.canEdit && this.supportedFormat && !!this.state.imageName },
  },
  methods: {
    point(event) {
      const canvas = this.$refs.canvas
      return canvas ? sourcePoint(event.clientX, event.clientY, canvas.getBoundingClientRect(),
                                  this.state.width, this.state.height) : null
    },
    pointerDown(event) {
      if (!this.canDraw || !this.state.activeSide) return
      const point = this.point(event)
      if (!point) return
      const side = this.state.activeSide
      const points = this.state[side]
      const rect = this.$refs.canvas.getBoundingClientRect()
      const radius = 16 * this.state.width / rect.width
      const index = points.findIndex(([x, y]) => Math.hypot(x - point[0], y - point[1]) <= radius)
      if (index >= 0) {
        this._dragIndex = index
        this._dragSide = side
        event.currentTarget.setPointerCapture?.(event.pointerId)
      } else if (points.length < 32) {
        this.state[side] = [...points, point]
        this.state.localNote = "Draft only; review the regions before saving."
      } else this.state.localNote = "Each side allows at most 32 vertices."
      this.redraw()
    },
    pointerMove(event) {
      if (this._dragIndex < 0 || !this._dragSide) return
      if (!this.canDraw) { this._dragIndex = -1; this._dragSide = null; return }
      const point = this.point(event)
      if (!point) return
      const points = [...this.state[this._dragSide]]
      points[this._dragIndex] = point
      this.state[this._dragSide] = points
      this.redraw()
    },
    pointerUp(event) {
      this._dragIndex = -1
      this._dragSide = null
      if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
    },
    undo(side) {
      this.state[side] = this.state[side].slice(0, -1)
      this.redraw()
    },
    clear(side) {
      this.state[side] = []
      this.redraw()
    },
    async saveRegions() {
      if (!this.canDraw) return
      const draft = annotationDraft(this.state.width, this.state.height,
                                    this.state.cameraLeft, this.state.cameraRight)
      if (!draft) {
        this.state.localNote = "Draw 3–32 vertices around at least one window. Regions cannot cross or leave the frame."
        return
      }
      this.state.localNote = ""
      this.state.reviewing = true
      try {
        await this.feed.preview(this.state.data.editorRow, 0, draft)
      } finally {
        this.state.reviewing = false
      }
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
        ctx.save()
        ctx.translate(w, 0)
        ctx.scale(-1, 1)
        ctx.drawImage(this.liveCamera.image, 0, 0, w, h)
        ctx.restore()
      }
      for (const [side, color] of [["cameraRight", "#5ee5ee"], ["cameraLeft", "#ffb865"]]) {
        const points = this.state[side]
        if (!points.length) continue
        ctx.beginPath()
        ctx.moveTo(w - points[0][0], points[0][1])
        for (const [x, y] of points.slice(1)) ctx.lineTo(w - x, y)
        if (points.length >= 3) ctx.closePath()
        ctx.lineWidth = Math.max(2, w / 640)
        ctx.strokeStyle = color
        ctx.fillStyle = side === "cameraRight" ? "#5ee5ee38" : "#ffb86538"
        if (points.length >= 3) ctx.fill()
        ctx.stroke()
        for (const [x, y] of points) {
          ctx.beginPath()
          ctx.arc(w - x, y, Math.max(5, w / 320), 0, Math.PI * 2)
          ctx.fillStyle = color
          ctx.fill()
        }
      }
    },
  },
  template: `
    <section class="gx-settings gx-vasm" aria-label="V-ASM saved settings">
      <header class="gx-settings__header"><div><h2>V-ASM Spot Monitoring</h2></div>
        <div class="gx-actions"><button type="button" class="gx-icon-btn" :disabled="state.cameraWarming" aria-label="Take a new cabin snapshot" title="New snapshot" @click="liveCamera.refresh()"><i class="bi bi-camera"></i></button><button type="button" class="gx-icon-btn" aria-label="Position side cameras" title="Position side cameras" @click="go('/theme_maker')"><i class="bi bi-layout-wtf" aria-hidden="true"></i></button></div></header>
      <GxNotice v-if="mode === 'local' && state.data && !state.data.parked" tone="warn">Turn the vehicle off to change these settings.</GxNotice>
      <div v-if="mode !== 'local'" class="gx-card gx-message" role="status">Local saved settings are unavailable in preview.</div>
      <template v-else>
        <div v-if="state.status === 'loading'" class="gx-card gx-message" role="status">Loading saved settings…</div>
        <GxNotice tone="danger" v-else-if="state.status === 'unavailable' && !state.error">Saved settings are unavailable.</GxNotice>
        <GxNotice tone="danger" v-if="state.error">{{ state.error }}
          </GxNotice>
        <div v-if="state.data" class="gx-settings__body">

          <section class="gx-card gx-vasm__editor" aria-label="Camera window region editor">
            <h3>Camera Window Regions</h3>
            <p>The display is mirrored: vehicle left is camera right; vehicle right is camera left. Trace visible side glass, leaving pillars and interior out.</p>
            <p class="gx-note gx-camera-status" role="status">{{ state.cameraWarming ? "Warming up the camera · 5 seconds…" : state.imageName ? "Snapshot ready" : "Turn off the vehicle to take a snapshot." }}</p>
            <div class="gx-actions">
              <button v-for="side in ['cameraRight', 'cameraLeft']" :key="side" type="button" class="gx-btn gx-btn--tonal" :aria-pressed="state.activeSide === side" :disabled="!canDraw" :aria-label="displaySide(side)" @click="state.activeSide=side">{{ side === 'cameraRight' ? 'Left' : 'Right' }}</button>
              <button type="button" class="gx-icon-btn" :disabled="!canDraw || !state[state.activeSide]?.length" aria-label="Undo last region point" title="Undo last point" @click="undo(state.activeSide)"><i class="bi bi-arrow-counterclockwise"></i></button>
              <button type="button" class="gx-icon-btn" :disabled="!canDraw || !state[state.activeSide]?.length" aria-label="Clear selected window region" title="Clear region" @click="clear(state.activeSide)"><i class="bi bi-eraser"></i></button>
              <button type="button" class="gx-btn" :disabled="!canDraw" aria-label="Save Regions" @click="saveRegions">Save</button>
            </div>
            <canvas ref="canvas" class="gx-vasm__canvas" :aria-label="'Mirrored camera window canvas, editing ' + displaySide(state.activeSide)"
              @pointerdown="pointerDown" @pointermove="pointerMove" @pointerup="pointerUp" @pointercancel="pointerUp"></canvas>
            <GxNotice tone="danger" v-if="state.cameraError">{{ state.cameraError }}</GxNotice>
            <p v-if="state.localNote" class="gx-note" role="status">{{ state.localNote }}</p>
            <p class="gx-note">A saved choice alone does not activate monitoring.</p>
          </section>
          <section class="gx-card gx-settings__section" aria-label="Saved settings">
            <GalaxySettingRow v-for="{ row, index } in controls" :key="state.data.page + ':' + index" :row="row" :index="index"
              :disabled="!state.data.parked || state.status !== 'ready' || state.reviewing || !!state.pending"
              :save-value="(index, value) => feed.previewValue(index, value)"
              @review="(index, direction) => feed.preview(index, direction)" @reset-default="index => feed.resetDefault(index)" />
          </section>
        </div>
        <Teleport to="body"><div v-if="state.pending" class="gx-settings__modal" role="dialog" aria-modal="true" aria-label="Confirm V-ASM preference">
          <div class="gx-card gx-settings__dialog"><h3>Confirm Saved Preference</h3><p>{{ state.pending.question }}</p>
            <div class="gx-settings__controls"><button type="button" class="gx-btn gx-btn--tonal" @click="feed.cancel()">Cancel</button>
              <button type="button" class="gx-btn" @click="feed.confirm()">Save</button></div></div></div></Teleport>
      </template>
    </section>`,
}
