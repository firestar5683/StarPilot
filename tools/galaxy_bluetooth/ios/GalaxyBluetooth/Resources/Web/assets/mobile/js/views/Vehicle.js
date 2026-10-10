import { api, showSnackbar } from "../api.js"
import { navigate, toolHref } from "../store.js"
import { GalaxySection } from "../components/GalaxySection.js"

const FEATURES = [
  { key: "doors", name: "Lock/Unlock Doors", icon: "bi-door-closed", desc: "Send lock or unlock commands remotely to your vehicle.", embed: "/manage_doors" },
  { key: "tsk", name: "Toyota Security Keys", icon: "bi-key-fill", desc: "Manage and apply security keys for secOC protected devices.", embed: "/manage_tsk" },
]

export const Vehicle = {
  name: "Vehicle",
  components: { GalaxySection },
  data() {
    return {
      features: FEATURES,
      featureStatus: {},
      busy: "",
    }
  },
  computed: {
    featureList() { return this.features },
  },
  methods: {
    statusOf(key) { return this.featureStatus[key] || "untested" },
    async openFeature(f) {
      if (this.busy) return
      if (this.statusOf(f.key) === "denied") {
        showSnackbar(`${f.name} is not supported for your current vehicle.`, "error")
        return
      }
      if (this.statusOf(f.key) === "allowed") {
        navigate(toolHref(f.embed))
        return
      }
      this.busy = f.key
      try {
        const data = await api.carFeaturesCheck(f.key)
        const allowed = !!data?.result
        this.featureStatus = { ...this.featureStatus, [f.key]: allowed ? "allowed" : "denied" }
        if (allowed) navigate(toolHref(f.embed))
        else showSnackbar(`${f.name} is not supported for your current vehicle.`, "error")
      } catch (e) {
        this.featureStatus = { ...this.featureStatus, [f.key]: "denied" }
        showSnackbar("Could not check vehicle compatibility.", "error")
      } finally {
        this.busy = ""
      }
    },
  },
  template: `
    <div class="gx-view">
      <h2 style="margin-top:0;">Vehicle Controls</h2>

      <GalaxySection title="Vehicle Features" icon="bi-check2-square">
        <div style="padding: var(--sp-3); display:grid; gap:8px;">
          <button v-for="f in featureList" :key="f.key" type="button"
            class="gx-row" style="width:100%; border:none; background:transparent; color:inherit; cursor:pointer; text-align:left;"
            @click="openFeature(f)">
            <div class="gx-row__info">
              <span class="gx-row__label"><i class="bi" :class="f.icon" style="margin-right:6px; color:var(--primary);"></i>{{ f.name }}</span>
              <span class="gx-row__desc">{{ f.desc }}</span>
            </div>
            <span v-if="busy === f.key" class="gx-chip" style="background:var(--surface-variant);">Checking...</span>
            <span v-else-if="statusOf(f.key) === 'denied'" class="gx-chip" style="background:var(--error);">Not supported</span>
            <i v-else class="bi bi-chevron-right" style="color:var(--text-muted);"></i>
          </button>
          <p style="color:var(--text-muted); margin:0;">These features verify vehicle compatibility when launched.</p>
        </div>
      </GalaxySection>
    </div>
  `,
}
