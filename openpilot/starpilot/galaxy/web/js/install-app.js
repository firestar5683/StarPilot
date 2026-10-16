let deferredPrompt = null
export function rememberInstallPrompt(event) {
  event.preventDefault()
  deferredPrompt = event
}

export function isIosDevice(agent = typeof navigator === 'undefined' ? '' : navigator.userAgent) {
  return /iPhone|iPad|iPod/.test(agent)
}

export function isAndroidDevice(agent = typeof navigator === 'undefined' ? '' : navigator.userAgent) {
  return /Android/.test(agent)
}

export function installHelp({ secure = window.isSecureContext, agent = navigator.userAgent } = {}) {
  if (!secure) return 'Bookmark this local address for hotspot or Wi-Fi access without Internet. To install Galaxy as a web app (PWA), open your device-specific https://galaxy.firestar.link link from Galaxy Access & Install; this remote link needs Internet.'
  if (/iPhone|iPad|iPod/.test(agent)) return 'Open Galaxy in Safari, tap Share, then Add to Home Screen. Turn on Open as Web App if shown.'
  return 'This browser cannot install Galaxy automatically. Open the browser menu and choose Install app or Add to Home Screen. On a Mac in Safari, choose File → Add to Dock.'
}

export function androidInstallHelp() {
  return 'Connect locally to your comma, then download the Android app from Galaxy Access & Install. Allow your browser to install unknown apps when Android asks.'
}

export const InstallApp = {
  name: 'InstallApp',
  props: { updateAvailable: { type: Boolean, default: false } },
  data: () => ({ prompt: null, installed: false, help: false, message: '',
    android: isAndroidDevice(), ios: isIosDevice() }),
  mounted() {
    this.prompt = deferredPrompt
    this.displayMode = window.matchMedia('(display-mode: standalone)')
    this.updateInstalled = () => { this.installed = !!window.StarPilotApp || this.displayMode.matches || navigator.standalone === true }
    this.onPrompt = (event) => { event.preventDefault(); deferredPrompt = event; this.prompt = event; this.help = false }
    this.onInstalled = () => { this.installed = true; this.prompt = deferredPrompt = null; this.help = false }
    this.updateInstalled()
    window.addEventListener('beforeinstallprompt', this.onPrompt)
    window.addEventListener('appinstalled', this.onInstalled)
    this.displayMode.addEventListener('change', this.updateInstalled)
  },
  beforeUnmount() {
    window.removeEventListener('beforeinstallprompt', this.onPrompt)
    window.removeEventListener('appinstalled', this.onInstalled)
    this.displayMode?.removeEventListener('change', this.updateInstalled)
    this.prompt = null
  },
  methods: {
    async installWeb() {
      if (!this.prompt) { this.message = installHelp(); this.help = !this.help; return }
      const prompt = this.prompt
      this.prompt = deferredPrompt = null
      try {
        await prompt.prompt()
        await prompt.userChoice
      } catch { this.message = installHelp(); this.help = true }
    },
    installAndroid() {
      if (this.updateAvailable && typeof window.StarPilotApp?.installUpdate === 'function') {
        window.StarPilotApp.installUpdate()
        return
      }
      if (location.protocol === 'http:') location.assign('./app.apk')
      else { this.message = androidInstallHelp(); this.help = true }
    },
  },
  template: `<div v-if="!installed || updateAvailable" class="gx-install-app">
    <div class="gx-actions">
      <button v-if="!installed" type="button" class="gx-btn gx-btn--tonal" @click="installWeb"><i class="bi bi-download" aria-hidden="true"></i><span>Install as web app</span></button>
      <button v-if="android && !ios && (!installed || updateAvailable)" type="button" class="gx-btn" @click="installAndroid"><i class="bi bi-download" aria-hidden="true"></i><span>{{ updateAvailable ? 'Update offline app (Android)' : 'Install as offline app (Android)' }}</span></button>
    </div>
    <p v-if="help" class="gx-note gx-install-help">{{ message }}</p>
  </div>`,
}
