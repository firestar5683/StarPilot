import { reactive } from "../vendor/vue/vue.esm-browser.js"
import { createRouteLeave } from "./route-leave.js"

const start = () => {
  const hash = location.hash.slice(1) || "/"
  try { return decodeURIComponent(hash) } catch { return hash }
}
export const route = reactive({ path: start() })
const index = () => Number.isInteger(history.state?.galaxyIndex) ? history.state.galaxyIndex : null
const url = (path) => `${location.pathname}${location.search}#${encodeURI(path)}`
let navigation
let pendingGuard = null
export function navigate(path, before = null) { navigation.navigate(path, before) }
export function navigateBack() { navigation.back() }
export function setRouteLeaveGuard(guard) { pendingGuard = guard; navigation?.setGuard(guard) }
export function startRouter() {
  history.replaceState({ ...history.state, galaxyIndex: index() ?? 0 }, "", url(route.path))
  navigation = createRouteLeave({
    read: () => ({ path: start(), index: index() }),
    push: (path, position) => history.pushState({ galaxyIndex: position }, "", url(path)),
    replace: (path, position) => history.replaceState({ galaxyIndex: position }, "", url(path)),
    go: (delta) => history.go(delta),
    show: () => { route.path = start(); window.scrollTo(0, 0) },
  })
  navigation.setGuard(pendingGuard)
  window.addEventListener("popstate", () => navigation.changed())
  window.addEventListener("hashchange", () => navigation.changed())
}
