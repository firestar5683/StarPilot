import { GxNotice } from "./notice.js"
import { connectionError } from "./polling.js"
import { NavigationMap } from "./navigation-map.js"
import { MapOperationsPanel } from "./map-operations.js"
import { OfflineRoadMapsPanel } from "./offline-road-maps.js"

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
const text = (value, limit) => typeof value === "string" && value.trim().length > 0 && value.length <= limit
export const validDestination = (value) => coordinate(value) && text(value.id, 256) && text(value.name, 256) &&
  (value.address === undefined || text(value.address, 512)) && (value.label === undefined || ["home", "work"].includes(value.label))
// Suggestions carry the search they came from; their temporary coordinates are retrieved only for routing.
export const validSuggestion = (value) => !!value && text(value.id, 256) && text(value.name, 256) &&
  (value.description === undefined || typeof value.description === "string" && value.description.length <= 512) &&
  typeof value.searchId === "string" && /^[0-9a-f-]{36}$/.test(value.searchId)
export const validSearchResult = (value) => validDestination(value) || validSuggestion(value)
export function validNavigation(value) {
  const instruction = value?.instruction
  if (value?.alternatives !== undefined && (!Array.isArray(value.alternatives) || value.alternatives.length > 3 ||
      !value.alternatives.every((row,index) => row.index === index && Number.isFinite(row.durationSeconds) && row.durationSeconds >= 0 &&
        Number.isFinite(row.distanceMeters) && row.distanceMeters >= 0 && Array.isArray(row.geometry) && row.geometry.length <= 512 && row.geometry.every(coordinate)) ||
      !Number.isInteger(value.selectedRoute) || value.selectedRoute < 0 || value.selectedRoute > 2)) return false
  return !!value && typeof value.enabled === "boolean" && typeof value.isMetric === "boolean" && typeof value.hasKey === "boolean" && STATUS.has(value.status) &&
    (value.network === undefined || ["online", "offline", "unknown"].includes(value.network)) &&
    typeof value.revision === "string" && value.revision.length > 0 && value.revision.length <= 128 &&
    (value.destination === null || validDestination(value.destination)) && Array.isArray(value.favorites) && value.favorites.length <= 100 &&
    (value.recents === undefined || Array.isArray(value.recents) && value.recents.length <= 10 && value.recents.every(validDestination)) &&
    (value.routeKey === undefined || typeof value.routeKey === "string" && /^[0-9a-f]{16}$/.test(value.routeKey)) &&
    (value.location == null || coordinate(value.location) && Number.isFinite(value.location.validForMs) && value.location.validForMs >= 0 && value.location.validForMs <= 2500) &&
    value.favorites.every(validDestination) && Array.isArray(value.route) && value.route.length <= 512 && value.route.every(coordinate) &&
    (instruction === null || !!instruction && ["text", "maneuverType", "maneuverModifier"].every((key) =>
      typeof instruction[key] === "string" && instruction[key].length <= 1024) &&
      ["distanceMeters", "remainingDistanceMeters", "remainingDurationSeconds"].every((key) =>
        Number.isFinite(instruction[key]) && instruction[key] >= 0))
}

// Equal route keys mean equal route lines, so only the small remainder is compared.
const withoutRoute = (value) => JSON.stringify({ ...value, route: undefined, alternatives: undefined })
export const sameSnapshot = (a, b) => !!a && !!b && (a.routeKey !== undefined && a.routeKey === b.routeKey ?
  withoutRoute(a) === withoutRoute(b) : JSON.stringify(a) === JSON.stringify(b))
