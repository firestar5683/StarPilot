import { requestJson } from './startup.js'
import { GxNotice } from './notice.js'
import { BluetoothNotice, bluetoothConnection } from './bluetooth-notice.js'

export function newerCompanionVersion(available, installed) {
  const parts = version => typeof version === 'string' && /^\d+(?:\.\d+){1,3}$/.test(version) ? version.split('.').map(Number) : []
  const next = parts(available), current = parts(installed)
  if (!next.length || !current.length || ![...next, ...current].every(Number.isSafeInteger)) return false
  for (let index = 0; index < Math.max(next.length, current.length); index++) {
    const difference = (next[index] || 0) - (current[index] || 0)
    if (difference) return difference > 0
  }
  return false
}

export function validCompanion(value) {
  return value?.protocol === 1 && ['enabled', 'connected', 'active', 'appAvailable', 'updateAvailable'].every(key => typeof value[key] === 'boolean') &&
    Number.isSafeInteger(value.bytes) && value.bytes >= 0 && typeof value.shippedVersion === 'string' &&
    ['active', 'waiting', 'disabled', 'error'].includes(value.state)
}

export const GalaxyCompanion = {
  components: { GxNotice, BluetoothNotice },
  emits: ['status'],
  props: { mode: String, unauthorized: Function },
  data: () => ({ status: null, error: '', native: !!window.StarPilotApp, sharing: false, autoStart: false,
    bluetooth: bluetoothConnection(), nativeBytes: 0, busy: false, generation: 0, alive: false }),
  computed: { windowAutoStart() { return !!window.StarPilotApp?.setAutoStart } },
  mounted() { this.start() },
  beforeUnmount() { this.stop() },
  watch: { mode() { this.stop(); this.start() } },
  methods: {
    connectionOptions() { window.StarPilotApp?.connectionOptions?.() },
    setAutoStart() { window.StarPilotApp.setAutoStart(this.autoStart) },
    start() { if (this.mode === 'local') { this.alive = true; this.refresh() } },
    stop() { this.alive = false; this.generation++; clearTimeout(this.timer); this.controller?.abort(); this.status = null; this.$emit('status', null) },
    adopt(status) {
      if (!validCompanion(status)) throw new Error('Invalid companion status')
      this.status = status
      this.$emit('status', status)
      if (this.native) {
        const state = JSON.parse(window.StarPilotApp.uplinkState())
        this.sharing = state.enabled === true; this.autoStart = state.autoStart === true
        this.nativeBytes = Number.isSafeInteger(state.bytes) && state.bytes >= 0 ? state.bytes : status.bytes
      }
    },
    async refresh() {
      if (!this.alive || this.busy) return
      clearTimeout(this.timer)
      const generation = ++this.generation
      this.controller = new AbortController()
      try {
        const status = await requestJson('./api/companion/status', { request: { signal: this.controller.signal } })
        if (!this.alive || generation !== this.generation) return
        this.adopt(status); this.error = ''
      } catch (e) {
        if (!this.alive || generation !== this.generation) return
        this.error = e.message
        if (e.status === 401) { this.stop(); this.unauthorized() }
      } finally { if (this.alive && generation === this.generation) this.timer = setTimeout(() => this.refresh(), 5000) }
    },
    async toggle() {
      if (this.bluetooth || !this.alive || this.busy || !this.status || this.mode !== 'local') return
      clearTimeout(this.timer); this.controller?.abort()
      const generation = ++this.generation
      this.busy = true
      try {
        const enabled = this.native ? !this.sharing : !this.status.enabled
        const status = await requestJson('./api/companion/settings', { request: { method: 'POST',
          headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled }) } })
        if (!this.alive || generation !== this.generation) return
        this.adopt(status)
        if (this.native) { window.StarPilotApp.setUplinkEnabled(enabled); this.sharing = enabled }
        this.error = ''
      } catch (e) {
        if (!this.alive || generation !== this.generation) return
        this.error = e.message
        if (e.status === 401) { this.stop(); this.unauthorized() }
      } finally {
        this.busy = false
        if (this.alive && generation === this.generation) this.timer = setTimeout(() => this.refresh(), 1000)
      }
    },
  },
  template: `<section class="gx-card gx-panel gx-stack"><h3>Android companion · Connections</h3>
    <p v-if="native"><button class="gx-btn gx-btn--tonal" @click="connectionOptions">Bluetooth, Galaxy Wi-Fi or LAN</button></p>
    <BluetoothNotice v-if="bluetooth" feature="Media transfers and phone internet">Phone internet requires the Galaxy hotspot. Settings and small requests remain available.</BluetoothNotice>
    <p v-else>Share your phone’s mobile data over Galaxy Wi-Fi. Navigation and online services use your mobile plan. Log uploads, software updates and offline map downloads are blocked.</p>
    <template v-if="!native"><p>Join the Android beta on Google Groups to get the app, then join TheGalaxy Wi-Fi.</p>
      <a class="gx-btn" href="https://groups.google.com/g/galaxy-starpilot-android-beta" target="_blank" rel="noopener">Join the Android beta</a>
    </template>
    <template v-if="status && mode === 'local'"><p>Status: <strong>{{ status.state }}</strong> {{ status.reason }} · {{ ((native ? nativeBytes : status.bytes) / 1048576).toFixed(1) }} MB today</p>
      <button v-if="!bluetooth" class="gx-btn gx-btn--tonal" :disabled="busy" @click="toggle">{{ (native ? sharing : status.enabled) ? 'Disable phone internet' : 'Enable phone internet' }}</button>
      <label v-if="!bluetooth && native && !!windowAutoStart"><input type="checkbox" v-model="autoStart" @change="setAutoStart" /> Resume sharing after phone restart (keeps a notification while waiting for Galaxy Wi-Fi)</label>
    </template><GxNotice v-if="error" tone="danger">{{ error }}</GxNotice>
  </section>`,
}
