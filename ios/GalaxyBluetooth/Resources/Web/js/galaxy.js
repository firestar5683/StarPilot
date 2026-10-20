import { GxState } from "./state.js"
import { GxNotice } from "./notice.js"
import { requestJson } from "./startup.js"
import { InstallApp } from "./install-app.js"
import { GalaxyHotspot } from "./hotspot.js"

export const GalaxyPage = {
  name: "GalaxyPage",
  components: { GxState, GxNotice, InstallApp, GalaxyHotspot },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ loading: true, paired: false, url: "", tunnelClientAvailable: false, legacyPassword: false,
    legacyPairingAvailable: false, password: "", busy: false, error: "" }),
  mounted() { this.load() },
  methods: {
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
      <p>Pair for remote access, install Galaxy, or set up a Wi-Fi hotspot.</p></div></header>
      <GxState v-if="mode !== 'local'">Connect to your comma to set up remote access.</GxState>
      <GxState v-else-if="loading" loading>Checking pairing status…</GxState>
      <section v-else class="gx-card gx-panel">
        <h3>Remote pairing</h3>
        <p>Pair your comma to get a secure Galaxy link and QR code. Remote access requires Internet on your phone and comma, plus an active tunnel.</p>
        <template v-if="paired">
          <GxNotice tone="success" title="Paired">Scan this code or open the link when the Galaxy tunnel is connected.</GxNotice>
          <p v-if="!tunnelClientAvailable" class="gx-note gx-note--danger">The remote tunnel client is not installed on this device yet. The link will work after Galaxy's tunnel client is available.</p>
          <img src="./api/galaxy/qr.svg" alt="QR code for your Galaxy link" class="gx-tunnel__qr" />
          <p><a :href="url" target="_blank" rel="noopener" class="gx-wrap">{{ url }}</a></p>
          <button type="button" class="gx-btn gx-btn--danger" @click="unpair">{{ busy ? 'Unpairing…' : 'Unpair' }}</button>
        </template>
        <template v-else>
          <GxNotice v-if="legacyPassword">Enter your existing Galaxy password to keep its saved link and QR code.</GxNotice>
          <GxNotice v-else-if="legacyPairingAvailable">An earlier Galaxy pairing is available. Enter its password to keep the saved link, or choose a new password (at least 8 characters) for a new link.</GxNotice>
          <GxNotice v-else>First choose a password, then pair your comma. Open Galaxy remotely using the link and QR code when the tunnel is connected.</GxNotice>
          <div class="gx-actions"><input class="gx-field gx-filter-field" type="password" v-model="password" :minlength="legacyPassword || legacyPairingAvailable ? 6 : 8" maxlength="255" :autocomplete="legacyPassword ? 'current-password' : 'new-password'" :placeholder="legacyPassword ? 'Existing Galaxy password' : legacyPairingAvailable ? 'Existing or new Galaxy password' : 'New password (at least 8 characters)'" @keydown.enter="pair" />
          <button type="button" class="gx-btn" :disabled="password.trim().length < (legacyPassword || legacyPairingAvailable ? 6 : 8)" @click="pair">{{ busy ? 'Pairing…' : 'Pair' }}</button></div>
        </template>
        <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
      </section>
      <section class="gx-card gx-info-card">
        <h3>Install Galaxy</h3><InstallApp />
        <p>Install Galaxy to launch it from your home screen or desktop. Use your remote Galaxy link for app installation; the button shows installation instructions when your browser needs them.</p>
        <ul class="gx-install-benefits"><li><i class="bi bi-window" aria-hidden="true"></i> Your own full-screen window</li><li><i class="bi bi-lightning-charge" aria-hidden="true"></i> Launch from your home screen</li><li><i class="bi bi-arrow-repeat" aria-hidden="true"></i> Automatic updates, no app store</li></ul>
        <p class="gx-note">The public Galaxy link requires Internet and an active tunnel. Installing the app does not provide an offline connection to your comma. For local access without Internet, bookmark the hotspot address or a local address from Home.</p>
      </section>
      <GalaxyHotspot :mode="mode" :unauthorized="unauthorized" />
    </div>
  `,
}
