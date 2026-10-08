import { GxNotice } from "./notice.js"
import { connectionError } from "./polling.js"
import { NavigationMap } from "./navigation-map.js"
import { MapOperationsPanel } from "./map-operations.js"

export function searchUuid() {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("")
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function remainingLocationLease(lease, requestStarted, now = performance.now()) {
  return Math.max(0, Math.min(2500, lease) - Math.max(0, now - requestStarted))
}

const STATUS = new Set(["disabled", "needsKey", "noDestination", "waitingForLocation", "routing", "guiding", "arrived", "routeUnavailable", "stale"])
const coordinate = (value) => !!value && Number.isFinite(value.latitude) && Math.abs(value.latitude) <= 90 &&
  Number.isFinite(value.longitude) && Math.abs(value.longitude) <= 180
export const validDestination = (value) => coordinate(value) && typeof value.id === "string" && value.id.length > 0 && value.id.length <= 256 &&
  typeof value.name === "string" && value.name.trim().length > 0 && value.name.length <= 256
export const validSearchResult = (value) => validDestination(value) || !!value && value.temporary === true &&
  typeof value.id === "string" && value.id.length > 0 && value.id.length <= 256 &&
  typeof value.name === "string" && value.name.trim().length > 0 && value.name.length <= 256 &&
  (value.description === undefined || typeof value.description === "string" && value.description.length <= 512) &&
  typeof value.searchId === "string" && /^[0-9a-f-]{36}$/.test(value.searchId)
export function validNavigation(value) {
  const instruction = value?.instruction
  if (value?.alternatives !== undefined && (!Array.isArray(value.alternatives) || value.alternatives.length > 3 ||
      !value.alternatives.every((row,index) => row.index === index && Number.isFinite(row.durationSeconds) && row.durationSeconds >= 0 &&
        Number.isFinite(row.distanceMeters) && row.distanceMeters >= 0 && Array.isArray(row.geometry) && row.geometry.length <= 512 && row.geometry.every(coordinate)) ||
      !Number.isInteger(value.selectedRoute) || value.selectedRoute < 0 || value.selectedRoute > 2)) return false
  return !!value && typeof value.enabled === "boolean" && typeof value.isMetric === "boolean" && typeof value.hasKey === "boolean" && STATUS.has(value.status) &&
    typeof value.revision === "string" && value.revision.length > 0 && value.revision.length <= 128 &&
    (value.destination === null || validDestination(value.destination)) && Array.isArray(value.favorites) && value.favorites.length <= 100 &&
    (value.location == null || coordinate(value.location) && Number.isFinite(value.location.validForMs) && value.location.validForMs >= 0 && value.location.validForMs <= 2500) &&
    value.favorites.every(validDestination) && Array.isArray(value.route) && value.route.length <= 512 && value.route.every(coordinate) &&
    (instruction === null || !!instruction && ["text", "maneuverType", "maneuverModifier"].every((key) =>
      typeof instruction[key] === "string" && instruction[key].length <= 1024) &&
      ["distanceMeters", "remainingDistanceMeters", "remainingDurationSeconds"].every((key) =>
        Number.isFinite(instruction[key]) && instruction[key] >= 0))
}

export function routePath(points) {
  if (!Array.isArray(points) || points.length < 2 || points.length > 512 || !points.every(coordinate)) return ""
  const latitude = points.reduce((sum, point) => sum + point.latitude, 0) / points.length
  const scale = Math.max(0.05, Math.cos(latitude * Math.PI / 180))
  const firstLongitude = points[0].longitude
  const projected = points.map((point) => [(((point.longitude - firstLongitude + 540) % 360) - 180) * scale, -point.latitude])
  const xs = projected.map((point) => point[0]), ys = projected.map((point) => point[1])
  const left = Math.min(...xs), top = Math.min(...ys)
  const width = Math.max(...xs) - left, height = Math.max(...ys) - top
  const zoom = Math.min(360 / Math.max(width, 1e-8), 180 / Math.max(height, 1e-8))
  return projected.map(([x, y], index) => `${index ? "L" : "M"}${(200 + (x - left - width / 2) * zoom).toFixed(2)},${(110 + (y - top - height / 2) * zoom).toFixed(2)}`).join(" ")
}

export class NavigationClient {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (timer) => clearTimeout(timer) }) {
    Object.assign(this, { publish, unauthorized, fetcher, later, cancelTimer })
    this.clientId = searchUuid()
    this.active = false
    this.generation = 0
    this.controller = this.timer = null
    this.data = null
    this.results = []
    this.searched = false
    this.busy = false
    this.error = ""
    this.stale = false
  }

  emit() { this.publish({ data: this.data, results: this.results, searched: this.searched, busy: this.busy, error: this.error, stale: this.stale }) }
  stop() {
    if (this.searchId && this.data) {
      this.fetcher("./api/navigation/action", { method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "cancelSearch",
          revision: this.data.revision, searchId: this.searchId }) }).catch(() => {})
    }
    this.searchId = null
    this.active = false
    this.generation++
    this.controller?.abort()
    if (this.timer !== null) this.cancelTimer(this.timer)
    this.controller = this.timer = null
    this.data = null
    this.results = []
    this.searched = false
    this.error = ""
    this.busy = this.stale = false
    this.emit()
  }
  start() { this.stop(); this.active = true; return this.load() }
  load() { return this.run("status") }
  search(query) {
    this.searchId = searchUuid()
    return this.run("search", { query: query.trim(), searchId: this.searchId, clientId: this.clientId })
  }
  choose(place) {
    return place.temporary ? this.action("selectPlace", { id: place.id, searchId: place.searchId }) :
      this.action("select", { destination: place })
  }
  action(action, value = {}) {
    if (!this.data || this.busy || this.stale) return Promise.resolve(null)
    return this.run("action", { action, revision: this.data.revision, ...value })
  }

  async run(operation, body = null) {
    if (!this.active || this.busy) return null
    this.controller?.abort()
    if (this.timer !== null) this.cancelTimer(this.timer)
    this.timer = null
    const requestStarted = performance.now()
    const generation = ++this.generation
    const controller = new AbortController()
    this.controller = controller
    this.busy = operation !== "status"
    if (operation !== "status") this.error = ""
    this.emit()
    const deadline = this.later(() => controller.abort(), operation === "search" ? 24000 : operation === "action" && body?.action === "selectPlace" ? 12000 : 4000)
    try {
      const response = await this.fetcher(`./api/navigation/${operation}`, {
        credentials: "same-origin", cache: "no-store", signal: controller.signal,
        ...(body === null ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
      })
      if (!this.active || generation !== this.generation) return null
      const payload = await response.json()
      if (!this.active || generation !== this.generation) return null
      if (controller.signal.aborted) throw new Error("Navigation did not respond.")
      if (response.status === 401 || response.status === 503 && ["access_unavailable", "setup_required"].includes(payload?.code)) {
        this.stop(); this.unauthorized(); return null
      }
      if (!response.ok) throw new Error(payload?.error || "Navigation could not complete this request.")
      this.error = ""
      if (operation === "search") {
        if (!Array.isArray(payload.results) || payload.results.length > 20 || !payload.results.every(validSearchResult))
          throw new Error("Search results could not be read.")
        this.results = payload.results
        this.searched = true
      } else {
        if (!validNavigation(payload)) throw new Error("Navigation status could not be read.")
        if (payload.location) {
          payload.location.validForMs = remainingLocationLease(payload.location.validForMs, requestStarted)
          payload.location.expiresAt = performance.now() + payload.location.validForMs
        }
        if (JSON.stringify(payload) !== JSON.stringify(this.data)) this.data = payload
        this.stale = false
        if (operation === "action" && ["select", "selectPlace", "clear"].includes(body.action)) { this.results = []; this.searched = false }
      }
      return payload
    } catch (error) {
      if (this.active && generation === this.generation) {
        this.error = controller.signal.aborted ? "Navigation did not respond. Reconnecting…" : connectionError(error)
        if (operation !== "search") this.stale = true
      }
      return null
    } finally {
      this.cancelTimer(deadline)
      if (this.active && generation === this.generation) {
        this.controller = null
        this.busy = false
        this.emit()
        this.timer = this.later(() => { this.timer = null; this.load() }, this.data?.enabled && this.data?.hasKey ? 1000 : this.data?.status === "guiding" ? 2000 : 5000)
      }
    }
  }
}

