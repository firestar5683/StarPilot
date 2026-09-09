import { api, showSnackbar } from "../api.js"
import { navigate, store } from "../store.js"
import {
  applyParamChange, countAdvancedHiddenByDeveloperMode, GALAXY_DEVELOPER_MODE_KEY, isSettingVisible,
  resolveVehicleUnitParam, slugifySectionName,
} from "../params.js"
import { SettingTree } from "../components/SettingTree.js"
import { PersonalityProfiles } from "../components/PersonalityProfiles.js"
import { GalaxyToggleCard } from "../components/GalaxyToggleCard.js"
import { GalaxySection } from "../components/GalaxySection.js"
import { DevModeBanner } from "../components/DevModeBanner.js"

// Match classic Galaxy's retired longitudinal controls in this replacement view.
// These are presentation exclusions only; registry values and backend policy stay intact.
const LEGACY_PERSONALITY_KEYS = new Set([
  "AccelerationProfile", "AggressiveFollow", "AggressiveFollowHigh", "CustomAccelProfile",
  "CustomAccelProfile0MPH", "CustomAccelProfile11MPH", "CustomAccelProfile22MPH", "CustomAccelProfile34MPH",
  "CustomAccelProfile45MPH", "CustomAccelProfile56MPH", "CustomAccelProfile89MPH", "DecelerationProfile",
  "EVTuning", "HumanAcceleration", "RelaxedFollow", "RelaxedFollowHigh", "StandardFollow",
  "StandardFollowHigh", "TrafficFollow", "TruckTuning",
])

