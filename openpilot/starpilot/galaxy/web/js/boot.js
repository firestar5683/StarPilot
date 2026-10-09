const status = document.getElementById("galaxy-boot")
const message = status.querySelector("p")
const retry = status.querySelector("button")
retry.addEventListener("click", () => location.reload())
function failed() {
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
import("./app.js").then(() => {
  clearTimeout(timer)
  if (document.querySelector("#galaxy-app .gx-app")) dismiss()
  else failed()
}).catch(() => { clearTimeout(timer); failed() })
