import { reactive } from "../vendor/vue/vue.esm-browser.js"

export function validLocalAccess(value) {
  if (!value || typeof value.available !== "boolean" || typeof value.reason !== "string" || value.reason.length > 1024 ||
      !Array.isArray(value.addresses) || value.addresses.length > 32 || value.available !== (value.addresses.length > 0)) return false
  return value.addresses.every(address => {
    if (!address || !["interface", "label", "url"].every(key => typeof address[key] === "string" && address[key].length > 0 && address[key].length <= 512)) return false
    try {
      const url = new URL(address.url)
      return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password && !!url.hostname
    } catch { return false }
  })
}

export class LocalAccessFeed {
  constructor({ publish, onUnauthorized = () => {}, fetcher = (...args) => fetch(...args),
    later = (fn, ms) => setTimeout(fn, ms), cancel = id => clearTimeout(id) }) {
    Object.assign(this, { publish, onUnauthorized, fetcher, later, cancel })
    this.active = false
    this.request = null
    this.generation = 0
  }
  start(mode) {
    this.stop()
    this.active = true
    this.mode = mode
    if (mode !== "local") {
      this.publish({ loading: false, data: null, error: "Local comma addresses are unavailable in sample mode." })
      return
    }
    return this.refresh()
  }
  stop() {
    this.active = false
    this.generation++
    this.request?.abort()
    this.request = null
  }
  async refresh() {
    if (!this.active || this.mode !== "local" || this.request) return
    const request = new AbortController(), generation = ++this.generation
    this.request = request
    this.publish({ loading: true, error: "" })
    const timer = this.later(() => request.abort(), 4000)
    try {
      const response = await this.fetcher("./api/local-access", { credentials: "same-origin", cache: "no-store", signal: request.signal })
      if (!this.active || generation !== this.generation) return
      if (response.status === 401) { this.stop(); this.onUnauthorized(); return }
      const data = await response.json()
      if (!this.active || generation !== this.generation) return
      if (!response.ok || !validLocalAccess(data)) throw new Error("Local comma addresses are unavailable. Try Refresh.")
      this.publish({ data, error: "" })
    } catch (error) {
      if (this.active && generation === this.generation)
        this.publish({ data: null, error: error.name === "AbortError" ? "Reading local addresses timed out. Try Refresh." : "Local comma addresses are unavailable. Try Refresh." })
    } finally {
      this.cancel(timer)
      if (this.active && generation === this.generation) {
        this.request = null
        this.publish({ loading: false })
      }
    }
  }
}

export const LocalAccess = {
  props: { mode: { type: String, required: true }, onUnauthorized: { type: Function, default: () => {} },
    showRefresh: { type: Boolean, default: true } },
  setup(props) {
    const state = reactive({ loading: false, data: null, error: "" })
    const feed = new LocalAccessFeed({ publish: update => Object.assign(state, update), onUnauthorized: props.onUnauthorized })
    return { state, feed }
  },
  mounted() { this.feed.start(this.mode) },
  watch: { mode(value) { this.feed.start(value) } },
  beforeUnmount() { this.feed.stop() },
  template: `<section class="gx-card gx-local-access" style="padding:var(--sp-4)" aria-label="Local comma access">
    <div class="gx-settings__subhead"><h3>Local Comma Access</h3><button v-if="showRefresh" class="gx-btn gx-btn--tonal" type="button" :disabled="mode !== 'local' || state.loading" @click="feed.refresh()">{{ state.loading ? 'Checking…' : 'Refresh' }}</button></div>
    <p v-if="state.error" class="gx-note" role="status">{{ state.error }}</p>
    <template v-else-if="state.data?.available">
      <p>On the same network, open one of these comma addresses:</p>
      <ul><li v-for="address in state.data.addresses" :key="address.interface + address.url"><a :href="address.url" target="_blank" rel="noopener" style="overflow-wrap:anywhere">{{ address.label }} · {{ address.url }}</a></li></ul>
      <p class="gx-note">These addresses come from the comma; your browser must be able to reach its network.</p>
    </template>
    <p v-else-if="state.data" class="gx-note" role="status">{{ state.data.reason || 'The comma has no local network address available.' }}</p>
  </section>`,
}
