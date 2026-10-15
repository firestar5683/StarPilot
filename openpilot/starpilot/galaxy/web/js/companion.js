import { requestJson } from './startup.js'
import { GxNotice } from './notice.js'

export function validCompanion(value) {
  return value?.protocol === 1 && ['enabled', 'connected', 'active', 'appAvailable', 'updateAvailable'].every(key => typeof value[key] === 'boolean') &&
    Number.isSafeInteger(value.bytes) && value.bytes >= 0 && typeof value.shippedVersion === 'string' &&
    ['active', 'waiting', 'disabled', 'error'].includes(value.state)
}

export const GalaxyCompanion = {
  components: { GxNotice },
  props: { mode: String, unauthorized: Function },
  data: () => ({ status: null, error: '', native: !!window.StarPilotApp, sharing: false, autoStart: false,
    bluetooth: window.StarPilotApp?.bluetooth?.() === true, nativeVersion: window.StarPilotApp?.version(), nativeBytes: 0, busy: false, generation: 0, alive: false }),
  computed: { windowAutoStart() { return !!window.StarPilotApp?.setAutoStart } },
  mounted() { this.start() },
  beforeUnmount() { this.stop() },
  watch: { mode() { this.stop(); this.start() } },
  methods: {
    connectionOptions() { window.StarPilotApp?.connectionOptions?.() },
    setAutoStart() { window.StarPilotApp.setAutoStart(this.autoStart) },
    start() { if (this.mode === 'local') { this.alive = true; this.refresh() } },
    stop() { this.alive = false; this.generation++; clearTimeout(this.timer); this.controller?.abort(); this.status = null },
    adopt(status) {
      if (!validCompanion(status)) throw new Error('Invalid companion status')
      this.status = status
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
      if (!this.alive || this.busy || !this.status || this.mode !== 'local') return
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
    <GxNotice v-if="bluetooth" tone="warn">Bluetooth carries settings and small requests using the screens bundled in this app. Videos, camera images, large downloads and phone internet require Wi-Fi or LAN. Update the app to refresh its Bluetooth screens.</GxNotice>
    <p>Share your phone’s mobile data over Galaxy Wi-Fi. Navigation and online services use your mobile plan. Log uploads, software updates and offline map downloads are blocked.</p>
    <template v-if="!native"><p>Join TheGalaxy Wi-Fi, download the Android app, then allow your browser to install unknown apps when Android asks.</p>
      <a v-if="status?.appAvailable && mode === 'local'" class="gx-btn" href="./app.apk">Download Android app</a>
      <p v-else class="gx-note">Connect locally to a comma with the companion APK installed to download.</p>
      <img v-if="status?.appAvailable && mode === 'local'" src="./api/companion/qr.svg" class="gx-tunnel__qr" alt="Download app over Galaxy Wi-Fi" />
    </template>
    <template v-if="status && mode === 'local'"><p>Status: <strong>{{ status.state }}</strong> {{ status.reason }} · {{ ((native ? nativeBytes : status.bytes) / 1048576).toFixed(1) }} MB today</p>
      <button class="gx-btn gx-btn--tonal" :disabled="busy" @click="toggle">{{ (native ? sharing : status.enabled) ? 'Disable phone internet' : 'Enable phone internet' }}</button>
      <label v-if="native && !!windowAutoStart"><input type="checkbox" v-model="autoStart" @change="setAutoStart" /> Resume sharing after phone restart (keeps a notification while waiting for Galaxy Wi-Fi)</label>
      <GxNotice v-if="status.updateAvailable || (nativeVersion && status.shippedVersion && nativeVersion !== status.shippedVersion)" tone="warn">A companion update is available. <a href="./app.apk">Update app</a></GxNotice>
    </template><GxNotice v-if="error" tone="danger">{{ error }}</GxNotice>
  </section>`,
}
