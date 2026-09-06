import { store, navigate, goBack, toolHref, toggleTheme } from "../store.js"
import { api } from "../api.js"
import { usePolling } from "../composables.js"

const NAV = {
  recordings: [
    { name: "Recordings", link: "/recordings", icon: "bi-camera-reels" },
  ],
  tools: [
    { name: "Cameras & Monitoring", link: "/cameras", icon: "bi-camera-video" },
    { name: "Galaxy", link: "/galaxy", icon: "bi-globe2" },
    { name: "Logs & Diagnostics", link: "/logs", icon: "bi-exclamation-triangle" },
    { name: "Model Manager", link: "/manage_models", icon: "bi-cpu" },
    { name: "Navigation & Maps", link: "/navigation", icon: "bi-map" },
    { name: "Sentry Mode", link: "/sentry", icon: "bi-shield-exclamation" },
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
  data() {
    return { store, BOTTOM_NAV, NAV }
  },
  computed: {
    online() { return store.online },
    statusLabel() { return store.online ? store.deviceStatus : "Offline" },
    isLight() { return store.theme === "light" },
    drawerOpen: {
      get() { return store.drawerOpen },
      set(v) { store.drawerOpen = v },
    },
    activePath() { return store.route },
    search: {
      get() { return store.search },
      set(v) { store.search = v },
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
    closeDrawer() { store.drawerOpen = false },
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
    clearSearch() {
      store.search = ""
      this.$nextTick(() => { const el = this.$refs.searchInput; if (el) el.focus() })
    },
    themeToggle() { toggleTheme() },
    navTo(link) {
      this.closeDrawer()
      navigate(toolHref(link))
    },
    bottomNavTo(item) {
      navigate(item.link)
    },
    isActive(link) {
      return this.activePath === link || (link !== "/" && this.activePath.startsWith(link))
    },
  },
  created() {
    this.statusPoll = usePolling(() => this.refreshStatus(), { interval: 5000 })
    this.statusPoll.start()
  },
  beforeUnmount() {
    this.statusPoll?.destroy()
  },
  template: `
    <div class="gx-app">
      <header class="gx-appbar">
        <button type="button" class="gx-icon-btn gx-appbar__back gx-back-btn" aria-label="Back" @click="back">
          <i class="bi bi-arrow-left"></i>
        </button>
        <div class="gx-appbar__pill">
          <button type="button" class="gx-icon-btn gx-menu-btn" aria-label="Menu" @click="store.drawerOpen = true">
            <i class="bi bi-list"></i>
          </button>
          <span class="gx-appbar__title">Big Dipper</span>
          <div class="gx-searchwrap">
            <input ref="searchInput" class="gx-search gx-appbar__search" type="search" placeholder="Search toggles..."
              v-model="search" aria-label="Search toggles" />
            <button v-if="search" type="button" class="gx-search-clear" aria-label="Clear search" @click="clearSearch">
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
        <button type="button" class="gx-icon-btn gx-theme-toggle" :aria-label="isLight ? 'Switch to dark mode' : 'Switch to light mode'"
          :title="isLight ? 'Dark mode' : 'Light mode'" @click="themeToggle">
          <i class="bi" :class="isLight ? 'bi-moon-stars-fill' : 'bi-sun-fill'"></i>
        </button>
      </header>

      <transition name="gx-fade">
        <div v-if="store.drawerOpen" class="gx-underlay" @click="closeDrawer"></div>
      </transition>
      <aside class="gx-drawer" :class="{ open: store.drawerOpen }">
        <div class="gx-drawer__header">
          <img class="gx-logo" src="/assets/images/main_logo.png" alt="Big Dipper logo" />
          <span class="gx-drawer-title">Big Dipper</span>
        </div>
        <div class="gx-nav-section">
          <div class="gx-nav-section__title">Main</div>
          <a class="gx-nav-item" :class="{ active: isActive('/') }" @click.prevent="navTo('/')">
            <i class="bi bi-house-fill"></i><span>Home</span>
          </a>
          <a class="gx-nav-item" :class="{ active: isActive('/settings') }" @click.prevent="navTo('/settings')">
            <i class="bi bi-toggle-on"></i><span>Toggles</span>
          </a>
          <a class="gx-nav-item" :class="{ active: isActive('/tools') }" @click.prevent="navTo('/tools')">
            <i class="bi bi-tools"></i><span>Tools</span>
          </a>
        </div>
        <div v-for="(links, section) in NAV" :key="section" class="gx-nav-section">
          <div class="gx-nav-section__title">{{ section }}</div>
          <a v-for="link in links" :key="link.link" class="gx-nav-item" @click.prevent="navTo(link.link)">
            <i class="bi" :class="link.icon"></i><span>{{ link.name }}</span>
          </a>
        </div>
      </aside>

      <main class="gx-content">
        <slot />
      </main>

      <nav class="liquid-glass-nav">
        <button v-for="item in BOTTOM_NAV" :key="item.link" type="button"
          class="nav-item" :class="{ active: isActive(item.link) }"
          @click="bottomNavTo(item)">
          <i class="bi" :class="item.icon"></i>
          <span>{{ item.name }}</span>
        </button>
      </nav>
    </div>
  `,
}
