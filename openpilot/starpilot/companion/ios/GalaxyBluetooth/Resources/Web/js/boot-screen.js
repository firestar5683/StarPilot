import { UPDATE_RESTART_MESSAGE } from "./update-restart.js"

const screen = document.getElementById("galaxy-boot")
const message = screen.querySelector("p")
const retry = screen.querySelector("button")
let mode = "opening"
let hideTimer = null

retry.addEventListener("click", () => location.reload())

export function bootScreenMode() { return mode }

export function showBootScreen(next, text, refresh = false) {
  clearTimeout(hideTimer)
  mode = next
  screen.hidden = false
  screen.classList.remove("gx-boot--done")
  screen.classList.toggle("gx-boot--failed", next === "failed")
  message.textContent = text
  retry.hidden = !refresh
}

export function showRestartScreen() { showBootScreen("restart", UPDATE_RESTART_MESSAGE, true) }

export function dismissBootScreen() {
  if (mode === "hidden") return
  mode = "hidden"
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) { screen.hidden = true; return }
  screen.classList.add("gx-boot--done")
  hideTimer = setTimeout(() => { if (mode === "hidden") screen.hidden = true }, 500)
}
