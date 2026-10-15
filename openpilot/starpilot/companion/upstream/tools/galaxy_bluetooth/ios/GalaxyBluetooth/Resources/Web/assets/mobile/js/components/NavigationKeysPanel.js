import { api, showSnackbar } from "../api.js"
import { GalaxyConfirm } from "./GalaxyModal.js"
import { GxNotice } from "./GxNotice.js"

const DEFAULT_PLAY_STORE_URL = "https://play.google.com/store/apps/details?id=com.embaucha.galaxynav&hl=en-US&ah=9FldHJ99kxL8oNbSlO5F4sQqwC4"

const KEY_META = {
  amap1: { body: "amap1", prefix: "", min: 39, title: "AMap / Gaode 1" },
  amap2: { body: "amap2", prefix: "", min: 39, title: "AMap / Gaode 2" },
  public: { body: "public", prefix: "pk.", min: 80, title: "Public Mapbox" },
  secret: { body: "secret", prefix: "sk.", min: 80, title: "Secret Mapbox" },
}

const KINDS = {
  amap: ["amap1", "amap2"],
  mapbox: ["public", "secret"],
}

function maskKey(raw) {
  if (!raw) return ""
  const prefix = ["pk.", "sk."].find((p) => raw.startsWith(p)) || ""
  return prefix + "x".repeat(raw.length - prefix.length)
}

function prefixed(raw, prefix) {
  return raw.startsWith(prefix) ? raw : prefix + raw
}

