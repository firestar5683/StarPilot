import { rememberInstallPrompt } from "./install-app.js"
import { toggleHaptic } from "./haptics.js"
import { GxState } from "./state.js"
import { BottomNav, NAV, primaryTab } from "./bottom-nav.js"
import { GalaxyLoading } from "./loading-screen.js"
import { GxNotice } from "./notice.js"
import { createApp, reactive, defineAsyncComponent } from "../vendor/vue/vue.esm-browser.js"
import { route, navigate, navigateBack, ensureBackEntry, setRouteLeaveGuard, startRouter } from "./router.js"
import { loadCatalog } from "./startup.js"
import { Tools } from "./tools.js"
window.addEventListener("beforeinstallprompt", rememberInstallPrompt)
const Logs = page(() => import("./logs.js").then((module) => module.Logs))
const SoftwarePage = page(() => import("./software-status.js").then((module) => module.SoftwarePage))
const NavigationPage = page(() => import("./navigation.js").then((module) => module.NavigationPage))
const ModelsPage = page(() => import("./models.js").then((module) => module.ModelsPage))
const LaboratoryPage = page(() => import("./model-laboratory.js").then((module) => module.LaboratoryPage))
import { SettingsPage } from "./settings.js"
import { ToggleSearch } from "./toggle-search.js"
const PlotsPage = page(() => import("./plots.js").then((module) => module.PlotsPage))
const FlmPage = page(() => import("./flm.js").then((module) => module.FlmPage))
import { LocalAuth } from "./auth-client.js"
import { Home } from "./home.js"
import { MenuTile } from "./menu-tile.js"
const LocalRecordingsPage = page(() => import("./record-history.js").then((module) => module.LocalRecordingsPage))
const CamerasPage = page(() => import("./cameras.js").then((module) => module.CamerasPage))
const SentryEventsPage = page(() => import("./sentry.js").then((module) => module.SentryEventsPage))
const VasmPage = page(() => import("./vasm.js").then((module) => module.VasmPage))
const PipPage = page(() => import("./pip.js").then((module) => module.PipPage))
import { DrivingPage, drivingPage } from "./driving.js"
const LongitudinalCurvesPage = page(() => import("./longitudinal-curves.js").then((module) => module.LongitudinalCurvesPage))
import { DevicePreferencesPage, devicePage } from "./device-preferences.js"
const BluetoothPage = page(() => import("./bluetooth.js").then((module) => module.BluetoothPage))
const AndroidAutoPage = page(() => import("./android-auto.js").then((module) => module.AndroidAutoPage))
const VehicleControlsPage = page(() => import("./vehicle-controls.js").then((module) => module.VehicleControlsPage))
const OnroadLayoutPage = page(() => import("./onroad-layout.js").then((module) => module.OnroadLayoutPage))
const GalaxyPage = page(() => import("./galaxy.js").then((module) => module.GalaxyPage))
import { DevicePicker } from "./device-picker.js"
import { DeviceState } from "./device-state.js"
import { spawnAmbientStars } from "./ambient-stars.js"

function page(loader) {
  return defineAsyncComponent({
    loader, delay: 150, timeout: 10000,
    loadingComponent: { components: { GxState }, template: '<GxState loading>Opening page…</GxState>' },
    errorComponent: { components: { GxState }, template: '<GxState tone="danger">This page could not open.<template #actions><button class="gx-btn" @click="reload">Reload page</button></template></GxState>',
      methods: { reload() { location.reload() } } },
    onError(_error, retry, fail, attempts) { if (attempts < 2) setTimeout(retry, 500); else fail() },
  })
}

const THEME_KEY = "galaxy-preview-theme"
const PIN_KEY = "galaxy-preview-nav-pinned"
const stored = (key) => { try { return localStorage.getItem(key) } catch { return null } }
const save = (key, value) => { try { localStorage.setItem(key, value) } catch {} }

const state = reactive({
  tools: [],
  loading: true,
  startupPending: false,
  error: "",
  pageError: "",
  monitorMode: "sample",
  drawerOpen: false,
  navPinned: stored(PIN_KEY) === "true",
  theme: stored(THEME_KEY) === "light" ? "light" : "dark",
  searchPage: "",
})
const authState = reactive({ status: "checking", error: "", localAccess: false, gatewayAccess: false })
const authForm = reactive({ password: "" })
const auth = new LocalAuth({ publish: (update) => {
  Object.assign(authState, update)
  if (update.status === "unavailable") scheduleReconnect()
} })



