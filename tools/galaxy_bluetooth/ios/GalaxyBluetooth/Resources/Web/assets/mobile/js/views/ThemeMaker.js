import { api, showSnackbar } from "../api.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"
import { GalaxySection } from "../components/GalaxySection.js"
import { GxNotice } from "../components/GxNotice.js"

const COLOR_LABELS = {
  LaneLines: "Lane Lines",
  LeadMarker: "Lead Marker",
  Path: "Path",
  PathEdge: "Path Edge",
  Sidebar1: "Sidebar Top",
  Sidebar2: "Sidebar Middle",
  Sidebar3: "Sidebar Bottom",
}

const DISTANCE_KEYS = ["traffic", "aggressive", "standard", "relaxed"]
const SOUND_KEYS = ["disengage", "engage", "prompt", "startup"]
const SOUND_LABELS = { disengage: "Disengage", engage: "Engage", prompt: "Prompt", startup: "Startup" }

function defaultColors() {
  const base = { red: 23, green: 134, blue: 68, alpha: 255 }
  return {
    LaneLines: { ...base },
    LeadMarker: { ...base },
    Path: { ...base },
    PathEdge: { red: 18, green: 107, blue: 54, alpha: 255 },
    Sidebar1: { ...base },
    Sidebar2: { ...base },
    Sidebar3: { ...base },
  }
}

function rgbToHex(c) {
  const p = (n) => Math.max(0, Math.min(255, Math.round(n || 0))).toString(16).padStart(2, "0")
  return "#" + p(c.red) + p(c.green) + p(c.blue)
}

function hexToRgb(hex) {
  return {
    red: parseInt(hex.slice(1, 3), 16),
    green: parseInt(hex.slice(3, 5), 16),
    blue: parseInt(hex.slice(5, 7), 16),
    alpha: 255,
  }
}

function emptyFiles() {
  return {
    distanceIcons: { traffic: null, aggressive: null, standard: null, relaxed: null },
    homeButton: null,
    settingsButton: null,
    steeringWheel: null,
    turnSignal: null,
    turnSignalBlindspot: null,
    sounds: { disengage: null, engage: null, prompt: null, startup: null },
  }
}

function emptyNames() {
  return {
    distanceIcons: { traffic: "", aggressive: "", standard: "", relaxed: "" },
    homeButton: "",
    settingsButton: "",
    steeringWheel: "",
    turnSignal: "",
    turnSignalBlindspot: "",
    sounds: { disengage: "", engage: "", prompt: "", startup: "" },
  }
}

