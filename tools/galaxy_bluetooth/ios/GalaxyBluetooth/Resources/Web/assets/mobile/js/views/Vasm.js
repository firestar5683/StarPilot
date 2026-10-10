import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"
import { GalaxySection } from "../components/GalaxySection.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"

const CANVAS_W = 640
const CANVAS_H = 480
const LEFT_LABEL = "LEFT SIDE OF VEHICLE - LEFT HERE"
const RIGHT_LABEL = "RIGHT SIDE OF VEHICLE - RIGHT HERE"
const BLUE = "#0d6efd"
const ORANGE = "#fd7e14"

function polyCenter(pts) {
  if (!pts || !pts.length) return null
  const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length
  const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length
  return [cx, cy]
}

export const Vasm = {
  name: "Vasm",
  components: { GalaxySection },
  props: { embedded: { type: Boolean, default: false } },
  data() {
    return {
      snapshotLoading: false,
      saving: false,
      error: "",
      success: "",
      configSaved: false,
      configExists: false,
      annotating: null,
      leftPoints: [],
      rightPoints: [],
      image: false,
      leftActive: "-",
      rightActive: "-",
      leftConf: "-",
      rightConf: "-",
      loadedConfig: null,
      BLUE,
      ORANGE,
      LEFT_LABEL,
      RIGHT_LABEL,
    }
  },
  computed: {
    canSave() {
      return this.leftPoints.length >= 3 || this.rightPoints.length >= 3
    },
    leftDone() { return this.leftPoints.length >= 3 },
    rightDone() { return this.rightPoints.length >= 3 },
  },
  mounted() {
    this._img = null
    const canvas = this.$refs.canvas
    if (canvas) { canvas.width = CANVAS_W; canvas.height = CANVAS_H }
    this.poll = usePolling(() => this.pollStatus(), { interval: 3000 })
    this.poll.start()
    this.loadConfig()
    this.loadSnapshot()
  },
  beforeUnmount() {
    this.poll?.destroy()
    if (this._img) this._img.src = ""
    this._img = null
  },
  methods: {
    clearMessages() { this.error = ""; this.success = "" },
    setError(msg) { this.error = msg || ""; showSnackbar(msg || "Something went wrong.", "error") },
    setSuccess(msg) { this.success = msg || "" },
    canvas() { return this.$refs.canvas },
    sizeCanvas() {
      const canvas = this.canvas()
      const img = this._img
      if (!canvas || !img) return
      const w = Math.min(img.naturalWidth, 1280)
      canvas.width = w
      canvas.height = Math.round(w * (img.naturalHeight / img.naturalWidth))
    },
    drawPolygon(ctx, points, fillColor, borderColor, label) {
      if (points.length < 2) {
        for (const pt of points) {
          ctx.beginPath()
          ctx.arc(pt[0], pt[1], 5, 0, Math.PI * 2)
          ctx.fillStyle = borderColor
          ctx.fill()
        }
        return
      }
      ctx.beginPath()
      ctx.moveTo(points[0][0], points[0][1])
      for (let i = 1; i < points.length; i++) ctx.lineTo(points[i][0], points[i][1])
      if (points.length >= 3) {
        ctx.closePath()
        ctx.fillStyle = fillColor
        ctx.fill()
      }
      ctx.strokeStyle = borderColor
      ctx.lineWidth = 2
      ctx.stroke()
      for (const pt of points) {
        ctx.beginPath()
        ctx.arc(pt[0], pt[1], 4, 0, Math.PI * 2)
        ctx.fillStyle = "#fff"
        ctx.fill()
        ctx.strokeStyle = borderColor
        ctx.lineWidth = 1.5
        ctx.stroke()
      }
      if (points.length >= 3) {
        const center = polyCenter(points)
        if (center) {
          ctx.fillStyle = "#fff"
          ctx.font = "bold 14px monospace"
          ctx.textAlign = "center"
          ctx.fillText(label, center[0], center[1] + 5)
        }
      }
    },
    redraw() {
      const canvas = this.canvas()
      if (!canvas) return
      this.sizeCanvas()
      const ctx = canvas.getContext("2d")
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const img = this._img
      if (!img) {
        ctx.fillStyle = "#222"
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = "#888"
        ctx.font = "16px monospace"
        ctx.textAlign = "center"
        ctx.fillText("Loading camera snapshot...", canvas.width / 2, canvas.height / 2)
        return
      }
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
      ctx.fillText(LEFT_LABEL, canvas.width / 4, 22)
      ctx.fillText(RIGHT_LABEL, canvas.width * 3 / 4, 22)
      this.drawPolygon(ctx, this.leftPoints, "rgba(13, 110, 253, 0.25)", BLUE, LEFT_LABEL)
      this.drawPolygon(ctx, this.rightPoints, "rgba(253, 126, 20, 0.25)", ORANGE, RIGHT_LABEL)
    },
    canvasClick(e) {
      if (!this.annotating || !this.image || !e) return
      const canvas = this.canvas()
      if (!canvas) return
      const rect = canvas.getBoundingClientRect()
      const x = Math.round((e.clientX - rect.left) * (canvas.width / rect.width))
      const y = Math.round((e.clientY - rect.top) * (canvas.height / rect.height))
      if (x < 0 || y < 0) return
      const key = this.annotating === "left" ? "leftPoints" : "rightPoints"
      const points = this[key].slice()
      if (points.length >= 3) {
        const first = points[0]
        const dist = Math.sqrt((x - first[0]) ** 2 + (y - first[1]) ** 2)
        if (dist < 12) { this.finishSide(); return }
      }
      points.push([x, y])
      this[key] = points
      this.redraw()
    },
    canvasRightClick() {
      if (!this.annotating) return
      const key = this.annotating === "left" ? "leftPoints" : "rightPoints"
      const points = this[key].slice()
      if (!points.length) return
      points.pop()
      this[key] = points
      this.redraw()
    },
    startAnnotate(side) {
      this.annotating = side
      this.clearMessages()
      this.redraw()
    },
    finishSide() {
      if (!this.annotating) return
      const side = this.annotating
      const points = side === "left" ? this.leftPoints : this.rightPoints
      if (points.length < 3) {
        this.setError("Need at least 3 points to define a region.")
        return
      }
      this.annotating = null
      this.setSuccess(`${side === "left" ? "Left" : "Right"} window annotated (${points.length} points)!`)
      this.redraw()
    },
    clearSide(side) {
      if (side === "left") this.leftPoints = []
      else this.rightPoints = []
      this.annotating = null
      this.redraw()
    },
    clearAll() {
      this.leftPoints = []
      this.rightPoints = []
      this.annotating = null
      this.configSaved = false
      this.clearMessages()
      this.redraw()
    },
    async saveConfig() {
      if (this.leftPoints.length < 3 && this.rightPoints.length < 3) {
        this.setError("Annotate at least one window with 3+ points.")
        return
      }
      const img = this._img
      const nativeW = img ? img.naturalWidth : 1920
      const nativeH = img ? img.naturalHeight : 1080
      const canvas = this.canvas()
      const cw = canvas ? canvas.width : nativeW
      const ch = canvas ? canvas.height : nativeH
      const scalePoints = (pts) => pts.map(([x, y]) => [Math.round((cw - x) * nativeW / cw), Math.round(y * nativeH / ch)])
      const config = { width: nativeW, height: nativeH }
      config.poly_right = this.leftPoints.length >= 3 ? scalePoints(this.leftPoints) : []
      config.poly_left = this.rightPoints.length >= 3 ? scalePoints(this.rightPoints) : []
      this.saving = true
      this.clearMessages()
      try {
        const data = await api.setVasmConfig(config)
        this.configSaved = true
        this.configExists = true
        this.setSuccess(data?.message || "Annotation config saved! V-ASM is now enabled.")
        showSnackbar("Annotation config saved! V-ASM is now enabled.")
        await this.loadConfig()
      } catch (e) {
        this.setError(e?.data?.error || e?.message || "Failed to save")
      } finally {
        this.saving = false
      }
    },
    async loadConfig() {
      try {
        const config = await api.getVasmConfig()
        this.loadedConfig = config && typeof config === "object" && !Array.isArray(config) ? config : null
      } catch (e) {
        this.loadedConfig = null
      }
      this.applyConfigToCanvas()
    },
    applyConfigToCanvas() {
      const config = this.loadedConfig
      const canvas = this.canvas()
      if (!config) {
        this.leftPoints = []
        this.rightPoints = []
        this.configExists = false
        this.redraw()
        return
      }
      const cw = canvas ? (canvas.width || CANVAS_W) : CANVAS_W
      const ch = canvas ? (canvas.height || CANVAS_H) : CANVAS_H
      const img = this._img
      const nativeW = img ? img.naturalWidth : (config.width || 1920)
      const nativeH = img ? img.naturalHeight : (config.height || 1080)
      const scaleX = cw / nativeW
      const scaleY = ch / nativeH
      const toCanvas = (pts) => pts.map(([x, y]) => [Math.round(cw - x * scaleX), Math.round(y * scaleY)])
      const left = Array.isArray(config.poly_right) && config.poly_right.length >= 3 ? toCanvas(config.poly_right) : []
      const right = Array.isArray(config.poly_left) && config.poly_left.length >= 3 ? toCanvas(config.poly_left) : []
      this.leftPoints = left
      this.rightPoints = right
      this.configExists = Boolean(left.length || right.length)
      this.redraw()
    },
    async deleteConfig() {
      const confirmed = await GalaxyConfirm({
        title: "Delete V-ASM Config?",
        message: "This clears your window annotations and disables V-ASM.",
        confirmLabel: "Delete Config",
        danger: true,
      })
      if (!confirmed) return
      this.saving = true
      this.clearMessages()
      try {
        const data = await api.deleteVasmConfig()
        this.leftPoints = []
        this.rightPoints = []
        this.annotating = null
        this.configSaved = false
        this.configExists = false
        this.loadedConfig = null
        this.setSuccess(data?.message || "Annotation config cleared.")
        showSnackbar("Annotation config cleared.")
        this.redraw()
      } catch (e) {
        this.setError(e?.data?.error || e?.message || "Failed to delete")
      } finally {
        this.saving = false
      }
    },
    async loadSnapshot() {
      this.clearMessages()
      this.image = false
      this.snapshotLoading = true
      let url = null
      try {
        const blob = await api.getVasmSnapshotBlob()
        url = URL.createObjectURL(blob)
        const img = new Image()
        img.onload = () => {
          this._img = img
          this.image = true
          this.sizeCanvas()
          this.setSuccess("Camera snapshot loaded. Click a window button above to start annotating.")
          this.applyConfigToCanvas()
          if (url) { URL.revokeObjectURL(url); url = null }
        }
        img.onerror = () => {
          this.image = false
          this.setError("Failed to decode image")
          if (url) { URL.revokeObjectURL(url); url = null }
          this.redraw()
        }
        img.src = url
      } catch (e) {
        this.image = false
        this.setError(e?.message || "Failed to load snapshot")
        this.redraw()
      } finally {
        this.snapshotLoading = false
      }
    },
    async pollStatus() {
      try {
        const [la, ra, lc, rc] = await Promise.all([
          api.getMemoryParam("VASMLeftActive"),
          api.getMemoryParam("VASMRightActive"),
          api.getMemoryParam("VASMLeftConfidence"),
          api.getMemoryParam("VASMRightConfidence"),
        ])
        this.leftActive = la === "1" ? "YES" : "no"
        this.rightActive = ra === "1" ? "YES" : "no"
        this.leftConf = Number.isFinite(parseFloat(lc)) ? parseFloat(lc).toFixed(3) : "-"
        this.rightConf = Number.isFinite(parseFloat(rc)) ? parseFloat(rc).toFixed(3) : "-"
      } catch (e) {
      }
    },
    activeColor(side) {
      return side === "left" ? BLUE : ORANGE
    },
  },
  template: `
    <div>
      <h2 v-if="!embedded" style="margin-top:0;">Vision Adjacent Spot Monitoring (V-ASM)</h2>

      <template v-if="!embedded">
        <GalaxySection title="About V-ASM" icon="bi-info-circle">
          <div style="padding: var(--sp-3); display:grid; gap:8px; color:var(--text-muted); line-height:1.5;">
            <p style="margin:0;">Camera-based adjacent spot monitoring using the driver camera. It works alongside factory blind spot monitoring or standalone.</p>
            <p style="margin:0;">Annotate window areas so V-ASM knows where to look. Submit edge cases and learn about the training pipeline in the form at <a href="https://github.com/prabhaavp/vasm-op" target="_blank" rel="noopener noreferrer">github.com/prabhaavp/vasm-op</a>.</p>
          </div>
        </GalaxySection>

        <GalaxySection title="Tracing Guidelines" icon="bi-bullseye">
          <ul style="margin:0; padding: var(--sp-3) var(--sp-3) var(--sp-3) calc(var(--sp-3) + 16px); color:var(--text-muted); line-height:1.6; display:grid; gap:6px;">
            <li>The preview is mirrored: the LEFT side of the vehicle is always on the LEFT here; the RIGHT side is always on the RIGHT.</li>
            <li>Trace the visible glass (front and rear side windows) seen by the driver camera. Mask as much window area as possible.</li>
            <li>Exclude A-pillars, door frames, and interior. Include the side mirror if visible through the glass.</li>
            <li>The B-pillar is fine to include as needed for a continuous mask. Be consistent left vs right.</li>
          </ul>
        </GalaxySection>
      </template>

      <div class="gx-alert" v-if="success" style="margin:0 0 12px;">{{ success }}</div>
      <div class="gx-alert" v-if="error" style="margin:0 0 12px; color:var(--error);">{{ error }}</div>

      <section class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-pencil-square"></i>
          <span class="gx-section__title">Annotate Windows</span>
          <span v-if="configSaved || configExists" class="gx-chip" style="background:var(--primary); color:var(--on-primary);">V-ASM enabled</span>
        </div>
        <div style="padding: var(--sp-3); display:grid; gap:12px;">
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button type="button" class="gx-btn gx-btn--tonal" :style="annotating === 'left' ? 'background:' + BLUE + '; color:#fff; border-color:' + BLUE + ';' : 'color:' + BLUE + '; border-color:' + BLUE + ';'" @click="startAnnotate('left')">
              {{ annotating === 'left' ? 'Annotating Left Side of Vehicle - Left Here...' : 'Annotate Left Side of Vehicle - Left Here' }}
            </button>
            <button type="button" class="gx-btn gx-btn--tonal" :style="annotating === 'right' ? 'background:' + ORANGE + '; color:#fff; border-color:' + ORANGE + ';' : 'color:' + ORANGE + '; border-color:' + ORANGE + ';'" @click="startAnnotate('right')">
              {{ annotating === 'right' ? 'Annotating Right Side of Vehicle - Right Here...' : 'Annotate Right Side of Vehicle - Right Here' }}
            </button>
            <button v-if="annotating" type="button" class="gx-btn" @click="finishSide">Finish {{ annotating === 'left' ? 'Left' : 'Right' }}</button>
            <button type="button" class="gx-btn" :disabled="saving || !canSave" @click="saveConfig"><i v-if="saving" class="bi bi-arrow-repeat gx-spin"></i><i v-else class="bi bi-check2-circle"></i> {{ saving ? 'Saving...' : 'Save Config' }}</button>
            <button v-if="configExists" type="button" class="gx-btn" style="background:var(--error); color:var(--on-error);" :disabled="saving" @click="deleteConfig"><i class="bi bi-trash"></i> Delete Config</button>
            <button type="button" class="gx-btn gx-btn--tonal" @click="clearAll"><i class="bi bi-eraser"></i> Clear All</button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="snapshotLoading" @click="loadSnapshot"><i v-if="snapshotLoading" class="bi bi-arrow-repeat gx-spin"></i><i v-else class="bi bi-camera"></i> {{ snapshotLoading ? 'Loading...' : 'Get a new Snapshot' }}</button>
          </div>

          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <span class="gx-chip" :style="'border-color:' + BLUE + '; color:' + BLUE + ';'">Left: {{ leftPoints.length }} pt{{ leftPoints.length !== 1 ? 's' : '' }}<i v-if="leftDone" class="bi bi-check-lg"></i>
              <span v-if="leftPoints.length > 0" style="margin-left:6px; cursor:pointer; color:var(--error);" @click="clearSide('left')">×</span>
            </span>
            <span class="gx-chip" :style="'border-color:' + ORANGE + '; color:' + ORANGE + ';'">Right: {{ rightPoints.length }} pt{{ rightPoints.length !== 1 ? 's' : '' }}<i v-if="rightDone" class="bi bi-check-lg"></i>
              <span v-if="rightPoints.length > 0" style="margin-left:6px; cursor:pointer; color:var(--error);" @click="clearSide('right')">×</span>
            </span>
          </div>

          <div v-if="annotating" class="gx-alert" :style="'color:' + activeColor(annotating) + ';'">
            {{ annotating === 'left' ? LEFT_LABEL : RIGHT_LABEL }} — Click the canvas to place points around the visible glass. Click near the first point to close the polygon. Right-click to undo the last point.
          </div>
          <div v-else-if="!image" class="gx-row__desc">Loading camera snapshot... The snapshot will load automatically.</div>
          <div v-else class="gx-row__desc">Idle — click a window button above to configure your active canvas boundaries.</div>

          <canvas ref="canvas" id="v-asm-canvas" style="width:100%; height:auto; background:#222; border-radius:8px; display:block; touch-action:none;" @click="canvasClick" @contextmenu.prevent="canvasRightClick"></canvas>
        </div>
      </section>

      <GalaxySection v-if="!embedded" title="Sensitivity Settings" icon="bi-sliders">
        <ul style="margin:0; padding: var(--sp-3) var(--sp-3) var(--sp-3) calc(var(--sp-3) + 16px); color:var(--text-muted); line-height:1.6; display:grid; gap:6px;">
          <li>Confidence Threshold: minimum confidence for a detection (higher means fewer false positives).</li>
          <li>Smoothing Duration: time constant for signal smoothing (higher means less flickering).</li>
          <li>Adjust these in Toggles → Lateral once enabled.</li>
        </ul>
      </GalaxySection>

      <section class="gx-card">
        <div class="gx-section__header">
          <i class="bi bi-activity"></i>
          <span class="gx-section__title">Current Status</span>
        </div>
        <div style="padding: var(--sp-3); display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:8px;">
          <div class="gx-card" style="padding: 8px 10px;"><div class="gx-row__label" style="font-size:var(--fs-xs);">Left Active</div><div class="gx-row__value" :style="leftActive === 'YES' ? 'color:var(--primary);' : 'color:var(--text-muted);'">{{ leftActive }}</div></div>
          <div class="gx-card" style="padding: 8px 10px;"><div class="gx-row__label" style="font-size:var(--fs-xs);">Right Active</div><div class="gx-row__value" :style="rightActive === 'YES' ? 'color:' + ORANGE + ';' : 'color:var(--text-muted);'">{{ rightActive }}</div></div>
          <div class="gx-card" style="padding: 8px 10px;"><div class="gx-row__label" style="font-size:var(--fs-xs);">Left Confidence</div><div class="gx-row__value">{{ leftConf }}</div></div>
          <div class="gx-card" style="padding: 8px 10px;"><div class="gx-row__label" style="font-size:var(--fs-xs);">Right Confidence</div><div class="gx-row__value">{{ rightConf }}</div></div>
        </div>
      </section>
    </div>
  `,
}