export const NavigationKeysPanel = {
  name: "NavigationKeysPanel",
  components: { GxNotice },
  data() {
    return {
      loading: true,
      error: "",
      meta: KEY_META,
      amapKinds: KINDS.amap,
      mapboxKinds: KINDS.mapbox,
      appUrl: DEFAULT_PLAY_STORE_URL,
      cookieName: "galaxy_session",
      paired: false,
      sessionToken: "",
      sessionVisible: false,
      keys: { amap1: "", amap2: "", public: "", secret: "" },
      saved: { amap1: false, amap2: false, public: false, secret: false },
      editing: { amap1: false, amap2: false, public: false, secret: false },
    }
  },
  async mounted() {
    try {
      const nav = await api.getNavigation()
      if (nav && typeof nav === "object") {
        const map = { amap1: nav.amap1Key, amap2: nav.amap2Key, public: nav.mapboxPublic, secret: nav.mapboxSecret }
        for (const kind of Object.keys(KEY_META)) {
          const raw = map[kind] || ""
          this.keys[kind] = raw
          this.saved[kind] = !!raw
          this.editing[kind] = false
        }
      }
      await this.loadSession()
    } catch (e) {
      this.error = e?.message || "Failed to load keys..."
    } finally {
      this.loading = false
    }
  },
  methods: {
    async loadSession() {
      try {
        const d = await api.getGalaxySession()
        this.appUrl = d?.appUrl || DEFAULT_PLAY_STORE_URL
        this.cookieName = d?.cookieName || "galaxy_session"
        this.paired = !!d?.paired
        this.sessionToken = d?.sessionToken || ""
        this.sessionVisible = false
      } catch (e) {
        showSnackbar(e?.message || "Failed to load Galaxy session...", "error")
      }
    },
    display(kind) {
      if (this.saved[kind] && !this.editing[kind]) return maskKey(this.keys[kind])
      return this.keys[kind] || ""
    },
    beginEdit(kind) {
      if (this.saved[kind] && !this.editing[kind]) {
        this.editing[kind] = true
        this.saved[kind] = false
        this.keys[kind] = ""
      }
    },
    inputKey(kind, value) {
      this.keys[kind] = value
    },
    canSave(kind) {
      const meta = KEY_META[kind]
      const value = (this.keys[kind] || "").trim()
      if (!value || this.saved[kind]) return false
      return prefixed(value, meta.prefix).length >= meta.min
    },
    async saveKey(kind) {
      const meta = KEY_META[kind]
      const value = prefixed((this.keys[kind] || "").trim(), meta.prefix)
      if (!value || value.length < meta.min) {
        showSnackbar(`${meta.title} key is invalid or too short...`, "error")
        return
      }
      try {
        const payload = await api.setNavigationKey({ [meta.body]: value })
        this.keys[kind] = value
        this.saved[kind] = true
        this.editing[kind] = false
        showSnackbar(payload?.message || "Saved!")
      } catch (e) {
        showSnackbar(e?.data?.error || e?.message || "Save failed...", "error")
      }
    },
    async removeKey(kind) {
      const meta = KEY_META[kind]
      const ok = await GalaxyConfirm({
        title: "Confirm Delete",
        message: `Are you sure you want to delete your <strong>${meta.title}</strong> key?`,
        confirmLabel: "Yes, Delete",
        danger: true,
      })
      if (!ok) return
      try {
        const payload = await api.deleteNavigationKey(kind)
        this.keys[kind] = ""
        this.saved[kind] = false
        this.editing[kind] = false
        showSnackbar(payload?.message || "Deleted!")
      } catch (e) {
        showSnackbar(e?.message || "Delete failed...", "error")
      }
    },
    async copyToken() {
      const text = this.sessionToken
      if (!text) return
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(text)
          showSnackbar("Session token copied!")
          return
        }
        const textarea = document.createElement("textarea")
        textarea.value = text
        textarea.setAttribute("readonly", "")
        textarea.style.position = "fixed"
        textarea.style.left = "-9999px"
        document.body.appendChild(textarea)
        textarea.select()
        const ok = document.execCommand("copy")
        textarea.remove()
        if (!ok) throw new Error("Copy failed")
        showSnackbar("Session token copied!")
      } catch (e) {
        showSnackbar("Copy failed...", "error")
      }
    },
    inputLabel(kind) {
      return kind[0].toUpperCase() + kind.slice(1).replace(/[0-9]/, (d) => " " + d)
    },
  },
  template: `
    <div style="display:grid; gap:12px;">
      <div v-if="loading" class="gx-loading">Loading keys...</div>
      <template v-else>
        <GxNotice v-if="error" tone="danger" :text="error" />

        <section class="gx-card">
          <div class="gx-section__header">
            <i class="bi bi-signpost"></i>
            <span class="gx-section__title">AMap / Gaode Keys</span>
          </div>
          <div style="padding: var(--sp-3); display:grid; gap:8px;">
            <p style="margin:0; color:var(--text-muted);">AMap is the Gaode provider, not Google Maps.</p>
            <div v-for="kind in amapKinds" :key="kind">
              <label class="gx-row__label" style="font-size:var(--fs-xs);">{{ inputLabel(kind) }} Key</label>
              <div style="display:flex; gap:8px;">
                <input class="gx-field" style="flex:1;" :value="display(kind)" @focus="beginEdit(kind)" @input="inputKey(kind, $event.target.value)" :placeholder="meta[kind].prefix + 'xxxxxx...'" autocomplete="off" />
                <button type="button" class="gx-icon-btn" :title="saved[kind] ? 'Delete key' : 'Save key'" :style="saved[kind] ? 'color:var(--error);' : ''" :disabled="!saved[kind] && !canSave(kind)" @click="saved[kind] ? removeKey(kind) : saveKey(kind)">
                  <i class="bi" :class="saved[kind] ? 'bi-trash' : 'bi-save'"></i>
                </button>
              </div>
            </div>
          </div>
        </section>

        <section class="gx-card">
          <div class="gx-section__header">
            <i class="bi bi-map"></i>
            <span class="gx-section__title">Mapbox Keys</span>
          </div>
          <div style="padding: var(--sp-3); display:grid; gap:8px;">
            <p style="margin:0; color:var(--text-muted);">Public and secret Mapbox tokens used by the navigation app.</p>
            <div v-for="kind in mapboxKinds" :key="kind">
              <label class="gx-row__label" style="font-size:var(--fs-xs);">{{ inputLabel(kind) }} Key</label>
              <div style="display:flex; gap:8px;">
                <input class="gx-field" style="flex:1;" :value="display(kind)" @focus="beginEdit(kind)" @input="inputKey(kind, $event.target.value)" :placeholder="meta[kind].prefix + 'xxxxxx...'" autocomplete="off" />
                <button type="button" class="gx-icon-btn" :title="saved[kind] ? 'Delete key' : 'Save key'" :style="saved[kind] ? 'color:var(--error);' : ''" :disabled="!saved[kind] && !canSave(kind)" @click="saved[kind] ? removeKey(kind) : saveKey(kind)">
                  <i class="bi" :class="saved[kind] ? 'bi-trash' : 'bi-save'"></i>
                </button>
              </div>
            </div>
          </div>
        </section>

        <section class="gx-card">
          <div class="gx-section__header">
            <i class="bi bi-phone"></i>
            <span class="gx-section__title">App Keys</span>
          </div>
          <div style="padding: var(--sp-3); display:grid; gap:8px;">
            <a class="gx-btn gx-btn--tonal" :href="appUrl" target="_blank" rel="noopener noreferrer" style="justify-self:start;">
              <i class="bi bi-google-play"></i> Install The App
            </a>
            <label class="gx-row__label" style="font-size:var(--fs-xs);">Cookie Name</label>
            <input class="gx-field gx-field--full" readonly :value="cookieName" />
            <label class="gx-row__label" style="font-size:var(--fs-xs);">Session Token</label>
            <div style="display:flex; gap:8px;">
              <input class="gx-field" style="flex:1;" readonly :type="sessionVisible ? 'text' : 'password'" :placeholder="paired ? 'Session token unavailable...' : 'Pair Galaxy to create a session token...'" :value="sessionToken" />
              <button type="button" class="gx-icon-btn" :title="sessionVisible ? 'Hide session token' : 'Show session token'" :disabled="!sessionToken" @click="sessionVisible = !sessionVisible">
                <i class="bi" :class="sessionVisible ? 'bi-eye-slash' : 'bi-eye'"></i>
              </button>
              <button type="button" class="gx-btn gx-btn--tonal" :disabled="!sessionToken" @click="copyToken"><i class="bi bi-copy"></i> Copy</button>
            </div>
          </div>
        </section>
      </template>
    </div>
  `,
}