export const Settings = {
  name: "Settings",
  components: { SettingTree, PersonalityProfiles, GalaxyToggleCard, GalaxySection, DevModeBanner },
  data() {
    return {
      layout: [],
      values: {},
      expanded: {},
      loading: true,
      activeSectionSlug: "",
      defaultSectionSlug: "lateral-steering",
    }
  },
  computed: {
    devModeOn() { return !!this.values[GALAXY_DEVELOPER_MODE_KEY] },
    route() { return store.route },
    sections() {
      return this.layout
        .filter((s) => s.name !== "Model & Customization")
        .map((s) => ({
          ...s,
          params: (s.params || []).filter((p) => !LEGACY_PERSONALITY_KEYS.has(p.key) && isSettingVisible(s, p, this.values)),
          slug: slugifySectionName(s.name),
        }))
        .filter((s) => s.params.length > 0)
    },
    activeSection() {
      return this.sections.find((s) => s.slug === this.activeSectionSlug) || this.sections[0]
    },
    hiddenAdvancedCount() { return countAdvancedHiddenByDeveloperMode(this.layout, this.values) },
    searchActive() { return !!this.searchTerm },
    searchTerm: {
      get() { return store.search },
      set(v) { store.search = v },
    },
    searchResults() {
      if (!this.searchActive) return []
      return this.sections
        .map((s) => {
          const descendants = new Set(["CustomPersonalities"])
          let size
          do { size = descendants.size; s.params.forEach(p => { if (descendants.has(p.parent_key)) descendants.add(p.key) }) } while (size !== descendants.size)
          return { ...s, matches: s.params.filter(p => p.key === "CustomPersonalities" ? s.params.some(child => descendants.has(child.key) && this.matchesFilter(child)) : !descendants.has(p.key) && this.matchesFilter(p)) }
        })
        .filter((s) => s.matches.length > 0)
    },
  },
  methods: {
    async load() {
      try {
        const [layout, values, defaults] = await Promise.all([
          api.getLayout(), api.getParams(), api.getDefaults(),
        ])
        this.layout = layout
        this.values = values || {}
        this.defaults = defaults || {}
        if (!this.activeSectionSlug && this.sections.length) {
          const preferred = this.sections.find((s) => s.slug === this.defaultSectionSlug)
          this.activeSectionSlug = (preferred || this.sections[0]).slug
        }
      } catch (e) {
        showSnackbar("Failed to load settings: " + (e?.message || e), "error")
      } finally {
        this.loading = false
      }
    },
    onParamChange(patch) {
      this.values = applyParamChange(this.values, patch)
    },
    toggleManage(key) {
      const next = !this.expanded[key]
      this.expanded = { ...this.expanded, [key]: next }
      const base = "/settings/" + this.activeSectionSlug
      window.location.hash = next ? `${base}?open=${encodeURIComponent(key)}` : base
    },
    matchesFilter(p) {
      if (!this.searchTerm) return true
      const q = this.searchTerm.toLowerCase()
      const displayParam = resolveVehicleUnitParam(p, this.values)
      return [displayParam.label, displayParam.key, displayParam.description, displayParam.unit, displayParam.unit_search_terms]
        .some((v) => String(v || "").toLowerCase().includes(q))
    },
    selectSection(slug) {
      if (slug !== this.activeSectionSlug) navigate("/settings/" + slug)
    },
    applyRouteSection() {
      const route = store.route
      if (!route.startsWith("/settings/")) return
      const slug = route.replace(/^\/settings\/?/, "").split("?")[0].split("/")[0]
      if (slug && this.sections.some((s) => s.slug === slug)) this.activeSectionSlug = slug
      if (store.params.open) this.expanded = { ...this.expanded, [store.params.open]: true }
    },
    lockReason(param) {
      if (param?.requires_offroad && this.values.IsOnroad) return "This setting can only be changed while parked."
      if (param?.requires_parked && !this.values.VehicleParked) return "This setting can only be changed while the vehicle is in Park."
      if (param?.disabled_when_key_true && this.values[param.disabled_when_key_true]) return param.disabled_reason || "Disabled by another setting."
      if (param?.requires_nonempty_key) {
        const val = this.values[param.requires_nonempty_key]
        if (!val || val === "{}" || val === "") return param.disabled_reason || "Required configuration missing."
      }
      return ""
    },
  },
  watch: {
    route() { this.applyRouteSection() },
    devModeOn() { this.load() },
  },
  async mounted() {
    await this.load()
    this.applyRouteSection()
  },
  template: `
    <div>
      <h2 style="margin-top:0;">Toggles</h2>

      <DevModeBanner :hidden-count="hiddenAdvancedCount" :dev-mode-on="devModeOn" />

      <div v-if="loading" class="gx-loading">Loading configuration...</div>

      <template v-else-if="sections.length">
        <div v-if="searchActive">
          <div class="gx-card">
            <div class="gx-section__header">
              <i class="bi bi-search"></i>
              <span class="gx-section__title">{{ searchResults.reduce((n, s) => n + s.matches.length, 0) }} result(s)</span>
            </div>
          </div>
          <template v-for="section in searchResults" :key="section.slug">
            <GalaxySection :title="section.name + ' (' + section.matches.length + ')'" :icon="section.icon || 'bi-search'" :default-open="false">
              <template v-for="p in section.matches" :key="p.key">
                <PersonalityProfiles v-if="p.key === 'CustomPersonalities'" :manage-open="!!expanded[p.key]" @manage="toggleManage(p.key)" @change="onParamChange" />
                <GalaxyToggleCard v-else :param="p" :value="values[p.key]" :values="values" :locked="lockReason(p) !== ''"
                  @change="onParamChange" />
              </template>
            </GalaxySection>
          </template>
        </div>

        <div v-else>
          <div class="gx-tabs" style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px;">
            <button v-for="s in sections" :key="s.slug" type="button"
              class="gx-chip" :style="s.slug === activeSection.slug ? 'background: var(--primary); color: var(--on-primary);' : 'background: var(--surface-variant); color: var(--on-surface-variant); cursor:pointer;'"
              @click="selectSection(s.slug)">
              {{ s.name }}
            </button>
          </div>

          <div class="gx-card">
            <div class="gx-section__header">
              <i class="bi" :class="activeSection.icon"></i>
              <span class="gx-section__title">{{ activeSection.name }}</span>
            </div>
            <SettingTree :params="activeSection.params" :parent-key="null" :values="values"
              :expanded="expanded" :lock-reason="lockReason" @change="onParamChange" @manage="toggleManage" />
            <div v-if="!activeSection.params.length" class="gx-empty">No settings in this section.</div>
          </div>
        </div>
      </template>

      <div v-else class="gx-empty">No settings available.</div>
    </div>
  `,
}
