import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"
import { GalaxySection } from "../components/GalaxySection.js"

function slotIdOf(slot) {
  return String((slot && slot.id) || "").trim()
}

function isUnusedOf(slot) {
  const name = String((slot && slot.name) || "").trim().toLowerCase()
  return name === "unused" || name.startsWith("unused ")
}

function variantLabelsOf(slot) {
  if (!slot || typeof slot !== "object") return { A: "A" }
  const labels = {}
  const raw = slot.variantLabels
  if (raw && typeof raw === "object") {
    for (const [key, value] of Object.entries(raw)) {
      const mode = String(key || "").trim().toUpperCase()
      const label = String(value || "").trim()
      if (mode.length === 1 && /^[A-Z]$/.test(mode) && label) labels[mode] = label
    }
  }
  const aLabel = String(slot.aLabel || "").trim()
  const bLabel = String(slot.bLabel || "").trim()
  if (aLabel) labels.A = labels.A || aLabel
  if (bLabel) labels.B = labels.B || bLabel
  if (!labels.A) labels.A = "A"
  return Object.keys(labels).sort().reduce((acc, key) => {
    acc[key] = labels[key]
    return acc
  }, {})
}

function variantModesOf(slot) {
  return Object.keys(variantLabelsOf(slot))
}

function defaultModeOf(slot) {
  const modes = variantModesOf(slot)
  if (modes.includes("A")) return "A"
  return modes[0] || "A"
}

function modeLabelOf(slot, mode) {
  const labels = variantLabelsOf(slot)
  const m = String(mode || "").trim().toUpperCase()
  return labels[m] || m || "A"
}