export const NavigationPage = {
  name: "NavigationPage",
  components: { GxNotice, MapOperationsPanel, NavigationMap },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true },
    go: { type: Function, default: null } },
  data: () => ({ data: null, results: [], busy: false, error: "", stale: false, tab: "route", favoritesOpen: false, query: "", token: "", searched: false }),
  computed: {
    available() { return this.mode === "local" && !!this.data && !this.stale && !this.busy },
    path() { return routePath(this.data?.route) },
    summary() {
      const instruction = this.data?.instruction, route = this.data?.alternatives?.[this.data?.selectedRoute || 0]
      return instruction ? {distance:instruction.remainingDistanceMeters,duration:instruction.remainingDurationSeconds} :
        route ? {distance:route.distanceMeters,duration:route.durationSeconds} : null
    },
    statusLabel() {
      return ({ disabled: "Navigation is off", needsKey: "Add your Mapbox key to get started", noDestination: "Where would you like to go?",
        waitingForLocation: "Waiting for GPS", routing: "Finding your route…", guiding: "Route guidance", arrived: "You have arrived",
        routeUnavailable: "A route could not be found", stale: "Waiting for navigation" })[this.data?.status] || "Connecting to navigation…"
    },
  },
  created() { this.client = new NavigationClient({ publish: (state) => Object.assign(this.$data, state), unauthorized: this.unauthorized }) },
  mounted() {
    if (this.mode !== "local") return
    this.visibilityHandler = () => document.visibilityState === "hidden" ? this.client.stop() : this.client.start()
    document.addEventListener("visibilitychange", this.visibilityHandler)
    if (document.visibilityState !== "hidden") this.client.start()
  },
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibilityHandler); this.client.stop(); this.token = "" },
  methods: {
    async search() { await this.client.search(this.query) },
    async saveKey(enable = false) { const token = this.token.trim(); this.token = ""; await this.client.action("configure", { patch: enable ? { token, enabled: true } : { token } }) },
    distance(value) {
      const metric = this.data?.isMetric !== false
      return metric ? value < 1000 ? `${Math.round(value)} m` : `${(value / 1000).toFixed(1)} km` :
        value < 160.9344 ? `${Math.round(value / 0.3048 / 10) * 10} ft` : `${(value / 1609.344).toFixed(1)} mi`
    },
    duration(value) { const minutes = Math.max(1, Math.round(value / 60)); return minutes >= 60 ? `${Math.floor(minutes / 60)} hr ${minutes % 60} min` : `${minutes} min` },
    isFavorite(place) { return this.data?.favorites.some((favorite) => favorite.id === place.id) },
  },
  template: `
    <div class="gx-view gx-navigation" :class="{'gx-navigation--fullscreen':tab==='route'}">
      <h2>Navigation</h2>
      <div class="gx-navigation__tabs gx-tabs" role="tablist" aria-label="Navigation tools">
        <button v-for="item in [{id:'route',label:'Destination'},{id:'maps',label:'Offline Maps'},{id:'setup',label:'Setup'}]" :key="item.id"
          type="button" class="gx-btn" :class="tab === item.id ? '' : 'gx-btn--tonal'" role="tab" :aria-selected="tab === item.id" @click="tab=item.id">{{ item.label }}</button>
      </div>
      <MapOperationsPanel v-if="tab === 'maps'" :mode="mode" :unauthorized="unauthorized" />
      <template v-else>
        <NavigationMap v-if="tab === 'route' && data?.enabled && data?.hasKey" :data="data" :stale="stale" />
        <div :class="tab === 'route' ? 'gx-navigation__panel' : 'gx-stack'">
          <p v-if="mode !== 'local'" class="gx-note">Connect to your comma to set up navigation and choose a destination.</p>
          <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
          <p v-if="stale && data" class="gx-note">Showing the last received route. Reconnecting before accepting changes.</p>
          <template v-if="tab === 'setup'">
            <section class="gx-card gx-navigation__section">
              <h3>Navigation</h3>
              <p>Show directions on your comma. Navigation works with every driving model. Route guidance helps prepare for turns; steering and speed control follow your normal engagement settings.</p>

            </section>
            <section class="gx-card gx-navigation__section">
              <h3>Mapbox</h3>
              <p>One public Mapbox access token (starting with pk.) handles maps, address search, place search and routes. A separate secret token is not needed.</p>
              <p>Save your token while parked. Galaxy keeps it on your comma and never displays it after saving. Saving address favorites requires permanent geocoding: a payment method on file or an enterprise agreement with Mapbox. Place-search results are available for the current route only. Map tiles use your Mapbox quota; URL-restricted keys may reject these requests.</p>
              <a class="gx-navigation__token-link" href="https://account.mapbox.com/access-tokens/" target="_blank" rel="noopener noreferrer">Get a Mapbox access token</a>
              <p v-if="data?.hasKey" class="gx-note">A Mapbox key is saved.</p>
              <div class="gx-field-group"><label for="navigation-token">Public Mapbox access token</label>
              <form @submit.prevent="saveKey(false)" class="gx-navigation__search">
                <input id="navigation-token" class="gx-field" type="password" autocomplete="off" v-model="token" placeholder="pk.…" maxlength="2048" required :disabled="!available">
                <button class="gx-btn" type="submit" :disabled="!available || !token.trim()">{{ data?.hasKey ? 'Replace key' : 'Save key' }}</button>
              </form></div>
            </section>
          </template>
          <template v-else>
            <button v-if="data?.enabled" type="button" class="gx-btn gx-btn--tonal" :disabled="!available" @click="client.action('configure',{patch:{enabled:false}})">Turn off navigation</button>

              <form v-if="data?.enabled && data?.hasKey" @submit.prevent="search" class="gx-navigation__search">
                <label for="navigation-search" class="gx-sr-only">Search destinations</label>
                <input id="navigation-search" class="gx-field" v-model="query" placeholder="Search here" minlength="2" maxlength="200" required :disabled="!available">
                <button class="gx-sr-only" type="submit" :disabled="!available || query.trim().length < 2">Search</button>
                <button v-if="data?.favorites.length" class="gx-btn gx-btn--tonal" type="button" @click="favoritesOpen=!favoritesOpen" :aria-expanded="favoritesOpen">♥ Favorites</button>
              </form>
            <section v-if="data?.destination" class="gx-card gx-navigation__section" :class="{'gx-navigation--stale':stale}">
              <h3 class="gx-navigation__summary-title">{{ data.destination.name }}</h3>
              <div v-if="summary" class="gx-navigation__summary">
                <div><span>🛣️</span><span>Distance:</span><span>{{distance(summary.distance)}}</span></div>
                <div><span>⌛</span><span>Duration:</span><span>{{duration(summary.duration)}}</span></div>
                <div><span>🕗</span><span>ETA:</span><span>{{new Date(Date.now()+summary.duration*1000).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}}</span></div>
              </div>
              <p v-else class="gx-note">{{statusLabel}}</p>
              <template v-if="data.instruction && !stale">
                <p class="gx-navigation__instruction">{{ data.instruction.text }}</p>
                <p>{{ distance(data.instruction.distanceMeters) }} · {{ duration(data.instruction.remainingDurationSeconds) }} remaining · {{ distance(data.instruction.remainingDistanceMeters) }}</p>
              </template>
              <div v-if="data.alternatives?.length > 1" class="gx-navigation__alternatives gx-actions" aria-label="Alternative routes">
                <button v-for="choice in data.alternatives" :key="choice.index" class="gx-btn" :class="choice.index===data.selectedRoute ? '' : 'gx-btn--tonal'" :aria-pressed="choice.index===data.selectedRoute" :disabled="!available" @click="client.action('selectRoute',{index:choice.index})">Route {{choice.index+1}} · {{duration(choice.durationSeconds)}} · {{distance(choice.distanceMeters)}}</button>
              </div>
              <div class="gx-navigation__route-actions gx-actions">
                <button type="button" class="gx-btn" :disabled="!available" @click="client.action('clear')">Cancel Navigation</button>
                <button v-if="!data.destination.temporary" class="gx-btn" :disabled="!available" @click="isFavorite(data.destination) ? client.action('removeFavorite',{id:data.destination.id}) : client.action('favorite',{destination:data.destination})">{{isFavorite(data.destination) ? '♥ Unfavorite' : '♥ Favorite'}}</button>
              </div>
            </section>
            <section v-if="data && !data.hasKey" class="gx-card gx-navigation__section"><h3>Connect Mapbox</h3><p>Add your public Mapbox key to search for places and plan a route. Your key stays on your comma.</p>
              <form @submit.prevent="saveKey(true)" class="gx-navigation__search"><label for="navigation-inline-token" class="gx-sr-only">Public Mapbox access token</label><input id="navigation-inline-token" class="gx-field" type="password" autocomplete="off" v-model="token" placeholder="pk.…" maxlength="2048" required :disabled="!available"><button type="submit" class="gx-btn" :disabled="!available || !token.trim()">Save and enable</button></form><button type="button" class="gx-btn gx-btn--tonal" @click="tab='setup'">Key details</button>
            </section>
            <section v-else-if="data && !data.enabled" class="gx-card gx-navigation__section"><h3>Navigation is off</h3><button type="button" class="gx-btn" :disabled="!available" @click="client.action('configure',{patch:{enabled:true}})">Enable Navigation</button></section>
            <template v-else>
              <p v-if="busy" role="status">Working…</p>
              <p v-if="searched && !busy && !error && results.length === 0" class="gx-note">No places found. Try a nearby town or a more specific address.</p>
              <ul v-if="results.length" class="gx-navigation__places" aria-label="Search results">
                <li v-for="place in results" :key="place.id" class="gx-card">
                  <span>{{ place.name }}<small v-if="place.description" class="gx-note">{{ place.description }}</small><small v-if="place.temporary" class="gx-note"> For this route only; cannot be saved.</small></span><div class="gx-navigation__actions gx-actions">
                    <button type="button" class="gx-btn gx-btn--tonal" :disabled="!available || place.temporary || isFavorite(place)" @click="client.action('favorite',{destination:place})">{{ isFavorite(place) ? 'Saved' : 'Save' }}</button>
                    <button type="button" class="gx-btn" :disabled="!available" @click="client.choose(place)">Go</button>
                  </div>
                </li>
              </ul>
              <ul v-if="favoritesOpen && data?.favorites.length" class="gx-navigation__places" aria-label="Saved places">
                <li v-for="place in data.favorites" :key="place.id" class="gx-card"><span>{{ place.name }}<small v-if="place.description" class="gx-note">{{ place.description }}</small><small v-if="place.temporary" class="gx-note"> For this route only; cannot be saved.</small></span><div class="gx-navigation__actions gx-actions">
                  <button type="button" class="gx-icon-btn" :aria-label="'Remove '+place.name" :disabled="!available" @click="client.action('removeFavorite',{id:place.id})">Remove</button>
                  <button type="button" class="gx-btn" :disabled="!available" @click="client.choose(place)">Go</button>
                </div></li>
              </ul>
            </template>
          </template>
        </div>
      </template>
      <button v-if="go" type="button" class="gx-navigation__exit" aria-label="Exit navigation" @click="go('/tools')"><i class="bi bi-x-lg"></i><span>Exit</span></button>
    </div>`,
}
