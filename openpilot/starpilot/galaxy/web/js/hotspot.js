import { requestJson } from "./startup.js"
import { GxNotice } from "./notice.js"
import { GxState } from "./state.js"
import { GalaxySettingRow, switchRow } from "./galaxy-setting-row.js"

export function validHotspot(value) {
  return value?.version === 1 && /^[a-f0-9]{64}$/.test(value.revision) &&
    typeof value.editable === 'boolean' && typeof value.active === 'boolean' &&
    ['active', 'starting', 'waiting', 'disabled', 'error', 'unavailable'].includes(value.state) &&
    typeof value.reason === 'string' && value.reason.length <= 256 &&
    value.url === 'http://172.31.254.1:8082/' && typeof value.config?.enabled === 'boolean' &&
    /^TheGalaxy-[a-f0-9]{4}$/.test(value.config.ssid) &&
    typeof value.config.password === 'string' && (value.config.password === '' || /^[\x21-\x7e]{12,63}$/.test(value.config.password))
}

export const GalaxyHotspot = {
  components: { GxNotice, GxState, GalaxySettingRow },
  props: { mode: String, unauthorized: Function },
  data: () => ({ snapshot: null, draft: null, revision: '', busy: false, error: '', notice: '',
    showPassword: false, timer: null, controller: null, generation: 0, active: false }),
  computed: { dirty() { return JSON.stringify(this.draft) !== JSON.stringify(this.snapshot?.config) } },
  mounted() { this.start() },
  beforeUnmount() { this.stop() },
  watch: { mode() { this.stop(); this.start() } },
  methods: {
    switchRow,
    start() { if (this.mode === 'local') { this.active = true; this.refresh() } },
    stop() {
      this.active = false; this.generation++; clearTimeout(this.timer); this.controller?.abort()
      this.snapshot = this.draft = null; this.revision = ''; this.showPassword = false; this.busy = false
    },
    adopt(value, reset = false) {
      if (!validHotspot(value)) throw new Error('Invalid hotspot status')
      const preserve = this.draft && this.dirty && !reset
      this.snapshot = value
      if (!preserve) { this.draft = { ...value.config }; this.revision = value.revision }
    },
    async refresh() {
      if (!this.active || this.busy) return
      clearTimeout(this.timer); this.controller?.abort()
      const generation = ++this.generation
      this.controller = new AbortController()
      try {
        const value = await requestJson('./api/galaxy/hotspot', { request: { signal: this.controller.signal } })
        if (!this.active || generation !== this.generation) return
        this.adopt(value); this.error = ''
      } catch (error) {
        if (!this.active || generation !== this.generation) return
        if (error.status === 401) { this.stop(); this.unauthorized(); return }
        this.error = error.message
      } finally {
        if (this.active && generation === this.generation) this.timer = setTimeout(() => this.refresh(), 5000)
      }
    },
    async save() {
      if (!this.active || this.busy || !this.snapshot?.editable) return
      clearTimeout(this.timer); this.controller?.abort()
      const generation = ++this.generation
      this.controller = new AbortController(); this.busy = true; this.error = ''; this.notice = ''
      try {
        const value = await requestJson('./api/galaxy/hotspot', { request: { signal: this.controller.signal,
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ revision: this.revision, config: this.draft }),
        } })
        if (!this.active || generation !== this.generation) return
        this.adopt(value, true)
        this.notice = value.config.enabled ? 'Settings saved. Join the network once its status is active.' : 'Hotspot disabled.'
      } catch (error) {
        if (!this.active || generation !== this.generation) return
        if (error.status === 401) { this.stop(); this.unauthorized(); return }
        this.error = `${error.message} If Wi-Fi disconnected, reconnect and reload to check whether settings saved.`
      } finally {
        if (this.active && generation === this.generation) { this.busy = false; this.timer = setTimeout(() => this.refresh(), 1000) }
      }
    },
  },
  template: `<section class="gx-card gx-panel gx-stack"><h3>Galaxy Wi-Fi Hotspot</h3>
    <p>Local Galaxy access for iPhone and Android. No Android Auto, Bluetooth browser support, or cellular connection needed.</p>
    <GxState v-if="mode !== 'local'">Connect to your comma to configure the hotspot.</GxState>
    <GxState v-else-if="!snapshot && !error" loading>Loading hotspot settings…</GxState>
    <template v-if="snapshot && draft">
      <GxNotice :busy="snapshot.state === 'starting'" :tone="['error', 'unavailable'].includes(snapshot.state) ? 'warn' : 'info'">Status: {{ snapshot.state }} {{ snapshot.reason }}</GxNotice>
      <GalaxySettingRow :row="switchRow('Broadcast hotspot automatically', draft.enabled)" :index="0"
        :busy="busy" :disabled="!snapshot.editable" :save-value="(index, value) => { draft.enabled = value === 'On' }" />
      <div class="gx-stack">
        <p>Network name: <strong>{{ snapshot.config.ssid }}</strong></p>
        <p class="gx-note">Fixed to TheGalaxy- plus the last four characters of your comma dongle ID. Once saved, the switch and password survive restarts.</p>
        <label class="gx-field-group">Password <input class="gx-field" :type="showPassword ? 'text' : 'password'" v-model="draft.password" :disabled="busy || !snapshot.editable" maxlength="63" autocomplete="new-password" placeholder="Blank generates a password" /></label>
        <label><input type="checkbox" v-model="showPassword" :disabled="busy || !snapshot.editable" /> Show password</label>
        <div class="gx-settings__controls gx-actions"><button class="gx-btn" type="button" :disabled="!dirty || busy || !snapshot.editable" @click="save">{{ busy ? 'Saving…' : 'Save hotspot' }}</button></div>
      </div>
      <GxNotice v-if="!snapshot.editable">Park before changing hotspot settings.</GxNotice>
      <p>Join the network, stay connected if warned of no Internet, then open and bookmark <a :href="snapshot.url">{{ snapshot.url }}</a>.</p>
    </template>
    <ul class="gx-install-benefits">
      <li><i class="bi bi-power" aria-hidden="true"></i><span>Starts automatically when enabled. Needs the comma on and Wi-Fi available.</span></li>
      <li><i class="bi bi-wifi" aria-hidden="true"></i><span>Works standalone, or shares the channel of connected Wi-Fi or Android Auto.</span></li>
      <li><i class="bi bi-phone" aria-hidden="true"></i><span>Local access without Internet; no Internet sharing.</span></li>
      <li><i class="bi bi-arrow-repeat" aria-hidden="true"></i><span>Network or channel changes may interrupt access. Changing the password or disabling the hotspot disconnects phones.</span></li>
      <li><i class="bi bi-globe" aria-hidden="true"></i><span>The public galaxy.firestar.link address still needs Internet and its tunnel.</span></li>
    </ul>
    <GxNotice v-if="error" tone="danger">{{ error }}</GxNotice><GxNotice v-if="notice" tone="success">{{ notice }}</GxNotice>
  </section>`,
}
