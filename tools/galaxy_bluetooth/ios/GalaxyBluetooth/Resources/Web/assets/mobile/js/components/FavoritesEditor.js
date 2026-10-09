import { api, showSnackbar } from "../api.js"
import { openControllerActionPicker } from "../../../components/tools/controller_action_picker.js"

const FAVORITE_COUNT = 3
const ACTION_PREFIX = "__starpilot_favorite_action__:"
const SET_SPEED = "__starpilot_controller_action__:set_speed"

function sortOptions(options) {
  return (options || []).slice().sort((a, b) =>
    String(a?.label || a?.key || "").localeCompare(String(b?.label || b?.key || ""), undefined, { numeric: true, sensitivity: "base" })
  )
}

function defaultSlots() {
  return [0, 1, 2].map(() => ({ enabled: false, show_onroad: false, key: null, label: "" }))
}

function normalizeSlots(slots) {
  const base = defaultSlots()
  if (!Array.isArray(slots)) return base
  slots.slice(0, FAVORITE_COUNT).forEach((slot, index) => {
    if (!slot || typeof slot !== "object") return
    const key = slot.key ? String(slot.key) : null
    base[index] = {
      enabled: !!slot.enabled,
      show_onroad: !!slot.show_onroad,
      key,
      ...(key === SET_SPEED ? { value: slot.value } : {}),
      label: key ? String(slot.label || key) : "",
    }
  })
  return base
}

