import { pwaState, requestInstall } from "../install.js"

export const FIRESTAR_HOST = "galaxy.firestar.link"

export function isFirestarOrigin() {
  return window.location.hostname === FIRESTAR_HOST
}

function isIos() {
  const ua = window.navigator.userAgent
  return /iPad|iPhone|iPod/.test(ua) && !/CriOS|FxiOS|OPiOS|EdgiOS/.test(ua)
}

export const PwaInstallSection = {
  name: "PwaInstallSection",
  props: {
    // The device's paired Galaxy link (https://galaxy.firestar.link/<slug>).
    galaxyUrl: { type: String, default: "" },
  },
  data() {
    return {
      isIos: isIos(),
      onFirestar: isFirestarOrigin(),
    }
  },
  computed: {
    // The stable URL users should install from. Prefer the paired Galaxy link;
    // fall back to the current page when we are already on the Firestar host.
    installUrl() {
      if (this.galaxyUrl) return this.galaxyUrl
      if (this.onFirestar) return window.location.origin
      return ""
    },
    installed() { return pwaState.installed },
    canInstall() { return !!pwaState.deferredPrompt && !pwaState.installed },
    showManual() { return this.isIos && !pwaState.installed && !pwaState.deferredPrompt },
    onLocal() { return !this.onFirestar && !this.installUrl },
  },
  methods: {
    async install() {
      await requestInstall()
    },
    installHost() {
      try { return new URL(this.installUrl).host } catch (e) { return this.installUrl }
    },
  },
  template: `
    <section v-if="!installed" class="gx-card gx-install">
      <div class="gx-section__header">
        <i class="bi bi-phone-fill"></i>
        <span class="gx-section__title">Install Galaxy as an App</span>
      </div>
      <div class="gx-install__body">
        <p class="gx-install__lead">
          Galaxy is designed to be used as a <strong>Progressive Web App</strong>, giving you a full-screen app experience with no app store download required.
        </p>

        <ul class="gx-install__benefits">
          <li><i class="bi bi-hdd"></i><span>Uses a tiny fraction of the storage of a native app.</span></li>
          <li><i class="bi bi-lightning-charge"></i><span>Opens instantly in its own window, giving a native-app like feel.</span></li>
          <li><i class="bi bi-cloud-download"></i><span>No need to manually update the app.</span></li>
          <li><i class="bi bi-wifi"></i><span>Requires an active network connection at all times, just like the browser version.</span></li>
        </ul>

        <div v-if="onLocal" class="gx-install__hint">
          <i class="bi bi-info-circle-fill"></i>
          <span>To install Galaxy, open it from a paired Galaxy link (not this device address, which can
          change between networks). If your device is paired, open the Galaxy link shown above and
          come back to this page for further steps.</span>
        </div>

        <div v-if="onFirestar && canInstall" class="gx-install__actions">
          <p class="gx-install__hint" style="margin:0 0 var(--sp-3);">
            <i class="bi bi-check-circle-fill"></i>
            <span>This page is ready. Add Galaxy to your home screen to launch it like a native app.</span>
          </p>
          <button type="button" class="gx-btn gx-btn--block" @click="install">
            <i class="bi bi-download"></i> Install Galaxy
          </button>
        </div>

        <div v-else-if="onFirestar && showManual" class="gx-install__manual">
          <p class="gx-install__hint"><i class="bi bi-share-fill"></i><span>Galaxy is already available
          on this page. To install it on your iPhone or iPad:</span></p>
          <ol class="gx-install__steps">
            <li>Tap the <strong>Share</strong> button in the browser toolbar.</li>
            <li>Scroll down and tap <strong>Add to Home Screen</strong>.</li>
            <li>Tap <strong>Add</strong>, and Galaxy will appear on your home screen.</li>
          </ol>
        </div>

        <div v-else-if="onFirestar && !isIos" class="gx-install__actions">
          <p class="gx-install__hint" style="margin:0 0 var(--sp-3);">
            <i class="bi bi-wifi"></i>
            <span>Checking whether this page can be installed... If the button doesn't appear, your
            browser may already have Galaxy installed or may need a stable connection.</span>
          </p>
        </div>

        <div v-if="installUrl && !onFirestar" class="gx-install__actions">
          <p class="gx-install__hint" style="margin:0 0 var(--sp-3);">
            <i class="bi bi-box-arrow-up-right"></i>
            <span>Open your Galaxy link ({{ installHost() }}) and use the install option there. It
            stays the same even if this device's address changes.</span>
          </p>
          <a class="gx-btn gx-btn--block" :href="installUrl" target="_blank" rel="noopener" style="text-decoration:none;">
            <i class="bi bi-box-arrow-up-right"></i> Open Galaxy to Install
          </a>
        </div>
      </div>
    </section>
  `,
}
