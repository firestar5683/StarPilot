import { api, showSnackbar } from "../api.js"
import { usePolling } from "../composables.js"
import { GxNotice } from "./GxNotice.js"

function address(device) { return String(device.address || "").toUpperCase() }

export const BluetoothPanel = {
  name: "BluetoothPanel",
  components: { GxNotice },
  data() {
    return {
      loading: true, busy: "", available: false, enabled: false, powered: false, discovering: false,
      offroad: false, selectedAudio: "", pairingAddress: "", devices: [], prompt: null, pairValue: "", error: "",
    }
  },
  created() { this.poll = usePolling(() => this.refresh(), { interval: 2000 }); this.poll.start() },
  beforeUnmount() { this.poll?.destroy() },
  computed: {
    known() { return this.devices.filter((d) => d.paired || d.trusted || d.connected) },
    availableDevices() { return this.devices.filter((d) => !d.paired && !d.trusted && !d.connected) },
  },
  methods: {
    address,
    async refresh() {
      try {
        const p = await api.getBluetoothStatus()
        this.available = !!p.available
        this.enabled = !!p.enabled
        this.powered = !!p.powered
        this.discovering = !!p.discovering
        this.offroad = !!p.offroad
        this.selectedAudio = String(p.selected_audio || "")
        this.pairingAddress = String(p.pairing_address || "")
        this.devices = Array.isArray(p.devices) ? p.devices : []
        this.prompt = p.prompt || null
        this.error = p.error || ""
      } catch (e) {
        this.available = false
        this.error = e?.message || "Bluetooth service unavailable"
      } finally {
        this.loading = false
      }
    },
    async request(operation, body = {}) {
      if (this.busy) return
      this.busy = operation
      try {
        await api.bluetoothOp(operation, body)
        this.error = ""
        await this.refresh()
      } catch (e) {
        this.error = e?.message || "Bluetooth operation failed"
      } finally {
        this.busy = ""
      }
    },
    pair(d) { this.request("pair", { address: d.address }) },
    connect(d) { this.request(d.connected ? "disconnect" : "connect", { address: d.address }) },
    forget(d) { this.request("forget", { address: d.address }) },
    audio(d) { const isSel = this.selectedAudio.toUpperCase() === address(d); this.request("select_audio", { address: isSel ? "" : d.address }) },
    testAudio(d) { this.request("test_audio", { address: d.address }) },
    respondPairing(accepted) {
      const prompt = this.prompt
      if (!prompt || this.busy === "pairing_response") return
      if (accepted && (prompt.kind === "pin" || prompt.kind === "passkey") && !this.pairValue.trim()) {
        this.error = "Enter the value to continue pairing."
        return
      }
      this.request("pairing_response", { prompt_id: prompt.id, accepted, value: this.pairValue.trim() })
    },
    isPairing(d) { return !!this.pairingAddress && this.pairingAddress.toUpperCase() === address(d) },
    statusOf(d) {
      if (this.isPairing(d)) return "Pairing…"
      if (d.connected) {
        const audioSel = this.selectedAudio.toUpperCase() === address(d)
        return audioSel ? "Connected · Audio output" : "Connected"
      }
      return d.paired ? "Saved" : "Ready to pair"
    },
    offroadDisabled() { return !this.offroad || !!this.busy },
    needsPairValue() { return this.prompt && (this.prompt.kind === "pin" || this.prompt.kind === "passkey") },
  },
  template: `
    <div>
      <div style="padding: var(--sp-3);">
        <div style="display:flex; align-items:center; gap:12px; justify-content:space-between;">
          <span>Bluetooth {{ enabled ? 'On' : 'Off' }}</span>
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="!available || offroadDisabled()" @click="request('power', { enabled: !enabled })">{{ enabled ? 'Turn Off' : 'Turn On' }}</button>
        </div>
        <GxNotice v-if="!offroad" text="Scanning, pairing, and forgetting devices are available offroad only." style="margin:0 0 var(--sp-2);" />
        <GxNotice v-if="error" tone="danger" :text="error" style="margin:0 0 var(--sp-2);" />

        <div v-if="prompt" class="gx-card" style="margin:12px 0; background:var(--surface-variant);">
          <div class="gx-section__header"><i class="bi bi-shield-check"></i><span class="gx-section__title">Pairing request · {{ prompt.name }}</span></div>
          <div style="padding: var(--sp-3);">
            <p style="color:var(--text-muted);">{{ prompt.kind === 'confirmation' ? 'Confirm the pairing request.' : prompt.kind === 'authorization' ? 'Allow this device to connect?' : prompt.kind === 'pin' ? 'Enter the PIN supplied by the device.' : 'Enter the device passkey.' }}</p>
            <input v-if="needsPairValue" v-model="pairValue" class="gx-field" style="width:100%;" inputmode="numeric" placeholder="Value" />
            <div v-if="!prompt.display_only" style="display:flex; gap:8px; margin-top:8px;">
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy==='pairing_response'" @click="respondPairing(false)">Cancel</button>
              <button type="button" class="gx-btn" :disabled="busy==='pairing_response'" @click="respondPairing(true)">Allow</button>
            </div>
          </div>
        </div>

        <div style="display:flex; gap:8px; margin:12px 0;">
          <button type="button" class="gx-btn" :disabled="!offroad || !enabled || offroadDisabled()" @click="request(discovering ? 'stop_scan' : 'scan')">{{ discovering ? 'Searching…' : 'Search for Devices' }}</button>
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="!!busy" @click="refresh"><i class="bi bi-arrow-clockwise"></i> Refresh</button>
        </div>

        <h4 style="margin:12px 0 8px;">My Devices</h4>
        <div v-if="!known.length" class="gx-empty" style="padding: var(--sp-2) 0;">No saved devices yet.</div>
        <div v-for="d in known" :key="d.address" class="gx-row" style="flex-wrap:wrap;">
          <div class="gx-row__info">
            <span class="gx-row__label">{{ d.name }} <span v-if="d.connected" class="gx-chip gx-chip--dev">Connected</span></span>
            <span class="gx-row__desc">{{ d.audio && d.controller ? 'Audio · Controller' : d.audio ? 'Audio' : d.controller ? 'Controller' : 'Bluetooth' }} · {{ statusOf(d) }}</span>
          </div>
          <div style="display:flex; gap:6px; flex-wrap:wrap;">
            <button v-if="d.paired || d.connected" type="button" class="gx-btn gx-btn--tonal" :disabled="!!busy" @click="connect(d)">{{ d.connected ? 'Disconnect' : 'Connect' }}</button>
            <button v-if="d.audio" type="button" class="gx-btn gx-btn--tonal" :disabled="!!busy" @click="audio(d)">{{ selectedAudio.toUpperCase() === address(d) ? 'Stop Using for Audio' : 'Use for Audio' }}</button>
            <button v-if="d.audio && d.connected" type="button" class="gx-btn gx-btn--tonal" :disabled="offroadDisabled()" @click="testAudio(d)">Test Audio</button>
            <button v-if="d.paired" type="button" class="gx-btn gx-btn--danger" :disabled="offroadDisabled()" @click="forget(d)"><i class="bi bi-trash"></i></button>
          </div>
        </div>

        <h4 style="margin:12px 0 8px;">Available Devices</h4>
        <div v-if="!availableDevices.length" class="gx-empty" style="padding: var(--sp-2) 0;">{{ discovering ? 'Searching for nearby devices…' : 'No nearby devices found.' }}</div>
        <div v-for="d in availableDevices" :key="d.address" class="gx-row">
          <div class="gx-row__info">
            <span class="gx-row__label">{{ d.name }}</span>
            <span class="gx-row__desc">{{ statusOf(d) }}</span>
          </div>
          <button type="button" class="gx-btn" :disabled="!offroad || !!busy || isPairing(d)" @click="pair(d)">{{ isPairing(d) ? 'Pairing…' : 'Pair' }}</button>
        </div>
      </div>
    </div>
  `,
}
