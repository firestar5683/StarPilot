import { api, showSnackbar } from "../api.js"

const FAVORITE_COUNT = 3
const ACTION_PREFIX = "__starpilot_favorite_action__:"

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
      actionPending: false,
      slots: [],
      options: [],
      values: {},
      filters: ["", "", ""],
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
  methods: {
    normalizeSlots,
    filteredOptions(index) {
      const q = (this.filters[index] || "").toLowerCase()
      return this.options.filter((o) =>
        !q || [o.label, o.key, o.section, o.description].some((v) => String(v || "").toLowerCase().includes(q))
      )
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
        this.values = { ...this.values, ...(data?.values || {}) }
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
        if (Array.isArray(data?.options)) this.options = sortOptions(data.options)
        if (data?.values) this.values = { ...this.values, ...data.values }
        showSnackbar(data?.message || "Favorite slots saved.")
      } catch (e) {
        showSnackbar(e?.message || "Failed to save favorite slots.", "error")
      } finally {
        this.saving = false
      }
    },
    updateSlot(index, patch) {
      const slots = this.slots.slice()
      slots[index] = { ...slots[index], ...patch }
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
    async runAction(key) {
      if (this.actionPending) return
      this.actionPending = true
      try {
        const data = await api.activateFavoriteAction(key)
        showSnackbar(data?.message || "Favorite action sent.")
      } catch (e) {
        showSnackbar(e?.message || "Failed to send favorite action.", "error")
      } finally {
        this.actionPending = false
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
            <strong>{{ f.opt.label || f.slot.key }}</strong>
            <span style="color:var(--text-muted); font-size:var(--fs-sm);">{{ f.opt.section || '' }}</span>
            <button v-if="isActionSlot(f.slot)" type="button" class="gx-btn" :disabled="saving || actionPending" @click.prevent="runAction(f.slot.key)">
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
            <label style="display:grid; gap:4px;">
              <span style="font-size:var(--fs-sm); color:var(--text-muted);">Search</span>
              <input class="gx-field" type="search" :value="filters[index] || ''" :disabled="saving" placeholder="Search toggles..." @input="filters = filters.map((f,i)=> i===index ? $event.target.value : f)" />
            </label>
            <label style="display:grid; gap:4px;">
              <span style="font-size:var(--fs-sm); color:var(--text-muted);">Toggle or action</span>
              <select class="gx-field" :value="slot.key || ''" :disabled="saving" @change="updateSlot(index, { key: $event.target.value || null })">
                <option value="">Select a toggle or action...</option>
                <option v-for="opt in filteredOptions(index)" :key="opt.key" :value="opt.key">{{ opt.label }}</option>
              </select>
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
