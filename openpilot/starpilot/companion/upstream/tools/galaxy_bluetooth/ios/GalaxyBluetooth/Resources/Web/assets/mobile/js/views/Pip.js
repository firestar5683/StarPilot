import { api, showSnackbar } from "../api.js"
import { GalaxySection } from "../components/GalaxySection.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"

const CANVAS_W = 640
const CANVAS_H = 480
const C4_ROAD_ASPECT = 476 / 240

const SIDE_LABELS = {
  left: {
    canvas: "LEFT SIDE OF VEHICLE - LEFT HERE",
    button: "Set Left Side of Vehicle - Left Here",
    moveButton: "Move Left Side of Vehicle - Left Here",
    color: "#0d6efd",
  },
  right: {
    canvas: "RIGHT SIDE OF VEHICLE - RIGHT HERE",
    button: "Set Right Side of Vehicle - Right Here",
    moveButton: "Move Right Side of Vehicle - Right Here",
    color: "#fd7e14",
  },
}

export const Pip = {
  name: "Pip",
  components: { GalaxySection },
  props: { embedded: { type: Boolean, default: false } },
  data() {
    return {
      armSide: null,
      leftCenter: null,
      rightCenter: null,
      zoom: 240,
      image: false,
      configSaved: false,
      configExists: false,
      loading: false,
      snapshotLoading: false,
      error: "",
      success: "",
      deviceType: null,
      loadedConfig: null,
    }
  },
  computed: {
    isC4() {
      return (this.deviceType || "").toLowerCase() === "mici"
    },
    canvasStyle() {
      return { width: "100%", height: "auto", display: "block", background: "#222", borderRadius: "var(--radius-md)", cursor: this.armSide ? "crosshair" : "default", touchAction: "manipulation" }
    },
    leftLabel() {
      return this.leftCenter ? SIDE_LABELS.left.moveButton : SIDE_LABELS.left.button
    },
    rightLabel() {
      return this.rightCenter ? SIDE_LABELS.right.moveButton : SIDE_LABELS.right.button
    },
  },
  mounted() {
    this._img = null
    this._sizedFor = null
    const canvas = this.canvas()
    if (canvas) { canvas.width = CANVAS_W; canvas.height = CANVAS_H }
    this.loadExistingConfig()
    this.loadSnapshot()
    this.$nextTick(() => this.redraw())
  },
  methods: {
    scolor(side) {
      return SIDE_LABELS[side]?.color || "#fff"
    },
    canvas() {
      return this.$refs?.canvas || null
    },
    sizeCanvas() {
      const canvas = this.canvas()
      const img = this._img
      if (!canvas || !img) return
      const w = Math.min(img.naturalWidth, 1280)
      canvas.width = w
      canvas.height = Math.round(w * (img.naturalHeight / img.naturalWidth))
    },
    canvasScale() {
      const canvas = this.canvas()
      const img = this._img
      const nativeW = img ? img.naturalWidth : 1920
      const nativeH = img ? img.naturalHeight : 1080
      const cw = canvas ? canvas.width || CANVAS_W : CANVAS_W
      const ch = canvas ? canvas.height || CANVAS_H : CANVAS_H
      return { cw, ch, nativeW, nativeH }
    },
    cropSource(center, zoom) {
      const { cw, ch, nativeW, nativeH } = this.canvasScale()
      const img = this._img
      const [cx, cy] = center
      const nativeCx = (cw - cx) * nativeW / cw
      const nativeCy = cy * nativeH / ch
      const nativeZoom = zoom * nativeW / cw
      return { cw, ch, nativeW, nativeH, cx, cy, nativeCx, nativeCy, nativeZoom, img }
    },
    drawCurvedRect(ctx, x, y, w, h) {
      const r = Math.min(w, h) * 0.22
      ctx.beginPath()
      ctx.moveTo(x + r, y)
      ctx.arcTo(x + w, y, x + w, y + h, r)
      ctx.arcTo(x + w, y + h, x, y + h, r)
      ctx.arcTo(x, y + h, x, y, r)
      ctx.arcTo(x, y, x + w, y, r)
      ctx.closePath()
    },
    drawC4Preview(ctx, center, zoom, color) {
      const { ch, cx, cy, nativeCx, nativeCy, nativeZoom, img } = this.cropSource(center, zoom)
      const cw = this.canvasScale().cw

      let w = Math.min(zoom * 1.1, cw * 0.55)
      w = Math.max(60, w)
      let h = w / C4_ROAD_ASPECT
      if (h > ch * 0.5) {
        h = ch * 0.5
        w = h * C4_ROAD_ASPECT
      }
      const x = cx - w / 2
      const y = cy - h / 2
      const aspect = w / h
      const sx = nativeCx - nativeZoom / 2
      const sh = nativeZoom / aspect
      const sy = nativeCy - sh / 2

      ctx.save()
      this.drawCurvedRect(ctx, x, y, w, h)
      ctx.fillStyle = "#000"
      ctx.fill()
      ctx.clip()
      ctx.translate(x + w, 0)
      ctx.scale(-1, 1)
      ctx.drawImage(img, sx, sy, nativeZoom, sh, 0, y, w, h)
      ctx.restore()

      ctx.save()
      this.drawCurvedRect(ctx, x, y, w, h)
      ctx.strokeStyle = color
      ctx.lineWidth = 2.5
      ctx.stroke()
      ctx.restore()
    },
    drawC3Preview(ctx, center, zoom, color) {
      const { cx, cy, nativeCx, nativeCy, nativeZoom, img } = this.cropSource(center, zoom)
      const half = zoom / 2
      const sx = nativeCx - nativeZoom / 2
      const sy = nativeCy - nativeZoom / 2

      ctx.save()
      ctx.beginPath()
      ctx.arc(cx, cy, half, 0, Math.PI * 2)
      ctx.fillStyle = "#000"
      ctx.fill()
      ctx.clip()
      ctx.translate(cx + half, 0)
      ctx.scale(-1, 1)
      ctx.drawImage(img, sx, sy, nativeZoom, nativeZoom, 0, cy - half, zoom, zoom)
      ctx.restore()

      ctx.save()
      ctx.beginPath()
      ctx.arc(cx, cy, half, 0, Math.PI * 2)
      ctx.strokeStyle = color
      ctx.lineWidth = 2
      ctx.stroke()
      ctx.restore()
    },
    redraw() {
      const canvas = this.canvas()
      if (!canvas) return

      const img = this._img
      if (img && this._sizedFor !== img) {
        this._sizedFor = img
        this.sizeCanvas()
      } else if (!img && (canvas.width === 0 || this._sizedFor)) {
        this._sizedFor = null
        canvas.width = CANVAS_W
        canvas.height = CANVAS_H
      }

      const ctx = canvas.getContext("2d")
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      if (img) {
        ctx.save()
        ctx.translate(canvas.width, 0)
        ctx.scale(-1, 1)
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
        ctx.restore()

        ctx.font = "bold 14px sans-serif"
        ctx.textAlign = "center"
        ctx.fillStyle = "rgba(0, 0, 0, 0.65)"
        ctx.fillRect(0, 0, canvas.width / 2, 34)
        ctx.fillRect(canvas.width / 2, 0, canvas.width / 2, 34)
        ctx.fillStyle = "#fff"
        ctx.fillText(SIDE_LABELS.left.canvas, canvas.width / 4, 22)
        ctx.fillText(SIDE_LABELS.right.canvas, canvas.width * 3 / 4, 22)
      } else {
        ctx.fillStyle = "#222"
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = "#888"
        ctx.font = "16px monospace"
        ctx.textAlign = "center"
        ctx.fillText("Loading camera snapshot...", canvas.width / 2, canvas.height / 2)
        return
      }

      const half = this.zoom / 2
      const sides = [
        { key: "left", center: this.leftCenter, color: SIDE_LABELS.left.color, label: SIDE_LABELS.left.canvas },
        { key: "right", center: this.rightCenter, color: SIDE_LABELS.right.color, label: SIDE_LABELS.right.canvas },
      ]

      for (const side of sides) {
        if (!side.center) continue
        const [cx, cy] = side.center

        if (this.isC4) {
          this.drawC4Preview(ctx, side.center, this.zoom, side.color)
        } else {
          this.drawC3Preview(ctx, side.center, this.zoom, side.color)
        }

        ctx.beginPath()
        ctx.arc(cx, cy, 4, 0, Math.PI * 2)
        ctx.fillStyle = "#fff"
        ctx.fill()
        ctx.strokeStyle = side.color
        ctx.lineWidth = 1.5
        ctx.stroke()

        ctx.fillStyle = side.color
        ctx.font = "bold 13px monospace"
        ctx.textAlign = "center"
        ctx.fillText(side.label, cx, cy - half - 8)
      }

      if (this.armSide) {
        ctx.fillStyle = "#fff"
        ctx.font = "bold 15px monospace"
        ctx.textAlign = "center"
        ctx.fillText(
          this.armSide === "left"
            ? "Click LEFT HERE for the LEFT SIDE OF VEHICLE"
            : "Click RIGHT HERE for the RIGHT SIDE OF VEHICLE",
          canvas.width / 2,
          canvas.height - 18,
        )
      }
    },
    async loadSnapshot() {
      this.error = ""
      this.success = ""
      this.image = false
      this.snapshotLoading = true
      try {
        const { src, cleanup } = await api.pipSnapshotSource()
        const img = new Image()
        img.onload = () => {
          this._img = img
          this._sizedFor = null
          this.image = true
          this.success = "Camera snapshot loaded. Place a center point on each window, then adjust the zoom."
          this.sizeCanvas()
          this.applyConfigToCanvas()
          this.redraw()
          if (cleanup) cleanup()
        }
        img.onerror = () => {
          this.image = false
          this.error = "Failed to decode image"
          this.redraw()
          if (cleanup) cleanup()
        }
        img.src = src
      } catch (e) {
        this.image = false
        this.error = e?.message || "Failed to load snapshot"
        this.redraw()
      } finally {
        this.snapshotLoading = false
      }
    },
    canvasClick(e) {
      if (!this.image || !this.armSide || !e) return
      const canvas = this.canvas()
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      const x = Math.round((e.clientX - rect.left) * (canvas.width / rect.width))
      const y = Math.round((e.clientY - rect.top) * (canvas.height / rect.height))
      if (x < 0 || y < 0 || x > canvas.width || y > canvas.height) return

      const leftHalf = x < canvas.width / 2
      if ((this.armSide === "left" && !leftHalf) || (this.armSide === "right" && leftHalf)) {
        this.error = this.armSide === "left"
          ? "LEFT SIDE OF VEHICLE is on the LEFT. Click the left half of the preview."
          : "RIGHT SIDE OF VEHICLE is on the RIGHT. Click the right half of the preview."
        this.success = ""
        this.redraw()
        return
      }

      if (this.armSide === "left") {
        this.leftCenter = [x, y]
      } else {
        this.rightCenter = [x, y]
      }
      this.armSide = null
      this.error = ""
      this.redraw()
    },
    arm(side) {
      this.armSide = side
      this.error = ""
      this.success = ""
      this.redraw()
    },
    onZoom(e) {
      const value = Number(e?.target?.value ?? 0)
      if (!Number.isFinite(value)) return
      this.zoom = value
      this.redraw()
    },
    clearAll() {
      this.leftCenter = null
      this.rightCenter = null
      this.armSide = null
      this.configSaved = false
      this.redraw()
    },
    async saveConfig() {
      if (!this.leftCenter && !this.rightCenter) {
        this.error = "Place at least one center point."
        this.success = ""
        return
      }
      const { cw, ch, nativeW, nativeH } = this.canvasScale()
      const toNative = (center) => {
        if (!center) return []
        return [Math.round((cw - center[0]) * nativeW / cw), Math.round(center[1] * nativeH / ch)]
      }
      const config = {
        width: nativeW,
        height: nativeH,
        center_left: toNative(this.rightCenter),
        center_right: toNative(this.leftCenter),
        crop_size: Math.round(this.zoom * nativeW / cw),
      }
      this.loading = true
      this.error = ""
      this.success = ""
      try {
        await api.setPipConfig(config)
        this.configSaved = true
        this.configExists = true
        this.success = "PiP Preview mask saved!"
        showSnackbar("PiP Preview mask saved!", "info")
        await this.loadExistingConfig()
      } catch (e) {
        this.error = e?.message || "Failed to save"
        showSnackbar(e?.message || "Save failed...", "error")
      } finally {
        this.loading = false
      }
    },
    async loadExistingConfig() {
      try {
        const data = await api.getPipConfig()
        this.deviceType = data?.device_type || this.deviceType || null
        this.loadedConfig = data?.mask || null
        this.applyConfigToCanvas()
      } catch (e) {
        console.error("PiP Preview config load failed", e)
      }
    },
    applyConfigToCanvas() {
      const config = this.loadedConfig
      if (!config) {
        this.leftCenter = null
        this.rightCenter = null
        this.configExists = false
        this.redraw()
        return
      }
      const { cw, ch, nativeW, nativeH } = this.canvasScale()
      const toCanvas = (center) => {
        if (!Array.isArray(center) || center.length < 2) return null
        return [Math.round(cw - center[0] * cw / nativeW), Math.round(center[1] * ch / nativeH)]
      }
      this.leftCenter = toCanvas(config.center_right)
      this.rightCenter = toCanvas(config.center_left)
      if (Number.isFinite(Number(config.crop_size))) {
        this.zoom = Math.round(Number(config.crop_size) * cw / nativeW)
      }
      this.configExists = Boolean(this.leftCenter || this.rightCenter)
      this.redraw()
    },
    async deleteConfig() {
      if (!(await GalaxyConfirm({
        title: "Confirm Delete",
        message: "Are you sure you want to delete the PiP Side Camera mask?",
        confirmLabel: "Yes, Delete",
        danger: true,
      }))) return
      this.loading = true
      this.error = ""
      this.success = ""
      try {
        await api.deletePipConfig()
        this.leftCenter = null
        this.rightCenter = null
        this.armSide = null
        this.configSaved = false
        this.configExists = false
        this.loadedConfig = null
        this.success = "PiP Preview mask cleared."
        showSnackbar("PiP Preview mask cleared.", "info")
        this.redraw()
      } catch (e) {
        this.error = e?.message || "Failed to delete"
        showSnackbar(e?.message || "Delete failed...", "error")
      } finally {
        this.loading = false
      }
    },
  },
  template: `
    <div>
      <h2 v-if="!embedded" style="margin-top:0;">PiP Side Camera Preview</h2>

      <div style="display:grid; gap:var(--sp-4);">
        <template v-if="!embedded">
          <GalaxySection title="About PiP Preview" icon="bi-info-circle" :default-open="true">
            <ul style="margin:0; padding-left:1.2em; color:var(--text-muted); line-height:1.6;">
              <li>Shows a temporary Picture-in-Picture bubble of the adjacent side window while the turn signal is on or a blind spot is detected</li>
              <li>Place a single center point on each window, then pick a shared zoom level</li>
              <li>This mask is separate from the V-ASM detection mask, so you can tune the visual crop independently</li>
              <li>Works alongside factory blind spot monitoring and/or V-ASM, and with turn signals alone</li>
            </ul>
          </GalaxySection>

          <GalaxySection title="Setup" icon="bi-tools" :default-open="false">
            <ul style="margin:0; padding-left:1.2em; color:var(--text-muted); line-height:1.6;">
              <li>This preview is mirrored to match the normal on-road driver-camera view</li>
              <li>The LEFT side of the vehicle is always on the LEFT here; the RIGHT side is always on the RIGHT</li>
              <li>Click the matching side shown in the large labels. Raw camera-coordinate conversion is automatic</li>
              <li>The zoom slider applies to BOTH windows so the preview stays consistent</li>
              <li>At least one window center is required to enable the preview</li>
            </ul>
          </GalaxySection>

          <div class="gx-row__desc" style="color:var(--text-muted); line-height:1.6; padding:0 2px;">
            Use the preview to enhance lateral awareness. Always check manually before merging and be aware the driver camera view is from the cabin and does not reflect your blind spot.
          </div>
        </template>

        <div v-if="error" class="gx-alert" style="border-left:4px solid var(--error); margin:0;">
          <i class="bi bi-exclamation-triangle-fill gx-alert__icon" style="color:var(--error);"></i>
          <div class="gx-alert__body"><span style="color:var(--error);">{{ error }}</span></div>
        </div>
        <div v-if="success" class="gx-alert gx-alert--info" style="margin:0;">
          <i class="bi bi-check-circle-fill gx-alert__icon"></i>
          <div class="gx-alert__body"><span>{{ success }}</span></div>
        </div>

        <div style="display:flex; gap:8px; flex-wrap:wrap;">
          <button type="button" class="gx-btn" :style="armSide === 'left' ? { background: scolor('left'), color: '#fff' } : {}" @click="arm('left')">
            <i class="bi bi-arrow-left"></i> {{ leftLabel }}
          </button>
          <button type="button" class="gx-btn gx-btn--tonal" :style="armSide === 'right' ? { background: scolor('right'), color: '#fff' } : {}" @click="arm('right')">
            <i class="bi bi-arrow-right"></i> {{ rightLabel }}
          </button>
          <button type="button" class="gx-btn" :disabled="loading || (!leftCenter && !rightCenter)" @click="saveConfig">
            <i class="bi bi-save"></i> {{ loading ? 'Saving...' : 'Save Mask' }}
          </button>
          <button v-if="configExists" type="button" class="gx-btn gx-btn--tonal" style="color:var(--error);" :disabled="loading" @click="deleteConfig">
            <i class="bi bi-trash"></i> Delete Mask
          </button>
          <button type="button" class="gx-btn gx-btn--tonal" @click="clearAll"><i class="bi bi-x-circle"></i> Clear All</button>
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="snapshotLoading" @click="loadSnapshot">
            <i class="bi bi-camera"></i> {{ snapshotLoading ? 'Loading...' : 'Get a new Snapshot' }}
          </button>
        </div>

          <div v-if="armSide" class="gx-alert gx-alert--warn" style="margin:0;">
          <i class="bi" :class="armSide === 'left' ? 'bi-arrow-left' : 'bi-arrow-right'" :style="{ color: scolor(armSide) }"></i>
          <div class="gx-alert__body">
            <strong>{{ armSide === 'left' ? 'LEFT SIDE OF VEHICLE - LEFT HERE' : 'RIGHT SIDE OF VEHICLE - RIGHT HERE' }}</strong>
            <span>Click the matching side of the mirrored preview</span>
          </div>
        </div>

        <div style="width:100%;">
          <canvas ref="canvas"
                  @click="canvasClick"
                  :style="canvasStyle"></canvas>
          <p style="margin:6px 0 0; color:var(--text-muted); font-size:var(--fs-sm); text-align:center;">
            {{ armSide ? 'Click the window to place its center point.' : 'Place a center point on each window, then use the zoom slider below.' }}
          </p>
        </div>

        <div class="gx-card" style="padding: var(--sp-4);">
          <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px;">
            <strong>Zoom</strong>
            <span class="gx-chip">{{ zoom }} px</span>
          </div>
          <input type="range" class="gx-field gx-field--full" style="padding:0;" min="60" max="640" step="5"
                 :value="zoom" @input="onZoom" />
          <div style="display:flex; justify-content:space-between; margin-top:4px;">
            <span class="gx-row__desc" style="margin:0;">Wide</span>
            <span class="gx-row__desc" style="margin:0;">Close</span>
          </div>
          <p class="gx-row__desc" style="margin:8px 0 0;">Applied to both windows so the preview stays consistent.</p>
        </div>

        <GalaxySection v-if="!embedded" title="Preview Settings" icon="bi-sliders" :default-open="false">
          <ul style="margin:0; padding-left:1.2em; color:var(--text-muted); line-height:1.6;">
            <li>Enable "PiP Side Preview" in Toggles -> Visual (Display &amp; UI) -> Driving Screen Widgets</li>
            <li>Choose to show the preview on the turn signal, on blind spot detection, or both</li>
          </ul>
        </GalaxySection>
      </div>
    </div>
  `,
}
