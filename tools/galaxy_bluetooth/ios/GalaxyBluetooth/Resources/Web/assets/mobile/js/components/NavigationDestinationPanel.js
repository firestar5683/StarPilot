import { api, showSnackbar } from "../api.js"
import { GxNotice } from "./GxNotice.js"
import {
  getMapboxSearchContext,
  addRouteToMap,
  highlightRoute,
  removeRouteFromMap,
  formatSecondsToHuman,
  formatMetersToHuman,
  formatMetersToMiles,
} from "../../../components/navigation/navigation_utilities.js?v=nav-route-selection-1"

const MAPBOX_STYLE = "mapbox://styles/frogsgomoo/cmcfv151j000o01rcdxebhl76"

let mapboxLoadPromise = null

function loadMapboxGL() {
  if (mapboxLoadPromise) return mapboxLoadPromise
  mapboxLoadPromise = new Promise((resolve, reject) => {
    if (window.mapboxgl) return resolve(window.mapboxgl)
    const link = document.createElement("link")
    link.rel = "stylesheet"
    link.href = "https://api.mapbox.com/mapbox-gl-js/v3.0.1/mapbox-gl.css"
    document.head.appendChild(link)
    const script = document.createElement("script")
    script.src = "https://api.mapbox.com/mapbox-gl-js/v3.0.1/mapbox-gl.js"
    script.onload = () => resolve(window.mapboxgl)
    script.onerror = () => reject(new Error("Failed to load Mapbox GL"))
    document.head.appendChild(script)
  })
  return mapboxLoadPromise
}

function number(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function coordinates(value) {
  if (Array.isArray(value) && value.length >= 2) {
    const longitude = number(value[0])
    const latitude = number(value[1])
    return longitude === null || latitude === null ? null : { longitude, latitude }
  }
  const latitude = number(value?.latitude)
  const longitude = number(value?.longitude)
  return latitude === null || longitude === null ? null : { latitude, longitude }
}

function parseJson(value, fallback) {
  if (Array.isArray(value)) return value
  if (typeof value !== "string" || !value.trim()) return fallback
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : fallback
  } catch (e) {
    return fallback
  }
}

function parseObject(value) {
  if (value && typeof value === "object" && !Array.isArray(value)) return value
  if (typeof value !== "string" || !value.trim()) return null
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null
  } catch (e) {
    return null
  }
}

function labelFor(place) {
  return String(place?.full_address || place?.place_name || place?.name || place?.address || "").trim()
}

function secondaryLabel(place) {
  const primary = String(place?.name || place?.text || "").trim()
  const full = labelFor(place)
  return full && full.toLowerCase() !== primary.toLowerCase() ? full : ""
}

