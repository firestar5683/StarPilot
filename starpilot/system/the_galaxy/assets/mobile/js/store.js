import { reactive } from "vue"

const THEME_KEY = "galaxy-theme"

function initialTheme() {
  return localStorage.getItem(THEME_KEY) || "dark"
}

export const store = reactive({
  route: "/",
  params: {},
  drawerOpen: false,
  search: "",
  snackbar: null,
  online: false,
  deviceStatus: "Parked",
  history: ["/"],
  theme: initialTheme(),
})

export function setTheme(theme) {
  const next = theme === "light" ? "light" : "dark"
  store.theme = next
  document.documentElement.setAttribute("data-theme", next)
  try { localStorage.setItem(THEME_KEY, next) } catch (e) {}
}

export function toggleTheme() {
  setTheme(store.theme === "dark" ? "light" : "dark")
}

export function parseHash(hash) {
  const raw = hash.replace(/^#/, "") || "/"
  const [pathname, queryString] = raw.split("?")
  const params = {}
  if (queryString) {
    for (const pair of queryString.split("&")) {
      const [k, v] = pair.split("=")
      if (k) params[decodeURIComponent(k)] = decodeURIComponent(v || "")
    }
  }
  return { path: pathname, params }
}

// Rebuild the canonical hash string for a route, preserving its query params.
export function toHash(route) {
  const { path, params } = parseHash(route)
  const qs = Object.keys(params).map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`).join("&")
  return qs ? `${path}?${qs}` : path
}

function currentPath() {
  return parseHash(window.location.hash).path
}

function pushIfNew(route) {
  const last = store.history[store.history.length - 1]
  if (last !== route) store.history.push(route)
}

function applyRoute(route, { scrollToTop = false } = {}) {
  const { path, params } = parseHash(route)
  const pathChanged = path !== store.route
  store.route = path
  store.params = params
  store.drawerOpen = false
  // Only jump to the top for real view changes. In-place hash updates (a Manage
  // panel opening under the same section, an embed switching src) must not yank
  // the reader back to the top of the page.
  if (scrollToTop || pathChanged) window.scrollTo(0, 0)
}

export function navigate(target) {
  const { path } = parseHash(target)
  if (path !== currentPath()) pushIfNew(path)
  applyRoute(target)
  window.location.hash = toHash(target)
}

export function goHome() {
  navigate("/")
}

export function goBack() {
  const current = currentPath()
  if (store.history[store.history.length - 1] === current && store.history.length > 1) {
    store.history.pop()
  }
  const prev = store.history[store.history.length - 1] || "/"
  applyRoute(prev, { scrollToTop: true })
  window.location.hash = prev
}

const NATIVE_ROOTS = new Set(["/", "/settings", "/tools", "/recordings", "/logs", "/tuning", "/navigation", "/vehicle", "/system", "/embed", "/manage_doors", "/galaxy", "/manage_tsk", "/sentry", "/manage_models", "/plots", "/testing_ground", "/theme_maker", "/model_laboratory", "/cameras"])

export function toolHref(link) {
  const path = link.split("?")[0]
  if (NATIVE_ROOTS.has(path) || path.startsWith("/settings/") || path.startsWith("/embed")) return link
  return "/embed?src=" + encodeURIComponent(path)
}

export function initRouter() {
  const apply = () => {
    const route = (window.location.hash || "").replace(/^#/, "") || "/"
    applyRoute(route)
    pushIfNew(route)
  }
  window.addEventListener("hashchange", apply)
  store.history = ["/"]
  apply()
  setTheme(store.theme)
}
