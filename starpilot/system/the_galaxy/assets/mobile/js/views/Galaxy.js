import { api, showSnackbar } from "../api.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"
import { PwaInstallSection, isFirestarOrigin } from "../components/PwaInstallSection.js"

const isTunnel = () => isFirestarOrigin()

function localDeviceUrl(ip, route = "/") {
  const raw = String(ip || "").trim()
  if (!raw || raw === "unknown") return ""
  const host = raw.includes(":") && !raw.startsWith("[") ? `[${raw}]` : raw
  return `http://${host}:8082/#${route}`
}

export const Galaxy = {
  name: "Galaxy",
  components: { PwaInstallSection },
  data() {
    return {
      loading: true,
      paired: false,
      url: "",
      password: "",
      submitting: false,
      localUrl: "",
    }
  },
  async mounted() {
    if (this.isTunnel) {
      try {
        const status = await api.getDeviceStatus()
        this.localUrl = localDeviceUrl(status?.lanIp, "/galaxy")
      } catch (e) {}
      return
    }
    try {
      const data = await api.getGalaxyStatus()
      this.paired = !!data?.paired
      this.url = data?.url || ""
    } catch (e) {
      showSnackbar("Failed to check pairing status.", "error")
    } finally {
      this.loading = false
    }
  },
  computed: { isTunnel: () => isTunnel() },
  methods: {
    async pair() {
      const pw = this.password.trim()
      if (pw.length < 6) { showSnackbar("Password must be at least 6 characters."); return }
      this.submitting = true
      try {
        const data = await api.galaxyPair(pw)
        this.paired = true
        this.url = data?.url || ""
        this.password = ""
        showSnackbar(data?.message || "Paired!")
      } catch (e) {
        showSnackbar(e?.message || "Network error — is the device reachable?", "error")
      } finally {
        this.submitting = false
      }
    },
    async unpair() {
      if (!(await GalaxyConfirm({
        title: "Confirm Unpair",
        message: "Are you sure you want to unpair from Galaxy? You will lose remote access until you pair again.",
        confirmLabel: "Unpair",
        danger: true,
      }))) return
      this.submitting = true
      try {
        const data = await api.galaxyUnpair()
        this.paired = false
        this.url = ""
        showSnackbar(data?.message || "Unpaired!")
      } catch (e) {
        showSnackbar(e?.message || "Network error — is the device reachable?", "error")
      } finally {
        this.submitting = false
      }
    },
  },
  template: `
    <div>
      <h2 style="margin-top:0;">Galaxy & App Install</h2>

      <template v-if="isTunnel">
        <section class="gx-card">
          <div class="gx-alert gx-alert--warn" style="border:none;margin:0;">
            <i class="bi bi-satellite gx-alert__icon"></i>
            <div class="gx-alert__body">
              <strong>Galaxy Pairing Unavailable via Galaxy</strong>
              <span>
                Galaxy pairing requires a direct connection. If you are on the same local network, connect here:
                <br />
                <a v-if="localUrl" class="gx-btn gx-btn--tonal" :href="localUrl" style="margin-top:var(--sp-3);">
                  <i class="bi bi-box-arrow-up-right"></i> Open Galaxy Locally
                </a>
                <span v-else>your device's local IP on port 8082.</span>
              </span>
            </div>
          </div>
        </section>
      </template>

      <div v-else-if="loading" class="gx-loading">Checking pairing status…</div>

      <section v-else class="gx-card">
        <template v-if="paired">
          <div style="padding: var(--sp-4); display:grid; gap:12px;">
            <span class="gx-chip" style="background:var(--success); color:var(--black); justify-self:start;"><i class="bi bi-check-circle-fill"></i> Paired</span>
            <p style="margin:0; color:var(--text-muted);">Your device is paired with Galaxy. Access it remotely at:</p>
            <a :href="url" target="_blank" rel="noopener" style="color:var(--primary); word-break:break-all;">{{ url }}</a>
            <div>
              <button type="button" class="gx-btn gx-btn--danger" :disabled="submitting" @click="unpair">
                {{ submitting ? 'Unpairing…' : 'Unpair' }}
              </button>
            </div>
          </div>
        </template>

        <template v-else>
          <div style="padding: var(--sp-4); display:grid; gap:12px;">
            <span class="gx-chip gx-chip--lock" style="justify-self:start;">Not Paired</span>
            <p style="margin:0; color:var(--text-muted);">Pair your device with Galaxy to access The Galaxy remotely from anywhere. Set a password to secure your connection.</p>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <input class="gx-field" style="flex:1; min-width:200px;" type="password" v-model="password" placeholder="Password (min 6 characters)" @keydown.enter="pair" />
              <button type="button" class="gx-btn" :disabled="submitting || password.trim().length < 6" @click="pair">
                {{ submitting ? 'Pairing…' : 'Pair' }}
              </button>
            </div>
          </div>
        </template>
      </section>

      <PwaInstallSection :galaxy-url="url" />
    </div>
  `,
}
