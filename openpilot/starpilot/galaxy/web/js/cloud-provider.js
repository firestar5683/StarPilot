import { GalaxySelect } from "./galaxy-select.js"
import { GxNotice } from "./notice.js"

export const validProviderStatus = value => value && ["comma", "konik"].includes(value.active) &&
  ["comma", "konik"].includes(value.selected) && /^[a-f0-9]{64}$/.test(value.revision) &&
  typeof value.restartRequired === "boolean" && typeof value.canSelect === "boolean" &&
  Array.isArray(value.providers) && value.providers.length === 2 &&
  ["comma", "konik"].every(name => value.providers.filter(p => p.id === name).length === 1) &&
  value.providers.every(p => ["comma", "konik"].includes(p.id) && typeof p.label === "string" &&
    p.url === (p.id === "comma" ? "https://connect.comma.ai" : "https://stable.konik.ai"))

export const CloudProviderPage = {
  name: "CloudProviderPage",
  components: { GalaxySelect, GxNotice },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ status: null, busy: false, error: "", request: null }),
  mounted() { this.load() },
  beforeUnmount() { this.request?.abort() },
  computed: {
    active() { return this.status?.providers.find(p => p.id === this.status.active) },
    selected() { return this.status?.providers.find(p => p.id === this.status.selected) },
  },
  methods: {
    async call(body) {
      this.request?.abort()
      const controller = new AbortController()
      this.request = controller
      const timer = setTimeout(() => controller.abort(), 8000)
      try {
        const response = await fetch("./api/connect/provider", { cache: "no-store", credentials: "same-origin",
          signal: controller.signal, ...(body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}) })
        if (response.status === 401) this.unauthorized()
        const value = await response.json()
        if (!response.ok) throw new Error(value.error || "Cloud provider request failed")
        if (!validProviderStatus(value)) throw new Error("Cloud provider status is unavailable")
        this.status = value
      } finally {
        clearTimeout(timer)
        if (this.request === controller) this.request = null
      }
    },
    async load() {
      if (this.mode !== "local") return
      try { await this.call() } catch (error) { this.error = error.message }
    },
    async select(name) {
      if (!this.status?.canSelect || this.busy || !this.status.providers.some(p => p.id === name)) return
      const label = this.status.providers.find(p => p.id === name).label
      if (!window.confirm(`Use ${label} after the next device reboot? The current session stays unchanged. Returning to comma restores its saved cloud identity.`)) return
      this.busy = true
      this.error = ""
      try { await this.call({ provider: name, revision: this.status.revision, confirmed: true }) }
      catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
  },
  template: `<div class="gx-settings__developer-body">
    <section v-if="mode !== 'local'" class="gx-card gx-message">Open this Developer page on your device to choose a cloud provider.</section>
    <template v-else>
      <p>Cloud accounts and uploads stay separate. Your older comma recordings keep their comma links.</p>
      <label class="gx-settings__developer-provider">Cloud provider
        <GalaxySelect class="gx-field gx-field--full" aria-label="Cloud provider" :value="status?.selected || ''"
          :disabled="busy || !status?.canSelect" @change="select($event.target.value)">
          <option v-for="provider in status?.providers || []" :key="provider.id" :value="provider.id">{{ provider.label }}</option>
        </GalaxySelect>
      </label>
      <GxNotice v-if="selected" :tone="active && selected.id === active.id ? 'info' : 'warn'">
        {{ selected.label }}{{ active && selected.id === active.id ? ' is currently active.' : ' applies after the next reboot.' }}
      </GxNotice>
      <p v-if="status?.restartRequired">Restart required. No automatic reboot will occur.</p>
      <p v-if="status && !status.canSelect">Turn off the vehicle to change this Developer setting.</p>
      <button class="gx-btn gx-btn--tonal" @click="load" :disabled="busy">Refresh</button>
      <p v-if="error" class="gx-note gx-note--danger" role="alert">{{ error }}</p>
    </template></div>`,
}
