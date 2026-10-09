import { requestJson } from "./startup.js"

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
  props: { mode: String, unauthorized: Function },
  data: () => ({ snapshot: null, draft: null, revision: '', busy: false, error: '', notice: '',
    showPassword: false, timer: null, controller: null, generation: 0, active: false }),
  computed: { dirty() { return JSON.stringify(this.draft) !== JSON.stringify(this.snapshot?.config) } },
  mounted() { this.start() },
  beforeUnmount() { this.stop() },
  watch: { mode() { this.stop(); this.start() } },
  methods: {
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
  template: `<section class="gx-card gx-panel"><h3>Galaxy Wi-Fi Hotspot</h3>
    <p>Local browser access for iPhone and Android while Android Auto projects. No Bluetooth browser API or cellular connection is required for Galaxy.</p>
    <p v-if="mode !== 'local'">Configure this on your comma.</p>
    <template v-if="snapshot && draft">
      <p role="status">Status: {{ snapshot.state }} {{ snapshot.reason }}</p>
      <fieldset class="gx-hotspot__controls" :disabled="busy || !snapshot.editable">
        <label><input type="checkbox" v-model="draft.enabled" /> Broadcast hotspot automatically</label>
        <p>Network name: <strong>{{ snapshot.config.ssid }}</strong></p>
        <p class="gx-note">Fixed to TheGalaxy- plus the last four characters of your comma dongle ID. Once saved, the switch and password survive restarts.</p>
        <p><label>Password <input class="gx-field" :type="showPassword ? 'text' : 'password'" v-model="draft.password" maxlength="63" autocomplete="new-password" placeholder="Blank generates a password" /></label></p>
        <label><input type="checkbox" v-model="showPassword" /> Show password</label>
        <p><button class="gx-btn" type="button" :disabled="!dirty" @click="save">{{ busy ? 'Saving…' : 'Save hotspot' }}</button></p>
      </fieldset>
      <p v-if="!snapshot.editable">Park before changing hotspot settings.</p>
      <p>Join this Wi-Fi network in your phone's settings, stay connected if warned that it has no Internet, then open <a :href="snapshot.url">{{ snapshot.url }}</a>.</p>
    </template>
    <p class="gx-note">When enabled, the hotspot starts automatically while the comma is running, even without another Wi-Fi connection. It uses a standalone channel or follows Android Auto/Wi-Fi's channel when connected. Joining a network or switching channels may briefly interrupt phone access. The Wi-Fi radio must be available. This hotspot provides no Internet gateway. Changing its password or disabling it disconnects hotspot clients.</p>
    <p class="gx-note">Bookmark the full local address. The public galaxy.firestar.link address still requires Internet and its tunnel.</p>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="notice" role="status">{{ notice }}</p>
  </section>`,
}
