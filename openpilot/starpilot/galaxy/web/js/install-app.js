let deferredPrompt = null
export function rememberInstallPrompt(event) {
  event.preventDefault()
  deferredPrompt = event
}

export function installHelp({ secure = window.isSecureContext, agent = navigator.userAgent } = {}) {
  if (/iPhone|iPad|iPod/.test(agent)) return 'Open Galaxy in Safari, tap Share, then Add to Home Screen. Turn on Open as Web App if shown.'
  if (!secure) return 'For the full web app, open your comma at https://galaxy.firestar.link, then choose Install Galaxy. Your local address can also be saved as a browser shortcut.'
  return 'This browser cannot install Galaxy automatically. Open the browser menu and choose Install app or Add to Home Screen. On a Mac in Safari, choose File → Add to Dock.'
}

export const InstallApp = {
  name: 'InstallApp',
  data: () => ({ prompt: null, installed: false, help: false, message: '' }),
  mounted() {
    this.prompt = deferredPrompt
    this.displayMode = window.matchMedia('(display-mode: standalone)')
    this.updateInstalled = () => { this.installed = this.displayMode.matches || navigator.standalone === true }
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
    async install() {
      if (!this.prompt) { this.message = installHelp(); this.help = !this.help; return }
      const prompt = this.prompt
      this.prompt = deferredPrompt = null
      try {
        await prompt.prompt()
        await prompt.userChoice
      } catch { this.message = installHelp(); this.help = true }
    },
  },
  template: `<div v-if="!installed" class="gx-install-app">
    <button type="button" class="gx-btn gx-btn--tonal" @click="install"><i class="bi bi-download" aria-hidden="true"></i><span>Install Galaxy</span></button>
    <p v-if="help" class="gx-note gx-install-help">{{ message }}</p>
  </div>`,
}
