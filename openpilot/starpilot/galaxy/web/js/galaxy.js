import { LocalAccess } from "./local-access.js"

export const GalaxyPage = {
  name: "GalaxyPage",
  components: { LocalAccess },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ loading: true, paired: false, url: "", tunnelClientAvailable: false, legacyPassword: false,
    legacyPairingAvailable: false, password: "", busy: false, error: "" }),
  mounted() { this.load() },
  methods: {
    async request(path, body) {
      const response = await fetch(path, body === undefined ? { cache: "no-store" } : {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      })
      if (response.status === 401) this.unauthorized()
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || "Galaxy request failed")
      return data
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
    <div><h2 style="margin-top:0">Galaxy Tunnel</h2><p>Pair this comma for remote Galaxy access. Galaxy is installed as a Progressive Web App: open the paired link, then use <strong>Install app</strong> or <strong>Add to Home Screen</strong> for a full-screen, app-like experience with no app store download, its own window, instant launch from your home screen, and automatic updates. It needs an active connection, just like the browser version.</p>
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
          <button type="button" class="gx-btn" :disabled="busy || password.trim().length < (legacyPassword || legacyPairingAvailable ? 6 : 8)" @click="pair">{{ busy ? 'Pairing…' : 'Set password & pair' }}</button></div>
        </template>
        <p v-if="error" class="gx-note gx-note--danger" role="alert">{{ error }}</p>
      </section>
      <LocalAccess :mode="mode" :on-unauthorized="unauthorized" />
    </div>
  `,
}
