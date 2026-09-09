import { api, showSnackbar } from "../api.js"
import {
  coerceValueByType, formatNumericParamValue, formatReadoutValue, getColorDefault,
  normalizeHexColor, numericBounds, numericEpsilon, snapNumericToBoundsAndStep,
  resolveVehicleUnitParam, stepPrecision,
} from "../params.js"
import { FavoritesEditor } from "./FavoritesEditor.js"

export const GalaxyToggleCard = {
  name: "GalaxyToggleCard",
  components: { FavoritesEditor },
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
    normalizeHexColor,
    getColorDefault,
    coerce(v) { return coerceValueByType(v, this.param.data_type) },
    labelOf(el) { return el?.options?.[el.selectedIndex]?.textContent || "" },
    rollback(prev) { this.$emit("change", { key: this.param.key, value: prev }) },
    async commit(nextValue) {
      if (this.locked || this.updating) return
      const prev = this.value
      const label = this.lastLabel || ""
      this.$emit("change", { key: this.param.key, value: nextValue })
      this.updating = true
      try {
        const data = await api.updateParam({ key: this.param.key, value: nextValue, label })
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
    onSwitch(e) {
      if (!this.locked) this.commit(!!e.target.checked)
      else e.target.checked = !!this.value
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
    onSliderInput(e) {
      this.beginInteract()
      this.preview = Number(e.target.value)
    },
    onSliderCommit(e) {
      this.interacting = false
      this.flushSlider(e.target.value)
    },
    onSliderBlur(e) {
      if (this.interacting) this.onSliderCommit(e)
    },
    snap(raw) {
      return snapNumericToBoundsAndStep(raw, this.bounds, this.precision)
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
  template: `
    <div>
      <div class="gx-row" :class="{ disabled: locked, 'gx-row--favorites': isFavorites, 'gx-row--stack': isSlider || isSelect }">
        <div class="gx-row__info">
          <span class="gx-row__label">{{ displayParam.label }}
            <span v-if="displayParam.settings_tier === 'advanced'" class="gx-chip gx-chip--advanced">Advanced</span>
          </span>
          <span v-if="displayParam.description" class="gx-row__desc">{{ displayParam.description }}</span>
          <div v-if="locked" class="gx-row__desc"><strong>Locked:</strong> {{ lockMessage }}</div>
        </div>

        <label v-if="isSwitch" class="gx-switch">
          <input type="checkbox" :checked="!!value" :disabled="locked || updating" @change="onSwitch" />
          <span class="gx-switch__track"></span>
          <span class="gx-switch__thumb"></span>
        </label>

        <div v-else-if="isFavorites" style="width:100%;">
          <FavoritesEditor />
        </div>

        <div v-else-if="isSlider" class="gx-slider-row">
          <span class="gx-row__value" style="min-width:64px; text-align:right;">{{ sliderDisplay }}</span>
          <input type="range" class="gx-slider" :min="bounds.min" :max="bounds.max" :step="bounds.step"
            :value="currentValue" :disabled="locked || updating"
            @input="onSliderInput" @change="onSliderCommit" @blur="onSliderBlur"
            @touchstart="beginInteract" @mousedown="beginInteract" @keydown="beginInteract" />
          <div v-if="displayParam.unit_type" class="gx-slider-meta">
            <span>{{ sliderRangeDisplay }}</span>
            <span>Step: {{ sliderStepDisplay }}</span>
          </div>
          <button class="gx-slider-reset" :disabled="locked || updating" @click="resetToDefault">Default</button>
        </div>

        <select v-else-if="isSelect" class="gx-field" :disabled="locked || updating" :value="String(value ?? '')" @change="onSelect">
          <option v-if="optionsLoading" value="">Loading...</option>
          <option v-else-if="!selectOptions.length" value="">No options available</option>
          <option v-for="opt in selectOptions" :key="String(opt.value)" :value="String(opt.value)">{{ opt.label }}</option>
        </select>

        <input v-else-if="isText" class="gx-field" :type="param.input_type || 'text'" :value="value ?? ''"
          :placeholder="param.placeholder || ''" :disabled="locked || updating" @change="onText" />

        <div v-else-if="isColor" style="display:flex; align-items:center; gap:8px;">
          <span class="gx-row__value">{{ displayValue }}</span>
          <input type="color" class="gx-color" :value="normalizeHexColor(value) || getColorDefault(param)"
            :disabled="locked || updating" @change="onColor" />
          <button class="gx-slider-reset" :disabled="locked || updating || !normalizeHexColor(value)" @click="resetColor">Stock</button>
        </div>

        <span v-else-if="isReadout" class="gx-row__value">{{ displayValue }}</span>

        <button v-else-if="isAction" class="gx-btn" :disabled="locked || updating" @click="runAction">
          {{ updating ? "Working..." : (param.action_label || "Run") }}
        </button>

        <button v-else-if="isGroup" class="gx-btn gx-btn--tonal" @click="$emit('manage', param.key)">Manage</button>
      </div>
      <button v-if="manageable" type="button" class="gx-manage-btn" @click="$emit('manage', param.key)">
        {{ manageOpen ? "Close" : "Manage" }}
        <i class="bi" :class="manageOpen ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
      </button>
    </div>
  `,
}
