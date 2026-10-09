import { GxState } from "./state.js"
import { GxNotice } from "./notice.js"
import { connectionError } from "./polling.js"
import { ControllersPage } from "./controllers.js"
import { BluetoothDeviceList } from "./bluetooth-devices.js"

const ADDRESS = /^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$/
const OPERATIONS = new Set(["power", "scan", "stop_scan", "connect", "disconnect", "forget", "pair", "pairing_response", "cancel_pair"])
const PAIR_STATES = new Set(["pairing", "paired", "failed", "canceled"])
const BLUETOOTH_ERRORS = {
  radio_unavailable: "Bluetooth radio support is unavailable on this device.",
  adapter_unavailable: "No Bluetooth adapter was detected. Turn Bluetooth on, then refresh.",
  service_unavailable: "The device's Bluetooth service could not be reached. Refresh to reconnect.",
  radio_preference_unavailable: "The Bluetooth power setting could not be read. Try again after restarting the device.",
  busy: "Bluetooth is being used by another operation. Finish pairing or stop searching, then try again.",
  park_required: "Park before changing Bluetooth connections.",
  session_expired: "The pairing session expired. Refresh and start pairing again.",
  changed: "The Bluetooth device or pairing request changed. Refresh and try again.",
}
export const bluetoothError = (code) => BLUETOOTH_ERRORS[code] || "Bluetooth could not complete the request. Refresh to try again."
const PROMPT_KINDS = new Set(["pin", "passkey", "confirmation", "authorization", "display_pin", "display_passkey"])

export function validPairInput(prompt, value) {
  if (prompt?.kind === "pin") return /^[\x20-\x7E]{1,16}$/.test(value)
  if (prompt?.kind === "passkey") return /^[0-9]{1,6}$/.test(value)
  return ["confirmation", "authorization"].includes(prompt?.kind)
}

function validPairing(value) {
  if (value === null) return true
  const prompt = value?.prompt
  return ADDRESS.test(value?.address) && PAIR_STATES.has(value?.state) &&
    (prompt === null || (typeof prompt === "object" && /^[0-9a-f]{32}$/.test(prompt.id) &&
      PROMPT_KINDS.has(prompt.kind) && typeof prompt.value === "string" && prompt.value.length <= 16 &&
      typeof prompt.displayOnly === "boolean"))
}

export function validBluetoothStatus(value) {
  return value?.version === 1 && typeof value.available === "boolean" && typeof value.parked === "boolean" &&
    typeof value.powered === "boolean" && typeof value.discovering === "boolean" &&
    (value.errorCode === null || ["radio_unavailable", "adapter_unavailable", "service_unavailable", "radio_preference_unavailable"].includes(value.errorCode)) &&
    validPairing(value.pairing ?? null) && Array.isArray(value.devices) && value.devices.length <= 64 && value.devices.every((device) =>
      ADDRESS.test(device?.address) && typeof device.name === "string" && device.name.length <= 80 &&
      [device.paired, device.connected, device.trusted].every((flag) => typeof flag === "boolean"))
}

