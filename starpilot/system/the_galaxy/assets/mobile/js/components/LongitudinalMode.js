import { LONGITUDINAL_MODE_KEY, LONGITUDINAL_MODES, validLongitudinalSnapshot } from "/assets/components/tools/longitudinal_mode.mjs"
import { SettingTree } from "./SettingTree.js"
import { isSettingVisible } from "../params.js"

// Selection is API readback, not the conditional controller's ExperimentalMode output.
export const LongitudinalMode = {
  name: "LongitudinalMode",
  components: { SettingTree },
  props: { section: { type: Object, required: true }, values: { type: Object, required: true } },
  emits: ["change"],
  data() { return { snapshot: null, pending: false, reading: false, expanded: {}, open: false, error: "", generation: 0, timer: null, disposed: false, modes: LONGITUDINAL_MODES } },
  computed: {
    mode() { return this.snapshot?.mode || "" },
    label() { return this.modes.find(m => m.value === this.mode)?.label || "Unavailable" },
    reason() { return this.snapshot?.locked ? this.snapshot.reason : this.snapshot ? "" : "Speed control state unavailable." },
    locked() { return this.pending || !this.snapshot || this.snapshot.locked },
    conditional() { return this.mode === "conditional_experimental" || this.mode === "conditional_chill" },
    description() { return this.section.params.find(p => p.key === LONGITUDINAL_MODE_KEY)?.description || "" },
    children() { return this.section.params.filter(p => p.longitudinal_mode === this.mode && isSettingVisible(this.section, p, this.values)) },
  },
  methods: {
    async request(init) {
      const response = await fetch("/api/longitudinal_mode", { cache: "no-store", ...init })
      const data = await response.json()
      if (!response.ok || !validLongitudinalSnapshot(data)) throw new Error(data.error || "Speed control state unavailable.")
      return data
    },
    async refresh() {
      if (this.pending || this.reading || this.disposed) return
      const generation = this.generation
      this.reading = true
      try {
        const snapshot = await this.request()
        if (!this.disposed && generation === this.generation) this.snapshot = snapshot
      } catch (_) {
        if (!this.disposed && generation === this.generation) this.snapshot = null
      } finally { this.reading = false }
    },
    async select(event) {
      const target = event.target.value
      event.target.value = this.mode
      if (this.locked || target === this.mode || !this.modes.some(m => m.value === target)) return
      ++this.generation // A pre-write GET may finish after this write; never publish it.
      this.pending = true
      this.error = ""
      try {
        const snapshot = await this.request({ method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode: target, expected: this.snapshot.values, acknowledged: true }) })
        if (!this.disposed) this.snapshot = snapshot
      } catch (error) {
        this.error = error.message
        // A failed HTTP response can follow a successful storage write. Reconcile,
        // rather than guessing that the old selection is still authoritative.
        try { this.snapshot = await this.request() } catch (_) { this.snapshot = null }
      } finally { this.pending = false }
    },
    childLock() { return this.pending ? "Speed control update in progress." : this.reason },
    manage(key) { this.expanded = { ...this.expanded, [key]: !this.expanded[key] } },
  },
  mounted() { this.refresh(); this.timer = setInterval(() => this.refresh(), 1500) },
  beforeUnmount() { this.disposed = true; ++this.generation; clearInterval(this.timer) },
  template: `
    <div class="gx-tree-node gx-longitudinal-mode">
      <div class="gx-row gx-row--stack" :class="{ disabled: locked }">
        <div class="gx-row__info">
          <label class="gx-row__label" for="gx-longitudinal-mode">Longitudinal control mode</label>
          <span id="gx-longitudinal-description" class="gx-row__desc">{{ description }}</span>
          <span v-if="reason" class="gx-row__desc" role="status">{{ reason }}</span>
          <span v-if="error" class="gx-row__desc" role="alert">{{ error }}</span>
        </div>
        <div class="gx-mode-select">
          <div class="gx-field gx-mode-select__label" aria-hidden="true"><span>{{ label }}</span><i class="bi bi-chevron-down"></i></div>
          <select id="gx-longitudinal-mode" :value="mode" :disabled="locked" aria-describedby="gx-longitudinal-description" @change="select">
            <option v-if="!snapshot" value="">Unavailable</option>
            <option v-for="m in modes" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
        </div>
      </div>
      <button v-if="conditional" type="button" class="gx-manage-btn" :aria-expanded="open" aria-controls="gx-longitudinal-children" @click="open = !open">
        {{ open ? 'Close' : 'Manage' }}<i class="bi" aria-hidden="true" :class="open ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
      </button>
      <div v-if="conditional && open" id="gx-longitudinal-children" class="gx-tree-children">
        <SettingTree :params="children" parent-key="LongitudinalControlMode" :depth="1" :values="values" :expanded="expanded" :lock-reason="childLock" @change="$emit('change', $event)" @manage="manage" />
      </div>
    </div>
  `,
}
