import { api } from "../api.js"
import { usePolling } from "../composables.js"
import { GxNotice } from "./GxNotice.js"

const FAVORITE_SLOT_COUNT = 3

export const WheelControls = {
  name: "WheelControls",
  components: { GxNotice },
  data() {
    return {
      loading: true, busy: "", available: false, offroad: false, learning: false,
      devices: [], mappings: [], slots: [], controllerSlots: [], controllerOptions: [],
      joystickDevice: "", learningSlot: null, remainingSeconds: 0, testing: false,
      disconnectControllersOffroad: false,
      lastTested: null, speedUnit: "mph", speedMinimum: 0, speedMaximum: 0, error: "",
    }
  },
  created() { this.poll = usePolling(() => this.refresh(), { interval: 750 }); this.poll.start() },
  beforeUnmount() { this.poll?.destroy() },
  methods: {
    async refresh() {
      try {
        const p = await api.getWheelControlsStatus()
        this.available = !!p.available
        this.offroad = !!p.offroad
        this.learning = !!p.learning
        this.devices = Array.isArray(p.devices) ? p.devices : []
        this.mappings = Array.isArray(p.mappings) ? p.mappings : []
        this.slots = Array.isArray(p.slots) ? p.slots : []
        this.controllerSlots = Array.isArray(p.controller_slots) ? p.controller_slots : []
        this.controllerOptions = Array.isArray(p.controller_options) ? p.controller_options : []
        this.disconnectControllersOffroad = !!p.disconnect_controllers_offroad
        this.joystickDevice = typeof p.joystick_device === "string" ? p.joystick_device : ""
        this.learningSlot = Number.isInteger(p.learning_slot) ? p.learning_slot : null
        this.remainingSeconds = Number.isFinite(Number(p.remaining_seconds)) ? Number(p.remaining_seconds) : 0
        this.testing = !!p.testing
        this.lastTested = p.last_tested && typeof p.last_tested === "object" ? p.last_tested : null
        this.speedUnit = String(p.speed_unit || "mph")
        this.speedMinimum = Number.isFinite(Number(p.speed_minimum)) ? Number(p.speed_minimum) : 0
        this.speedMaximum = Number.isFinite(Number(p.speed_maximum)) ? Number(p.speed_maximum) : 0
        this.error = ""
      } catch (e) {
        this.available = false
        this.error = e?.message || "Wheel controls are unavailable"
      } finally {
        this.loading = false
      }
    },
    async request(operation, body = {}) {
      if (this.busy) return
      this.busy = operation
      try {
        await api.wheelControlsOp(operation, body)
        this.error = ""
        await this.refresh()
      } catch (e) {
        this.error = e?.message || "Wheel control operation failed"
      } finally {
        this.busy = ""
      }
    },
    mappingsOf(slot) { return this.mappings.filter((m) => m.slot === slot) },
    actionSlotIndex(i) { return FAVORITE_SLOT_COUNT + i },
    learn(slot) { this.request(this.learningAt(slot) ? "cancel" : "learn", { slot }) },
    learningAt(slot) { return !!this.learning && this.learningSlot === slot },
    disabled() { return !this.offroad || !!this.busy },
    configured(slot) { return !!slot?.enabled && !!slot?.key },
    optionByKey(key) { return this.controllerOptions.find((o) => o.key === key) || null },
    isSpeedSlot(slot) { return this.optionByKey(slot?.key)?.value_type === "speed" },
    onActionSelect(i, e) {
      if (this.disabled()) return
      const key = String(e.target.value || "")
      const option = this.optionByKey(key)
      const value = option?.value_type === "speed"
        ? Number(this.controllerSlots[i]?.value ?? option.default_value ?? 30)
        : null
      this.request("action", { slot: i, key, value })
    },
    onSpeedChange(i, e) {
      if (this.disabled()) return
      const key = String(this.controllerSlots[i]?.key || "")
      const value = Number(e.target.value)
      if (!Number.isFinite(value)) return
      this.request("action", { slot: i, key, value })
    },
    listenLabel(slot) {
      if (!this.learningAt(slot)) return "Learn Button"
      const seconds = Math.max(0, Math.ceil(this.remainingSeconds))
      return seconds > 0 ? `Listening (${seconds}s)` : "Listening..."
    },
    deleteMapping(m) { this.request("delete", { id: m.id }) },
  },
  template: `
    <div>
      <div style="padding: var(--sp-3);">
        <GxNotice v-if="!offroad" text="Mappings can only be changed while offroad. Mapped buttons continue working onroad." style="margin:0 0 var(--sp-2);" />
        <GxNotice v-if="error" tone="danger" :text="error" style="margin:0 0 var(--sp-2);" />
        <p v-if="!loading && !available && !mappings.length" style="color: var(--text-muted);">The wheel control service is starting.</p>
        <div style="display:flex; gap:8px; margin-bottom:12px; flex-wrap:wrap;">
          <button type="button" class="gx-btn" :disabled="disabled() || !mappings.length" @click="request(testing ? 'test-stop' : 'test')">{{ testing ? 'Stop Testing' : 'Test Buttons' }}</button>
          <button type="button" class="gx-btn gx-btn--danger" :disabled="disabled() || !mappings.length" @click="request('clear')">Clear All</button>
        </div>
        <div class="gx-row" style="margin-bottom:12px;">
          <div class="gx-row__info">
            <span class="gx-row__label">Disconnect controllers when offroad</span>
            <span class="gx-row__desc">After two minutes offroad, paired controllers disconnect to save battery and reconnect when the car starts. Bluetooth and audio-only devices stay connected.</span>
          </div>
          <label class="gx-switch">
            <input type="checkbox" :checked="disconnectControllersOffroad" :disabled="disabled()"
              @change="request('offroad-disconnect', { enabled: $event.target.checked })" />
            <span class="gx-switch__track"></span>
            <span class="gx-switch__thumb"></span>
          </label>
        </div>
        <div v-if="testing && lastTested" style="margin-bottom:12px;">
          <span class="gx-chip" :style="lastTested.mapped ? 'background:var(--success);' : 'background:var(--error);'">{{ lastTested.mapped ? 'Successful' : 'Not mapped' }}</span>
          <p style="color:var(--text-muted); margin-top:6px;">{{ lastTested.event_name || ('Button ' + lastTested.event_code) }} on {{ lastTested.device_name || 'External input' }} {{ lastTested.mapped ? 'is mapped to slot ' + lastTested.slot : 'has no mapping' }}.</p>
        </div>

        <h4 style="margin:12px 0 8px;">Connected input devices</h4>
        <p style="color:var(--text-muted); margin:0 0 8px;">Favorite buttons are the default, with controller-only actions below. Only the selected gamepad controls Joystick Mode.</p>
        <div v-if="devices.length" style="display:grid; gap:8px;">
          <div v-for="d in devices" :key="d.device_id" class="gx-row" style="flex-wrap:wrap;">
            <div class="gx-row__info">
              <span class="gx-row__label">{{ d.name }}</span>
              <span class="gx-row__desc">{{ d.joystick_capable ? 'Buttons and joystick axes' : 'Buttons only' }}</span>
            </div>
            <button v-if="d.joystick_capable" type="button" class="gx-btn gx-btn--tonal" :disabled="disabled()"
              @click="request('joystick', { device_id: d.device_id, enabled: !(d.device_id === joystickDevice) })">
              {{ d.device_id === joystickDevice ? 'Enabled for Joystick Mode' : 'Enable for Joystick Mode' }}
            </button>
          </div>
        </div>
        <p v-else style="color:var(--text-muted); margin:0;">Connect or pair a controller, macropad, or keyboard.</p>

        <h4 style="margin:12px 0 8px;">On-screen Favorites</h4>
        <div style="display:grid; gap:8px;">
          <div v-for="(slot, i) in slots" :key="'fav'+i" class="gx-row" style="flex-wrap:wrap;">
            <div class="gx-row__info">
              <span class="gx-row__label">Favorite #{{ i + 1 }}</span>
              <span class="gx-row__desc">{{ configured(slot) ? (slot.label || slot.key) : 'Not configured' }}</span>
            </div>
            <button v-if="configured(slot)" type="button" class="gx-btn gx-btn--tonal" :disabled="disabled() || testing" @click="learn(i)">{{ listenLabel(i) }}</button>
            <span v-if="mappingsOf(i).length" class="gx-chip gx-chip--dev" v-for="m in mappingsOf(i)" :key="m.id || m.event_code" style="display:inline-flex; align-items:center; gap:4px;">{{ m.event_name || ('Button ' + m.event_code) }}<button type="button" class="gx-chip-x" :disabled="disabled() || testing" title="Remove mapping" @click="deleteMapping(m)"><i class="bi bi-x"></i></button></span>
          </div>
        </div>
        <p v-if="!configured(slots[0]) && !configured(slots[1]) && !configured(slots[2])" style="color:var(--text-muted); margin:0;">Choose and enable these slots in Toggles to map buttons to them.</p>

        <h4 style="margin:16px 0 8px;">Controller-only Actions</h4>
        <p style="color:var(--text-muted); margin:0 0 8px;">Ten additional actions for physical buttons. These never appear as on-screen Favorites.</p>
        <div style="display:grid; gap:8px; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));">
          <div v-for="(slot, i) in controllerSlots" :key="'act'+i" class="gx-card" style="padding:var(--sp-3); display:grid; gap:8px; margin:0;">
            <div class="gx-row" style="border:none; padding:0; flex-wrap:wrap;">
              <div class="gx-row__info">
                <span class="gx-row__label">Controller Action #{{ i + 1 }}</span>
                <span class="gx-row__desc">{{ slot.enabled ? (slot.label || 'Configured') : 'Not configured' }}</span>
              </div>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!slot.enabled || disabled() || testing" @click="learn(actionSlotIndex(i))">{{ listenLabel(actionSlotIndex(i)) }}</button>
            </div>
            <select class="gx-field gx-field--full" :value="String(slot.key || '')" :disabled="disabled()" @change="onActionSelect(i, $event)">
              <option value="">Not configured</option>
              <option v-for="opt in controllerOptions" :key="opt.key" :value="opt.key">{{ opt.label }}</option>
            </select>
            <div v-if="isSpeedSlot(slot)" class="gx-row" style="border:none; padding:0;">
              <div class="gx-row__info">
                <span class="gx-row__label">Set speed ({{ speedUnit }})</span>
              </div>
              <input class="gx-field" type="number" inputmode="decimal" style="min-width:90px;"
                :min="speedMinimum" :max="speedMaximum" step="1"
                :value="Number(slot.value ?? 30)" :disabled="disabled()" @change="onSpeedChange(i, $event)" />
            </div>
            <div v-if="learningAt(actionSlotIndex(i))" style="color:var(--text-muted); font-size:var(--fs-sm);">Press one button on your controller, macropad, or keyboard.</div>
            <div v-if="mappingsOf(actionSlotIndex(i)).length" style="display:flex; flex-wrap:wrap; gap:4px;">
              <span v-for="m in mappingsOf(actionSlotIndex(i))" :key="m.id || m.event_code" class="gx-chip gx-chip--dev" style="display:inline-flex; align-items:center; gap:4px;">{{ m.event_name || ('Button ' + m.event_code) }}<button type="button" class="gx-chip-x" :disabled="disabled() || testing" title="Remove mapping" @click="deleteMapping(m)"><i class="bi bi-x"></i></button></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
}
