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
import { SystemTools } from "./views/SystemTools.js"
import { ToolEmbed } from "./views/ToolEmbed.js"
import { Doors } from "./views/Doors.js"
import { Galaxy } from "./views/Galaxy.js"
import { Tsk } from "./views/Tsk.js"
import { Sentry } from "./views/Sentry.js"
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
  "/system": SystemTools,
  "/embed": ToolEmbed,
  "/manage_doors": Doors,
  "/galaxy": Galaxy,
  "/manage_tsk": Tsk,
  "/sentry": Sentry,
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