createApp({
  components: { BottomNav, GalaxyLoading, Home, Tools, Logs, SoftwarePage, NavigationPage, ModelsPage, LaboratoryPage, SettingsPage, ToggleSearch, PlotsPage, FlmPage, LocalRecordingsPage, CamerasPage, SentryEventsPage, VasmPage, PipPage, DrivingPage, DevicePreferencesPage, BluetoothPage, AndroidAutoPage, LongitudinalCurvesPage, VehicleControlsPage, OnroadLayoutPage, GalaxyPage, DevicePicker, DeviceState, MenuTile },
  data: () => ({ state, authState, authForm, route, NAV, routeDirection: 1, nextLayoutLeavePresentation: "inline" }),
  computed: {
    visibleTools() { return state.tools.filter(tool => tool.visibility !== "authenticated" ||
      (state.monitorMode === "local" && authState.status === "authenticated")).sort((a, b) =>
        Number(a.path === "/galaxy") - Number(b.path === "/galaxy")) },
    currentTool() { return state.tools.find((tool) => route.path === tool.path || route.path.startsWith(tool.path + "/")) },
    drivingSettingsPage() { return drivingPage(route.path) },
    deviceSettingsPage() { return devicePage(route.path) },
    pageName() {
      if (this.currentTool) return this.currentTool.name
      return NAV.find((item) => item.path === route.path)?.name || "This page"
    },
    isLight() { return state.theme === "light" },
    connectionLabel() {
      if (state.monitorMode !== "local") return "Preview"
      if (authState.status === "authenticated") return authState.localAccess ? "Local connection" : "Remote connection"
      return authState.status === "checking" ? "Connecting…" : "Not connected"
    },
  },
  errorCaptured() { state.pageError = "This page could not finish loading."; return false },
  watch: { 'route.path'(path, previous) {
    state.pageError = ""
    this.routeDirection = route.direction < 0 || primaryTab(path) < primaryTab(previous) ? -1 : 1
  } },
  methods: {
    toggleHaptic,
    setPageActive(element, active) { element.inert = !active; element.setAttribute("aria-hidden", String(!active)) },
    reloadPage() { location.reload() },
    go(path) { navigate(path, () => { state.drawerOpen = false; state.searchPage = "" }) },
    goFromMenu(path) {
      state.drawerOpen = false
      if (path === route.path) return
      this.nextLayoutLeavePresentation = "modal"
      this.go(path)
    },
    openSearchHit(hit) { navigate("/settings", () => { state.drawerOpen = false; state.searchPage = hit.page }) },
    returnFromSearch() { state.searchPage = "" },
    returnToDriving() { this.go("/driving") },
    returnToDevice() { this.go("/device-preferences") },
    ensureBackEntry,
    routeBack() { state.drawerOpen = false; navigateBack() },
    toggleTheme() {
      state.theme = this.isLight ? "dark" : "light"
      document.documentElement.dataset.theme = state.theme
      save(THEME_KEY, state.theme)
    },
    togglePin() {
      state.navPinned = !state.navPinned
      state.drawerOpen = state.navPinned
      save(PIN_KEY, String(state.navPinned))
    },
    isActive(path) { return route.path === path || route.path.startsWith(path + "/") },
    async signIn() {
      const password = authForm.password
      authForm.password = ""
      await auth.login(password)
    },
    async signOut() { await auth.logout() },
    sessionExpired() { if (initializing) return; auth.expired(); initialize() },
  },
  mounted() {
    document.documentElement.dataset.theme = state.theme
    this.visibility = () => {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
      if (!document.hidden && (state.error || authState.status === "unavailable") && !initializing) initialize()
    }
    document.addEventListener("visibilitychange", this.visibility)
    setRouteLeaveGuard((proceed, { back } = {}) => {
      if (back && this.$refs.activeSettings?.navigateBack()) return
      if (back && state.searchPage) { this.returnFromSearch(); return }
      const presentation = this.nextLayoutLeavePresentation
      this.nextLayoutLeavePresentation = "inline"
      if (this.$refs.activeLayout) this.$refs.activeLayout.requestLeave(proceed, presentation)
      else if (this.$refs.activeSettings) this.$refs.activeSettings.requestRouteLeave(proceed)
      else proceed()
    })
  },
  beforeUnmount() {
    reconnectEnabled = false
    clearTimeout(reconnectTimer)
    startupGeneration++
    document.removeEventListener("visibilitychange", this.visibility)
  },
  template: `
    <div class="gx-app" :class="{'gx-nav-pinned':state.navPinned}" @change.capture="toggleHaptic">
      <header class="gx-appbar">
        <button type="button" class="gx-icon-btn gx-appbar__back gx-back-btn" aria-label="Back" @click="routeBack"><i class="bi bi-arrow-left"></i></button>
        <div class="gx-appbar__pill">
          <button type="button" class="gx-appbar__home" aria-label="Galaxy Home" @click="go('/')"><span class="gx-brand" aria-hidden="true"></span><span class="gx-appbar__title">Galaxy</span></button>
          <ToggleSearch :enabled="state.monitorMode === 'local' && authState.status === 'authenticated'" :unauthorized="sessionExpired" :open-page="openSearchHit" />
          <div class="gx-appbar__right"><DeviceState v-if="state.monitorMode === 'local' && authState.status === 'authenticated'" :unauthorized="sessionExpired" :connection="connectionLabel" />
            <span v-else class="gx-status-pill"><span class="gx-status-dot offline"></span>{{ connectionLabel }}</span>
            <button v-if="state.monitorMode === 'local' && authState.status === 'authenticated' && !authState.localAccess && !authState.gatewayAccess" type="button" class="gx-btn gx-btn--tonal" @click="signOut">Sign out</button></div>
        </div>
        <button type="button" class="gx-icon-btn gx-theme-toggle" :aria-label="isLight ? 'Switch to dark mode' : 'Switch to light mode'" @click="toggleTheme"><i class="bi" :class="isLight ? 'bi-moon-stars-fill' : 'bi-sun-fill'"></i></button>
        <button type="button" class="gx-icon-btn gx-appbar__menu" aria-label="Menu" @click="state.drawerOpen=true"><i class="bi bi-list"></i></button>
      </header>
      <div v-if="state.drawerOpen && !state.navPinned" class="gx-underlay" @click="state.drawerOpen=false"></div>
      <aside class="gx-drawer" :class="{open:state.drawerOpen || state.navPinned}" aria-label="Galaxy navigation">
        <div class="gx-drawer__header"><span class="gx-brand" aria-hidden="true"></span><span class="gx-drawer-title">Galaxy</span><button type="button" class="gx-icon-btn gx-drawer__pin" :aria-pressed="state.navPinned" :aria-label="state.navPinned ? 'Unpin navigation' : 'Pin navigation'" @click="togglePin"><i class="bi" :class="state.navPinned ? 'bi-pin-angle-fill' : 'bi-pin-angle'"></i></button></div>
        <div class="gx-nav-section"><div class="gx-nav-section__title">Main</div>
          <button v-for="item in NAV.slice(0,3)" :key="item.path" type="button" class="gx-nav-item" :class="{active:isActive(item.path)}" @click="goFromMenu(item.path)"><i class="bi" :class="item.icon"></i><span>{{ item.name }}</span></button>
        </div>
        <div class="gx-nav-section"><div class="gx-nav-section__title">Recordings</div><button type="button" class="gx-nav-item" :class="{active:isActive('/recordings')}" @click="goFromMenu('/recordings')"><i class="bi bi-camera-reels"></i><span>Recordings</span></button></div>
        <div class="gx-nav-section"><div class="gx-nav-section__title">Tools</div>
          <button v-for="tool in visibleTools.filter(tool => tool.path !== '/galaxy')" :key="tool.path" type="button" class="gx-nav-item" :class="{active:isActive(tool.path)}" @click="goFromMenu(tool.path)"><i class="bi" :class="tool.icon"></i><span>{{ tool.name }}</span></button>

        </div>
        <div class="gx-nav-footer"><DevicePicker />
          <button type="button" class="gx-nav-item" :class="{active:isActive('/galaxy')}" @click="goFromMenu('/galaxy')"><i class="bi bi-globe"></i><span>Install Galaxy / Tunnel</span></button>
        </div>
      </aside>
      <main class="gx-content" :style="{'--route-direction': routeDirection}"><div class="gx-route-stage">
        <Transition name="gx-route" @before-enter="setPageActive($event, true)" @before-leave="setPageActive($event, false)"><div class="gx-route" :key="route.path">
        <template v-if="state.loading && !state.error"><GalaxyLoading v-if="state.startupPending" message="Connecting to your device…" /></template>
        <GxNotice v-else-if="state.error" tone="danger">{{ state.error }}</GxNotice>
        <section v-else-if="state.monitorMode === 'local' && authState.status !== 'authenticated'" class="gx-card gx-auth" aria-label="Galaxy sign in">
          <h2>Galaxy access</h2>
          <p v-if="authState.status === 'checking'">Checking Galaxy access…</p>
          <p v-else-if="authState.status === 'setup_required'">Remote Galaxy access is not configured.</p>
          <p v-else-if="authState.status === 'unavailable'">Galaxy access is unavailable.</p>
          <p v-else-if="authState.status === 'gateway_login'"><a class="gx-btn" href="/">Reconnect to Galaxy</a></p>
          <form v-else @submit.prevent="signIn"><label for="galaxy-password">Password</label><input id="galaxy-password" class="gx-field" type="password" v-model="authForm.password" minlength="8" maxlength="255" autocomplete="current-password" required><button class="gx-btn" type="submit">Sign in</button></form>
          <GxNotice v-if="authState.error" tone="danger">{{ authState.error }}</GxNotice>

        </section>
        <GxNotice v-else-if="state.pageError" tone="danger">{{ state.pageError }} <button class="gx-btn" @click="reloadPage">Reload page</button></GxNotice>
        <Home v-else-if="route.path === '/'" :mode="state.monitorMode" :unauthorized="sessionExpired" :go="go" />
        <LocalRecordingsPage v-else-if="route.path === '/recordings'" :mode="state.monitorMode" :unauthorized="sessionExpired" />
        <CamerasPage v-else-if="route.path === '/cameras'" :mode="state.monitorMode" :go="go" :unauthorized="sessionExpired" />
        <SentryEventsPage v-else-if="['/cameras/events', '/cameras/sentry-settings'].includes(route.path)" :mode="state.monitorMode" :unauthorized="sessionExpired" :go="go" />
        <PipPage v-else-if="route.path === '/cameras/pip'" :mode="state.monitorMode" :unauthorized="sessionExpired" :go="go" />
        <VasmPage v-else-if="route.path === '/cameras/vasm'" :mode="state.monitorMode" :unauthorized="sessionExpired" :go="go" />
        <Tools v-else-if="route.path === '/tools'" :tools="visibleTools" :mode="state.monitorMode" />
        <SettingsPage @nested="ensureBackEntry" ref="activeSettings" v-else-if="route.path === '/developer/connect'" :mode="state.monitorMode" :unauthorized="sessionExpired" initial-section="developer" />
        <GalaxyPage v-else-if="route.path === '/galaxy'" :mode="state.monitorMode" :unauthorized="sessionExpired" />
        <OnroadLayoutPage ref="activeLayout" v-else-if="['/theme_maker', '/theme_maker/android_auto'].includes(route.path)" :key="route.path" :projection="route.path === '/theme_maker/android_auto'" :mode="state.monitorMode" :unauthorized="sessionExpired" @target="go($event === 'projection' ? '/theme_maker/android_auto' : '/theme_maker')" @close="routeBack" />
        <Logs v-else-if="route.path === '/logs' || route.path.startsWith('/logs/') || ['/troubleshoot', '/manage_tmux'].includes(route.path)" :path="route.path === '/troubleshoot' ? '/logs/troubleshoot' : route.path === '/manage_tmux' ? '/logs/tmux' : route.path" :mode="state.monitorMode" :unauthorized="sessionExpired" />
        <SoftwarePage v-else-if="route.path === '/system'" :mode="state.monitorMode" :unauthorized="sessionExpired" />
        <NavigationPage v-else-if="route.path === '/navigation'" :mode="state.monitorMode" :unauthorized="sessionExpired" :go="go" />
        <ModelsPage v-else-if="route.path === '/manage_models'" :mode="state.monitorMode" :unauthorized="sessionExpired" />
        <LaboratoryPage v-else-if="route.path === '/model_laboratory'" :mode="state.monitorMode" :unauthorized="sessionExpired" />
        <BluetoothPage v-else-if="route.path === '/bluetooth'" :mode="state.monitorMode" :unauthorized="sessionExpired" />
        <AndroidAutoPage v-else-if="route.path === '/android-auto'" :mode="state.monitorMode" :local-access="authState.localAccess" :unauthorized="sessionExpired" />
        <VehicleControlsPage v-else-if="route.path === '/vehicle'" :mode="state.monitorMode" :unauthorized="sessionExpired" />
        <DevicePreferencesPage v-else-if="route.path === '/device-preferences'" :mode="state.monitorMode" :go="go" />
        <SettingsPage @nested="ensureBackEntry" ref="activeSettings" v-else-if="deviceSettingsPage" :key="deviceSettingsPage" :mode="state.monitorMode" :unauthorized="sessionExpired" :initial-page="deviceSettingsPage" :title="deviceSettingsPage === 'sounds' ? 'Sounds & Alerts' : 'Display'" :return-to="returnToDevice" />
        <DrivingPage v-else-if="route.path === '/driving'" :mode="state.monitorMode" :go="go" />
        <LongitudinalCurvesPage v-else-if="route.path === '/driving/longitudinal-curves'" :mode="state.monitorMode" :unauthorized="sessionExpired" :go="go" />
        <SettingsPage @nested="ensureBackEntry" ref="activeSettings" v-else-if="drivingSettingsPage" :key="drivingSettingsPage" :mode="state.monitorMode" :unauthorized="sessionExpired" :initial-page="drivingSettingsPage" :title="'Driving settings · ' + drivingSettingsPage.replaceAll('_', ' ')" :return-to="returnToDriving" />
        <SettingsPage @nested="ensureBackEntry" ref="activeSettings" v-else-if="route.path === '/settings'" :key="state.searchPage || 'hub'" :mode="state.monitorMode" :unauthorized="sessionExpired"
          :initial-page="state.searchPage || 'hub'" :return-to="state.searchPage ? returnFromSearch : null" />
        <SettingsPage @nested="ensureBackEntry" ref="activeSettings" v-else-if="route.path === '/appearance'" :mode="state.monitorMode" :unauthorized="sessionExpired" initial-page="appearance" title="Driving Screen Widgets" />
        <div v-else-if="route.path === '/tuning'" class="gx-view">
          <h2>Plots &amp; Analysis</h2>
          <p class="gx-note">Live control observations and recorded-drive analysis.</p>
          <div class="gx-grid">
            <MenuTile icon="bi-graph-up" title="Live plots" description="Compare steering and acceleration targets with measured response" @select="go('/tuning/plots')" />
            <MenuTile icon="bi-file-earmark-bar-graph" title="Recorded-drive analysis" description="Review lateral tracking from saved drives" @select="go('/tuning/flm')" />
          </div>
        </div>
        <PlotsPage v-else-if="route.path === '/tuning/plots'" :mode="state.monitorMode" :unauthorized="sessionExpired" />
        <FlmPage v-else-if="route.path === '/tuning/flm'" :mode="state.monitorMode" :unauthorized="sessionExpired" :go="go" />
        <GxState v-else :title="pageName">This capability is unavailable in this build. No operation was attempted.</GxState>
      </div></Transition></div></main>
      <BottomNav :path="route.path" @navigate="go" />
    </div>
  `,
}).component("GxState", GxState).component("GxNotice", GxNotice).mount("#galaxy-app")

