import { reactive } from "../vendor/vue/vue.esm-browser.js"
import { GxDialog } from "./dialog.js"
import { GxNotice } from "./notice.js"

export const ToyotaToolsPage = {
  props: { mode: String, unauthorized: Function },
  components: { GxDialog, GxNotice },
  setup() { return { state: reactive({ data: null, error: "", busy: false, name: "", value: "", pending: null }),
    controller: null, timer: null, generation: 0, alive: false } },
  mounted() { if (this.mode === "local") { this.alive = true; this.load() } },
  beforeUnmount() { this.alive = false; this.generation++; this.controller?.abort(); clearTimeout(this.timer); this.state.value = "" },
  methods: {
    async request(payload = null) {
      if (!this.alive || this.state.busy) return null
      this.controller?.abort()
      clearTimeout(this.timer)
      const generation = ++this.generation
      const controller = this.controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 8000)
      this.state.busy = true
      try {
        const response = await fetch(payload ? "./api/toyota-tools/action" : "./api/toyota-tools", {
          method: payload ? "POST" : "GET", credentials: "same-origin", cache: "no-store", signal: controller.signal,
          headers: payload ? { "Content-Type": "application/json" } : {}, body: payload ? JSON.stringify(payload) : undefined })
        if (!this.alive || generation !== this.generation) return null
        if (response.status === 401) this.unauthorized?.()
        const result = await response.json()
        if (!response.ok) throw new Error(result.error || "Toyota settings are unavailable")
        this.state.error = ""
        return result
      } catch (error) {
        if (this.alive && generation === this.generation) { this.state.data = null; this.state.error = error.message || "Toyota settings are unavailable" }
        return null
      } finally {
        clearTimeout(timeout)
        if (generation === this.generation) { this.state.busy = false; this.controller = null }
      }
    },
    async load() {
      const result = await this.request()
      if (result?.version === 1 && typeof result.visible === "boolean" && Array.isArray(result.keys)) this.state.data = result
      if (this.alive) this.timer = setTimeout(() => this.load(), 2000)
    },
    choose(action, name = null, value = null) {
      if (!this.state.data?.parked || !this.state.data.readable || this.state.busy) return
      const payload = { view: this.state.data.view, action, confirmed: true }
      if (["lock", "unlock"].includes(action)) payload.value = value
      else { payload.name = name; if (action === "save_key") payload.value = this.state.value }
      this.state.pending = payload
      clearTimeout(this.timer)
    },
    cancel() { this.state.pending = null; this.load() },
    async confirm() {
      const payload = this.state.pending
      this.state.pending = null
      const result = await this.request(payload)
      this.state.value = ""
      if (result?.saved) await this.load()
      else if (this.alive) this.timer = setTimeout(() => this.load(), 2000)
    },
  },
  template: `<section v-if="mode === 'local' && (state.data?.visible || state.error)" class="gx-card" aria-label="Toyota features">
    <h3>Toyota Features</h3><GxNotice v-if="state.error" tone="danger">{{ state.error }}</GxNotice>
    <template v-if="state.data?.visible">
      <p>Changes apply after the next start. Only the connected Toyota controller can send door commands.</p>
      <p v-if="!state.data.parked || !state.data.readable">Park the car and refresh before changing these settings.</p>
      <div class="gx-actions"><button class="gx-btn gx-btn--tonal" :disabled="state.busy || !state.data.parked || !state.data.readable"
        @click="choose('lock', null, !state.data.lock)">Auto lock leaving Park: {{ state.data.lock ? 'On' : 'Off' }}</button>
      <button class="gx-btn gx-btn--tonal" :disabled="state.busy || !state.data.parked || !state.data.readable"
        @click="choose('unlock', null, !state.data.unlock)">Auto unlock entering Park: {{ state.data.unlock ? 'On' : 'Off' }}</button></div>
      <p>Commands are sent once at a stationary gear transition with doors closed. Door response must be checked on your vehicle.</p>
      <template v-if="state.data.security"><h4>Toyota Security Keys</h4>
        <p>{{ state.data.activePresent ? 'A key is saved for the next start.' : 'No valid active key is saved.' }} Key values are never displayed.</p>
        <div v-for="key in state.data.keys" :key="key.name" class="gx-actions"><strong>{{ key.name }}{{ key.active ? ' · selected' : '' }}</strong>
          <button class="gx-btn" :disabled="state.busy || !state.data.parked || !state.data.readable" @click="choose('use_key', key.name)">Use key</button>
          <button class="gx-btn gx-btn--tonal" :disabled="state.busy || !state.data.parked || !state.data.readable" @click="choose('delete_key', key.name)">Delete saved copy</button></div>
        <label>Key name<input class="gx-field" v-model="state.name" maxlength="48" autocomplete="off"></label>
        <label>32-character hexadecimal key<input class="gx-field" type="password" v-model="state.value" maxlength="32" autocomplete="new-password" spellcheck="false"></label>
        <button class="gx-btn" :disabled="state.busy || !state.data.parked || !state.data.readable || !/^[0-9a-fA-F]{32}$/.test(state.value) || !state.name"
          @click="choose('save_key', state.name)">Save key</button>
      </template>
    </template>
    <GxDialog v-if="state.pending" labelledby="gx-toyota-confirm" @close="cancel()"><h3 id="gx-toyota-confirm">Save Toyota preference?</h3>
      <p>The change applies after the next start. Deleting a saved key copy does not clear the active key.</p>
      <div class="gx-actions"><button class="gx-btn gx-btn--tonal" @click="cancel()">Cancel</button><button class="gx-btn" @click="confirm()">Confirm</button></div>
    </GxDialog>
  </section>`,
}
