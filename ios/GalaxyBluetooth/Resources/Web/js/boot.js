import { savedUpdateRestart, UPDATE_RESTART_MESSAGE } from "./update-restart.js"
import { requestJson } from "./startup.js"

const status = document.getElementById("galaxy-boot")
const message = status.querySelector("p")
const retry = status.querySelector("button")
if (savedUpdateRestart()) { message.textContent = UPDATE_RESTART_MESSAGE; retry.textContent = "↻ Refresh Galaxy"; retry.hidden = false }
retry.addEventListener("click", () => location.reload())
let probe = null, sawOffline = false, opened = false
function reloadWhenBack() {
  if (probe !== null || opened) return
  probe = setTimeout(() => requestJson("./data/runtime.json")
    .then(() => true, () => false)
    .then(online => {
      probe = null
      if (opened) return
      if (online && sawOffline) location.reload()
      else { sawOffline ||= !online; reloadWhenBack() }
    }), 3000)
}
function failed() {
  reloadWhenBack()
  if (savedUpdateRestart()) return
  message.textContent = "Galaxy could not finish opening. Check your connection and try again."
  status.classList.add("gx-boot--failed")
  retry.hidden = false
}
function dismiss() {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) { status.remove(); return }
  status.classList.add("gx-boot--done")
  status.addEventListener("transitionend", () => status.remove(), { once: true })
  setTimeout(() => status.remove(), 800)
}
const timer = setTimeout(failed, 10000)
// Local pages use their local origin; public pages use the authenticated tunnel.
// Do not intercept fetch or ask a public page to probe private network addresses.
import("./connection-migration.js").then(module => module.retireLegacyPhone()).catch(() => {})
import("./app.js").then(() => {
    clearTimeout(timer)
    if (document.querySelector("#galaxy-app .gx-app")) { opened = true; clearTimeout(probe); probe = null; dismiss() }
    else failed()
  }).catch(() => { clearTimeout(timer); failed() })
