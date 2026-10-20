import { GxState } from "./state.js"
import { GxNotice } from "./notice.js"
import { requestJson } from "./startup.js"
import { InstallApp, isIosDevice } from "./install-app.js"
import { GalaxyCompanion, newerCompanionVersion } from "./companion.js"
import { GalaxyHotspot } from "./hotspot.js"
import { BluetoothNotice, bluetoothConnection } from "./bluetooth-notice.js"

const DISMISSED_UPDATE = 'galaxy.companion.dismissedUpdateVersion'
const dismissedUpdate = () => { try { return localStorage.getItem(DISMISSED_UPDATE) || '' } catch { return '' } }

export const GalaxyPage = {
  name: "GalaxyPage",
  components: { GxState, GxNotice, BluetoothNotice, InstallApp, GalaxyHotspot, GalaxyCompanion },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ loading: true, paired: false, url: "", tunnelClientAvailable: false, legacyPassword: false,
    legacyPairingAvailable: false, password: "", busy: false, error: "", companionStatus: null,
    bluetooth: bluetoothConnection(), nativeVersion: window.StarPilotApp?.version?.() || '', dismissedUpdateVersion: dismissedUpdate(),
    ios: isIosDevice() }),
  computed: {
    availableAppVersion() { return this.companionStatus?.appAvailable ? this.companionStatus.shippedVersion : '' },
    installedAppVersion() { return this.nativeVersion || this.companionStatus?.version || '' },
    appUpdateAvailable() {
      return this.mode === 'local' && newerCompanionVersion(this.availableAppVersion, this.installedAppVersion)
    },
    nativeInstallerAvailable() { return typeof window.StarPilotApp?.installUpdate === 'function' },
    showAppUpdate() {
      return this.appUpdateAvailable && this.availableAppVersion !== this.dismissedUpdateVersion
    },
  },
  mounted() { this.load() },
  methods: {
    installAppUpdate() { window.StarPilotApp?.installUpdate?.() },
    dismissAppUpdate() {
      this.dismissedUpdateVersion = this.availableAppVersion
      try { localStorage.setItem(DISMISSED_UPDATE, this.dismissedUpdateVersion) } catch {}
    },
    async request(path, body) {
      try {
        return await requestJson(path, { request: body === undefined ? {} : {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
        } })
      } catch (error) {
        if (error.status === 401) this.unauthorized()
        throw error
      }
    },
    async load() {
      if (this.mode !== "local") { this.loading = false; return }
      try {
        const data = await this.request("./api/galaxy/status")
        this.paired = data.paired
        this.url = data.url
        this.tunnelClientAvailable = data.tunnelClientAvailable === true
        this.legacyPassword = data.legacyPassword === true
        this.legacyPairingAvailable = data.legacyPairingAvailable === true
      } catch (error) { this.error = error.message }
      finally { this.loading = false }
    },
    async pair() {
      this.busy = true
      this.error = ""
      try {
        const data = await this.request("./api/galaxy/pair", { password: this.password })
        this.paired = data.paired
        this.url = data.url
        this.password = ""
      } catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
    async unpair() {
      if (!window.confirm("Unpair from Galaxy? Remote access will stop until you pair again.")) return
      this.busy = true
      this.error = ""
      try {
        await this.request("./api/galaxy/unpair", {})
        this.paired = false
        this.url = ""
      } catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
  },
  template: `
    <div class="gx-settings gx-tunnel" :inert="busy" :aria-busy="busy || undefined"><header class="gx-settings__header gx-page-header"><div><h2>Galaxy Access & Install</h2>
      <p>Pair your comma, then install Galaxy from your remote link.</p></div></header>
      <BluetoothNotice v-if="showAppUpdate && bluetooth && !ios" :feature="'Android app update ' + availableAppVersion">
        Installed: {{ installedAppVersion }}.
        <button type="button" class="gx-btn gx-btn--tonal" aria-label="Dismiss app update notice" @click="dismissAppUpdate">Dismiss</button>
      </BluetoothNotice>
      <GxNotice v-else-if="showAppUpdate && !ios" tone="warn" title="Android app update available">
        Version {{ availableAppVersion }} is available. Installed: {{ installedAppVersion }}.
        <div class="gx-actions"><button v-if="nativeInstallerAvailable" type="button" class="gx-btn" @click="installAppUpdate">Update app</button>
          <a v-else class="gx-btn" href="./app.apk">Update app</a>
          <button type="button" class="gx-btn gx-btn--tonal" aria-label="Dismiss app update notice" @click="dismissAppUpdate">Dismiss</button></div>
      </GxNotice>
      <GxState v-if="mode !== 'local'">Connect to your comma to set up remote access.</GxState>
      <GxState v-else-if="loading" loading>Checking pairing status…</GxState>
      <ol v-else class="gx-aa__steps">
        <li class="gx-card gx-aa-step" :class="{'gx-aa-step--done': paired}">
          <div class="gx-aa-step__head"><span class="gx-aa-step__num" aria-hidden="true"><i v-if="paired" class="bi bi-check-lg"></i><template v-else>1</template></span>
            <div><h3>Remote pairing</h3><p>Pair your comma to get a secure Galaxy link.</p></div></div>
          <div class="gx-aa-step__body">
            <template v-if="paired">
              <GxNotice v-if="!tunnelClientAvailable" tone="warn">The remote tunnel client is unavailable. Your link will work when it is installed.</GxNotice>
              <BluetoothNotice v-if="bluetooth" feature="Galaxy QR code">Your Galaxy link remains available below.</BluetoothNotice>
              <img v-else src="./api/galaxy/qr.svg" alt="QR code for your Galaxy link" class="gx-tunnel__qr" />
              <p><a :href="url" target="_blank" rel="noopener" class="gx-btn gx-btn--tonal gx-wrap">Open your Galaxy link</a></p>
              <div class="gx-actions"><button type="button" class="gx-btn gx-btn--danger" @click="unpair">{{ busy ? 'Unpairing…' : 'Unpair' }}</button></div>
            </template>
            <template v-else>
              <p v-if="legacyPassword">Enter your existing password to keep your Galaxy link.</p>
              <p v-else-if="legacyPairingAvailable">Enter your old password to keep the link, or choose a new one with at least 8 characters.</p>
              <p v-else>Choose a password to pair your comma.</p>
              <div class="gx-actions"><input class="gx-field gx-filter-field" type="password" v-model="password" :minlength="legacyPassword || legacyPairingAvailable ? 6 : 8" maxlength="255" :autocomplete="legacyPassword ? 'current-password' : 'new-password'" :placeholder="legacyPassword ? 'Existing Galaxy password' : legacyPairingAvailable ? 'Existing or new Galaxy password' : 'New password (at least 8 characters)'" @keydown.enter="pair" />
                <button type="button" class="gx-btn" :disabled="password.trim().length < (legacyPassword || legacyPairingAvailable ? 6 : 8)" @click="pair">{{ busy ? 'Pairing…' : 'Pair' }}</button></div>
            </template>
            <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
          </div>
        </li>
        <li class="gx-card gx-aa-step">
          <div class="gx-aa-step__head"><span class="gx-aa-step__num" aria-hidden="true">2</span>
            <div><h3>Install Galaxy</h3><p>Launch Galaxy from your home screen or desktop.</p></div></div>
          <div class="gx-aa-step__body"><InstallApp :url="url" :update-available="appUpdateAvailable" />
            <p v-if="availableAppVersion && !ios">Android offline app version: <strong>{{ availableAppVersion }}</strong><span v-if="installedAppVersion"> · {{ nativeVersion ? 'Installed' : 'Connected phone' }}: {{ installedAppVersion }}</span></p>
            <p v-if="!ios"><strong>Install as offline app (Android)</strong> to use Galaxy over Galaxy Wi-Fi or your local network without Internet. Download it while connected locally from this page.</p>
            <p class="gx-note">Your remote link needs Internet and an active tunnel. For offline local access, bookmark your hotspot or local address.</p>
          </div>
        </li>
      </ol>
      <GalaxyHotspot :mode="mode" :unauthorized="unauthorized" />
      <GalaxyCompanion v-if="!ios" :mode="mode" :unauthorized="unauthorized" @status="companionStatus = $event" />
    </div>
  `,
}