export class BluetoothFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, later, cancelTimer })
    this.active = false
    this.generation = 0
    this.request = null
    this.timer = null
    this.pollTimer = null
    this.busy = false
    this.status = null
    this.deviceList = new BluetoothDeviceList()
    this.error = ""
  }

  emit() { this.publish({ status: this.status, busy: this.busy, error: this.error }) }
  stop(cancelPair = false) {
    if (cancelPair && this.active && this.status?.pairing?.state === "pairing") {
      this.fetcher("./api/bluetooth/action", { method: "POST", credentials: "same-origin", keepalive: true,
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ operation: "cancel_pair" }) }).catch(() => {})
    }
    this.active = false
    this.generation++
    this.request?.abort()
    if (this.timer !== null) this.cancelTimer(this.timer)
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    this.request = this.timer = this.pollTimer = null
    this.busy = false
    this.status = null
    this.deviceList.reset()
    this.error = ""
    this.emit()
  }
  start() { this.stop(); this.active = true; return this.refresh() }

  retire(generation, request) {
    if (!this.active || this.generation !== generation || this.request !== request) return false
    if (this.timer !== null) this.cancelTimer(this.timer)
    this.timer = null
    this.request = null
    this.busy = false
    if (this.pollTimer === null) this.pollTimer = this.later(() => this.refresh(), 2000)
    this.emit()
    return true
  }

  async run(url, options, timeout, background = false) {
    if (!this.active || this.busy || background && this.request !== null) return null
    if (!background) {
      // The user action supersedes any in-flight poll, including its JSON body.
      this.generation++
      this.request?.abort()
      if (this.timer !== null) this.cancelTimer(this.timer)
      if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
      this.request = this.timer = this.pollTimer = null
    }
    const generation = this.generation
    const request = new AbortController()
    this.request = request
    if (!background) { this.busy = true; this.emit() }
    this.timer = this.later(() => {
      if (!this.retire(generation, request)) return
      request.abort()
      this.generation++
      this.error = "Bluetooth took too long to respond. Refresh to check its current state."
      this.emit()
    }, timeout)
    try {
      const response = await this.fetcher(url, { ...options, signal: request.signal, credentials: "same-origin", cache: "no-store" })
      if (!this.active || this.generation !== generation || this.request !== request || request.signal.aborted) return null
      if (response.status === 401) { this.stop(); this.unauthorized(); return null }
      const data = await response.json().catch(() => { throw new Error("Galaxy could not reach Bluetooth. Refresh to reconnect.") })
      if (!this.active || this.generation !== generation || this.request !== request || request.signal.aborted) return null
      if (response.status === 503 && ["setup_required", "access_unavailable"].includes(data?.code)) {
        this.stop(); this.unauthorized(); return null
      }
      if (!response.ok) throw new Error(bluetoothError(data?.code))
      if (!validBluetoothStatus(data)) throw new Error("Galaxy received an invalid Bluetooth response. Refresh to reconnect.")
      this.status = { ...data, devices: this.deviceList.update(data.devices) }
      this.error = ""
      return data
    } catch (error) {
      if (this.active && this.generation === generation && this.request === request) {
        this.error = connectionError(error)
      }
      return null
    } finally {
      this.retire(generation, request)
    }
  }

  async refresh() {
    if (!this.active || this.busy || this.request !== null) return
    if (this.pollTimer !== null) { this.cancelTimer(this.pollTimer); this.pollTimer = null }
    await this.run("./api/bluetooth/status", {}, 12000, true)
  }

  async action(operation, fields = {}) {
    if (!OPERATIONS.has(operation) || !this.active || this.busy || (operation === 'power' && !this.status?.parked)) return
    const payload = { operation, ...fields }
    const result = await this.run("./api/bluetooth/action", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    }, operation === "power" ? 35000 : ["connect", "disconnect"].includes(operation) ? 30000 : 15000)
    if (result) await this.refresh()
  }
}

