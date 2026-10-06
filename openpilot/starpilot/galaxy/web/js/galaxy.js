import { GxNotice } from "./notice.js"
import { requestJson } from "./startup.js"
import { LocalAccess } from "./local-access.js"

export const GalaxyPage = {
  name: "GalaxyPage",
  components: { GxNotice, LocalAccess },
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
    <div class="gx-settings gx-tunnel"><h2>Galaxy Tunnel</h2>
      <GxNotice tone="info" title="Your comma, wherever you are">Pair your device for secure remote Galaxy access.</GxNotice>
      <section v-if="mode !== 'local'" class="gx-card gx-message">Pairing is available on your comma.</section>
      <section v-else-if="loading" class="gx-card gx-message">Checking pairing status…</section>
      <section v-else class="gx-card" style="padding:var(--sp-4)">
        <template v-if="paired">
          <span class="gx-chip"><i class="bi bi-check-circle-fill"></i> Paired</span>
          <p>Pairing saved. Scan this code or open the link when the Galaxy tunnel is connected.</p>
          <p v-if="!tunnelClientAvailable" class="gx-note gx-note--danger">The remote tunnel client is not installed on this device yet. The link will work after Galaxy's tunnel client is available.</p>
          <img src="./api/galaxy/qr.svg" alt="QR code for your Galaxy link" style="display:block;width:min(250px,100%);background:white;padding:8px;border-radius:12px" />
          <p><a :href="url" target="_blank" rel="noopener" style="word-break:break-all">{{ url }}</a></p>
          <button type="button" class="gx-btn gx-btn--danger" :disabled="busy" @click="unpair">{{ busy ? 'Unpairing…' : 'Unpair' }}</button>
        </template>
        <template v-else>
          <span class="gx-chip gx-chip--lock">Not Paired</span>
          <p v-if="legacyPassword">Enter your existing Galaxy password to keep its saved link and QR code.</p>
          <p v-else-if="legacyPairingAvailable">An earlier Galaxy pairing is available. Enter its password to keep the saved link, or choose a new password (at least 8 characters) for a new link.</p>
          <p v-else>First choose a password, then pair your comma. Open Galaxy remotely using the link and QR code when the tunnel is connected.</p>
          <div style="display:flex;gap:8px;flex-wrap:wrap"><input class="gx-field" style="flex:1;min-width:200px" type="password" v-model="password" :minlength="legacyPassword || legacyPairingAvailable ? 6 : 8" maxlength="255" :autocomplete="legacyPassword ? 'current-password' : 'new-password'" :placeholder="legacyPassword ? 'Existing Galaxy password' : legacyPairingAvailable ? 'Existing or new Galaxy password' : 'New password (at least 8 characters)'" @keydown.enter="pair" />
          <button type="button" class="gx-btn" :disabled="busy || password.trim().length < (legacyPassword || legacyPairingAvailable ? 6 : 8)" @click="pair">{{ busy ? 'Pairing…' : 'Pair' }}</button></div>
        </template>
        <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
      </section>
      <section class="gx-card gx-info-card">
        <h3><i class="bi bi-phone" aria-hidden="true"></i> Install Galaxy</h3>
        <p>Open your paired link, then choose <strong>Install app</strong> or <strong>Add to Home Screen</strong>.</p>
        <ul class="gx-install-benefits"><li><i class="bi bi-window" aria-hidden="true"></i> Your own full-screen window</li><li><i class="bi bi-lightning-charge" aria-hidden="true"></i> Launch from your home screen</li><li><i class="bi bi-arrow-repeat" aria-hidden="true"></i> Automatic updates, no app store</li></ul>
        <p class="gx-note">Galaxy is a Progressive Web App and needs an active connection.</p>
      </section>
      <LocalAccess :mode="mode" :on-unauthorized="unauthorized" />
    </div>
  `,
}