// The place fields the comma stores; ids are recomputed from the coordinates.
export const placeOf = (place) => Object.fromEntries(["name", "latitude", "longitude", "address"].filter((key) => place[key] !== undefined).map((key) => [key, place[key]]))

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

  emit() { this.publish({ data: this.data, results: this.results, searched: this.searched, busy: this.busy, error: this.error, stale: this.stale,
    suggestions: this.suggestions }) }
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
    this.endSuggestions(false)
    this.emit()
  }
  start() { this.stop(); this.active = true; return this.load() }
  load() { return this.run("status") }
  async search(query) {
    const text = query.trim()
    if (this.pendingSuggestion && this.suggestionQuery === text) await this.pendingSuggestion
    if (!this.active || this.busy) return null
    if (this.suggestionResultsQuery === text && this.suggestions?.length && this.autocompleteId && !this.suggestions.some(place => place.temporary)) {
      this.searchId = this.autocompleteId
      this.results = this.suggestions.slice()
      this.searched = true
      this.error = ""
      this.endSuggestions(false)
      this.emit()
      return { results: this.results }
    }
    this.endSuggestions()
    this.searchId = searchUuid()
    return this.run("search", { query: text, searchId: this.searchId, clientId: this.clientId })
  }
  choose(place) {
    const pending = place.searchId ? this.action("selectPlace", { id: place.id, searchId: place.searchId }) :
      this.action("select", { destination: placeOf(place) })
    this.endSuggestions()
    return pending
  }
  save(place, label) {
    if (place.temporary) return Promise.resolve(null)
    const category = label === undefined ? {} : { label }
    return place.searchId ? this.action("favoritePlace", { id: place.id, searchId: place.searchId, ...category }) :
      this.action("favorite", { destination: placeOf(place), ...category })
  }

  // As-you-type suggestions run beside status polling and never cancel it. One typing session
  // shares a Mapbox search session on the comma until a place is chosen or a full search runs.
  suggest(query) {
    this.suggestionQuery = query.trim()
    return this.pendingSuggestion = this.runSuggestion(query)
  }
  async runSuggestion(query) {
    const text = query.trim()
    this.suggestController?.abort()
    if (!this.active || text.length < 3 || !this.data?.hasKey || !this.data?.enabled) {
      if (this.suggestions?.length) { this.suggestions = []; this.emit() }
      return []
    }
    this.autocompleteId ??= searchUuid()
    const controller = new AbortController(), sequence = this.suggestSequence = (this.suggestSequence || 0) + 1
    this.suggestController = controller
    const timer = this.later(() => controller.abort(), 8000)
    try {
      const response = await this.fetcher("./api/navigation/search", { method: "POST", credentials: "same-origin", cache: "no-store",
        signal: controller.signal, headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text, searchId: this.autocompleteId, clientId: this.clientId, autocomplete: true }) })
      const payload = await response.json().catch(() => null)
      if (sequence !== this.suggestSequence || !this.active) return []
      if (response.status === 401) { this.stop(); this.unauthorized(); return [] }
      if (!response.ok || !Array.isArray(payload?.results) || payload.results.length > 20 || !payload.results.every(validSearchResult)) {
        this.autocompleteId = null  // the comma ended this session (expired, or settings changed); the next keystroke starts another
        this.suggestions = []
      } else {
        this.suggestions = payload.results
        this.suggestionResultsQuery = text
      }
      this.emit()
      return this.suggestions
    } catch {
      if (sequence === this.suggestSequence && !controller.signal.aborted) { this.suggestions = []; this.emit() }
      return []
    } finally { this.cancelTimer(timer) }
  }
  endSuggestions(emit = true) {
    this.suggestController?.abort()
    this.suggestSequence = (this.suggestSequence || 0) + 1
    this.autocompleteId = null
    this.suggestionQuery = null
    this.suggestionResultsQuery = null
    this.pendingSuggestion = null
    const had = this.suggestions?.length
    this.suggestions = []
    if (emit && had) this.emit()
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
      // Status polls name the route lines they already hold; the comma then leaves them out.
      const query = operation === "status" && this.data?.routeKey ? `?routeKey=${this.data.routeKey}` : ""
      const response = await this.fetcher(`./api/navigation/${operation}${query}`, {
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
        if (payload?.routeUnchanged === true) {
          delete payload.routeUnchanged
          if (this.data?.routeKey === payload.routeKey) {
            payload.route = this.data.route
            if (this.data.alternatives) payload.alternatives = this.data.alternatives
          } else {
            payload.route = []
            delete payload.routeKey  // the next poll asks for the lines again
          }
        }
        if (!validNavigation(payload)) throw new Error("Navigation status could not be read.")
        // Route lines are drawn, never edited: keep them out of Vue's deep reactivity.
        Object.freeze(payload.route)
        if (payload.alternatives) Object.freeze(payload.alternatives)
        if (payload.location) {
          payload.location.validForMs = remainingLocationLease(payload.location.validForMs, requestStarted)
          payload.location.expiresAt = performance.now() + payload.location.validForMs
        }
        if (!sameSnapshot(payload, this.data)) this.data = payload
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

const LABELS = { home: { name: "Home", icon: "bi-house-fill" }, work: { name: "Work", icon: "bi-briefcase-fill" } }
const matches = (place, text) => place.name.toLocaleLowerCase().includes(text) || !!place.address?.toLocaleLowerCase().includes(text)

export const FavoriteChoices = {
  props: ["available"],
  emits: ["choose"],
  template: `<div class="gx-navigation__favorite-choices" role="group" aria-label="Save place as">
    <button v-for="choice in [{label:'home',name:'Home',icon:'bi-house'}, {label:'work',name:'Work',icon:'bi-briefcase'}, {label:null,name:'Other',icon:'bi-star'}]"
      :key="choice.name" type="button" class="gx-btn gx-btn--tonal" :disabled="!controlsAvailable" @click="$emit('choose', choice.label)"><i class="bi" :class="choice.icon" aria-hidden="true"></i>{{ choice.name }}</button>
  </div>`,
}

export const NavigationPage = {
  name: "NavigationPage",
  components: { GxNotice, MapOperationsPanel, NavigationMap, OfflineRoadMapsPanel, FavoriteChoices },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true },
    go: { type: Function, default: null }, initialTab: { type: String, default: "route" } },
  data() { return { data: null, results: [], busy: false, error: "", stale: false, tab: this.initialTab, query: "", token: "", searched: false,
    suggestions: [], suggestOpen: false, savedSearchIds: [], savedSuggestionPlaces: {}, favoritePicker: null, searchPending: false } },
  watch: { initialTab(value) { this.tab = value } },
  computed: {
    controlsAvailable() { return this.mode === "local" && !!this.data && !this.stale },
    available() { return this.controlsAvailable && !this.busy && !this.searchPending },
    ready() { return !!this.data?.enabled && !!this.data?.hasKey },
    offline() { return this.mode === "local" && this.ready && !this.stale && this.data?.network === "offline" },
    usingSavedLocation() { return this.mode === "local" && this.ready && !this.stale && this.data?.network === "online" &&
      this.data?.location?.lastKnown === true },
    favorites() { return this.data?.favorites || [] },
    savedIds() { return new Set(this.favorites.map((place) => place.id)) },
    // Recent places that are not already saved, newest first.
    recents() { return (this.data?.recents || []).filter((place) => !this.savedIds.has(place.id)) },
    // Saved places as one-tap buttons: Home and Work first (the comma sends them in that order).
    shortcuts() { return this.favorites.slice(0, 8) },
    showShortcuts() { return this.ready && !this.data.destination && !this.suggestOpen && !this.results.length && this.shortcuts.length > 0 },
    localMatches() {
      const text = this.query.trim().toLocaleLowerCase()
      if (!text) return []
      return [...this.favorites, ...this.recents].filter((place) => matches(place, text)).slice(0, 5)
    },
    showQuick() { return this.suggestOpen && !this.query.trim() && (this.favorites.length > 0 || this.recents.length > 0) },
    showSuggestions() { return this.suggestOpen && !!this.query.trim() && (this.localMatches.length > 0 || this.suggestions.length > 0) },
    destinationSaved() { return !!this.data?.destination && this.favorites.find((place) => place.id === this.data.destination.id) || null },
    usageRows() {
      const usage = this.data?.mapboxUsage
      if (!usage) return []
      return [["searchSessions", "Searches"], ["geocoding", "Address lookups"], ["directions", "Routes"], ["staticTiles", "Map views"]]
        .filter(([key]) => usage[key]).map(([key, label]) => ({ key, label, ...usage[key] }))
    },
    path() { return routePath(this.data?.route) },
    summary() {
      const instruction = this.data?.instruction, route = this.data?.alternatives?.[this.data?.selectedRoute || 0]
      return instruction ? {distance:instruction.remainingDistanceMeters,duration:instruction.remainingDurationSeconds} :
        route ? {distance:route.distanceMeters,duration:route.durationSeconds} : null
    },
    statusLabel() {
      if (this.data?.status === 'waitingForLocation' && this.data.route?.length)
        return 'Route preview from last saved location'
      if (this.data?.status === 'routing' && this.data.location?.lastKnown)
        return 'Finding a route from last saved location…'
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
  beforeUnmount() { document.removeEventListener("visibilitychange", this.visibilityHandler); clearTimeout(this.suggestTimer); this.client.stop(); this.token = "" },
  methods: {
    selectTab(tab) {
      this.tab = tab
      this.go?.(tab === 'route' ? '/navigation' : `/navigation/${tab}`)
    },
    async search() {
      if (this.searchPending) return
      clearTimeout(this.suggestTimer)
      this.suggestOpen = false
      this.savedSearchIds = []
      this.savedSuggestionPlaces = {}
      this.favoritePicker = null
      this.searchPending = true
      try { await this.client.search(this.query) }
      finally { this.searchPending = false }
    },
    typed() {
      clearTimeout(this.suggestTimer)
      this.suggestOpen = true
      if (!this.query.trim()) { this.client.endSuggestions(); return }
      this.favoritePicker = null
      this.suggestTimer = setTimeout(() => this.client.suggest(this.query), 150)
    },
    onSearchFocusOut(event) {
      if (!event.relatedTarget?.closest('.gx-navigation__suggestions, .gx-navigation__search')) this.closeSuggestions()
    },
    closeSuggestions() { this.suggestOpen = false; clearTimeout(this.suggestTimer) },
    clearQuery() {
      this.query = ""
      this.savedSearchIds = []
      this.savedSuggestionPlaces = {}
      this.favoritePicker = null
      this.results = []
      this.searched = false
      this.client.endSuggestions()
      this.$refs.search?.focus()
    },
    async pick(place) {
      this.favoritePicker = null
      this.closeSuggestions()
      this.query = ""
      this.$refs.search?.blur()
      await this.client.choose(place)
    },
    // Search suggestions get their saved id from the comma, so the ones saved here are remembered by suggestion id.
    isFavorite(place) { return this.savedIds.has(this.savedSuggestionPlaces[place.id] || place.id) },
    async save(place) {
      if (await this.client.save(place) && place.searchId) this.savedSearchIds = [...this.savedSearchIds, place.id]
    },
    favoriteKey(place) { return `${place.searchId || ''}:${place.id}` },
    openFavorite(place) {
      const key = this.favoriteKey(place)
      this.favoritePicker = this.favoritePicker === key ? null : key
    },
    async saveAs(place, label) {
      const saved = this.favorites.find(row => row.id === (this.savedSuggestionPlaces[place.id] || place.id))
      const result = saved ? await this.client.action("labelFavorite", { id: saved.id, label }) : await this.client.save(place, label)
      if (!result) return
      if (place.searchId) {
        this.savedSearchIds = [...new Set([...this.savedSearchIds, place.id])]
        const row = result.favorites.find(row => row.name === place.name && (!place.description || row.address === place.description))
          || result.favorites.find(row => row.name === place.name)
        if (row) this.savedSuggestionPlaces[place.id] = row.id
      }
      this.favoritePicker = null
    },
    async removeFavorite(place) {
      if (!this.isFavorite(place)) return
      const id = this.savedSuggestionPlaces[place.id] || place.id
      this.favoritePicker = null
      const result = await this.client.action("removeFavorite", { id })
      if (!result) return
      for (const [suggestionId, savedId] of Object.entries(this.savedSuggestionPlaces)) {
        if (savedId === id) {
          delete this.savedSuggestionPlaces[suggestionId]
          this.savedSearchIds = this.savedSearchIds.filter(value => value !== suggestionId)
        }
      }
      return result
    },
    setLabel(place, label) { return this.client.action("labelFavorite", { id: place.id, label: place.label === label ? null : label }) },
    placeIcon(place) { return LABELS[place.label]?.icon || (this.isFavorite(place) ? "bi-star-fill" : place.searchId ? "bi-geo-alt-fill" : "bi-clock-history") },
    placeName(place) { return LABELS[place.label]?.name || place.name },
    placeDetail(place) { return place.label ? place.name : place.address || place.description || "" },
    async saveKey(enable = false) { const token = this.token.trim(); this.token = ""; await this.client.action("configure", { patch: enable ? { token, enabled: true } : { token } }) },
    distance(value) {
      const metric = this.data?.isMetric !== false
      return metric ? value < 1000 ? `${Math.round(value)} m` : `${(value / 1000).toFixed(1)} km` :
        value < 160.9344 ? `${Math.round(value / 0.3048 / 10) * 10} ft` : `${(value / 1609.344).toFixed(1)} mi`
    },
    duration(value) { const minutes = Math.max(1, Math.round(value / 60)); return minutes >= 60 ? `${Math.floor(minutes / 60)} hr ${minutes % 60} min` : `${minutes} min` },
  },
  template: `
    <div class="gx-view gx-navigation" :inert="busy || searchPending" :aria-busy="busy || searchPending || undefined">
      <header class="gx-settings__header gx-page-header"><div><h2>Navigation</h2>
        <p>Set a destination, prepare offline maps, and configure navigation and Mapbox.</p></div></header>
      <div class="gx-tabs gx-actions" role="group" aria-label="Navigation tools">
        <button v-for="item in [{id:'route',label:'Destination'},{id:'maps',label:'Offline Maps'},{id:'setup',label:'Setup'}]" :key="item.id"
          type="button" class="gx-btn" :class="tab === item.id ? '' : 'gx-btn--tonal'" :aria-pressed="tab === item.id" @click="selectTab(item.id)">{{ item.label }}</button>
      </div>
      <div v-if="tab === 'maps'" class="gx-navigation__offline">
        <OfflineRoadMapsPanel :mode="mode" :unauthorized="unauthorized" :has-key="!!data?.hasKey" :metric="data?.isMetric !== false" />
        <MapOperationsPanel :mode="mode" :unauthorized="unauthorized" />
      </div>
      <template v-else-if="tab === 'setup'">
        <p v-if="mode !== 'local'" class="gx-note">Connect to your comma to set up navigation and choose a destination.</p>
        <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
        <section class="gx-card gx-navigation__section">
          <h3>Navigation</h3>
          <p>Show directions on your comma. Navigation works with every driving model. Route guidance helps prepare for turns; steering and speed control follow your normal engagement settings.</p>
          <button v-if="data" type="button" class="gx-btn" :class="{'gx-btn--tonal':data.enabled}" :disabled="!controlsAvailable"
            @click="client.action('configure',{patch:{enabled:!data.enabled}})">{{ data.enabled ? 'Turn off navigation' : 'Turn on navigation' }}</button>
        </section>
        <section class="gx-card gx-navigation__section">
          <h3>Mapbox</h3>
          <p>One public Mapbox access token (starting with pk.) handles the map, place and address search, and routes. A separate secret token is not needed.</p>
          <p>Save your token while parked. Galaxy keeps it on your comma and never displays it after saving. Permanent address results can be saved. Search suggestions are temporary and used only for the current route. Favorites and recent destinations are also kept on your comma; going to one skips search, so it uses none of your search allowance. URL-restricted keys may reject map requests.</p>
          <p class="gx-note">Typing suggestions and offline road maps stop just short of Mapbox's free monthly allowance and resume on the 1st. Permanent address lookups are billed by Mapbox. Searches, address lookups, routes and map views are counted here but not limited.</p>
          <dl v-if="usageRows.length" class="gx-navigation__usage" aria-label="Mapbox use this month">
            <template v-for="row in usageRows" :key="row.key"><dt>{{ row.label }}</dt><dd>{{ row.used.toLocaleString() }}<template v-if="row.key !== 'geocoding'"> of {{ row.limit.toLocaleString() }} free</template> this month</dd></template>
          </dl>
          <a class="gx-navigation__token-link" href="https://account.mapbox.com/access-tokens/" target="_blank" rel="noopener noreferrer">Get a Mapbox access token</a>
          <p v-if="data?.hasKey" class="gx-note">A Mapbox key is saved.</p>
          <div class="gx-field-group"><label for="navigation-token">Public Mapbox access token</label>
          <form @submit.prevent="saveKey(false)" class="gx-navigation__search">
            <input id="navigation-token" class="gx-field" type="password" autocomplete="off" v-model="token" placeholder="pk.…" maxlength="2048" required :disabled="!controlsAvailable">
            <button class="gx-btn" type="submit" :disabled="!controlsAvailable || !token.trim()">{{ data?.hasKey ? 'Replace key' : 'Save key' }}</button>
          </form></div>
        </section>
      </template>
      <template v-else>
        <div class="gx-navigation__workspace">
        <div class="gx-navigation__panel">
          <p v-if="mode === 'local' && !data" role="status" class="gx-note">{{ error ? 'Navigation could not be loaded.' : 'Connecting to your comma…' }}</p>
          <button v-if="mode === 'local' && !data && error" type="button" class="gx-btn" @click="client.load()">Try again</button>
          <p v-if="mode !== 'local'" class="gx-card gx-navigation__section gx-note">Connect to your comma to set up navigation and choose a destination.</p>
          <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
          <p v-if="stale && data" class="gx-card gx-navigation__section gx-note">Showing the last received route. Reconnecting before accepting changes.</p>
          <GxNotice v-if="offline" tone="warn">Your comma has no network connection. You can
            <a href="#/navigation/maps" @click.prevent="selectTab('maps')">download maps for offline navigation views</a>
            when you're back online. New routes need internet.</GxNotice>
          <GxNotice v-else-if="usingSavedLocation">Using your last saved location to plan routes online. Offline map downloads aren't required.
            Live guidance starts when GPS is available.</GxNotice>
          <form v-if="ready" @submit.prevent="search" class="gx-navigation__search" role="search" @focusout="onSearchFocusOut">
            <div class="gx-navigation__field">
              <i class="bi bi-search" aria-hidden="true"></i>
              <label for="navigation-search" class="gx-sr-only">Search destinations</label>
              <input id="navigation-search" ref="search" v-model="query" placeholder="Address or place name" minlength="2" maxlength="200" required
                autocomplete="off" enterkeyhint="search" :disabled="!controlsAvailable" role="searchbox"
                @input="typed" @focus="suggestOpen = true" @keydown.escape="closeSuggestions">
              <button v-if="query || results.length" type="button" class="gx-navigation__icon" aria-label="Clear search" @mousedown.prevent @click="clearQuery"><i class="bi bi-x-lg" aria-hidden="true"></i></button>
            </div>
          </form>
          <div v-if="showQuick || showSuggestions" id="navigation-suggestions" class="gx-navigation__suggestions" @mousedown.prevent @focusout="onSearchFocusOut">
            <template v-if="showQuick">
              <div v-if="favorites.length" class="gx-navigation__group"><span>Saved</span></div>
              <div v-for="place in favorites" :key="'saved-' + place.id" class="gx-navigation__row">
                <button type="button" class="gx-navigation__suggestion" :disabled="!controlsAvailable" @click="pick(place)">
                  <i class="bi" :class="placeIcon(place)" aria-hidden="true"></i><span><strong>{{ placeName(place) }}</strong><small v-if="placeDetail(place)">{{ placeDetail(place) }}</small></span></button>
                <button type="button" class="gx-navigation__icon" :aria-label="'Remove ' + place.name + ' from saved places'" :disabled="!controlsAvailable" @click="removeFavorite(place)"><i class="bi bi-x-lg" aria-hidden="true"></i></button>
                <button type="button" class="gx-navigation__icon" :aria-label="'Save ' + place.name + ' as Home, Work, or Other'" :aria-expanded="favoritePicker === favoriteKey(place)" :disabled="!controlsAvailable || place.temporary" :title="place.temporary ? 'Search for an address to save this place' : undefined" @click="openFavorite(place)"><i class="bi bi-star-fill" aria-hidden="true"></i></button>
                <FavoriteChoices v-if="favoritePicker === favoriteKey(place)" :available="controlsAvailable" @choose="saveAs(place, $event)" />
              </div>
              <div v-if="recents.length" class="gx-navigation__group"><span>Recent</span>
                <button type="button" class="gx-navigation__link" :disabled="!controlsAvailable" @click="client.action('clearRecents')">Clear</button></div>
              <div v-for="place in recents" :key="'recent-' + place.id" class="gx-navigation__row">
                <button type="button" class="gx-navigation__suggestion" :disabled="!controlsAvailable" @click="pick(place)">
                  <i class="bi bi-clock-history" aria-hidden="true"></i><span><strong>{{ place.name }}</strong><small v-if="place.address">{{ place.address }}</small></span></button>
                <button type="button" class="gx-navigation__icon" :aria-label="'Save ' + place.name" :aria-expanded="favoritePicker === favoriteKey(place)" :disabled="!controlsAvailable || place.temporary" :title="place.temporary ? 'Search for an address to save this place' : undefined" @click="openFavorite(place)"><i class="bi bi-star" aria-hidden="true"></i></button>
                <button type="button" class="gx-navigation__icon" :aria-label="'Remove ' + place.name + ' from recent places'" :disabled="!controlsAvailable" @click="client.action('removeRecent',{id:place.id})"><i class="bi bi-x-lg" aria-hidden="true"></i></button>
                <FavoriteChoices v-if="favoritePicker === favoriteKey(place)" :available="controlsAvailable" @choose="saveAs(place, $event)" />
              </div>
            </template>
            <template v-else>
              <div v-for="place in localMatches" :key="'local-' + place.id" class="gx-navigation__row">
                <button type="button" class="gx-navigation__suggestion" :disabled="!controlsAvailable" @click="pick(place)">
                  <i class="bi" :class="placeIcon(place)" aria-hidden="true"></i><span><strong>{{ placeName(place) }}</strong><small>{{ placeDetail(place) || (isFavorite(place) ? 'Saved place' : 'Recent') }}</small></span></button>
                <button type="button" class="gx-navigation__icon" :aria-label="'Save ' + place.name" :aria-expanded="favoritePicker === favoriteKey(place)" :disabled="!controlsAvailable || place.temporary" :title="place.temporary ? 'Search for an address to save this place' : undefined" @click="openFavorite(place)"><i class="bi" :class="isFavorite(place) ? 'bi-star-fill' : 'bi-star'" aria-hidden="true"></i></button>
                <FavoriteChoices v-if="favoritePicker === favoriteKey(place)" :available="controlsAvailable" @choose="saveAs(place, $event)" />
              </div>
              <div v-for="place in suggestions" :key="place.id" class="gx-navigation__row">
                <button type="button" class="gx-navigation__suggestion" :disabled="!controlsAvailable" @click="pick(place)">
                  <i class="bi bi-geo-alt-fill" aria-hidden="true"></i><span><strong>{{ place.name }}</strong><small v-if="place.description">{{ place.description }}</small></span></button>
                <button type="button" class="gx-navigation__icon" :aria-label="'Save ' + place.name" :aria-pressed="isFavorite(place)" :aria-expanded="favoritePicker === favoriteKey(place)" :disabled="!controlsAvailable || place.temporary" :title="place.temporary ? 'Search for an address to save this place' : undefined" @click="openFavorite(place)"><i class="bi" :class="isFavorite(place) ? 'bi-star-fill' : 'bi-star'" aria-hidden="true"></i></button>
                <FavoriteChoices v-if="favoritePicker === favoriteKey(place)" :available="controlsAvailable" @choose="saveAs(place, $event)" />
              </div>
            </template>
          </div>
          <div v-if="showShortcuts" class="gx-navigation__shortcuts" aria-label="Saved places">
            <button v-for="place in shortcuts" :key="place.id" type="button" class="gx-navigation__chip" :disabled="!controlsAvailable" @click="pick(place)">
              <i class="bi" :class="placeIcon(place)" aria-hidden="true"></i>{{ placeName(place) }}</button>
          </div>
          <section v-if="data?.destination" class="gx-card gx-navigation__section gx-navigation__destination" :class="{'gx-navigation--stale':stale}">
            <div class="gx-navigation__heading">
              <div><h3 class="gx-navigation__summary-title">{{ data.destination.name }}</h3><p v-if="data.destination.address" class="gx-note">{{ data.destination.address }}</p></div>
              <button type="button" class="gx-navigation__icon gx-navigation__save" :class="{'gx-navigation__save--on':destinationSaved}" :aria-pressed="!!destinationSaved"
                :aria-label="destinationSaved ? 'Change saved place category' : 'Save this place'" :aria-expanded="favoritePicker === favoriteKey(data.destination)" :disabled="!controlsAvailable || data.destination.temporary" :title="data.destination.temporary ? 'Search for an address to save this place' : undefined" @click="openFavorite(data.destination)">
                <i class="bi" :class="destinationSaved ? 'bi-star-fill' : 'bi-star'" aria-hidden="true"></i></button>
            </div>
            <FavoriteChoices v-if="favoritePicker === favoriteKey(data.destination)" :available="controlsAvailable" @choose="saveAs(data.destination, $event)" />
            <div v-if="summary" class="gx-navigation__summary">
              <div><strong>{{duration(summary.duration)}}</strong><span>{{distance(summary.distance)}}</span><span>Arrive {{new Date(Date.now()+summary.duration*1000).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}}</span></div>
            </div>
            <p v-else class="gx-note">{{statusLabel}}</p>
            <template v-if="data.instruction && !stale">
              <p class="gx-navigation__instruction">{{ data.instruction.text }}</p>
              <p class="gx-note">In {{ distance(data.instruction.distanceMeters) }}</p>
            </template>
            <div v-if="data.alternatives?.length > 1" class="gx-navigation__alternatives gx-actions" aria-label="Alternative routes">
              <button v-for="choice in data.alternatives" :key="choice.index" type="button" class="gx-btn" :class="choice.index===data.selectedRoute ? '' : 'gx-btn--tonal'" :aria-pressed="choice.index===data.selectedRoute" :disabled="!controlsAvailable" @click="client.action('selectRoute',{index:choice.index})">{{duration(choice.durationSeconds)}} · {{distance(choice.distanceMeters)}}</button>
            </div>
            <div class="gx-navigation__route-actions gx-actions">
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!controlsAvailable" @click="$refs.search?.focus()"><i class="bi bi-search" aria-hidden="true"></i> Change destination</button>
              <button type="button" class="gx-btn gx-btn--danger" :disabled="!controlsAvailable" @click="client.action('clear')">End navigation</button>
            </div>
          </section>
          <section v-if="data && !data.hasKey" class="gx-card gx-navigation__section"><h3>Connect Mapbox</h3><p>Add your public Mapbox key to search for places and plan a route. Your key stays on your comma.</p>
            <form @submit.prevent="saveKey(true)" class="gx-navigation__search"><label for="navigation-inline-token" class="gx-sr-only">Public Mapbox access token</label><input id="navigation-inline-token" class="gx-field" type="password" autocomplete="off" v-model="token" placeholder="pk.…" maxlength="2048" required :disabled="!controlsAvailable"><button type="submit" class="gx-btn" :disabled="!controlsAvailable || !token.trim()">Save and enable</button></form><button type="button" class="gx-btn gx-btn--tonal" @click="selectTab('setup')">Key details</button>
          </section>
          <section v-else-if="data && !data.enabled" class="gx-card gx-navigation__section"><h3>Navigation is off</h3><button type="button" class="gx-btn" :disabled="!controlsAvailable" @click="client.action('configure',{patch:{enabled:true}})">Turn on navigation</button></section>
          <template v-else>
            <p v-if="busy || searchPending" role="status" class="gx-navigation__busy">{{ searchPending ? 'Searching…' : 'Working…' }}</p>
            <p v-if="searched && !busy && !error && results.length === 0" class="gx-card gx-navigation__section gx-note">No places found. Try a nearby town or a more specific address.</p>
            <ul v-if="results.length" class="gx-navigation__places" aria-label="Search results">
              <li v-for="place in results" :key="place.id" class="gx-navigation__row">
                <button type="button" class="gx-navigation__suggestion" :disabled="!controlsAvailable" @click="pick(place)" :aria-label="'Start navigation to ' + place.name">
                  <i class="bi bi-arrow-up-right" aria-hidden="true"></i><span><strong>{{ place.name }}</strong><small v-if="place.address || place.description">{{ place.address || place.description }}</small><small class="gx-navigation__start">Start navigation</small></span>
                </button>
                <button type="button" class="gx-navigation__icon" :aria-label="(isFavorite(place) ? 'Saved: ' : 'Save ') + place.name" :aria-pressed="isFavorite(place)" :aria-expanded="favoritePicker === favoriteKey(place)" :disabled="!controlsAvailable || place.temporary" :title="place.temporary ? 'Search for an address to save this place' : undefined" @click="openFavorite(place)"><i class="bi" :class="isFavorite(place) ? 'bi-star-fill' : 'bi-star'" aria-hidden="true"></i></button>
                <FavoriteChoices v-if="favoritePicker === favoriteKey(place)" :available="controlsAvailable" @choose="saveAs(place, $event)" />
              </li>
            </ul>
          </template>
        </div>
        <section class="gx-card gx-navigation__preview" aria-label="Route preview">
          <div class="gx-navigation__preview-head"><div class="gx-navigation__step"><div><h3>Your route</h3><p role="status">{{ stale ? 'Reconnecting · last received route' : statusLabel }}</p></div></div>
            <span v-if="summary" class="gx-navigation__trip">{{ duration(summary.duration) }} · {{ distance(summary.distance) }}</span></div>
          <NavigationMap v-if="ready" :data="data" :stale="stale" />
          <div v-else class="gx-navigation__empty"><i class="bi bi-signpost-split" aria-hidden="true"></i><p>{{ mode !== 'local' ? 'Connect to your comma to use navigation.' : 'Set up navigation to show the map.' }}</p><button v-if="mode === 'local' && data" type="button" class="gx-btn gx-btn--tonal" @click="selectTab('setup')">Open navigation setup</button></div>
        </section>
        </div>
      </template>
    </div>`,
}
