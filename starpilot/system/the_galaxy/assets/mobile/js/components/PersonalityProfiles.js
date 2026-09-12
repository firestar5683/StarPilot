import { api, showSnackbar } from "../api.js"
import { numericBounds } from "../params.js"
import { formatProfileSpeed, profileSpeedUnit, personalityProfileParamKey } from "../../../components/tools/personality_profiles.mjs"

const PROFILES = ["traffic", "aggressive", "standard", "relaxed"]
const CATEGORIES = { acceleration: "Acceleration", braking: "Braking", following: "Following" }

export const PersonalityProfiles = {
  name: "PersonalityProfiles",
  props: { manageOpen: { default: null } },
  emits: ["change", "manage"],
  data() {
    return { PROFILES, CATEGORIES, data: null, values: {}, meta: {}, busy: false, ready: false,
      error: "", notice: "", localExpanded: false, advancedOpen: {}, drafts: {}, curvePending: false, recovery: false, curveText: {}, advancedText: {}, curveErrors: {}, advancedErrors: {}, drag: null, advancedCustom: {}, contextPending: false, contextRequest: null, loadPending: false, timer: null, disposed: false }
  },
  computed: {
    expanded: { get() { return this.manageOpen ?? this.localExpanded }, set(value) { this.localExpanded = value; this.$emit("manage") } },
    offroad() { return [false, "", "0", "False", "false"].includes(this.values.IsOnroad) && [true, "1", "True", "true"].includes(this.values.IsOffroad) },
    locked() { return !this.ready || this.busy || !this.offroad },
    editingLocked() { return this.locked || this.curvePending || !!this.data?.migration_required },
  },
  async mounted() {
    await this.load()
    if (!this.disposed) this.timer = setInterval(() => this.ready ? this.refreshContext() : this.load(), 4000)
  },
  beforeUnmount() {
    this.disposed = true; clearInterval(this.timer)
    this.drag = null; this.drafts = {}; this.curveText = {}
  },
  methods: {
    enabled(value) { return [true, 1, "1", "True", "true"].includes(value) },
    label(value) { return value.split("_").map(s => s === "plus" ? "+" : s[0].toUpperCase() + s.slice(1)).join(" ").replace(" +", "+") },
    key: personalityProfileParamKey,
    speed(value) { return formatProfileSpeed(value, this.enabled(this.values.IsMetric)) },
    speedUnit() { return profileSpeedUnit(this.enabled(this.values.IsMetric)) },
    bounds(param) { return numericBounds(param, this.values) },
    options(category) { return (category === "following" ? ["close", "medium", "far", "custom"] : ["eco", "standard", "sport", "sport_plus", "custom"]).filter(x => this.data.options[category].includes(x)) },
    advancedParams(profile) {
      return Object.values(this.meta).filter(p => p.parent_key === this.key(profile) && p.key.includes("Jerk"))
    },
    advancedMode(key) {
      if (this.advancedCustom[key]) return "custom"
      const value = Number(this.values[key])
      if (value === 100) return "standard"
      if (!key.endsWith("JerkDanger") && value === 50) return "chill"
      return "custom"
    },
    async advancedPreset(param, mode) {
      if (this.paramLocked(param.key)) return
      if (mode === "custom") { this.advancedCustom[param.key] = true; return }
      if (await this.setAdvanced(param, mode === "chill" ? 50 : 100)) delete this.advancedCustom[param.key]
    },
    paramLocked(key) {
      const p = this.meta[key]
      return this.editingLocked || !p ||
        (p.requires_parked && !this.values.VehicleParked) ||
        (p.requires_capability && !this.values[p.requires_capability]) ||
        (p.disabled_when_key_true && !!this.values[p.disabled_when_key_true]) ||
        (p.requires_nonempty_key && (!this.values[p.requires_nonempty_key] || this.values[p.requires_nonempty_key] === "{}"))
    },
    validate(data) {
      for (const profile of PROFILES) for (const category of Object.keys(CATEGORIES)) {
        const config = data?.profiles?.[profile]?.[category]
        const speeds = data?.speed_breakpoints_mph?.[category]
        const bounds = data?.bounds?.[category]
        const reference = data?.reference_curves?.[profile]?.[category]
        if (!config || !Array.isArray(config.curve) || !Array.isArray(speeds) || !speeds.length ||
            !speeds.every((v, i) => Number.isFinite(v) && v >= 0 && (!i || v > speeds[i - 1])) || speeds.at(-1) <= 0 ||
            !Array.isArray(bounds) || bounds.length !== 2 || !bounds.every(Number.isFinite) || bounds[0] >= bounds[1] ||
            !Array.isArray(reference) || reference.length !== speeds.length || !reference.every(Number.isFinite) ||
            !Array.isArray(data?.options?.[category]) || !data.options[category].includes(config.preset) ||
            (config.preset === "custom" && config.curve.length !== speeds.length) || !config.curve.every(Number.isFinite) ||
            !Array.isArray(data?.bounds?.[category]) || !Array.isArray(data?.options?.[category])) {
          throw new Error("Profile data is unavailable or malformed. Retrying automatically…")
        }
      }
      return data
    },
    acceptData(data) {
      const next = this.validate(data)
      for (const profile of PROFILES) for (const category of Object.keys(CATEGORIES)) {
        const key = profile + category
        if (this.drafts[key] && JSON.stringify(this.data?.profiles?.[profile]?.[category]) !== JSON.stringify(next.profiles[profile][category])) {
          this.discard(profile, category)
          if (!this.busy && !this.curvePending) { this.drag = null; this.notice = "Saved profiles changed. The affected preview was cancelled." }
        }
      }
      this.data = next
    },
    async load() {
      if (this.busy || this.loadPending || this.contextPending) return
      this.loadPending = true
      this.ready = false
      try {
        const [data, values, layout] = await Promise.all([api.getPersonalityProfiles(), api.getParams(), api.getLayout()])
        if (this.disposed) return
        if (!values || typeof values !== "object" || Array.isArray(values) || !Array.isArray(layout) || !layout.every(s => Array.isArray(s.params))) throw new Error("Settings metadata is unavailable. Retrying automatically…")
        this.acceptData(data)
        this.values = values
        this.meta = Object.fromEntries(layout.flatMap(s => s.params).map(p => [p.key, p]))
        const required = ["CustomPersonalities", ...PROFILES.flatMap(profile => [this.key(profile), ...["Acceleration", "Deceleration", "Danger", "SpeedDecrease", "Speed"].map(suffix => this.label(profile) + "Jerk" + suffix)])]
        if (required.some(key => !this.meta[key])) throw new Error("Personality metadata is incomplete. Retrying automatically…")
        this.ready = true
        this.error = ""
        if (this.recovery) { this.notice = "Save could not be confirmed. Showing verified saved state; review it before editing again."; this.recovery = false }
      } catch (e) { this.error = e.message }
      finally { this.loadPending = false }
    },
    async refreshContext() {
      if (this.busy || !this.ready || this.contextPending) return
      this.contextPending = true
      try {
        this.contextRequest = api.getParams()
        const values = await this.contextRequest
        if (this.disposed) return
        if (!this.busy) this.values = values
        if (!this.offroad) { this.drag = null; this.drafts = {}; this.curveText = {} }
      } catch (e) { this.ready = false; this.error = "Connection lost. Reconnecting…" }
      finally { this.contextPending = false; this.contextRequest = null }
    },
    async write(action, check = () => !this.editingLocked) {
      if (this.contextPending) { try { await this.contextRequest } catch { return } }
      if (this.disposed || !check()) return
      this.busy = true
      this.error = ""
      this.notice = ""
      try {
        await action()
        if (this.disposed) return
        const [data, values] = await Promise.all([api.getPersonalityProfiles(), api.getParams()])
        if (this.disposed) return
        this.acceptData(data)
        this.values = values
        this.$emit("change", values)
        showSnackbar("Driving personalities saved.")
        return true
      } catch (e) {
        if (this.disposed) return
        this.error = e.message + " Rechecking saved state…"
        this.ready = false
        this.recovery = true
        this.drafts = {}; this.curveText = {}
      } finally { this.busy = false }
      if (!this.disposed) await this.load()
    },
    migrate() { return this.write(() => api.migratePersonalityProfiles(), () => !this.locked) },
    toggle(key, event) {
      const value = event.target.checked
      event.target.checked = this.enabled(this.values[key])
      return this.write(() => api.updateParam({ key, value }), () => !this.paramLocked(key))
    },
    async preset(profile, category, preset) {
      if (this.data.profiles[profile][category].preset === preset) return
      if (await this.write(() => api.savePersonalityProfile({ profile, category, preset, curve: [], expected: this.data.profiles[profile][category] }))) { this.discard(profile, category); this.notice = ""; if (preset === "custom") this.advancedOpen[profile] = true }
    },
    draft(profile, category) { return this.drafts[profile + category] || this.data.profiles[profile][category].curve },
    point(profile, category, index, event, preview = false) {
      if (this.editingLocked) return
      const raw = event.target.value
      delete this.curveText[profile + category + index]
      const value = Number(raw)
      const [min, max] = this.data.bounds[category]
      if (!raw.trim() || !Number.isFinite(value) || value < min || value > max || Math.abs(value / 0.05 - Math.round(value / 0.05)) > 1e-7) {
        event.target.value = this.draft(profile, category)[index]
        this.curveErrors[profile + category] = `Edited points must be between ${min} and ${max}, in 0.05 increments.`
        return
      }
      const curve = [...this.draft(profile, category)]
      curve[index] = value
      this.drafts = { ...this.drafts, [profile + category]: curve }
      delete this.curveErrors[profile + category]
      if (!preview) return this.saveCurve(profile, category)
    },
    discard(profile, category) { delete this.drafts[profile + category]; delete this.curveErrors[profile + category] },
    async saveCurve(profile, category, reset = false) {
      if (this.editingLocked || this.disposed) return
      const curve = reset ? [] : this.draft(profile, category)
      if (!Array.isArray(curve)) return
      const snapshot = [...curve]
      this.curvePending = true
      try {
        if (this.contextPending) { try { await this.contextRequest } catch { return } }
        if (this.disposed) return
        if (await this.write(() => api.savePersonalityProfile({ profile, category, preset: "custom", curve: snapshot, ...(reset ? { reset: true } : {}), expected: this.data.profiles[profile][category] }), () => !this.locked && !this.data?.migration_required)) this.notice = ""
      } finally {
        this.discard(profile, category)
        this.curvePending = false
      }
    },
    async setAdvanced(param, raw) {
      if (this.contextPending) { try { await this.contextRequest } catch { return } }
      if (this.disposed) return
      const value = Number(raw)
      const { min, max, step } = this.bounds(param)
      if (String(raw).trim() === "" || !Number.isFinite(value) || value < min || value > max || Math.abs((value - min) / step - Math.round((value - min) / step)) > 1e-7) {
        this.advancedErrors[param.key] = `Enter ${min}–${max}% in increments of ${step}.`; return
      }
      delete this.advancedErrors[param.key]
      return this.write(() => api.updateParam({ key: param.key, value }), () => !this.paramLocked(param.key))
    },
    graphMax(profile, category) {
      if (this.drag?.profile === profile && this.drag.category === category) return this.drag.max
      return Math.max(this.data.bounds[category][1], ...this.draft(profile, category), ...(this.data.reference_curves?.[profile]?.[category] || []))
    },
    graphMin(profile, category) { return this.drag?.profile === profile && this.drag.category === category ? this.drag.min : Math.min(this.data.bounds[category][0], ...this.draft(profile, category), ...(this.data.reference_curves?.[profile]?.[category] || [])) },
    graphPoints(profile, category, reference = false) {
      const curve = reference ? this.data.reference_curves?.[profile]?.[category] : this.draft(profile, category)
      const max = this.graphMax(profile, category)
      const min = this.graphMin(profile, category)
      const speeds = this.data.speed_breakpoints_mph[category]
      return (curve || []).map((v, i) => ({ x: 10 + speeds[i] / speeds[speeds.length - 1] * 280, y: 90 - (v - min) / (max - min) * 80 }))
    },
    graph(profile, category, reference = false) {
      return this.graphPoints(profile, category, reference).map(p => `${p.x},${p.y}`).join(" ")
    },
    startDrag(profile, category, index, event) {
      if (this.editingLocked || this.drag || event.button !== 0) return
      const svg = event.currentTarget.ownerSVGElement || event.currentTarget
      svg.setPointerCapture(event.pointerId)
      this.drag = { profile, category, index, pointerId: event.pointerId, min: this.graphMin(profile, category), max: this.graphMax(profile, category), previous: this.drafts[profile + category] ? [...this.drafts[profile + category]] : null }
      event.preventDefault()
      this.moveDrag(event)
    },
    pickPoint(profile, category, event) {
      const matrix = event.currentTarget.getScreenCTM()
      if (!matrix) return
      const x = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse()).x
      const points = this.graphPoints(profile, category)
      const index = points.reduce((best, p, i) => Math.abs(p.x - x) < Math.abs(points[best].x - x) ? i : best, 0)
      this.startDrag(profile, category, index, event)
    },
    moveDrag(event) {
      const d = this.drag
      if (!d || d.pointerId !== event.pointerId) return
      if (this.editingLocked) { this.endDrag(event); return }
      const matrix = event.currentTarget.getScreenCTM()
      if (!matrix) return
      const position = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse())
      const [min, max] = this.data.bounds[d.category]
      const value = Math.max(min, Math.min(max, Math.round((d.min + (90 - position.y) / 80 * (d.max - d.min)) * 20) / 20))
      this.point(d.profile, d.category, d.index, { target: { value: String(value) } }, true)
      event.preventDefault()
    },
    endDrag(event) {
      if (!this.drag || this.drag.pointerId !== event.pointerId) return
      const { profile, category } = this.drag
      const commit = event.type === "pointerup" && !this.editingLocked
      if (event.type === "pointercancel" || event.type === "lostpointercapture" || this.editingLocked) {
        const key = this.drag.profile + this.drag.category
        if (this.drag.previous) this.drafts[key] = this.drag.previous
        else delete this.drafts[key]
      }
      this.drag = null
      if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
      if (commit) return this.saveCurve(profile, category)
    },
  },
  template: `
    <section class="gx-personalities" aria-label="Driving personalities">
      <div class="gx-row gx-personalities__heading">
        <div class="gx-row__info"><span class="gx-row__label">Driving Personalities</span><span class="gx-row__desc">Acceleration, braking and following for each driving style.</span></div>
        <label class="gx-switch">
          <input type="checkbox" aria-label="Custom personalities" :checked="enabled(values.CustomPersonalities)" :disabled="paramLocked('CustomPersonalities')" @change="toggle('CustomPersonalities', $event)" />
          <span class="gx-switch__track"></span><span class="gx-switch__thumb"></span>
        </label>
      </div>
      <button type="button" class="gx-manage-btn" :aria-expanded="expanded" aria-controls="gx-personality-settings" @click="expanded = !expanded">{{ expanded ? 'Close' : 'Manage' }}<i class="bi" :class="expanded ? 'bi-chevron-up' : 'bi-chevron-down'" aria-hidden="true"></i></button>
      <div id="gx-personality-settings" v-show="expanded">
      <p v-if="error" role="alert" class="gx-personalities__error">{{ error }}</p>
      <button v-if="error && !ready" type="button" class="gx-btn gx-btn--tonal" :disabled="busy || loadPending || contextPending" @click="load">Retry loading</button>
      <p v-if="notice" role="status">{{ notice }}</p>
      <p v-if="busy" role="status" class="gx-personalities__live">Saving…</p>
      <p v-if="!data && !error" role="status">Loading profiles…</p>
      <template v-if="data">
        <p v-if="!offroad" role="note">Active driving personality can be switched on-road. Saved profile tuning is available off-road.</p>
        <div v-if="data.migration_required" role="alert" class="gx-personalities__error">
          <p>Stored profiles need migration before editing.</p>
          <button type="button" class="gx-btn" :disabled="locked" @click="migrate">Migrate profiles</button>
        </div>
        <p v-if="!enabled(values.CustomPersonalities)">Enable to configure profiles. Existing defaults remain active while off.</p>
        <div class="gx-personalities__grid">
          <article v-for="profile in PROFILES" :key="profile" class="gx-card gx-personalities__profile">
            <div class="gx-personalities__toggle"><strong>{{ profile === 'traffic' ? 'Traffic Mode' : label(profile) }}</strong>
              <label class="gx-switch"><input type="checkbox" :aria-label="label(profile) + ' profile'" :checked="enabled(values[key(profile)])" :disabled="paramLocked(key(profile))" @change="toggle(key(profile), $event)" /><span class="gx-switch__track"></span><span class="gx-switch__thumb"></span></label>
            </div>
            <p v-if="!enabled(values[key(profile)])">Turn on to configure this profile.</p>
            <template v-else>
              <section v-for="(title, category) in CATEGORIES" :key="category" class="gx-personalities__category">
                <h4>{{ title }}</h4>
                <div class="gx-personalities__options" role="group" :aria-label="label(profile) + ' ' + title">
                  <button v-for="option in options(category)" :key="option" type="button" class="gx-btn gx-btn--tonal"
                    :aria-pressed="data.profiles[profile][category].preset === option" :disabled="editingLocked"
                    @click="preset(profile, category, option)">{{ label(option) }}</button>
                </div>
                <p v-if="data.profiles[profile][category].preset === 'dom_default'">Using existing Dom default.</p>
              </section>
              <details class="gx-personalities__advanced" :open="advancedOpen[profile]" @toggle="advancedOpen[profile] = $event.target.open">
                <summary>Advanced</summary>
                <template v-for="(title, category) in CATEGORIES" :key="category">
                <details v-if="data.profiles[profile][category].preset === 'custom'" open class="gx-personalities__curve">
                  <summary>Custom {{ title.toLowerCase() }} graph</summary>
                  <p>{{ category === 'following' ? 'Seconds' : 'm/s²' }} · {{ speedUnit() }}. Dashed: Dom default.</p>
                  <div class="gx-personalities__plot" tabindex="0" :aria-label="label(profile) + ' ' + title + ' graph; scroll horizontally on narrow screens'">
                  <svg viewBox="-30 -12 340 140" role="group" :aria-disabled="editingLocked" :aria-label="label(profile) + ' ' + title + ' editable curve; exact values below'"
                    style="touch-action: pan-x" @pointerdown="pickPoint(profile, category, $event)" @pointermove="moveDrag" @pointerup="endDrag" @pointercancel="endDrag" @lostpointercapture="endDrag">
                    <g fill="currentColor" font-size="10" style="pointer-events: none">
                      <text x="10" y="-3">{{ category === 'following' ? 'Seconds' : 'm/s²' }}</text>
                      <g v-for="tick in [0, 1, 2, 3, 4]" :key="'y' + tick">
                        <line x1="10" x2="290" :y1="90 - tick * 20" :y2="90 - tick * 20" stroke="currentColor" opacity="0.18" />
                        <text x="5" :y="93 - tick * 20" text-anchor="end">{{ Number((graphMin(profile, category) + (graphMax(profile, category) - graphMin(profile, category)) * tick / 4).toFixed(2)) }}</text>
                      </g>
                      <g v-for="tick in [0, 1, 2, 3, 4]" :key="'x' + tick">
                        <line :x1="10 + tick * 70" :x2="10 + tick * 70" y1="10" y2="94" stroke="currentColor" opacity="0.18" />
                        <text :x="10 + tick * 70" y="105" text-anchor="middle">{{ speed(data.speed_breakpoints_mph[category].at(-1) * tick / 4) }}</text>
                      </g>
                      <text x="150" y="121" text-anchor="middle">Speed ({{ speedUnit() }})</text>
                    </g>
                    <polyline :points="graph(profile, category, true)" fill="none" stroke="currentColor" stroke-dasharray="4 4" opacity="0.5" />
                    <polyline :points="graph(profile, category)" fill="none" stroke="var(--primary)" stroke-width="2" />
                    <g v-for="(p, i) in graphPoints(profile, category)" :key="i">
                      <circle :cx="p.x" :cy="p.y" r="3" fill="var(--primary)" stroke="currentColor" stroke-width="0.5" />
                      <circle :cx="p.x" :cy="p.y" r="9" fill="transparent" :style="{ cursor: editingLocked ? 'not-allowed' : 'ns-resize' }"
                        ><title>{{ speed(data.speed_breakpoints_mph[category][i]) }} {{ speedUnit() }}: {{ draft(profile, category)[i] }}</title></circle>
                    </g>
                  </svg>
                  </div>

                  <p v-if="draft(profile, category).some(v => v > data.bounds[category][1])" role="note">Saved values above {{ data.bounds[category][1] }} are shown at their original scale. Only edited points use the current authoring bounds.</p>
                  <p v-if="curveErrors[profile + category]" :id="'curve-error-' + profile + category" role="alert" class="gx-personalities__error">{{ curveErrors[profile + category] }}</p>
                  <div class="gx-personalities__points">
                    <label v-for="(value, i) in draft(profile, category)" :key="i">{{ speed(data.speed_breakpoints_mph[category][i]) }} {{ speedUnit() }}
                      <input type="number" step="0.05" :min="data.bounds[category][0]" :max="data.bounds[category][1]" :value="curveText[profile + category + i] ?? value" :disabled="editingLocked"
                        @input="curveText[profile + category + i] = $event.target.value"
                        :aria-invalid="!!curveErrors[profile + category]" :aria-describedby="curveErrors[profile + category] ? 'curve-error-' + profile + category : undefined"
                        :aria-label="label(profile) + ' ' + title + ' at ' + speed(data.speed_breakpoints_mph[category][i]) + ' ' + speedUnit() + ', ' + (category === 'following' ? 'seconds' : 'm/s²')" @change="point(profile, category, i, $event)" />
                    </label>
                  </div>
                  <div class="gx-personalities__options">
                    <button type="button" class="gx-btn gx-btn--tonal" :disabled="editingLocked"
                      :aria-label="label(profile) + ' ' + title + ' reset to default'" @click="saveCurve(profile, category, true)">Reset to default</button>
                  </div>
                </details>
                </template>
                <p>Custom values are untested and may not be supported by the developer.</p>
                <div v-for="param in advancedParams(profile)" :key="param.key" class="gx-personalities__category">
                  <label>{{ param.label }}
                    <span class="gx-row__desc">{{ param.description }}</span>
                    <input v-if="advancedMode(param.key) === 'custom'" type="number" :value="advancedText[param.key] ?? values[param.key]" :min="bounds(param).min" :max="bounds(param).max" :step="bounds(param).step"
                      @input="advancedText[param.key] = $event.target.value"
                      :aria-label="label(profile) + ' ' + param.label + ' custom percentage'"
                      :aria-invalid="!!advancedErrors[param.key]" :aria-describedby="advancedErrors[param.key] ? 'advanced-error-' + param.key : undefined"
                      :disabled="paramLocked(param.key)" @change="async event => { await setAdvanced(param, event.target.value); delete advancedText[param.key]; event.target.value = values[param.key] }" />
                    <span v-if="advancedMode(param.key) === 'custom'" class="gx-row__desc">{{ bounds(param).min }}–{{ bounds(param).max }}% · step {{ bounds(param).step }}</span>
                  </label>
                  <p v-if="advancedErrors[param.key]" :id="'advanced-error-' + param.key" role="alert" class="gx-personalities__error">{{ advancedErrors[param.key] }}</p>
                  <div class="gx-personalities__options" role="group" :aria-label="label(profile) + ' advanced ' + param.label + ' percentage'">
                    <button v-if="!param.key.endsWith('JerkDanger')" class="gx-btn gx-btn--tonal" :aria-pressed="advancedMode(param.key) === 'chill'" :disabled="paramLocked(param.key)" @click="advancedPreset(param, 'chill')">Chill</button>
                    <button class="gx-btn gx-btn--tonal" :aria-pressed="advancedMode(param.key) === 'standard'" :disabled="paramLocked(param.key)" @click="advancedPreset(param, 'standard')">Standard</button>
                    <button class="gx-btn gx-btn--tonal" :aria-pressed="advancedMode(param.key) === 'custom'" :disabled="paramLocked(param.key)" @click="advancedPreset(param, 'custom')">Custom</button>
                  </div>
                </div>
              </details>
            </template>
          </article>
        </div>
      </template>
      </div>
    </section>
  `,
}
