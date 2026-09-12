import { api, showSnackbar } from "../api.js"
import { t } from "../i18n.js"

function boundedInt(value, min, max, fallback) {
  if (value === undefined || value === null || value === "") return fallback
  const number = Number(value)
  return Number.isFinite(number) ? Math.min(max, Math.max(min, Math.round(number))) : fallback
}

export const ScreenBrightnessControl = {
  name: "ScreenBrightnessControl",
  props: {
    param: { type: Object, required: true },
    value: { default: undefined },
    values: { type: Object, default: () => ({}) },
    locked: { type: Boolean, default: false },
    lockMessage: { type: String, default: "This setting can only be changed while parked." },
  },
  emits: ["change"],
  data() {
    const brightness = boundedInt(this.value, 0, 101, 101)
    return {
      brightness,
      manual: brightness <= 100 ? brightness : boundedInt(this.values[`${this.param.key}Manual`], 0, 100, 100),
      offset: boundedInt(this.values[`${this.param.key}Offset`], -30, 30, 0),
      preview: null,
      interacting: false,
      updating: false,
    }
  },
  computed: {
    mode() { return this.brightness === 101 ? "auto" : "manual" },
    manualKey() { return `${this.param.key}Manual` },
    offsetKey() { return `${this.param.key}Offset` },
    savedManual() { return this.values[this.manualKey] },
    savedOffset() { return this.values[this.offsetKey] },
    controlId() { return `gx-${this.param.key}` },
    sliderValue() { return this.preview ?? (this.mode === "auto" ? this.offset : this.brightness) },
    sliderReadout() {
      return `${this.mode === "auto" && this.sliderValue > 0 ? "+" : ""}${this.sliderValue}%`
    },
  },
  watch: {
    value(value) {
      if (this.updating || this.interacting) return
      this.brightness = boundedInt(value, 0, 101, 101)
      if (this.brightness <= 100) this.manual = this.brightness
    },
    savedManual(value) {
      if (!this.updating && !this.interacting) this.manual = boundedInt(value, 0, 100, 100)
    },
    savedOffset(value) {
      if (!this.updating && (!this.interacting || this.mode !== "auto")) this.offset = boundedInt(value, -30, 30, 0)
    },
  },
  methods: {
    tr(key) { return t(key, key) },
    async commit(key, value) {
      if (this.locked || this.updating) return
      const previous = { brightness: this.brightness, manual: this.manual, offset: this.offset }
      const patch = { [key]: value }
      if (key === this.param.key) {
        this.brightness = value
        if (value <= 100) this.manual = value
        patch[this.manualKey] = this.manual
      } else {
        this.offset = value
      }
      this.updating = true
      this.$emit("change", patch)
      try {
        const data = await api.updateParam({ key, value })
        const updated = { ...patch, ...(data?.updated || {}) }
        if (this.param.key in updated) this.brightness = boundedInt(updated[this.param.key], 0, 101, 101)
        if (this.manualKey in updated) this.manual = boundedInt(updated[this.manualKey], 0, 100, 100)
        if (this.offsetKey in updated) this.offset = boundedInt(updated[this.offsetKey], -30, 30, 0)
        this.$emit("change", updated)
        showSnackbar(this.tr("Screen settings updated."))
      } catch (error) {
        Object.assign(this, previous)
        this.$emit("change", key === this.param.key
          ? { [this.param.key]: previous.brightness, [this.manualKey]: previous.manual }
          : { [this.offsetKey]: previous.offset })
        showSnackbar(error?.message || this.tr("Unable to save screen settings."), "error")
      } finally {
        // Let the parent's optimistic patch/readback settle before accepting prop updates.
        await this.$nextTick()
        this.updating = false
      }
    },
    async onModeChange(event) {
      const next = event.target.value === "auto" ? 101 : this.manual
      if (next !== this.brightness) await this.commit(this.param.key, next)
      event.target.value = this.mode
    },
    beginInteract() { if (!this.locked && !this.updating) this.interacting = true },
    onSliderInput(event) {
      if (this.locked || this.updating) return
      this.interacting = true
      this.preview = boundedInt(event.target.value, this.mode === "auto" ? -30 : 0, this.mode === "auto" ? 30 : 100, 0)
    },
    async onSliderCommit(event) {
      const auto = this.mode === "auto"
      const next = boundedInt(event.target.value, auto ? -30 : 0, auto ? 30 : 100, auto ? this.offset : this.brightness)
      this.preview = null
      this.interacting = false
      if (next !== (auto ? this.offset : this.brightness)) await this.commit(auto ? this.offsetKey : this.param.key, next)
      event.target.value = this.sliderValue
    },
    onSliderBlur(event) { if (this.interacting) this.onSliderCommit(event) },
    reset() { this.commit(this.mode === "auto" ? this.offsetKey : this.param.key, this.mode === "auto" ? 0 : 100) },
  },
  template: `
    <div class="gx-row gx-row--stack gx-brightness" :class="{ disabled: locked }">
      <div class="gx-row__info">
        <label class="gx-row__label" :for="controlId + '-mode'">{{ tr(param.label) }}</label>
        <span class="gx-row__desc">{{ tr(param.description) }}</span>
        <span v-if="locked" class="gx-row__desc">{{ tr(lockMessage) }}</span>
      </div>
      <select class="gx-field" :id="controlId + '-mode'" :value="mode" :disabled="locked || updating" @change="onModeChange">
        <option value="auto">{{ tr("Auto") }}</option>
        <option value="manual">{{ tr("Manual") }}</option>
      </select>
      <div class="gx-slider-row">
        <div class="gx-brightness__readout">
          <label :for="controlId + '-slider'">{{ mode === 'auto' ? tr("Auto brightness offset") : tr("Brightness") }}</label>
          <output class="gx-row__value" :for="controlId + '-slider'">{{ sliderReadout }}</output>
        </div>
        <input :id="controlId + '-slider'" type="range" class="gx-slider" :min="mode === 'auto' ? -30 : 0" :max="mode === 'auto' ? 30 : 100" step="1"
          :value="sliderValue" :aria-valuetext="sliderReadout" :disabled="locked || updating"
          @input="onSliderInput" @change="onSliderCommit" @blur="onSliderBlur"
          @touchstart="beginInteract" @mousedown="beginInteract" @keydown="beginInteract" />
        <div class="gx-slider-meta"><span>{{ mode === 'auto' ? '-30%' : '0%' }}</span><span>{{ mode === 'auto' ? '+30%' : '100%' }}</span></div>
        <span v-if="mode === 'auto'" class="gx-row__desc">{{ tr("Adjust automatic brightness by up to 30% of its normal level. 0% keeps it unchanged. Auto stays at least 5% while the screen is awake.") }}</span>
        <span v-else-if="brightness === 0" class="gx-row__desc">{{ tr("At 0%, the screen turns off.") }}</span>
        <button type="button" class="gx-slider-reset" :disabled="locked || updating" @click="reset">{{ mode === 'auto' ? tr("Reset offset") : tr("Default") }}</button>
      </div>
    </div>
  `,
}
