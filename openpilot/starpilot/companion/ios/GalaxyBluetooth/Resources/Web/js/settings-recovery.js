import { GxDialog } from "./dialog.js"

export const SettingsRecoveryPage = {
  components: { GxDialog },
  props: { mode: { type: String, default: "local" }, unauthorized: Function },
  data() { return { snapshot: null, selected: [], pending: null, busy: false, error: "", result: "", timer: null } },
  mounted() { if (this.mode !== "local") return; this.refresh(); this.timer = setInterval(() => { if (!this.pending && !this.busy) this.refresh() }, 10000) },
  beforeUnmount() { clearInterval(this.timer) },
  methods: {
    async request(path, body) {
      const response = await fetch(path, { method: body ? "POST" : "GET", credentials: "same-origin", cache: "no-store",
        headers: body ? { "Content-Type": "application/json" } : {}, ...(body ? { body: JSON.stringify(body) } : {}) })
      const value = await response.json()
      if (response.status === 401 && this.unauthorized) this.unauthorized()
      if (!response.ok) throw new Error(value.error || "Settings are unavailable")
      return value
    },
    async refresh() {
      try {
        const selected = new Set((this.snapshot?.rows || []).filter(row => this.selected.includes(row.id)).map(row => `${row.page}:${row.label}`))
        this.snapshot = await this.request("./api/settings/non-defaults")
        this.selected = this.snapshot.rows.filter(row => row.resetAvailable && selected.has(`${row.page}:${row.label}`)).map(row => row.id)
        this.error = ""
      } catch (error) { this.error = error.message }
    },
    async review(ids) {
      if (!ids.length || this.busy) return
      this.busy = true
      try { this.pending = await this.request("./api/settings/recovery/preview", { view: this.snapshot.view, selected: ids }) }
      catch (error) { this.error = error.message; await this.refresh() }
      finally { this.busy = false }
    },
    async confirm() {
      this.busy = true
      try {
        const value = await this.request("./api/settings/recovery/confirm", { intent: this.pending.intent, confirmed: true })
        this.result = value.saved ? "Selected settings restored to defaults." : `${value.applied.length} settings restored. ${value.reason}`
        this.pending = null; this.selected = []; await this.refresh()
      } catch (error) { this.error = error.message; this.pending = null; await this.refresh() }
      finally { this.busy = false }
    },
  },
  template: `<section class="gx-settings"><h1>Show Non-Default Values</h1>
    <p>Review saved settings that differ from this vehicle’s StarPilot defaults.</p>
    <p v-if="snapshot && snapshot.resettableCount < snapshot.count">Some settings are unavailable for this vehicle. Their saved values remain unchanged.</p>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="result" role="status">{{ result }}</p>
    <div class="gx-card" v-if="snapshot"><p v-if="!snapshot.rows.length">All available settings use their defaults.</p>
      <div v-for="row in snapshot.rows" :key="row.id" class="gx-setting-row gx-setting-row--modified">
        <label><input type="checkbox" v-model="selected" :value="row.id" :disabled="busy || !row.resetAvailable"> {{ row.label }}</label>
        <p>Current: <strong>{{ row.current }}</strong> · Default: {{ row.default }}</p>
        <p v-if="!row.available">{{ row.reason }}</p>
        <button @click="review([row.id])" :disabled="busy || !row.resetAvailable">Reset to Default</button>
      </div>
      <button @click="review(selected)" :disabled="busy || !selected.length">Reset Selected</button>
      <button @click="review(snapshot.rows.filter(row => row.resetAvailable).map(row => row.id))" :disabled="busy || !snapshot.resettableCount">Reset All Non-Default Settings</button>
      <button @click="refresh" :disabled="busy">Refresh</button>
    </div>
    <GxDialog v-if="pending" labelledby="recovery-question" @close="pending = null">
      <h2 id="recovery-question">{{ pending.question }}</h2><ul><li v-for="label in pending.labels" :key="label">{{ label }}</li></ul>
      <button @click="pending = null" :disabled="busy">Cancel</button><button @click="confirm" :disabled="busy">Reset Settings</button>
    </GxDialog></section>`,
}
