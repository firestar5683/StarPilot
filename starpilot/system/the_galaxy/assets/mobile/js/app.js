import { createApp, h } from "vue"
import { AppShell } from "./components/AppShell.js"
import { Home } from "./views/Home.js"
import { Settings } from "./views/Settings.js"
import { Tools } from "./views/Tools.js"
import { Recordings } from "./views/Recordings.js"
import { Logs } from "./views/Logs.js"
import { Tuning } from "./views/Tuning.js"
import { Navigation } from "./views/Navigation.js"
import { Vehicle } from "./views/Vehicle.js"
import { Bluetooth } from "./views/Bluetooth.js"
import { SystemTools } from "./views/SystemTools.js"
import { ToolEmbed } from "./views/ToolEmbed.js"
import { Doors } from "./views/Doors.js"
import { Galaxy } from "./views/Galaxy.js"
import { Tsk } from "./views/Tsk.js"
import { ModelManager } from "./views/ModelManager.js"
import { Plots } from "./views/Plots.js"
import { TestingGround } from "./views/TestingGround.js"
import { ThemeMaker } from "./views/ThemeMaker.js"
import { ModelLaboratory } from "./views/ModelLaboratory.js"
import { Cameras } from "./views/Cameras.js"
import { store, initRouter, navigate } from "./store.js"
import { showSnackbar } from "./api.js"

window.__galaxyVue = { createApp, h }

window.addEventListener("message", (event) => {
  const data = event?.data
  if (!data || data.source !== "galaxy-embed" || typeof data.path !== "string") return
  const current = store.params.src || ""
  const target = data.path
  if (target === current || target === "/" + current) return
  navigate("/embed?src=" + encodeURIComponent(target))
})

const VIEWS = {
  "/": Home,
  "/settings": Settings,
  "/tools": Tools,
  "/recordings": Recordings,
  "/logs": Logs,
  "/tuning": Tuning,
  "/navigation": Navigation,
  "/vehicle": Vehicle,
  "/bluetooth": Bluetooth,
  "/system": SystemTools,
  "/embed": ToolEmbed,
  "/manage_doors": Doors,
  "/galaxy": Galaxy,
  "/manage_tsk": Tsk,
  "/sentry": Cameras,
  "/manage_models": ModelManager,
  "/plots": Plots,
  "/testing_ground": TestingGround,
  "/theme_maker": ThemeMaker,
  "/model_laboratory": ModelLaboratory,
  "/cameras": Cameras,
}

function resolveView(path) {
  if (path === "/embed" || path.startsWith("/embed/")) return ToolEmbed
  for (const [root, view] of Object.entries(VIEWS)) {
    if (path === root || (root !== "/" && path.startsWith(root + "/"))) return view
  }
  if (path === "/") return Home
  return ToolEmbed
}

const app = createApp({
  name: "GalaxyApp",
  errorCaptured(err) {
    console.error("[galaxy-ui]", err)
    showSnackbar("Something went wrong: " + (err?.message || err), "error")
    return false
  },
  computed: {
    View() {
      return resolveView(store.route)
    },
  },
  render() {
    return h(AppShell, null, {
      default: () => h(this.View),
    })
  },
})

app.mount("#galaxy-app")

initRouter()

// Disable card blur during document scrolling.
;(() => {
  let timer = null
  let scrollEnded = true
  const touches = new Set()
  const nativeScrollEnd = "onscrollend" in document
  const body = document.body

  const isModalEvent = (e) => {
    const t = e.target
    return t instanceof Element && t.closest(".gx-scrim, .gx-sheet, .gx-dialog, .gx-drawer") !== null
  }

  const setScrolling = (active) => {
    if (active) {
      if (!body.classList.contains("is-scrolling")) body.classList.add("is-scrolling")
    } else if (!touches.size && body.classList.contains("is-scrolling")) {
      body.classList.remove("is-scrolling")
    }
  }

  const scheduleRestore = () => {
    clearTimeout(timer)
    const scrollY = window.scrollY
    // Finger release and completion notifications can precede the last movement.
    // Keep glass disabled until the scroll position has also settled.
    timer = setTimeout(() => {
      if (window.scrollY !== scrollY) scheduleRestore()
      else setScrolling(false)
    }, 120)
  }

  document.addEventListener("scroll", () => {
    scrollEnded = false
    setScrolling(true)
    clearTimeout(timer)
    if (!nativeScrollEnd) scheduleRestore()
  }, { passive: true })

  document.addEventListener("scrollend", () => {
    scrollEnded = true
    scheduleRestore()
  }, { passive: true })

  window.addEventListener("touchstart", (e) => {
    if (isModalEvent(e)) return
    for (const touch of e.changedTouches) touches.add(touch.identifier)
  }, { passive: true })

  const releaseTouches = (e) => {
    for (const touch of e.changedTouches) touches.delete(touch.identifier)
    if (!touches.size && (scrollEnded || !nativeScrollEnd)) scheduleRestore()
  }
  window.addEventListener("touchend", releaseTouches, { passive: true })
  window.addEventListener("touchcancel", releaseTouches, { passive: true })

  window.addEventListener("hashchange", () => {
    scrollEnded = true
    touches.clear()
    clearTimeout(timer)
    body.classList.remove("is-scrolling")
  }, { passive: true })
})()

// Layer 2: Ambient Hero Stars Spawner
;(() => {
  const bg = document.getElementById("galaxy-bg")
  if (!bg) return
  for (let i = 0; i < 14; i++) {
    const s = document.createElement("i")
    s.className = "galaxy-hero"
    s.style.left = (Math.random() * 100).toFixed(2) + "%"
    s.style.top = (Math.random() * 100).toFixed(2) + "%"
    s.style.animationDelay = (Math.random() * 4).toFixed(2) + "s"
    const size = Math.random() > 0.6 ? 3 : 2
    s.style.width = s.style.height = size + "px"
    bg.appendChild(s)
  }
})()
