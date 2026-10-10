import { api } from "../api.js"
import { isSettingVisible, resolveVehicleUnitParam, slugifySectionName, applyParamChange } from "../params.js"
import { SettingTree } from "./SettingTree.js"
import { GalaxySection } from "./GalaxySection.js"

export const ParamSections = {
  name: "ParamSections",
  components: { SettingTree, GalaxySection },
  props: {
    sectionNames: { type: Array, required: true },
    search: { type: String, default: "" },
  },
  data() {
    return {
      layout: [],
      values: {},
      expanded: {},
      loading: true,
      error: "",
    }
  },
  computed: {
    sections() {
      return this.layout
        .filter((s) => this.sectionNames.includes(s.name))
        .map((s) => ({
          ...s,
          params: (s.params || []).filter((p) => isSettingVisible(s, p, this.values) && this.matches(p)),
          slug: slugifySectionName(s.name),
        }))
        .filter((s) => s.params.length > 0)
    },
  },
  methods: {
    matches(p) {
      if (!this.search) return true
      const q = this.search.toLowerCase()
      const displayParam = resolveVehicleUnitParam(p, this.values)
      return [displayParam.label, displayParam.key, displayParam.description, displayParam.unit, displayParam.unit_search_terms]
        .some((v) => String(v || "").toLowerCase().includes(q))
    },
    async load() {
      try {
        const [layout, values] = await Promise.all([api.getLayout(), api.getParams()])
        this.layout = layout
        this.values = values || {}
      } catch (e) {
        this.error = e?.message || "Failed to load settings."
      } finally {
        this.loading = false
      }
    },
    onParamChange(patch) { this.values = applyParamChange(this.values, patch) },
    toggleManage(key) { this.expanded = { ...this.expanded, [key]: !this.expanded[key] } },
  },
  async mounted() { await this.load() },
  template: `
    <div>
      <div v-if="loading" class="gx-loading">Loading configuration...</div>
      <div v-if="error" class="gx-empty" style="color: var(--error);">{{ error }}</div>
      <GalaxySection v-for="s in sections" :key="s.slug" :title="s.name" :icon="s.icon || 'bi-toggles'" :count="s.params.length">
        <SettingTree :params="s.params" :parent-key="null" :values="values" :expanded="expanded"
          @change="onParamChange" @manage="toggleManage" />
        <div v-if="!s.params.length" class="gx-empty">No settings in this section.</div>
      </GalaxySection>
    </div>
  `,
}
