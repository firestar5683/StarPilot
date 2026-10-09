import { store, navigate, goBack, toolHref, toggleTheme, toggleNavPinned } from "../store.js"
import { api } from "../api.js"
import { usePolling } from "../composables.js"
import { languageState, setLanguage, t } from "../i18n.js"
import { DevicePicker } from "./DevicePicker.js"

const NAV = {
  recordings: [
    { name: "Recordings", link: "/recordings", icon: "bi-camera-reels" },
  ],
  tools: [
    { name: "Bluetooth", link: "/bluetooth", icon: "bi-bluetooth" },
    { name: "Cameras & Monitoring", link: "/cameras", icon: "bi-camera-video" },
    { name: "Galaxy", link: "/galaxy", icon: "bi-globe2" },
    { name: "Logs & Diagnostics", link: "/logs", icon: "bi-exclamation-triangle" },
    { name: "Model Manager", link: "/manage_models", icon: "bi-cpu" },
    { name: "Navigation & Maps", link: "/navigation", icon: "bi-map" },
    { name: "System Tools", link: "/system", icon: "bi-arrow-repeat" },
    { name: "Model Laboratory", link: "/model_laboratory", icon: "bi-bezier2" },
    { name: "Plots", link: "/plots", icon: "bi-graph-up-arrow" },
    { name: "Testing Ground", link: "/testing_ground", icon: "bi-bezier2" },
    { name: "Theme Maker", link: "/theme_maker", icon: "bi-palette-fill" },
    { name: "Tuning, Plots & Testing", link: "/tuning", icon: "bi-sign-turn-right" },
    { name: "Vehicle Controls", link: "/vehicle", icon: "bi-car-front" },
  ],
}

const BOTTOM_NAV = [
  { name: "Home", link: "/", icon: "bi-house-fill" },
  { name: "Toggles", link: "/settings", icon: "bi-toggle-on" },
  { name: "Tools", link: "/tools", icon: "bi-tools" },
  { name: "Recordings", link: "/recordings", icon: "bi-camera-reels" },
]