export const NavigationDestinationPanel = {
  name: "NavigationDestinationPanel",
  components: { GxNotice },
  data() {
    return {
      loading: true,
      searching: false,
      loadingRoute: false,
      error: "",
      query: "",
      suggestions: [],
      recentDestinations: [],
      favorites: [],
      destination: null,
      routeSummary: null,
      routes: [],
      selectedRouteId: "main",
      navigationStarted: false,
      isMetric: false,
      mapboxPublic: "",
      mapboxSecret: "",
      language: "",
      lastPosition: null,
      map: null,
      mapReady: false,
      currentMarker: null,
      destinationMarker: null,
      searchTimer: null,
      searchRequest: 0,
      sessionToken: globalThis.crypto?.randomUUID?.() || Math.random().toString(36).slice(2),
    }
  },
  computed: {
    hasMapbox() { return !!this.mapboxPublic },
    hasRoutingKey() { return !!this.mapboxSecret },
    recentPlaces() {
      const seen = new Set()
      return [...this.favorites, ...this.recentDestinations].filter((place) => {
        const coords = coordinates(place)
        const key = coords ? `${coords.latitude}:${coords.longitude}` : labelFor(place).toLowerCase()
        if (!key || seen.has(key)) return false
        seen.add(key)
        return true
      }).slice(0, 10)
    },
    favoriteDestination() {
      const destination = coordinates(this.destination)
      if (!destination) return null
      return this.favorites.find((favorite) => {
        const favoriteCoordinates = coordinates(favorite)
        return favoriteCoordinates && Math.abs(favoriteCoordinates.latitude - destination.latitude) < 0.00001 && Math.abs(favoriteCoordinates.longitude - destination.longitude) < 0.00001
      }) || null
    },
    isFavorite() { return !!this.favoriteDestination },
  },
  async mounted() {
    await this.load()
  },
  beforeUnmount() {
    clearTimeout(this.searchTimer)
    if (this.map) {
      removeRouteFromMap(this.map)
      this.map.remove()
      this.map = null
    }
  },
  methods: {
    secondaryLabel,
    isPlaceFavorite(place) {
      const placeCoordinates = coordinates(place)
      return !!placeCoordinates && this.favorites.some((favorite) => {
        const favoriteCoordinates = coordinates(favorite)
        return favoriteCoordinates && Math.abs(favoriteCoordinates.latitude - placeCoordinates.latitude) < 0.00001 && Math.abs(favoriteCoordinates.longitude - placeCoordinates.longitude) < 0.00001
      })
    },
    async load() {
      try {
        const [nav, favoritePayload] = await Promise.all([
          api.getNavigation(),
          api.getNavigationFavorites().catch(() => ({ favorites: [] })),
        ])
        this.mapboxPublic = String(nav?.mapboxPublic || "").trim()
        this.mapboxSecret = String(nav?.mapboxSecret || "").trim()
        this.language = String(nav?.language || "").trim()
        this.isMetric = !!nav?.isMetric
        this.lastPosition = coordinates(nav?.lastPosition)
        this.favorites = Array.isArray(favoritePayload?.favorites) ? favoritePayload.favorites : []
        this.recentDestinations = parseJson(nav?.previousDestinations, [])
        const saved = parseObject(nav?.destination)
        const savedDestination = coordinates(nav?.destination) || coordinates(saved)
        if (savedDestination) {
          const raw = saved || nav?.destination || {}
          const savedName = String(raw?.name || raw?.text || "").trim()
          const savedRouteId = String(raw?.routeId || "main")
          this.selectedRouteId = /^(?:main|alt-[1-9]\d*)$/.test(savedRouteId) ? savedRouteId : "main"
          this.destination = { ...raw, ...savedDestination, name: savedName || labelFor(raw) || "Current destination" }
          this.query = this.destination.name
          this.navigationStarted = true
        }
      } catch (e) {
        this.error = e?.message || "Failed to load navigation."
      } finally {
        this.loading = false
        if (this.hasMapbox) {
          await this.$nextTick()
          await this.setupMap()
        }
      }
    },
    async setupMap() {
      if (!this.hasMapbox || this.map || !this.$refs.map) return
      try {
        const mapboxgl = await loadMapboxGL()
        mapboxgl.accessToken = this.mapboxPublic
        const center = this.lastPosition || coordinates(this.destination) || { longitude: 0, latitude: 0 }
        this.map = new mapboxgl.Map({
          container: this.$refs.map,
          center: [center.longitude, center.latitude],
          zoom: this.lastPosition ? 15 : (this.destination ? 12 : 2),
          style: MAPBOX_STYLE,
          attributionControl: false,
          logoPosition: "bottom-right",
        })
        this.map.on("load", () => {
          this.mapReady = true
          if (this.lastPosition) this.currentMarker = new mapboxgl.Marker().setLngLat([this.lastPosition.longitude, this.lastPosition.latitude]).addTo(this.map)
          if (this.destination) this.previewDestination(this.destination)
        })
      } catch (e) {
        this.error = e?.message || "Failed to load the map."
      }
    },
    searchContext(query) {
      const context = getMapboxSearchContext(query, this.lastPosition, [this.language, ...(navigator.languages || [navigator.language])])
      if (this.lastPosition) context.proximity = `${this.lastPosition.longitude},${this.lastPosition.latitude}`
      return context
    },
    onInput(event) {
      this.destination = null
      this.routeSummary = null
      this.routes = []
      this.selectedRouteId = "main"
      this.navigationStarted = false
      if (this.map) removeRouteFromMap(this.map)
      this.searchRequest += 1
      this.searching = false
      this.error = ""
      clearTimeout(this.searchTimer)
      const rawValue = event?.target?.value ?? this.query
      this.query = String(rawValue)
      const value = this.query.trim()
      if (value.length < 3 || !this.hasMapbox) {
        this.suggestions = []
        return
      }
      this.searchTimer = setTimeout(() => this.search(value), 350)
    },
    async search(value) {
      const request = ++this.searchRequest
      this.searching = true
      try {
        const payload = await api.mapboxSuggest(value, this.mapboxPublic, this.sessionToken, this.searchContext(value))
        if (request === this.searchRequest) this.suggestions = Array.isArray(payload?.suggestions) ? payload.suggestions : []
      } catch (e) {
        if (request === this.searchRequest) this.error = e?.message || "Destination search failed."
      } finally {
        if (request === this.searchRequest) this.searching = false
      }
    },
    async resolvePlace(place) {
      const primaryLabel = String(place?.name || place?.text || "").trim()
      const placeLabel = primaryLabel || labelFor(place) || this.query.trim()
      let coords = coordinates(place?.geometry?.coordinates) || coordinates(place)
      if (!coords && place?.mapbox_id) {
        const payload = await api.mapboxRetrieve(place.mapbox_id, this.mapboxPublic, this.sessionToken)
        coords = coordinates(payload?.features?.[0]?.geometry?.coordinates)
      }
      if (!coords) {
        const payload = await api.mapboxGeocode(placeLabel, this.mapboxPublic, this.searchContext(placeLabel))
        coords = coordinates(payload?.features?.[0]?.geometry?.coordinates)
      }
      if (!coords) throw new Error("Could not determine that location.")
      return { ...coords, name: primaryLabel || placeLabel, place_name: labelFor(place) || placeLabel }
    },
    async chooseSuggestion(place) {
      this.searching = true
      try {
        this.selectedRouteId = "main"
        this.destination = await this.resolvePlace(place)
        this.query = this.destination.name
        this.suggestions = []
        await this.previewDestination(this.destination)
      } catch (e) {
        this.error = e?.message || "Could not determine that location."
        showSnackbar(this.error, "error")
      } finally {
        this.searching = false
      }
    },
    async resolveQuery() {
      const value = this.query.trim()
      if (!value) return null
      if (this.destination && this.destination.name === value) return this.destination
      return this.resolvePlace({ name: value })
    },
    async setDestination(place = null) {
      if (!this.hasMapbox) {
        showSnackbar("Add a Mapbox public key in App Keys first.", "error")
        return
      }
      if (!this.hasRoutingKey) {
        showSnackbar("Add a Mapbox secret key in App Keys first. It is required for the comma to calculate the on-device route and provide navigation turn desires.", "error")
        return
      }
      this.loadingRoute = true
      try {
        this.destination = place || await this.resolveQuery()
        if (!this.destination) throw new Error("Enter a destination first.")
        const selectedRouteId = this.selectedRouteId || this.routeSummary?.routeId || "main"
        this.destination = { ...this.destination, routeId: selectedRouteId }
        await api.setNavigation(this.destination)
        this.navigationStarted = true
        this.query = this.destination.name
        this.suggestions = []
        await this.previewDestination(this.destination, selectedRouteId)
        showSnackbar("Destination set.")
      } catch (e) {
        this.error = e?.message || "Failed to set destination."
        showSnackbar(this.error, "error")
      } finally {
        this.loadingRoute = false
      }
    },
    async cancelNavigation() {
      try {
        await api.clearNavigation()
        this.navigationStarted = false
        this.destination = null
        this.routeSummary = null
        this.routes = []
        this.selectedRouteId = "main"
        this.query = ""
        this.suggestions = []
        if (this.map) removeRouteFromMap(this.map)
        this.destinationMarker?.remove()
        this.destinationMarker = null
        showSnackbar("Navigation cancelled.")
      } catch (e) {
        showSnackbar(e?.message || "Could not cancel navigation.", "error")
      }
    },
    async toggleFavorite() {
      const destination = coordinates(this.destination)
      if (!destination) return
      const favorite = this.favoriteDestination
      try {
        if (favorite) {
          await api.deleteNavigationFavorite(favorite)
          showSnackbar("Removed from favorites.")
        } else {
          await api.navigationFavorite({
            name: this.destination.name || this.query || "Favorite destination",
            longitude: destination.longitude,
            latitude: destination.latitude,
            routeId: this.routeSummary?.routeId || null,
          })
          showSnackbar("Added to favorites.")
        }
        const payload = await api.getNavigationFavorites()
        this.favorites = Array.isArray(payload?.favorites) ? payload.favorites : []
      } catch (e) {
        showSnackbar(e?.message || "Could not update favorites.", "error")
      }
    },
    formatDistance(value) {
      return this.isMetric ? formatMetersToHuman(value, true) : formatMetersToMiles(value)
    },
    formatDuration(value) { return formatSecondsToHuman(value) },
    formatEta(value) {
      const eta = new Date(Date.now() + Number(value || 0) * 1000)
      return eta.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
    },
    routeId(index) { return index === 0 ? "main" : `alt-${index}` },
    selectRoute(route, routeId = "main") {
      if (!route) return
      this.selectedRouteId = routeId
      if (this.destination) this.destination = { ...this.destination, routeId }
      this.routeSummary = {
        distance: Number(route.distance) || 0,
        duration: Number(route.duration) || 0,
        routeId,
      }
      if (this.map && this.routes.length) highlightRoute(this.map, this.routes, routeId)
    },
    async previewDestination(place, preferredRouteId = null) {
      if (!this.mapReady || !this.map || !place) return
      const mapboxgl = window.mapboxgl
      this.destinationMarker?.remove()
      this.destinationMarker = new mapboxgl.Marker({ color: "#9d72ff" }).setLngLat([place.longitude, place.latitude]).addTo(this.map)
      if (!this.lastPosition) {
        this.routeSummary = null
        this.routes = []
        this.selectedRouteId = "main"
        this.map.flyTo({ center: [place.longitude, place.latitude], zoom: 14 })
        return
      }
      try {
        const payload = await api.mapboxDirections(this.lastPosition, place, this.mapboxPublic)
        const routes = Array.isArray(payload?.routes) ? payload.routes : []
        if (routes.length) {
          const requestedRouteId = preferredRouteId || place.routeId || this.selectedRouteId || "main"
          const selectedIndex = routes.findIndex((_, index) => this.routeId(index) === requestedRouteId)
          const selectedRouteId = selectedIndex >= 0 ? requestedRouteId : "main"
          this.routes = routes
          this.selectRoute(routes[selectedIndex >= 0 ? selectedIndex : 0], selectedRouteId)
          removeRouteFromMap(this.map)
          addRouteToMap(
            this.map,
            routes,
            [this.lastPosition.longitude, this.lastPosition.latitude],
            [place.longitude, place.latitude],
            (route, routeId) => this.selectRoute(route, routeId),
            this.isMetric,
            () => this.selectedRouteId,
          )
        } else {
          this.routeSummary = null
          this.routes = []
          this.selectedRouteId = "main"
          this.map.fitBounds([[this.lastPosition.longitude, this.lastPosition.latitude], [place.longitude, place.latitude]], { padding: 80, duration: 500 })
        }
      } catch (e) {
        this.routeSummary = null
        this.routes = []
        this.selectedRouteId = "main"
        this.map.fitBounds([[this.lastPosition.longitude, this.lastPosition.latitude], [place.longitude, place.latitude]], { padding: 80, duration: 500 })
      }
    },
    usePlace(place) { this.chooseSuggestion(place) },
  },
  template: `
    <div class="gx-navigation-stage">
      <div v-if="loading || !hasMapbox" class="gx-navigation-empty gx-card">
        <div class="gx-loading">{{ loading ? 'Loading navigation...' : 'Map unavailable until a Mapbox key is configured.' }}</div>
        <p v-if="!hasMapbox && !loading">Add a Mapbox public key in <a href="#/navigation/keys">App Keys</a> to search destinations and show the map.</p>
      </div>
      <div v-else ref="map" class="gx-navigation-map"></div>

      <div v-if="hasMapbox && !loading" class="gx-navigation-overlay">
        <GxNotice v-if="!hasRoutingKey" tone="warn" icon="bi-key-fill" style="margin:0;">
          The map and destination search only use your public Mapbox key. Add a <a href="#/navigation/keys">secret Mapbox key in App Keys</a> before starting navigation so the comma can calculate the on-device route and provide turn desires.
        </GxNotice>
        <section class="gx-navigation-search gx-card">
          <div class="gx-navigation-search__row">
            <i class="bi bi-search" aria-hidden="true"></i>
            <input class="gx-field" v-model="query" @input="onInput" @keyup.enter="setDestination()" placeholder="Search here" aria-label="Search for a destination" autocomplete="off" />
            <button type="button" class="gx-icon-btn gx-navigation-send" :disabled="loadingRoute || searching || !query.trim() || !hasRoutingKey" @click="setDestination()" aria-label="Send destination" :title="hasRoutingKey ? 'Send destination' : 'A Mapbox secret key is required to start navigation'"><i class="bi bi-send-fill"></i></button>
          </div>
          <div v-if="searching" class="gx-navigation-status">Searching...</div>
          <div v-if="suggestions.length" class="gx-navigation-suggestions">
            <button v-for="place in suggestions" :key="place.mapbox_id || place.id || place.name" type="button" class="gx-navigation-suggestion" @click="chooseSuggestion(place)">
              <span><strong>{{ place.name || place.text || place.place_name || 'Unnamed location' }}</strong><small>{{ secondaryLabel(place) }}</small></span>
              <i class="bi bi-chevron-right"></i>
            </button>
          </div>
        </section>

        <section v-if="destination" class="gx-navigation-summary gx-card">
          <div class="gx-navigation-summary__title">
            <span class="gx-navigation-summary__name">{{ destination.name || query || 'Destination' }}</span>
            <button type="button" class="gx-icon-btn gx-navigation-summary__fav" :class="{ active: isFavorite }" :aria-pressed="isFavorite" :title="isFavorite ? 'Remove from favorites' : 'Add to favorites'" @click="toggleFavorite">
              <i class="bi" :class="isFavorite ? 'bi-heart-fill' : 'bi-heart'"></i>
            </button>
          </div>
          <div v-if="routeSummary" class="gx-navigation-metrics">
            <div class="gx-navigation-metric"><i class="bi bi-signpost-2" aria-hidden="true"></i><span>Distance</span><strong>{{ formatDistance(routeSummary.distance) }}</strong></div>
            <div class="gx-navigation-metric"><i class="bi bi-clock" aria-hidden="true"></i><span>Duration</span><strong>{{ formatDuration(routeSummary.duration) }}</strong></div>
            <div class="gx-navigation-metric"><i class="bi bi-clock-history" aria-hidden="true"></i><span>ETA</span><strong>{{ formatEta(routeSummary.duration) }}</strong></div>
          </div>
          <div v-if="routes.length > 1" class="gx-navigation-route-picker" aria-label="Choose a route">
            <button v-for="(route, index) in routes" :key="routeId(index)" type="button"
              class="gx-navigation-route-option" :class="{ selected: selectedRouteId === routeId(index) }"
              :aria-pressed="selectedRouteId === routeId(index)" :aria-label="'Select route ' + (index + 1)"
              @click="selectRoute(route, routeId(index))">
              <strong>Route {{ index + 1 }}</strong>
              <small>{{ formatDistance(route.distance) }} · {{ formatDuration(route.duration) }}</small>
            </button>
          </div>
          <div class="gx-navigation-summary__actions">
            <button v-if="navigationStarted" type="button" class="gx-btn gx-btn--danger" @click="cancelNavigation"><i class="bi bi-x-lg"></i> Cancel Navigation</button>
            <button v-else type="button" class="gx-btn gx-btn--success" :disabled="loadingRoute || !hasRoutingKey" :title="hasRoutingKey ? 'Start Navigation' : 'A Mapbox secret key is required to start navigation'" @click="setDestination(destination)"><i class="bi bi-sign-turn-right"></i> {{ loadingRoute ? 'Calculating...' : 'Start Navigation' }}</button>
          </div>
        </section>

        <section v-if="recentPlaces.length && !suggestions.length && !query && !destination" class="gx-navigation-recent gx-card">
          <div class="gx-navigation-recent__title">Recent and favorite destinations</div>
          <button v-for="place in recentPlaces" :key="place.id || place.name" type="button" class="gx-navigation-suggestion" @click="usePlace(place)">
            <span><strong>{{ place.name || place.place_name }}</strong><small>{{ secondaryLabel(place) }}</small></span>
            <i class="bi" :class="isPlaceFavorite(place) ? 'bi-heart-fill' : 'bi-clock-history'"></i>
          </button>
        </section>
        <GxNotice v-if="error" tone="danger" :text="error" style="margin:0;" />
      </div>
    </div>
  `,
}