export const BluetoothPage = {
  components: { GxState, GxNotice, ControllersPage },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ status: null, busy: false, error: "", pairValue: "" }),
  mounted() {
    this.feed = new BluetoothFeed({ publish: (value) => Object.assign(this, value), unauthorized: this.unauthorized })
    this.visibility = () => document.hidden ? this.feed.stop(true) : this.feed.start()
    document.addEventListener("visibilitychange", this.visibility)
    if (this.mode === "local" && !document.hidden) this.feed.start()
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibility); this.feed?.stop(true) },
  watch: {
    mode(value) { if (value === "local" && !document.hidden) this.feed?.start(); else this.feed?.stop(true) },
    'status.pairing.prompt.id'() { this.pairValue = "" },
  },
  computed: {
    saved() { return this.status?.devices?.filter((device) => device.paired || device.trusted || device.connected) || [] },
    nearby() { return this.status?.devices?.filter((device) => !device.paired && !device.trusted && !device.connected) || [] },
    canAllowPair() { return validPairInput(this.status?.pairing?.prompt, this.pairValue) },
  },
  methods: {
    bluetoothError,
    refresh() { return this.feed.refresh() },
    action(operation, fields) { return this.feed.action(operation, fields) },
    respond(accepted) {
      const prompt = this.status?.pairing?.prompt
      if (!prompt || prompt.displayOnly || accepted && !validPairInput(prompt, this.pairValue)) return
      const value = accepted && ["pin", "passkey"].includes(prompt.kind) ? this.pairValue : ""
      return this.action("pairing_response", { promptId: prompt.id, accepted, value })
    },
  },
  template: `
    <section class="gx-driving" aria-label="Bluetooth" :inert="busy" :aria-busy="busy || undefined">
      <header class="gx-settings__header gx-page-header"><div><h2>Bluetooth</h2>
        <p>View, pair and manage nearby and saved devices.</p></div></header>
      <GxState v-if="mode !== 'local'">Bluetooth requires the device. No radio was checked in preview.</GxState>
      <template v-else>
        <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
        <GxState v-if="!status && !error" loading>Checking Bluetooth…</GxState>
        <template v-else-if="status">
          <div class="gx-card gx-driving__intro"><h3>Adapter {{ status.powered ? 'On' : 'Off' }}</h3>
            <p v-if="status.errorCode">{{ bluetoothError(status.errorCode) }}</p>
            <p v-else-if="!status.parked">Park to restart the Bluetooth radio.</p>
            <div class="gx-driving__actions gx-actions"><button class="gx-btn" :disabled="!status.parked || !status.available" @click="action('power', {enabled: !status.powered})">Turn {{ status.powered ? 'Off' : 'On' }}</button>

              <button class="gx-btn gx-btn--tonal" :disabled="!status.powered" @click="action(status.discovering ? 'stop_scan' : 'scan')">{{ status.discovering ? 'Stop Search' : 'Search' }}</button></div></div>
          <div v-if="status.pairing" class="gx-card gx-driving__intro" role="status"><h3>Pairing {{ status.pairing.address }}</h3>
            <p v-if="status.pairing.state === 'pairing'">Waiting for the device and any confirmation below.</p>
            <p v-else>{{ status.pairing.state === 'paired' ? 'Device paired.' : status.pairing.state === 'canceled' ? 'Pairing canceled.' : 'Pairing did not complete.' }}</p>
            <div v-if="status.pairing.prompt" class="gx-driving__intro"><p>{{ status.pairing.prompt.kind === 'confirmation' ? 'Confirm this code matches the device:' :
              status.pairing.prompt.kind === 'pin' ? 'Enter the PIN shown by the device.' :
              status.pairing.prompt.kind === 'passkey' ? 'Enter the device passkey.' :
              status.pairing.prompt.kind === 'authorization' ? 'Allow this device to pair?' : 'Use this code on the device:' }}</p>
              <strong v-if="status.pairing.prompt.value">{{ status.pairing.prompt.value }}</strong>
              <input v-if="['pin', 'passkey'].includes(status.pairing.prompt.kind)" v-model="pairValue" class="gx-field" type="text" maxlength="16" autocomplete="off" placeholder="PIN or passkey" />
              <div v-if="!status.pairing.prompt.displayOnly" class="gx-driving__actions gx-actions"><button class="gx-btn gx-btn--tonal" @click="respond(false)">Reject</button>
                <button class="gx-btn" :disabled="!canAllowPair" @click="respond(true)">{{ status.pairing.prompt.kind === 'pin' ? 'Submit PIN' : status.pairing.prompt.kind === 'passkey' ? 'Submit Passkey' : 'Allow' }}</button></div></div>
            <button v-if="status.pairing.state === 'pairing'" class="gx-btn gx-btn--tonal" @click="action('cancel_pair')">Cancel Pairing</button></div>
          <div class="gx-card gx-driving__intro"><h3>Saved Devices</h3><p v-if="!saved.length">No saved devices found.</p>
            <div v-for="device in saved" :key="device.address" class="gx-row"><div class="gx-row__info"><strong>{{ device.name }}</strong><small>{{ device.connected ? 'Connected' : 'Disconnected' }}</small></div>
              <div class="gx-driving__actions gx-actions"><button class="gx-btn gx-btn--tonal" :disabled="!status.powered" @click="action(device.connected ? 'disconnect' : 'connect', {address:device.address})">{{ device.connected ? 'Disconnect' : 'Connect' }}</button>
                <button class="gx-btn gx-btn--tonal" @click="action('forget', {address:device.address})">Forget</button></div></div></div>
          <div class="gx-card gx-driving__intro"><h3>Nearby Devices</h3><p v-if="!nearby.length">{{ status.discovering ? 'Searching…' : 'No nearby devices found.' }}</p>
            <div v-for="device in nearby" :key="device.address" class="gx-row"><strong>{{ device.name }}</strong>
              <button class="gx-btn" :disabled="!status.powered || status.pairing?.state === 'pairing'" @click="action('pair', {address:device.address})">Pair</button></div></div>
        </template>
      </template>
      <ControllersPage :mode="mode" :unauthorized="unauthorized" />
    </section>`,
}