export const AppShell = {
  name: "AppShell",
  components: { DevicePicker },
  data() {
    return { store, BOTTOM_NAV, NAV, searchNarrow: false }
  },
  computed: {
    online() { return store.online },
    statusLabel() { return store.online ? t(store.deviceStatus, store.deviceStatus) : t("Offline") },
    isLight() { return store.theme === "light" },
    navPinned() { return store.navPinned },
    drawerOpen: {
      get() { return store.drawerOpen },
      set(v) { store.drawerOpen = v },
    },
    activePath() { return store.route },
    search: {
      get() { return store.search },
      set(v) { store.search = v },
    },
    searchPlaceholder() {
      return this.searchNarrow ? t("Search") : t("Search toggles...")
    },
  },
  watch: {
    "store.search"(q) {
      if (q && store.route !== "/settings" && !store.route.startsWith("/settings/")) {
        navigate("/settings")
      }
    },
  },
  methods: {
    tr(key, fallback = key) { return t(key, fallback) },
    closeDrawer() { if (!store.navPinned) store.drawerOpen = false },
    back() { goBack() },
    async refreshStatus() {
      try {
        const payload = await api.getDeviceStatus()
        if (!payload) throw new Error("no status")
        store.online = true
        store.deviceStatus = String(payload.status || "Parked")
      } catch (e) {
        store.online = false
      }
    },
    async loadLanguage() {
      try {
        const values = await api.getParams()
        setLanguage(values?.LanguageSetting || languageState.code || "en")
      } catch (e) {
        setLanguage(languageState.code || "en")
      }
    },
    clearSearch() {
      store.search = ""
      this.$nextTick(() => { const el = this.$refs.searchInput; if (el) el.focus() })
    },
    measureSearch() {
      const el = this.$refs.searchInput
      if (!el) return
      const styles = window.getComputedStyle(el)
      const padding = parseFloat(styles.paddingLeft || "0") + parseFloat(styles.paddingRight || "0")
      const available = el.clientWidth - padding
      if (available <= 0) return
      if (!this._searchCanvas) this._searchCanvas = document.createElement("canvas")
      const ctx = this._searchCanvas.getContext("2d")
      if (!ctx) return
      ctx.font = `${styles.fontStyle} ${styles.fontWeight} ${styles.fontSize} ${styles.fontFamily}`
      this.searchNarrow = ctx.measureText(t("Search toggles...")).width > available
    },
    themeToggle() { toggleTheme() },
    toggleNavPin() { toggleNavPinned() },
    navTo(link) {
      this.closeDrawer()
      navigate(toolHref(link))
    },
    bottomNavTo(item) {
      navigate(item.link)
    },
    goHome() {
      navigate("/")
    },
    isActive(link) {
      return this.activePath === link || (link !== "/" && this.activePath.startsWith(link))
    },
  },
  created() {
    this.loadLanguage()
    this.statusPoll = usePolling(() => this.refreshStatus(), { interval: 5000 })
    this.statusPoll.start()
  },
  mounted() {
    this.measureSearch()
    if (typeof ResizeObserver !== "undefined" && this.$refs.searchInput) {
      this.searchObserver = new ResizeObserver(() => this.measureSearch())
      this.searchObserver.observe(this.$refs.searchInput)
    } else {
      window.addEventListener("resize", this.measureSearch)
    }
  },
  beforeUnmount() {
    this.statusPoll?.destroy()
    this.searchObserver?.disconnect()
    window.removeEventListener("resize", this.measureSearch)
  },
  template: `
    <div class="gx-app" :class="{ 'gx-nav-pinned': navPinned }">
      <header class="gx-appbar">
        <button type="button" class="gx-icon-btn gx-appbar__back gx-back-btn" :aria-label="tr('Back')" @click="back">
          <i class="bi bi-arrow-left"></i>
        </button>
        <div class="gx-appbar__pill">
          <span class="gx-appbar__home" role="button" tabindex="0"
            :aria-label="tr('Galaxy home')" @click="goHome" @keydown.enter="goHome" @keydown.space.prevent="goHome">
            <span class="gx-appbar__title">Galaxy</span>
          </span>
          <div class="gx-searchwrap">
            <input ref="searchInput" class="gx-search gx-appbar__search" type="search" :placeholder="searchPlaceholder"
              v-model="search" :aria-label="tr('Search toggles')" />
            <button v-if="search" type="button" class="gx-search-clear" :aria-label="tr('Clear search')" @click="clearSearch">
              <i class="bi bi-x"></i>
            </button>
          </div>
          <div class="gx-appbar__right">
            <span class="gx-status-pill">
              <span class="gx-status-dot" :class="online ? 'online' : 'offline'"></span>
              {{ statusLabel }}
            </span>
          </div>
        </div>
        <button type="button" class="gx-icon-btn gx-theme-toggle" :aria-label="isLight ? tr('Switch to dark mode') : tr('Switch to light mode')"
          :title="isLight ? tr('Dark mode') : tr('Light mode')" @click="themeToggle">
          <i class="bi" :class="isLight ? 'bi-moon-stars-fill' : 'bi-sun-fill'"></i>
        </button>
        <button type="button" class="gx-icon-btn gx-appbar__menu" :aria-label="tr('Menu')" :title="tr('Menu')" @click="store.drawerOpen = true">
          <i class="bi bi-list"></i>
        </button>
      </header>

      <transition name="gx-fade">
        <div v-if="store.drawerOpen && !navPinned" class="gx-underlay" @click="closeDrawer"></div>
      </transition>
      <aside class="gx-drawer" :class="{ open: store.drawerOpen || navPinned }">
        <div class="gx-drawer__header">
          <img class="gx-logo" src="/assets/images/main_logo.png" alt="Galaxy logo" />
          <span class="gx-drawer-title">{{ tr("Galaxy") }}</span>
          <button type="button" class="gx-icon-btn gx-drawer__pin" :aria-pressed="navPinned"
            :aria-label="navPinned ? tr('Unpin navigation') : tr('Pin navigation')"
            :title="navPinned ? tr('Unpin navigation') : tr('Pin navigation')" @click.stop="toggleNavPin">
            <i class="bi" :class="navPinned ? 'bi-pin-angle-fill' : 'bi-pin-angle'"></i>
          </button>
        </div>
        <div class="gx-nav-section">
          <div class="gx-nav-section__title">{{ tr("Main") }}</div>
          <a class="gx-nav-item" :class="{ active: isActive('/') }" @click.prevent="navTo('/')">
            <i class="bi bi-house-fill"></i><span>{{ tr("Home") }}</span>
          </a>
          <a class="gx-nav-item" :class="{ active: isActive('/settings') }" @click.prevent="navTo('/settings')">
            <i class="bi bi-toggle-on"></i><span>{{ tr("Toggles") }}</span>
          </a>
          <a class="gx-nav-item" :class="{ active: isActive('/tools') }" @click.prevent="navTo('/tools')">
            <i class="bi bi-tools"></i><span>{{ tr("Tools") }}</span>
          </a>
        </div>
        <div v-for="(links, section) in NAV" :key="section" class="gx-nav-section">
          <div class="gx-nav-section__title">{{ tr(section === 'recordings' ? 'Recordings' : 'Tools') }}</div>
          <a v-for="link in links" :key="link.link" class="gx-nav-item" @click.prevent="navTo(link.link)">
            <i class="bi" :class="link.icon"></i><span>{{ tr(link.name, link.name) }}</span>
          </a>
        </div>
        <DevicePicker />
      </aside>

      <main class="gx-content">
        <slot />
      </main>

      <nav class="blur-nav">
        <button v-for="item in BOTTOM_NAV" :key="item.link" type="button"
          class="nav-item" :class="{ active: isActive(item.link) }"
          @click="bottomNavTo(item)">
          <i class="bi" :class="item.icon"></i>
          <span>{{ tr(item.name, item.name) }}</span>
        </button>
      </nav>
    </div>
  `,
}