export const ThemeMaker = {
  name: "ThemeMaker",
  components: { GalaxySection, GxNotice },
  data() {
    return {
      colors: defaultColors(),
      files: emptyFiles(),
      names: emptyNames(),
      labels: COLOR_LABELS,
      soundLabels: SOUND_LABELS,
      flags: { colors: true, distance_icons: false, icons: false, sounds: false, steering_wheel: false, turn_signals: false },
      turnSignalStyle: "Static",
      turnSignalLength: 100,
      themeName: "",
      themes: [],
      loading: true,
      loadedError: "",
      busy: false,
    }
  },
  async mounted() {
    this.refreshThemeList()
    try {
      const data = await api.getThemeDefault()
      if (data && data.colors && typeof data.colors === "object") {
        this.colors = this.normalizeColors(data.colors)
        this.flags.colors = true
      }
    } catch (e) {}
  },
  computed: {
    colorKeys() {
      return Object.keys(COLOR_LABELS)
    },
    sectionOptions() {
      const opts = [{ key: "colors", label: "Colors" }]
      if (this.hasContent("distance_icons")) opts.push({ key: "distance_icons", label: "Distance Icons" })
      if (this.hasContent("icons")) opts.push({ key: "icons", label: "Icons" })
      if (this.hasContent("sounds")) opts.push({ key: "sounds", label: "Sounds" })
      if (this.hasContent("steering_wheel")) opts.push({ key: "steering_wheel", label: "Steering Wheel" })
      if (this.hasContent("turn_signals")) opts.push({ key: "turn_signals", label: "Turn Signals" })
      return opts
    },
    anyChecked() {
      return this.sectionOptions.some((s) => this.flags[s.key])
    },
    canSave() {
      return !this.busy && !!this.themeName.trim() && this.anyChecked
    },
  },
  methods: {
    normalizeColors(obj) {
      const base = defaultColors()
      for (const key of Object.keys(base)) {
        const src = obj[key]
        if (src && typeof src === "object") {
          base[key] = {
            red: Number(src.red) || 0,
            green: Number(src.green) || 0,
            blue: Number(src.blue) || 0,
            alpha: Number(src.alpha) != null ? Number(src.alpha) : 255,
          }
        }
      }
      return base
    },
    hexFor(key) {
      return rgbToHex(this.colors[key])
    },
    rgbaFor(key) {
      const c = this.colors[key] || {}
      const a = c.alpha != null ? Number(c.alpha) / 255 : 1
      return "rgba(" + (c.red || 0) + "," + (c.green || 0) + "," + (c.blue || 0) + "," + a + ")"
    },
    onColorChange(e, key) {
      this.colors[key] = hexToRgb(e.target.value)
      this.flags.colors = true
    },
    resetColors() {
      this.colors = defaultColors()
      this.flags.colors = true
    },
    basename(path) {
      return String(path || "").split("/").pop()
    },
    onFileChoose(e, kind, key, subkey) {
      const file = e.target.files && e.target.files[0]
      e.target.value = ""
      if (!file) return
      if (file.size > 5 * 1024 * 1024) {
        showSnackbar("That file is too large! Please upload files under 5MB.", "error")
        return
      }
      if (kind === "image" && !file.type.startsWith("image/")) {
        showSnackbar("Invalid file type! Please upload an image file.", "error")
        return
      }
      if (kind === "audio" && !file.type.startsWith("audio/")) {
        showSnackbar("Invalid file type! Please upload an audio file.", "error")
        return
      }
      if (subkey) {
        this.files[key][subkey] = file
        this.names[key][subkey] = file.name
      } else {
        this.files[key] = file
        this.names[key] = file.name
      }
      const comp = key === "distanceIcons" ? "distance_icons"
        : key === "homeButton" || key === "settingsButton" ? "icons"
        : key === "steeringWheel" ? "steering_wheel"
        : key === "turnSignal" || key === "turnSignalBlindspot" ? "turn_signals"
        : kind === "audio" ? "sounds"
        : null
      if (comp) this.flags[comp] = true
    },
    clearFile(kind, key, subkey) {
      if (subkey) {
        this.files[key][subkey] = null
        this.names[key][subkey] = ""
      } else {
        this.files[key] = null
        this.names[key] = ""
      }
    },
    hasContent(comp) {
      if (comp === "colors") return true
      if (comp === "distance_icons") return DISTANCE_KEYS.some((k) => this.files.distanceIcons[k])
      if (comp === "icons") return !!(this.files.homeButton || this.files.settingsButton)
      if (comp === "sounds") return SOUND_KEYS.some((k) => this.files.sounds[k])
      if (comp === "steering_wheel") return !!this.files.steeringWheel
      if (comp === "turn_signals") return !!(this.files.turnSignal || this.files.turnSignalBlindspot)
      return false
    },
    fileRow(key, subkey, label) {
      const name = subkey ? this.names[key][subkey] : this.names[key]
      return { key, subkey, label, name }
    },
    getFormData() {
      const fd = new FormData()
      fd.append("themeName", this.themeName.trim() || "")
      fd.append("saveChecklist", JSON.stringify(this.flags))
      fd.append("selectedThemeSources", "{}")
      if (this.flags.colors) fd.append("colors", JSON.stringify(this.colors))
      if (this.flags.turn_signals) {
        fd.append("turnSignalStyle", this.turnSignalStyle)
        fd.append("turnSignalType", "Single Image")
        fd.append("turnSignalLength", String(this.turnSignalLength))
        if (this.files.turnSignal) fd.append("turnSignal", this.files.turnSignal)
        if (this.files.turnSignalBlindspot) fd.append("turnSignalBlindspot", this.files.turnSignalBlindspot)
      }
      if (this.flags.icons) {
        if (this.files.homeButton) fd.append("homeButton", this.files.homeButton)
        if (this.files.settingsButton) fd.append("settingsButton", this.files.settingsButton)
      }
      if (this.flags.steering_wheel && this.files.steeringWheel) fd.append("steeringWheel", this.files.steeringWheel)
      if (this.flags.distance_icons) {
        for (const k of DISTANCE_KEYS) {
          if (this.files.distanceIcons[k]) fd.append("distanceIcons_" + k, this.files.distanceIcons[k])
        }
      }
      if (this.flags.sounds) {
        for (const k of SOUND_KEYS) {
          if (this.files.sounds[k]) fd.append(k, this.files.sounds[k])
        }
      }
      return fd
    },
    async save() {
      if (!this.canSave) { showSnackbar("Enter a theme name and select at least one component.", "error"); return }
      this.busy = true
      try {
        const res = await api.saveTheme(this.getFormData())
        showSnackbar(res?.message || "Theme saved!")
        this.themeName = ""
        await this.refreshThemeList()
      } catch (e) {
        showSnackbar(e?.data?.error || e?.message || "Failed to save theme.", "error")
      } finally {
        this.busy = false
      }
    },
    async apply() {
      if (!this.anyChecked) { showSnackbar("Select at least one component to apply.", "error"); return }
      const confirmed = await GalaxyConfirm({
        title: "Apply theme?",
        message: "This makes the current colors/assets the active theme on device. It does not save them as a named theme.",
        confirmLabel: "Apply",
      })
      if (!confirmed) return
      this.busy = true
      try {
        const res = await api.applyTheme(this.getFormData())
        showSnackbar(res?.message || "Theme applied!")
      } catch (e) {
        showSnackbar(e?.data?.error || e?.message || "Failed to apply theme.", "error")
      } finally {
        this.busy = false
      }
    },
    async exportTheme() {
      if (!this.themeName.trim()) { showSnackbar("Enter a theme name before exporting.", "error"); return }
      if (!this.anyChecked) { showSnackbar("Select at least one component to export.", "error"); return }
      this.busy = true
      try {
        const blob = await api.downloadTheme(this.getFormData())
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = this.themeName.trim().replace(/\s+/g, "_") + ".zip"
        a.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
        showSnackbar("Theme exported as a zip.")
      } catch (e) {
        showSnackbar(e?.message || "Failed to export theme.", "error")
      } finally {
        this.busy = false
      }
    },
    async refreshThemeList() {
      this.loading = true
      try {
        const data = await api.getThemeList()
        this.themes = Array.isArray(data?.themes) ? data.themes.slice().sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), undefined, { numeric: true })) : []
        this.loadedError = ""
      } catch (e) {
        this.loadedError = "Failed to load themes."
      } finally {
        this.loading = false
      }
    },
    compChips(t) {
      const out = []
      if (t.hasColors) out.push("Colors")
      if (t.hasDistanceIcons) out.push("Distance Icons")
      if (t.hasIcons) out.push("Icons")
      if (t.hasSounds) out.push("Sounds")
      if (t.hasSteeringWheel) out.push("Steering Wheel")
      if (t.hasTurnSignals) out.push("Turn Signals")
      return out
    },
    canDelete(t) {
      return !this.busy && String(t?.type || "").toLowerCase() !== "holiday"
    },
    async loadThemeToEditor(t) {
      if (this.busy) return
      this.busy = true
      try {
        const data = await api.loadTheme(t.path, t.type)
        const fetchFile = async (assetPath) => {
          if (!assetPath) return null
          try {
            const blob = await api.getThemeAssetBlob(t.path, t.type, assetPath)
            return new File([blob], this.basename(assetPath), { type: blob.type || "application/octet-stream" })
          } catch (e) {
            return null
          }
        }
        let loadedAny = false
        if (data?.colors && typeof data.colors === "object" && Object.keys(data.colors).length) {
          this.colors = this.normalizeColors(data.colors)
          this.flags.colors = true
          loadedAny = true
        }
        const imgs = data?.images || {}
        if (imgs.distanceIcons && typeof imgs.distanceIcons === "object") {
          for (const k of DISTANCE_KEYS) {
            const asset = imgs.distanceIcons[k]
            if (asset && asset.path) {
              const f = await fetchFile(asset.path)
              if (f) { this.files.distanceIcons[k] = f; this.names.distanceIcons[k] = f.name; this.flags.distance_icons = true; loadedAny = true }
            }
          }
        }
        const setNamedFile = async (slotKey, asset) => {
          if (!asset || !asset.path) return
          const f = await fetchFile(asset.path)
          if (f) { this.files[slotKey] = f; this.names[slotKey] = f.name; loadedAny = true }
        }
        await setNamedFile("homeButton", imgs.homeButton)
        await setNamedFile("settingsButton", imgs.settingsButton)
        await setNamedFile("steeringWheel", imgs.steeringWheel)
        await setNamedFile("turnSignal", imgs.turnSignal)
        await setNamedFile("turnSignalBlindspot", imgs.turnSignalBlindspot)
        if (this.files.homeButton || this.files.settingsButton) this.flags.icons = true
        if (this.files.steeringWheel) this.flags.steering_wheel = true
        if (this.files.turnSignal || this.files.turnSignalBlindspot) this.flags.turn_signals = true
        if (data?.sounds && typeof data.sounds === "object") {
          for (const k of SOUND_KEYS) {
            const asset = data.sounds[k]
            if (asset && asset.path) {
              const f = await fetchFile(asset.path)
              if (f) { this.files.sounds[k] = f; this.names.sounds[k] = f.name; this.flags.sounds = true; loadedAny = true }
            }
          }
        }
        if (data?.turnSignalStyle) this.turnSignalStyle = data.turnSignalStyle
        if (data?.turnSignalLength != null) this.turnSignalLength = Number(data.turnSignalLength) || 100
        if (!loadedAny) showSnackbar("That theme has no loadable content.", "info")
        else showSnackbar("Loaded \"" + t.name + "\" into the editor!")
      } catch (e) {
        showSnackbar(e?.message || "Failed to load theme.", "error")
      } finally {
        this.busy = false
      }
    },
    async removeTheme(t) {
      if (!this.canDelete(t)) return
      const kind = t?.type === "steering_wheel" ? "steering wheel" : "theme"
      const confirmed = await GalaxyConfirm({
        title: "Delete theme?",
        message: "Delete " + kind + " \"" + t.name + "\"? This cannot be undone.",
        confirmLabel: "Delete",
        danger: true,
      })
      if (!confirmed) return
      this.busy = true
      try {
        const res = await api.deleteTheme(t.path, t.type)
        showSnackbar(res?.message || "Theme deleted.")
        await this.refreshThemeList()
      } catch (e) {
        showSnackbar(e?.data?.error || e?.message || "Failed to delete theme.", "error")
      } finally {
        this.busy = false
      }
    },
    setStyle(s) {
      this.turnSignalStyle = s
      this.flags.turn_signals = true
    },
    onLengthBlur(e) {
      let v = parseInt(e.target.value, 10)
      if (isNaN(v)) v = 100
      this.turnSignalLength = Math.max(25, Math.min(1000, v))
      this.flags.turn_signals = true
    },
  },
  template: `
    <div class="gx-view">
      <h2 style="margin-top:0;">Theme Maker</h2>
      <p style="color:var(--text-muted); margin-top:0;">Customize the on-road colors and assets. Changes apply to the active on-device theme; saving keeps them as a named theme.</p>

      <GalaxySection title="Colors" icon="bi-palette">
        <div style="padding: var(--sp-3); display:grid; gap:14px;">
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
            <div v-for="key in colorKeys" :key="key" class="gx-card" style="margin:0; padding: var(--sp-2); display:flex; align-items:center; gap:10px;">
              <span style="width:22px; height:22px; border-radius:6px; flex:none; box-shadow: inset 0 0 0 1px rgba(255,255,255,.2);" :style="{ background: rgbaFor(key) }"></span>
              <div style="flex:1; min-width:0;">
                <div class="gx-row__label" style="font-size:var(--fs-xs);">{{ labels[key] }}</div>
                <div style="font-family:monospace; font-size:12px; opacity:.8;">{{ hexFor(key) }}</div>
              </div>
              <input type="color" style="width:44px; height:32px; border:0; background:transparent; padding:0; cursor:pointer;" :value="hexFor(key)" @input="onColorChange($event, key)" />
            </div>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:8px;">
            <button type="button" class="gx-btn gx-btn--tonal" @click="resetColors">Reset to Stock Green</button>
          </div>
        </div>
      </GalaxySection>

      <GalaxySection title="Distance Icons" icon="bi-sign-turn-left" :default-open="true">
        <div style="padding: var(--sp-3);">
          <p class="gx-note" style="margin:0 0 var(--sp-2);">Recommended size 250x250.</p>
          <div class="gx-tight-grid">
          <div v-for="k in ['traffic','aggressive','standard','relaxed']" :key="k" class="gx-row" style="border:none; background:var(--surface); min-height:0; padding:6px 10px;">
            <div style="flex:1; min-width:0;">
              <div class="gx-row__label">{{ k.charAt(0).toUpperCase() + k.slice(1) }}</div>
              <div class="gx-row__desc" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{{ names.distanceIcons[k] || 'No file selected' }}</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <label class="gx-btn gx-btn--tonal" style="margin:0; cursor:pointer;">Choose
                <input type="file" accept="image/*" style="display:none;" @change="onFileChoose($event, 'image', 'distanceIcons', k)" />
              </label>
              <button type="button" v-if="files.distanceIcons[k]" class="gx-icon-btn" style="color:var(--error);" title="Clear" @click="clearFile('image', 'distanceIcons', k)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
          </div>
        </div>
      </GalaxySection>

      <GalaxySection title="Icons" icon="bi-grid" :default-open="true">
        <div style="padding: var(--sp-3); display:grid; gap:10px;">
          <div class="gx-row" style="border-top:none; min-height:0; padding:6px 0;">
            <div style="flex:1; min-width:0;">
              <div class="gx-row__label">Home Button</div>
              <div class="gx-row__desc" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{{ names.homeButton || 'No file selected' }}</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <label class="gx-btn gx-btn--tonal" style="margin:0; cursor:pointer;">Choose
                <input type="file" accept="image/*" style="display:none;" @change="onFileChoose($event, 'image', 'homeButton')" />
              </label>
              <button type="button" v-if="files.homeButton" class="gx-icon-btn" style="color:var(--error);" title="Clear" @click="clearFile('image', 'homeButton')"><i class="bi bi-trash"></i></button>
            </div>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:6px 0;">
            <div style="flex:1; min-width:0;">
              <div class="gx-row__label">Settings Button</div>
              <div class="gx-row__desc" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{{ names.settingsButton || 'No file selected' }}</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <label class="gx-btn gx-btn--tonal" style="margin:0; cursor:pointer;">Choose
                <input type="file" accept="image/*" style="display:none;" @change="onFileChoose($event, 'image', 'settingsButton')" />
              </label>
              <button type="button" v-if="files.settingsButton" class="gx-icon-btn" style="color:var(--error);" title="Clear" @click="clearFile('image', 'settingsButton')"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
      </GalaxySection>

      <GalaxySection title="Sounds" icon="bi-volume-up" :default-open="true">
        <div style="padding: var(--sp-3);">
          <div class="gx-tight-grid">
          <div v-for="k in ['disengage','engage','prompt','startup']" :key="k" class="gx-row" style="border:none; background:var(--surface); min-height:0; padding:6px 10px;">
            <div style="flex:1; min-width:0;">
              <div class="gx-row__label">{{ soundLabels[k] }}</div>
              <div class="gx-row__desc" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{{ names.sounds[k] || 'No file selected' }}</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <label class="gx-btn gx-btn--tonal" style="margin:0; cursor:pointer;">Choose
                <input type="file" accept="audio/*" style="display:none;" @change="onFileChoose($event, 'audio', 'sounds', k)" />
              </label>
              <button type="button" v-if="files.sounds[k]" class="gx-icon-btn" style="color:var(--error);" title="Clear" @click="clearFile('audio', 'sounds', k)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
          </div>
        </div>
      </GalaxySection>

      <GalaxySection title="Steering Wheel" icon="bi-bicycle" :default-open="true">
        <div style="padding: var(--sp-3); display:grid; gap:10px;">
          <p style="margin:0 0 4px; color:var(--text-muted);">Recommended size 250x250.</p>
          <div class="gx-row" style="border-top:none; min-height:0; padding:6px 0;">
            <div style="flex:1; min-width:0;">
              <div class="gx-row__label">Steering Wheel Image</div>
              <div class="gx-row__desc" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{{ names.steeringWheel || 'No file selected' }}</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <label class="gx-btn gx-btn--tonal" style="margin:0; cursor:pointer;">Choose
                <input type="file" accept="image/*" style="display:none;" @change="onFileChoose($event, 'image', 'steeringWheel')" />
              </label>
              <button type="button" v-if="files.steeringWheel" class="gx-icon-btn" style="color:var(--error);" title="Clear" @click="clearFile('image', 'steeringWheel')"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
      </GalaxySection>

      <GalaxySection title="Turn Signals" icon="bi-arrow-left-right" :default-open="true">
        <div style="padding: var(--sp-3); display:grid; gap:12px;">
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Style</span>
            <span class="gx-row__value" style="display:flex; gap:6px;">
              <button type="button" class="gx-btn gx-btn--text" :style="turnSignalStyle === 'Static' ? 'background:var(--primary); color:var(--on-primary);' : ''" @click="setStyle('Static')">Static</button>
              <button type="button" class="gx-btn gx-btn--text" :style="turnSignalStyle === 'Traditional' ? 'background:var(--primary); color:var(--on-primary);' : ''" @click="setStyle('Traditional')">Traditional</button>
            </span>
          </div>
          <div class="gx-row" style="border-top:none; min-height:0; padding:4px 0;">
            <span class="gx-row__label">Length (25-1000ms)</span>
            <span class="gx-row__value">
              <input class="gx-field" type="number" style="width:110px; text-align:right;" :value="turnSignalLength" @input="turnSignalLength = $event.target.value" @blur="onLengthBlur" />
            </span>
          </div>
          <div v-for="f in [fileRow('turnSignal',null,'Turn Signal'), fileRow('turnSignalBlindspot',null,'Blind Spot')]" :key="f.label" class="gx-row" style="border-top:none; min-height:0; padding:6px 0;">
            <div style="flex:1; min-width:0;">
              <div class="gx-row__label">{{ f.label }}</div>
              <div class="gx-row__desc" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{{ f.name || 'No file selected' }}</div>
            </div>
            <div style="display:flex; gap:6px; align-items:center;">
              <label class="gx-btn gx-btn--tonal" style="margin:0; cursor:pointer;">Choose
                <input type="file" accept="image/*" style="display:none;" @change="onFileChoose($event, 'image', f.key)" />
              </label>
              <button type="button" v-if="files[f.key]" class="gx-icon-btn" style="color:var(--error);" title="Clear" @click="clearFile('image', f.key)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </div>
      </GalaxySection>

      <GalaxySection title="Save / Apply" icon="bi-save">
        <div style="padding: var(--sp-3); display:grid; gap:10px;">
          <label class="gx-row__label" style="font-size:var(--fs-xs);">Theme Name</label>
          <input class="gx-field gx-field--full" v-model="themeName" placeholder="Enter a name for this theme..." autocomplete="off" />
          <p style="margin:4px 0 0; color:var(--text-muted);">Select which components to include:</p>
          <div style="display:flex; flex-wrap:wrap; gap:8px;">
            <label v-for="s in sectionOptions" :key="s.key" class="gx-chip" style="cursor:pointer; user-select:none; gap:6px; display:inline-flex; align-items:center;">
              <input type="checkbox" style="accent-color:var(--primary);" :checked="flags[s.key]" @change="flags[s.key] = !flags[s.key]" />
              {{ s.label }}
            </label>
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; margin-top:8px;">
            <button type="button" class="gx-btn" :disabled="!canSave" @click="save">
              <i v-if="busy" class="bi bi-arrow-repeat gx-spin"></i>
              <i v-else class="bi bi-save"></i> Save Theme
            </button>
            <button type="button" class="gx-btn" :disabled="busy || !anyChecked" @click="apply"><i class="bi bi-check2-circle"></i> Apply Theme</button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy || !anyChecked" @click="exportTheme"><i class="bi bi-download"></i> Export (.zip)</button>
          </div>
        </div>
      </GalaxySection>

      <GalaxySection title="Theme Library" icon="bi-collection">
        <div style="padding: var(--sp-3);">
          <div v-if="loading" class="gx-loading">Loading themes...</div>
          <GxNotice v-else-if="loadedError" tone="danger" :text="loadedError" />
          <div v-else-if="!themes.length" class="gx-empty">No themes yet. Build one above and hit Save Theme.</div>
          <template v-else>
            <div class="gx-card-grid">
            <div v-for="t in themes" :key="t.type + ':' + t.path" class="gx-card" style="padding: var(--sp-3); display:flex; flex-direction:column; gap:10px;">
              <div style="flex:1; min-width:0;">
                <div style="font-weight:600; display:flex; align-items:center; gap:6px;">
                  {{ t.name }}
                  <i v-if="t.is_user_created" class="bi bi-star-fill" style="color:var(--warning); font-size:12px;"></i>
                  <span class="gx-chip" v-if="t.type === 'holiday'">Holiday</span>
                  <span class="gx-chip" v-else-if="t.type === 'steering_wheel'">Wheel</span>
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:6px;" v-if="compChips(t).length">
                  <span class="gx-chip" style="opacity:.85; font-size:11px;" v-for="c in compChips(t)" :key="c">{{ c }}</span>
                </div>
              </div>
              <div style="display:flex; gap:6px; flex:none;">
                <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="loadThemeToEditor(t)" title="Load into editor"><i class="bi bi-pencil"></i> Load</button>
                <button type="button" v-if="canDelete(t)" class="gx-icon-btn" style="color:var(--error);" title="Delete" @click="removeTheme(t)"><i class="bi bi-trash"></i></button>
              </div>
            </div>
            </div>
          </template>
        </div>
      </GalaxySection>
    </div>
  `,
}