export const TestingGround = {
  name: "TestingGround",
  props: { embedded: { type: Boolean, default: false } },
  components: { GalaxySection },
  data() {
    return { loading: true, busy: false, error: "", data: null, selectedSlot: "" }
  },
  created() {
    this.poll = usePolling(() => this.load(), { interval: 3000, enabled: () => !this.busy })
    this.poll.start()
  },
  beforeUnmount() { this.poll?.destroy() },
  computed: {
    slots() { return Array.isArray(this.data?.slots) ? this.data.slots : [] },
    selectableSlots() {
      const sel = Array.isArray(this.data?.selectableSlots) ? this.data.selectableSlots : []
      if (sel.length) return sel
      return this.slots.filter((slot) => !isUnusedOf(slot))
    },
    selectedSlotObj() {
      const id = String(this.selectedSlot || "").trim()
      if (!id) return null
      return this.slots.find((slot) => slotIdOf(slot) === id) || null
    },
    activeSlotObj() {
      const id = String(this.data?.activeSlot || "").trim()
      if (!id) return null
      return this.slots.find((slot) => slotIdOf(slot) === id) || null
    },
    activeModeLabel() {
      const data = this.data
      if (!data) return ""
      return String(data.activeVariantLabel || "").trim() || (this.activeSlotObj
        ? modeLabelOf(this.activeSlotObj, String(data.activeVariant || "").trim().toUpperCase() || "A")
        : String(data.activeVariant || "A"))
    },
    selectedModeDisplay() {
      const slot = this.selectedSlotObj
      if (!slot) return "Not active"
      const data = this.data
      if (String(data?.activeSlot || "").trim() === String(this.selectedSlot || "").trim()) {
        const activeMode = String(data?.activeVariant || "").trim().toUpperCase() || defaultModeOf(slot)
        return String(data?.activeVariantLabel || "").trim() || modeLabelOf(slot, activeMode)
      }
      return "Not active"
    },
    hasSelection() { return !!this.selectedSlotObj },
  },
  methods: {
    slotIdOf,
    isUnusedOf,
    variantModesOf,
    modeLabelOf,
    defaultModeOf,
    slotId(slot) { return slotIdOf(slot) },
    isActiveSlot(slot) {
      return !!slot && String(this.data?.activeSlot || "").trim() === slotIdOf(slot)
    },
    isModeActive(mode) {
      const m = String(mode || "").trim().toUpperCase()
      const data = this.data
      return String(data?.activeSlot || "").trim() === String(this.selectedSlot || "").trim()
        && String(data?.activeVariant || "").trim().toUpperCase() === m
    },
    onSelectSlot(event) {
      const value = String(event?.target?.value || "").trim()
      if (!value || this.busy) return
      this.selectedSlot = value
    },
    applyPayload(payload) {
      if (!payload || typeof payload !== "object") throw new Error("Failed to load testing grounds")
      this.data = payload
      this.error = ""
      const selectable = Array.isArray(payload.selectableSlots) ? payload.selectableSlots : []
      const current = String(this.selectedSlot || "").trim()
      const hasCurrent = selectable.some((slot) => slotIdOf(slot) === current)
      if (!hasCurrent) {
        const active = String(payload.activeSlot || "").trim()
        const hasActive = selectable.some((slot) => slotIdOf(slot) === active)
        this.selectedSlot = hasActive ? active : slotIdOf(selectable[0] || {})
      }
    },
    async load() {
      try {
        const payload = await api.getOptions("/api/testing_grounds")
        this.applyPayload(payload)
      } catch (e) {
        this.error = e?.message || "Failed to load testing grounds"
        throw e
      } finally {
        this.loading = false
      }
    },
    async applySelection(slotValue, mode, toast = true) {
      const normalizedSlot = String(slotValue || "").trim()
      const normalizedMode = String(mode || "").trim().toUpperCase()
      if (!normalizedSlot || !normalizedMode) return false
      this.busy = true
      try {
        const payload = await api.selectTestingGround({ slotId: normalizedSlot, variant: normalizedMode })
        this.applyPayload(payload)
        this.selectedSlot = normalizedSlot
        this.error = ""
        if (toast) {
          const selectedSlot = Array.isArray(payload.slots)
            ? payload.slots.find((slot) => slotIdOf(slot) === normalizedSlot)
            : null
          const selectedLabel = String(payload.activeVariantLabel || "").trim() || modeLabelOf(selectedSlot, normalizedMode)
          showSnackbar(payload.message || `Testing Ground ${normalizedSlot} set to ${selectedLabel}.`)
        }
        return true
      } catch (e) {
        const message = e?.message || "Failed to update testing ground mode"
        this.error = message
        if (toast) showSnackbar(message, "error")
        return false
      } finally {
        this.busy = false
      }
    },
    async selectMode(mode) {
      if (this.busy) return
      if (!this.selectedSlotObj) {
        showSnackbar("Select a testing ground first.", "error")
        return
      }
      await this.applySelection(slotIdOf(this.selectedSlotObj), mode, true)
    },
  },
  template: `
    <div>
      <h2 v-if="!embedded" style="margin-top:0;">Testing Ground</h2>
      <GalaxySection title="A/B Tuning Sandbox" icon="bi-sliders" :collapsible="false">
        <div style="padding: var(--sp-3);">
          <p class="gx-note" style="margin:0 0 var(--sp-3); line-height:1.6;">
            A/B Tuning Sandbox. If you don't know what this is, you probably shouldn't be here ;)
          </p>

          <div v-if="loading" class="gx-loading">Loading testing ground state...</div>

          <template v-if="!loading && data">
            <div v-if="error" class="gx-alert" style="border:none;">{{ error }}</div>

            <div v-if="!selectableSlots.length && !error" class="gx-empty">No active test slots.</div>

            <template v-if="selectableSlots.length">
              <div class="gx-section__header"><i class="bi bi-activity"></i><span class="gx-section__title">Status</span></div>
              <div class="gx-row"><span class="gx-row__label">Selected Slot</span><span class="gx-row__value">{{ selectedSlotObj?.name || 'Unknown' }}</span></div>
              <div class="gx-row"><span class="gx-row__label">Selected Mode</span><span class="gx-row__value">{{ selectedModeDisplay }}</span></div>
              <div class="gx-row"><span class="gx-row__label">Onroad</span><span class="gx-row__value">{{ data?.isOnroad ? 'Yes' : 'No' }}</span></div>
              <div class="gx-row"><span class="gx-row__label">Selectable Slots</span><span class="gx-row__value">{{ selectableSlots.length }}</span></div>

              <div class="gx-section__header" style="margin-top: var(--sp-3);">
                <i class="bi bi-grid-1x2"></i><span class="gx-section__title">Current Test Slots</span><span class="gx-chip">{{ selectableSlots.length }}</span>
              </div>
              <ul style="list-style:none; margin:0; padding: var(--sp-2) var(--sp-4); display:grid; gap:6px;">
                <li v-for="slot in selectableSlots" :key="slotId(slot)" class="gx-row"
                  style="border:none; min-height:0; padding:6px 10px;"
                  :style="isActiveSlot(slot) ? 'background:var(--primary-container); border-radius:var(--radius-md); color:var(--on-primary-container);' : ''">
                  <span class="gx-row__label" :style="isActiveSlot(slot) ? 'color:var(--on-primary-container);' : ''">{{ slotId(slot) }}. {{ slot.name }}</span>
                </li>
              </ul>

              <div class="gx-row" style="border-top:none;">
                <span class="gx-row__label">View Slot</span>
                <GalaxySelect class="gx-field" :value="selectedSlot" :disabled="busy" @change="onSelectSlot">
                  <option v-for="slot in selectableSlots" :key="slotId(slot)" :value="slotId(slot)">{{ slotId(slot) }}. {{ slot.name }}</option>
                </GalaxySelect>
              </div>
              <p class="gx-note">
                Only one Testing Ground can be active at a time. Switching slots only changes what you're viewing; the active test stays enabled until you explicitly choose another mode.
              </p>

              <template v-if="hasSelection">
                <div class="gx-section__header" style="margin-top: var(--sp-3);">
                  <i class="bi bi-bezier2"></i><span class="gx-section__title">{{ selectedSlotObj.name }}</span>
                  <span v-if="isActiveSlot(selectedSlotObj)" class="gx-chip" style="background:var(--primary);color:var(--on-primary);">Active</span>
                </div>
                <p v-if="selectedSlotObj.description" class="gx-note" style="margin:0 0 var(--sp-2);">{{ selectedSlotObj.description }}</p>
                <div class="gx-tabs" style="margin-bottom:0;">
                  <button v-for="mode in variantModesOf(selectedSlotObj)" :key="mode" type="button"
                    class="gx-tab" :class="{ active: isModeActive(mode) }" :disabled="busy"
                    @click="selectMode(mode)">
                    <i class="bi" :class="isModeActive(mode) ? 'bi-check2-circle' : 'bi-circle'"></i>
                    {{ mode }} · {{ modeLabelOf(selectedSlotObj, mode) }}
                  </button>
                </div>
                <p class="gx-note">
                  Selecting a mode sets {{ selectedSlotObj.name }} as the active Testing Ground.
                </p>
              </template>

              <div class="gx-section__header" style="margin-top: var(--sp-3);">
                <i class="bi bi-check2-circle"></i><span class="gx-section__title">Currently Active</span>
              </div>
              <div v-if="activeSlotObj" class="gx-row" style="border:none; background:var(--primary-container); border-radius:var(--radius-md); min-height:0; padding:8px 12px; margin:0 var(--sp-3) var(--sp-3);">
                <div class="gx-row__info"><span class="gx-row__label" style="color:var(--on-primary-container);">{{ activeSlotObj.id }}. {{ activeSlotObj.name }}</span></div>
                <span class="gx-row__value" style="color:var(--on-primary-container);">Mode {{ activeModeLabel }}</span>
              </div>
            </template>
          </template>

          <div v-if="!loading && !data && error" class="gx-alert" style="border:none;">{{ error }}</div>
        </div>
      </GalaxySection>
    </div>
  `,
}
