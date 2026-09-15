import { api, showSnackbar } from "../api.js"
import {
  coerceValueByType, formatNumericParamValue, formatReadoutValue, getColorDefault,
  normalizeHexColor, numericBounds, numericEpsilon, snapNumericToBoundsAndStep,
  resolveVehicleUnitParam, stepPrecision,
} from "../params.js"
import { ScreenBrightnessControl } from "./ScreenBrightnessControl.js"
import { FavoritesEditor } from "./FavoritesEditor.js"
import { t } from "../i18n.js"

const PANDA_FIRMWARE_TOGGLE_KEYS = new Set(["IgnoreIgnitionLine", "RemoteStartBootsComma", "HKGRemoteStartBootsComma", "TeslaWakeOnCAN"])

const FINE_SCRUB_HOLD_MS = 300
const FINE_SCRUB_FACTOR = 5
const FINE_SCRUB_JITTER_PX = 4

export const GalaxyToggleCard = {
  name: "GalaxyToggleCard",
  components: { FavoritesEditor, ScreenBrightnessControl },
  props: {
    param: { type: Object, required: true },
    value: { default: undefined },
    values: { type: Object, default: () => ({}) },
    locked: { type: Boolean, default: false },
    lockMessage: { type: String, default: "This setting can only be changed while parked." },
    manageable: { type: Boolean, default: false },
    manageOpen: { type: Boolean, default: false },
  },
  emits: ["change", "manage"],
  data() {
    return {
      updating: false,
      endpointOptions: null,
      optionsLoaded: false,
      endpointLoading: false,
      preview: undefined,
      interacting: false,
      fineScrub: null,
      isFineScrubbing: false,
    }
  },
  computed: {
    displayParam() { return resolveVehicleUnitParam(this.param, this.values) },
    bounds() { return numericBounds(this.displayParam, this.values) },
    precision() { return stepPrecision(this.bounds.step, this.displayParam.precision) },
    epsilon() { return numericEpsilon(this.precision) },
    isSlider() { return this.isNumeric },
    isNumeric() { return this.param.ui_type === "numeric" },
    isReadout() { return this.param.ui_type === "readout" },
    isGroup() { return this.param.ui_type === "group" },
    currentValue() { return this.preview !== undefined ? this.preview : this.value },
    displayValue() {
      if (this.isColor) return normalizeHexColor(this.value) ? normalizeHexColor(this.value).toUpperCase() : "Stock"
      if (this.isReadout) return formatReadoutValue(this.displayParam, this.value)
      return this.value !== undefined && this.value !== null ? formatNumericParamValue(this.displayParam, this.value, this.values) : ".."
    },
    sliderDisplay() {
      return this.value !== undefined ? formatNumericParamValue(this.displayParam, this.currentValue, this.values) : ".."
    },
    sliderRangeDisplay() {
      return `${formatNumericParamValue(this.displayParam, this.bounds.min, this.values)} to ${formatNumericParamValue(this.displayParam, this.bounds.max, this.values)}`
    },
    sliderStepDisplay() {
      return formatNumericParamValue(this.displayParam, this.bounds.step, this.values)
    },
    isColor() { return this.param.ui_type === "color" },
    isAction() { return this.param.ui_type === "action" },
    isFavorites() { return this.param.ui_type === "favorites" },
    isText() { return this.param.ui_type === "text" },
    isSelect() { return this.param.ui_type === "dropdown" },
    isSwitch() { return !this.isNumeric && !this.isColor && !this.isAction && !this.isFavorites && !this.isGroup && !this.isReadout && !this.isSelect && !this.isText },
    selectOptions() {
      return this.param.options || this.endpointOptions || []
    },
    optionsLoading() {
      return Boolean(this.param.options_endpoint) && this.endpointLoading
    },
  },
  methods: {
    tr(key, fallback = key) { return t(key, fallback) },
    normalizeHexColor,
    getColorDefault,
    coerce(v) { return coerceValueByType(v, this.param.data_type) },
    labelOf(el) { return el?.options?.[el.selectedIndex]?.textContent || "" },
    rollback(prev) { this.$emit("change", { key: this.param.key, value: prev }) },
    async commit(nextValue) {
      if (this.locked || this.updating) return
      const firmwareToggle = PANDA_FIRMWARE_TOGGLE_KEYS.has(this.param.key)
      if (firmwareToggle && this.values.IsOnroad) return
      if (firmwareToggle && !window.confirm(`${this.param.label} requires a Panda firmware update and device reboot.\n\n${nextValue ? "Enable" : "Disable"} ${this.param.label} and flash the Panda now?`)) {
        this.rollback(this.value)
        return
      }
      const prev = this.value
      const label = this.lastLabel || ""
      this.$emit("change", { key: this.param.key, value: nextValue })
      this.updating = true
      try {
        const data = await api.updateParam({ key: this.param.key, value: nextValue, label, ...(firmwareToggle ? { confirmedPandaFirmwareFlash: true } : {}) })
        const updated = data?.updated && typeof data.updated === "object" ? data.updated : {}
        if (Object.prototype.hasOwnProperty.call(updated, this.param.key)) {
          this.$emit("change", { key: this.param.key, value: updated[this.param.key], ...updated })
        }
        showSnackbar(data?.message || `Parameter '${this.param.key}' updated.`)
      } catch (err) {
        this.rollback(prev)
        showSnackbar(err?.message || "Network error — is the device reachable?", "error")
      } finally {
        this.updating = false
      }
    },
    async onSwitch(e) {
      if (!this.locked) await this.commit(!!e.target.checked)
      e.target.checked = !!this.value
    },
    onSelect(e) {
      if (this.locked) { e.target.value = String(this.value ?? "") ; return }
      this.lastLabel = e.target.options?.[e.target.selectedIndex]?.textContent || ""
      this.commit(this.coerce(e.target.value))
    },
    onText(e) {
      if (!this.locked) this.commit(this.coerce(e.target.value))
    },
    onColor(e) {
      if (this.locked) return
      this.commit(normalizeHexColor(e.target.value) || getColorDefault(this.param))
    },
    beginInteract() { this.interacting = true },
    flushSlider(rawValue) {
      const next = snapNumericToBoundsAndStep(rawValue, this.bounds, this.precision)
      this.preview = undefined
      if (next === null) return
      const current = this.snap(this.value)
      if (Math.abs(next - current) <= this.epsilon) return
      this.commit(next)
    },
    snap(raw) {
      return snapNumericToBoundsAndStep(raw, this.bounds, this.precision)
    },
    clearHoldTimer() {
      if (this._holdTimer) {
        clearTimeout(this._holdTimer)
        this._holdTimer = null
      }
    },
    startHoldTimer() {
      this.clearHoldTimer()
      if (!this.fineScrub || this.fineScrub.active) return
      this._holdTimer = setTimeout(() => {
        this.activateFineScrub()
      }, FINE_SCRUB_HOLD_MS)
    },
    activateFineScrub() {
      if (!this.fineScrub || this.fineScrub.active) return
      this.fineScrub.active = true
      this.fineScrub.baseValue = this.snap(this.currentValue) ?? Number(this.bounds.min)
      this.fineScrub.baseX = this.fineScrub.lastX
      this.isFineScrubbing = true
      try { navigator.vibrate?.(15) } catch (_) {}
    },
    onSliderInput(e) {
      if (this.fineScrub?.active) {
        if (this.$refs.slider) this.$refs.slider.value = this.currentValue
        return
      }
      this.beginInteract()
      this.preview = Number(e.target.value)
      this.startHoldTimer()
    },
    onSliderCommit(e) {
      if (this.fineScrub?.active) return
      this.interacting = false
      this.flushSlider(e.target.value)
    },
    onSliderBlur(e) {
      if (this.interacting && !this.fineScrub) this.onSliderCommit(e)
    },
    onSliderPointerDown(e) {
      this.beginInteract()
      try { e.target.setPointerCapture?.(e.pointerId) } catch (err) {}
      const rect = e.target.getBoundingClientRect()
      this.fineScrub = {
        active: false,
        baseValue: this.snap(this.currentValue) ?? Number(this.bounds.min),
        baseX: e.clientX,
        lastX: e.clientX,
        min: Number(this.bounds.min),
        max: Number(this.bounds.max),
        track: rect.width || 200,
        pointerId: e.pointerId,
      }
      this.startHoldTimer()
    },
    onSliderPointerMove(e) {
      const scrub = this.fineScrub
      if (!scrub) return

      if (!scrub.active) {
        if (Math.abs(e.clientX - scrub.lastX) > FINE_SCRUB_JITTER_PX) {
          scrub.lastX = e.clientX
          this.startHoldTimer()
        }
        return
      }

      e.preventDefault()
      if (!Number.isFinite(scrub.min) || !Number.isFinite(scrub.max) || !Number.isFinite(scrub.track) || scrub.track <= 0) return
      const totalSpan = scrub.max - scrub.min
      const dx = e.clientX - scrub.baseX
      const raw = scrub.baseValue + (dx * totalSpan) / scrub.track / FINE_SCRUB_FACTOR
      const next = this.snap(raw)
      if (next === null) return
      this.preview = next
      if (this.$refs.slider) this.$refs.slider.value = next
    },
    onSliderPointerEnd(e) {
      this.clearHoldTimer()
      const wasFine = this.isFineScrubbing
      this.fineScrub = null
      this.isFineScrubbing = false
      try { e.target.releasePointerCapture?.(e.pointerId) } catch (_) {}
      this.interacting = false
      if (wasFine || this.preview !== undefined) {
        this.flushSlider(this.currentValue)
      }
    },
    async resetToDefault() {
      const defaults = await api.getDefaults()
      const stockKey = `${this.param.key}Stock`
      const stock = defaults?.[stockKey]
      const raw = stock !== undefined && stock !== null ? stock : defaults?.[this.param.key]
      const next = this.snap(raw)
      if (next === null) { showSnackbar("No default value available for this setting.", "error"); return }
      if (Math.abs(next - (this.snap(this.value) ?? 0)) <= this.epsilon) return
      this.commit(next)
    },
    resetColor() {
      if (normalizeHexColor(this.value) === "") return
      this.commit("stock")
    },
    runAction() {
      if (this.locked || this.updating) return
      this.updating = true
      api.postAction(String(this.param.action_endpoint || ""))
        .then((data) => {
          if (!data?.error) {
            showSnackbar(data?.message || `${this.param.label || this.param.key} completed.`)
            if (data?.updated && typeof data.updated === "object") this.$emit("change", data.updated)
          } else {
            showSnackbar(data.error, "error")
          }
        })
        .catch(() => showSnackbar(`${this.param.label || this.param.key} failed.`, "error"))
        .finally(() => { this.updating = false })
    },
    loadEndpointOptions() {
      if (!this.param.options_endpoint || this.optionsLoaded) return
      this.optionsLoaded = true
      this.endpointLoading = true
      api.getOptions(this.param.options_endpoint)
        .then((opts) => { this.endpointOptions = opts })
        .catch(() => { this.endpointOptions = [] })
        .finally(() => { this.endpointLoading = false })
    },
  },
  mounted() {
    if (this.param.options_endpoint) this.loadEndpointOptions()
  },
  unmounted() {
    this.clearHoldTimer()
  },
  template: `
    <ScreenBrightnessControl v-if="param.ui_type === 'brightness'" :param="param" :value="value" :values="values"
      :locked="locked" :lock-message="lockMessage" @change="$emit('change', $event)" />
    <div v-else>
      <div class="gx-row" :class="{ disabled: locked, 'gx-row--favorites': isFavorites, 'gx-row--stack': isSlider || isSelect }">
        <div class="gx-row__info">
          <span class="gx-row__label">{{ tr(displayParam.label, displayParam.label) }}
            <span v-if="displayParam.settings_tier === 'advanced'" class="gx-chip gx-chip--advanced">{{ tr("Advanced") }}</span>
          </span>
          <span v-if="displayParam.description" class="gx-row__desc">{{ tr(displayParam.description, displayParam.description) }}</span>
          <div v-if="locked" class="gx-row__desc"><strong>{{ tr("Locked:") }}</strong> {{ tr(lockMessage, lockMessage) }}</div>
        </div>

        <label v-if="isSwitch" class="gx-switch">
          <input type="checkbox" :checked="!!value" :disabled="locked || updating" @change="onSwitch" />
          <span class="gx-switch__track"></span>
          <span class="gx-switch__thumb"></span>
        </label>

        <div v-else-if="isFavorites" style="width:100%;">
          <FavoritesEditor />
        </div>

        <div v-else-if="isSlider" class="gx-slider-row" :class="{ 'is-fine-scrubbing': isFineScrubbing }">
          <div class="gx-slider-header" style="display:flex; justify-content:space-between; align-items:center; width:100%;">
            <div style="display:flex; align-items:baseline; gap:8px;">
              <span class="gx-row__value">{{ sliderDisplay }}</span>
              <span v-if="interacting" class="gx-slider-hint" style="font-size:0.75rem; opacity:0.6; user-select:none;">
                {{ isFineScrubbing ? tr("Fine scrubbing") : tr("Hold to fine scrub") }}
              </span>
            </div>
            <button class="gx-slider-reset" :disabled="locked || updating" @click="resetToDefault">{{ tr("Default") }}</button>
          </div>
          <input ref="slider" type="range" class="gx-slider" :min="bounds.min" :max="bounds.max" :step="bounds.step"
            :value="currentValue" :disabled="locked || updating"
            @input="onSliderInput" @change="onSliderCommit" @blur="onSliderBlur"
            @pointerdown="onSliderPointerDown" @pointermove="onSliderPointerMove"
            @pointerup="onSliderPointerEnd" @pointercancel="onSliderPointerEnd"
            @touchstart="beginInteract" @mousedown="beginInteract" @keydown="beginInteract" />
          <div v-if="displayParam.unit_type" class="gx-slider-meta">
            <span>{{ sliderRangeDisplay }}</span>
            <span>{{ tr("Step:") }} {{ sliderStepDisplay }}</span>
          </div>
        </div>

        <GalaxySelect v-else-if="isSelect" class="gx-field" :disabled="locked || updating" :value="String(value ?? '')" @change="onSelect">
          <option v-if="optionsLoading" value="">{{ tr("Loading...") }}</option>
          <option v-else-if="!selectOptions.length" value="">{{ tr("No options available") }}</option>
          <option v-for="opt in selectOptions" :key="String(opt.value)" :value="String(opt.value)">{{ tr(opt.label, opt.label) }}</option>
        </GalaxySelect>

        <input v-else-if="isText" class="gx-field" :type="param.input_type || 'text'" :value="value ?? ''"
          :placeholder="param.placeholder || ''" :disabled="locked || updating" @change="onText" />

        <div v-else-if="isColor" style="display:flex; align-items:center; gap:8px;">
          <span class="gx-row__value">{{ displayValue }}</span>
          <input type="color" class="gx-color" :value="normalizeHexColor(value) || getColorDefault(param)"
            :disabled="locked || updating" @change="onColor" />
          <button class="gx-slider-reset" :disabled="locked || updating || !normalizeHexColor(value)" @click="resetColor">{{ tr("Stock") }}</button>
        </div>

        <span v-else-if="isReadout" class="gx-row__value">{{ displayValue }}</span>

        <button v-else-if="isAction" class="gx-btn" :disabled="locked || updating" @click="runAction">
          {{ updating ? tr("Working...") : tr(param.action_label || "Run", param.action_label || "Run") }}
        </button>

        <button v-else-if="isGroup" class="gx-btn gx-btn--tonal" @click="$emit('manage', param.key)">{{ tr("Manage") }}</button>
      </div>
      <button v-if="manageable" type="button" class="gx-manage-btn" @click="$emit('manage', param.key)">
        {{ manageOpen ? tr("Close") : tr("Manage") }}
        <i class="bi" :class="manageOpen ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
      </button>
    </div>
  `,
}