export const FavoritesEditor = {
  name: "FavoritesEditor",
  data() {
    return {
      loading: true,
      saving: false,
      slots: [],
      savedSlots: [],
      options: [],
      values: {},
      isMetric: false,
    }
  },
  computed: {
    optionByKey() { return new Map(this.options.map((o) => [o.key, o])) },
    quickFavorites() {
      return this.slots
        .map((slot, index) => {
          const opt = this.optionByKey.get(slot.key || "")
          return { index, slot, opt, checked: !!(slot.key && opt && !!this.values[slot.key]) }
        })
        .filter((f) => f.slot.enabled && f.slot.key && f.opt)
    },
  },
  beforeUnmount() { this.closeActionPicker?.() },
  methods: {
    normalizeSlots,
    chooseControl(index, event) {
      this.closeActionPicker?.()
      this.closeActionPicker = openControllerActionPicker({
        theme: "dipper", index, trigger: event.currentTarget,
        title: `Favorite #${index + 1}`, slotAttribute: "data-favorite-control-slot", noun: "controls",
        getOptions: () => this.options, getSlot: () => this.slots[index],
        isDisabled: () => this.loading || this.saving,
        onSelect: key => this.updateSlot(index, { key: key || null }),
      })
    },
    isSpeedSlot(slot) { return slot.key === SET_SPEED },
    controlLabel(slot) {
      const label = this.optionByKey.get(slot.key)?.label || slot.label || slot.key || "Not configured"
      return this.isSpeedSlot(slot) ? `${label} ${slot.value ?? 30} ${this.isMetric ? 'km/h' : 'mph'}` : label
    },
    isActionSlot(slot) {
      const opt = this.optionByKey.get(slot.key || "")
      return String(slot.key || "").startsWith(ACTION_PREFIX) || !!opt?.action
    },
    async load() {
      this.loading = true
      try {
        const data = await api.getFavoritesSlots()
        this.options = sortOptions(data?.options)
        this.slots = normalizeSlots(data?.slots)
        this.savedSlots = normalizeSlots(data?.slots)
        this.values = { ...this.values, ...(data?.values || {}) }; this.isMetric = !!data?.is_metric
      } catch (e) {
        showSnackbar("Failed to load favorite slots.", "error")
      } finally {
        this.loading = false
      }
    },
    async saveSlots() {
      if (this.saving) return
      this.saving = true
      try {
        const data = await api.saveFavoritesSlots(this.slots)
        this.slots = normalizeSlots(data?.slots)
        this.savedSlots = normalizeSlots(data?.slots)
        if (Array.isArray(data?.options)) this.options = sortOptions(data.options)
        if (data?.values) this.values = { ...this.values, ...data.values }
        showSnackbar(data?.message || "Favorite slots saved.")
      } catch (e) {
        this.slots = normalizeSlots(this.savedSlots)
        showSnackbar(e?.message || "Failed to save favorite slots.", "error")
      } finally {
        this.saving = false
      }
    },
    updateSlot(index, patch) {
      if (this.saving) return
      const slots = this.slots.slice()
      slots[index] = { ...slots[index], ...patch }
      if (Object.hasOwn(patch, "key")) {
        if (patch.key === SET_SPEED) slots[index].value = slots[index].key === this.slots[index].key ? this.slots[index].value : 30
        else delete slots[index].value
      }
      if (!slots[index].key) {
        slots[index].label = ""
      } else {
        slots[index].label = this.optionByKey.get(slots[index].key)?.label || slots[index].key
      }
      this.slots = slots
      this.saveSlots()
    },
    async toggleValue(key, checked) {
      const previous = this.values[key]
      this.values = { ...this.values, [key]: checked }
      try {
        const data = await api.updateParam({ key, value: checked })
        if (data?.updated && typeof data.updated === "object") this.values = { ...this.values, ...data.updated }
        showSnackbar(data?.message || `Parameter '${key}' updated.`)
      } catch (e) {
        this.values = { ...this.values, [key]: previous }
        showSnackbar(e?.message || "Network error — is the device reachable?", "error")
      }
    },
    async runAction(key, value) {
      try {
        const data = await api.activateFavoriteAction(key, value)
        showSnackbar(data?.message || "Favorite action sent.")
      } catch (e) {
        showSnackbar(e?.message || "Failed to send favorite action.", "error")
      }
    },
  },
  async mounted() { await this.load() },
  template: `
    <div class="favorites-editor" style="display:grid; gap:var(--sp-3);">
      <div v-if="loading" class="gx-loading">Loading favorite slots...</div>

      <template v-else>
        <div v-if="quickFavorites.length" style="display:grid; gap:8px; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));">
          <div v-for="f in quickFavorites" :key="f.slot.key"
            style="display:flex; flex-direction:column; gap:4px; padding:var(--sp-2) var(--sp-3); border:1px solid var(--outline-variant); border-radius:var(--radius-md);">
            <small style="color:var(--text-muted);">Favorite #{{ f.index + 1 }}</small>
            <strong>{{ controlLabel(f.slot) }}</strong>
            <span style="color:var(--text-muted); font-size:var(--fs-sm);">{{ f.opt.section || '' }}</span>
            <button v-if="isActionSlot(f.slot)" type="button" class="gx-btn" :disabled="saving" @click.prevent="runAction(f.slot.key, f.slot.value)">
              Press
            </button>
            <label v-else class="gx-switch" style="align-self:flex-start;">
              <input type="checkbox" :checked="f.checked" :disabled="saving" @change="toggleValue(f.slot.key, $event.target.checked)" />
              <span class="gx-switch__track"></span>
              <span class="gx-switch__thumb"></span>
            </label>
          </div>
        </div>

        <div v-for="(slot, index) in slots" :key="index" class="gx-card">
          <div class="gx-section__header">
            <span class="gx-section__title">Favorite #{{ index + 1 }}</span>
            <label class="gx-switch">
              <input type="checkbox" :checked="slot.enabled" :disabled="saving" @change="updateSlot(index, { enabled: $event.target.checked })" />
              <span class="gx-switch__track"></span>
              <span class="gx-switch__thumb"></span>
            </label>
          </div>
          <div style="padding: var(--sp-3); display:grid; gap:12px;">
            <button type="button" class="gx-btn gx-btn--tonal" style="white-space:normal; height:auto; min-height:44px;"
              :data-favorite-control-slot="index" aria-haspopup="dialog" :disabled="saving" @click="chooseControl(index, $event)">
              {{ controlLabel(slot) }} · Choose control
            </button>
            <label v-if="isSpeedSlot(slot)" style="display:grid; gap:4px;">
              <span>Set speed ({{ isMetric ? 'km/h' : 'mph' }})</span>
              <input class="gx-field" type="number" :min="isMetric ? 8 : 5" :max="isMetric ? 145 : 90" step="1" :value="slot.value" :disabled="saving"
                :aria-label="'Favorite #' + (index + 1) + ' set speed'" @change="updateSlot(index, { value: Number($event.target.value) })" />
            </label>
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="flex:1; font-size:var(--fs-sm);">On-Road Button (C4: tap invisible third)</span>
              <label class="gx-switch">
                <input type="checkbox" :checked="slot.show_onroad" :disabled="saving || !slot.enabled || !slot.key" @change="updateSlot(index, { show_onroad: $event.target.checked })" />
                <span class="gx-switch__track"></span>
                <span class="gx-switch__thumb"></span>
              </label>
            </div>
          </div>
        </div>
      </template>
    </div>
  `,
}
