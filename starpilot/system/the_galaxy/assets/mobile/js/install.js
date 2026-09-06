import { reactive } from "vue"

function inStandaloneMode() {
  return window.matchMedia("(display-mode: standalone)").matches || !!window.navigator.standalone
}

export const pwaState = reactive({
  deferredPrompt: null,
  installed: inStandaloneMode(),
})

function capture(event) {
  event.preventDefault()
  pwaState.deferredPrompt = event
}

window.addEventListener("beforeinstallprompt", capture)
window.addEventListener("appinstalled", () => {
  pwaState.deferredPrompt = null
  pwaState.installed = true
})

export async function requestInstall() {
  const prompt = pwaState.deferredPrompt
  if (!prompt) return false
  prompt.prompt()
  try { await prompt.userChoice } catch (e) { /* user dismissed */ }
  pwaState.deferredPrompt = null
  return true
}
