import { html, reactive } from "/assets/vendor/arrow-core.js"
import { createBrowserHistory, createRouter } from "/assets/vendor/remix-router-1.3.1.js"
import { hideSidebar } from "/assets/js/utils.js"
import { DeviceSettings } from "/assets/components/tools/device_settings.js?v=favorite-slots-5"
import { ErrorLogs } from "/assets/components/tools/error_logs.js"
import { VehicleFeatures } from "/assets/components/tools/vehicle_features.js"
import { GalaxyPairing } from "/assets/components/tools/galaxy.js"
import { Home } from "/assets/components/home/home.js"
import { LateralManeuvers } from "/assets/components/tools/lateral_maneuvers.js"
import { LongitudinalManeuvers } from "/assets/components/tools/longitudinal_maneuvers.js"
import { MapsManager } from "/assets/components/tools/maps.js"
import { NavDestination } from "/assets/components/navigation/navigation_destination.js?v=nav-favorites-2"
import { NavKeys } from "/assets/components/navigation/navigation_keys.js"
import { RouteRecordings } from "/assets/components/recordings/dashcam_routes.js"
import { SettingsView } from "/assets/components/settings.js"
import { ScreenRecordings } from "/assets/components/recordings/screen_recordings.js"
import { Sidebar } from "/assets/components/sidebar.js"
import { SpeedLimits } from "/assets/components/tools/speed_limits.js"
import { ModelManager } from "/assets/components/tools/model_manager.js?v=20260303t"
import { LivePlots } from "/assets/components/tools/plots.js"
import { ThemeMaker } from "/assets/components/tools/theme_maker.js"
import { TestingGround } from "/assets/components/tools/testing_ground.js"
import { Troubleshoot } from "/assets/components/tools/troubleshoot.js"
import { TmuxLog } from "/assets/components/tools/tmux.js"
import { ToggleControl } from "/assets/components/tools/toggles.js"
import { UpdateManager } from "/assets/components/tools/update_manager.js"

let router, routerState

function toRouterHref(href) {
  try {
    const url = new URL(href, window.location.origin)
    return `${url.pathname}${url.search}${url.hash}`
  } catch {
    return href
  }
}

function createRoute(id, path, component) {
  return {
    id,
    path,
    loader: () => { },
    element: component,
  }
}

function SafeHome() {
  return html`
    <div>
      <h1>Galaxy</h1>
      <p>Safe mode is active while UI rendering is being repaired.</p>
      <p>
        <a href="/galaxy">Galaxy Pairing</a> |
        <a href="/device_settings">Toggles</a> |
        <a href="/manage_updates">Software</a>
      </p>
    </div>
  `
}

function Root() {
  let routes = [
    createRoute("device_settings", "/device_settings/:section?", DeviceSettings),
    createRoute("errorLogs", "/manage_error_logs", ErrorLogs),
    createRoute("galaxy", "/galaxy", GalaxyPairing),
    createRoute("navdestination", "/set_navigation_destination", NavDestination),
    createRoute("navkeys", "/manage_navigation_keys", NavKeys),
    createRoute("root", "/", Home),
    createRoute("routes", "/dashcam_routes", RouteRecordings),
    createRoute("screen_recordings", "/screen_recordings", ScreenRecordings),
    createRoute("settings", "/settings/:section/:subsection?", SettingsView),
    createRoute("speed_limits", "/download_speed_limits", SpeedLimits),
    createRoute("model_manager", "/manage_models", ModelManager),
    createRoute("lateral_maneuvers", "/lateral_maneuvers", LateralManeuvers),
    createRoute("longitudinal_maneuvers", "/longitudinal_maneuvers", LongitudinalManeuvers),
    createRoute("maps", "/manage_maps", MapsManager),
    createRoute("plots", "/plots", LivePlots),
    createRoute("thememaker", "/theme_maker", ThemeMaker),
    createRoute("testing_ground", "/testing_ground", TestingGround),
    createRoute("troubleshoot", "/troubleshoot", Troubleshoot),
    createRoute("tmux", "/manage_tmux", TmuxLog),
    createRoute("toggles", "/manage_toggles", ToggleControl),
    createRoute("updates", "/manage_updates", UpdateManager),
    createRoute("vehicle_features", "/vehicle_features", VehicleFeatures),
  ]

  router = createRouter({
    routes,
    history: createBrowserHistory(),
  }).initialize()

  window.__thePondNavigate = (href) => {
    router.navigate(toRouterHref(href))
    window.scrollTo(0, 0)
  }

  routerState = reactive({
    activePath: "/",
    activePathFull: "/",
    initialized: false,
    navigation: { state: "loading" },
    errors: [],
    params: {},
    activeMatch: null,
  })

  router.subscribe(({ initialized, navigation, matches, errors }) => {
    const match = Array.isArray(matches) && matches.length > 0
      ? matches[matches.length - 1]
      : null
    Object.assign(routerState, {
      initialized,
      activePath: match?.route?.path || "",
      activePathFull: match?.pathname || "",
      navigation,
      params: match?.params || {},
      errors,
      activeMatch: match,
    })
  })

  return html`
    ${() => Sidebar(routerState.activePathFull)}
    <div class="content">
      ${() => {
      if (!routerState.initialized) {
        return Home({ params: routerState.params })
      }

      if (routerState.errors?.root?.status === 404) {
        return html`<h1>Not Found</h1>`
      }

      const routeElement = routerState.activeMatch?.route?.element
      if (typeof routeElement !== "function") {
        console.warn("[router] no route element for path:", routerState.activePathFull)
        return Home({ params: routerState.params })
      }
      return routeElement({ params: routerState.params })
    }}
    </div>
  `
}

export function Link(href, children, onClick, classes = "") {
  return html`<a
    class="${classes}"
    href="${() => href}"
    @click="${(e) => {
      e.preventDefault()
      router.navigate(toRouterHref(e.currentTarget.href))
      hideSidebar()
      onClick?.()
    }}"
  >${children}</a>`
}

export function Navigate(href) {
  router.navigate(toRouterHref(href))
  window.scrollTo(0, 0)
}

function mountRouterWhenReady() {
  const mountNode = document.getElementById("app")
  if (!mountNode) {
    // Some embedded browsers execute module scripts before <body> is fully available.
    setTimeout(mountRouterWhenReady, 0)
    return
  }

  if (!window.__thePondRouterMounted) {
    window.__thePondRouterMounted = true
    Root()(mountNode)
  } else {
    console.warn("[router] duplicate mount prevented")
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mountRouterWhenReady, { once: true })
} else {
  mountRouterWhenReady()
}