spawnAmbientStars(document.getElementById("galaxy-bg"))

startRouter()

let startupGeneration = 0
let reconnectTimer = null
let initializing = false
let reconnectEnabled = true
function scheduleReconnect() {
  if (!reconnectEnabled || document.hidden || initializing || reconnectTimer !== null) return
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null
    if (reconnectEnabled && !document.hidden && !initializing && (state.error || authState.status === "unavailable")) initialize()
  }, 3000)
}
async function initialize() {
  const generation = ++startupGeneration
  initializing = true
  clearTimeout(reconnectTimer)
  reconnectTimer = null
  state.loading = !state.tools.length
  const loadingDelay = setTimeout(() => { if (generation === startupGeneration) state.startupPending = true }, 150)
  try {
    const catalog = await loadCatalog()
    if (generation !== startupGeneration) return
    state.monitorMode = catalog.mode
    state.tools = catalog.tools
    state.error = ""
    if (state.monitorMode === "local") await auth.check()
    else authState.status = "preview"
  } catch {
    if (generation === startupGeneration) state.error = "Galaxy could not connect. Reconnecting automatically…"
  } finally {
    clearTimeout(loadingDelay)
    if (generation === startupGeneration) {
      state.loading = state.startupPending = false
      initializing = false
      if (state.error || authState.status === "unavailable") scheduleReconnect()
    }
  }
}
initialize()
