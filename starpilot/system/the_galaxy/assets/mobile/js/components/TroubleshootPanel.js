import { api, showSnackbar } from "../api.js"
import { GalaxyConfirm } from "./GalaxyModal.js"
import { GxNotice } from "./GxNotice.js"

function formatValue(value) {
  if (typeof value === "boolean") return value ? "On" : "Off"
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(4)))
  if (value === null || value === undefined) return "n/a"
  const text = String(value).trim()
  return text || "(empty)"
}

function formatLearnedValue(value) {
  if (value === null || value === undefined) return ""
  const text = String(value).trim()
  return text ? formatValue(value) : ""
}

function valuesMatch(left, right) {
  if (left === right) return true
  if ((left === null || left === undefined) && (right === null || right === undefined)) return true
  if (typeof left === "number" && typeof right === "number") return Math.abs(left - right) < 1e-9
  const lt = String(left ?? "").trim()
  const rt = String(right ?? "").trim()
  if (!lt && !rt) return true
  const ln = Number(lt)
  const rn = Number(rt)
  if (lt !== "" && rt !== "" && Number.isFinite(ln) && Number.isFinite(rn)) return Math.abs(ln - rn) < 1e-9
  return lt === rt
}

export const TroubleshootPanel = {
  name: "TroubleshootPanel",
  components: { GxNotice },
  data() {
    return {
      loading: true,
      refreshing: false,
      busySection: "",
      error: "",
      onlyNonDefault: false,
      vehicleStatus: { available: false, summary: "", summarySeverity: "neutral", items: [] },
      snapshot: [],
      sections: [],
      isOnroad: false,
    }
  },
  computed: {
    countNonDefault() {
      return this.sections.reduce((count, s) => count + (Array.isArray(s.items) ? s.items.filter((i) => !valuesMatch(i?.value, i?.defaultValue)).length : 0), 0)
    },
    visibleSections() {
      if (!this.onlyNonDefault) return this.sections
      return this.sections.filter((s) => (Array.isArray(s.items) ? s.items.filter((i) => !valuesMatch(i?.value, i?.defaultValue)).length : 0) > 0)
    },
  },
  mounted() { this.load() },
  methods: {
    formatValue,
    formatLearnedValue,
    isChanged(item) { return !valuesMatch(item?.value, item?.defaultValue) },
    itemsVisible(section) {
      const items = Array.isArray(section?.items) ? section.items : []
      return this.onlyNonDefault ? items.filter((i) => !valuesMatch(i?.value, i?.defaultValue)) : items
    },
    severity(sev) {
      const s = String(sev || "neutral").toLowerCase()
      if (s === "ok" || s === "live") return "var(--success)"
      if (s === "warn" || s === "warning") return "var(--warning)"
      if (s === "error" || s === "critical") return "var(--error)"
      return "var(--text-muted)"
    },
    statusText() {
      const s = String(this.vehicleStatus?.summarySeverity || "neutral").toLowerCase()
      const badge = this.vehicleStatus?.available ? { label: "Live", color: "var(--success)" } : { label: "Unavailable", color: s === "error" ? "var(--error)" : "var(--text-muted)" }
      return badge
    },
    async load(showToast = false) {
      if (this.refreshing) return
      this.refreshing = true
      if (!this.sections.length) this.loading = true
      this.error = ""
      try {
        const p = await api.getTroubleshoot()
        if (!p) throw new Error("Failed to load troubleshoot data")
        this.snapshot = Array.isArray(p.snapshot) ? p.snapshot : []
        this.sections = Array.isArray(p.sections) ? p.sections : []
        this.vehicleStatus = {
          available: !!p.vehicleStatus?.available,
          summary: String(p.vehicleStatus?.summary || ""),
          summarySeverity: String(p.vehicleStatus?.summarySeverity || "neutral"),
          items: Array.isArray(p.vehicleStatus?.items) ? p.vehicleStatus.items : [],
        }
        this.isOnroad = !!p.isOnroad
        if (showToast) showSnackbar("Troubleshoot data refreshed.")
      } catch (e) {
        this.error = e?.message || "Failed to load troubleshoot data"
        if (showToast) showSnackbar(this.error, "error")
      } finally {
        this.refreshing = false
        this.loading = false
      }
    },
    async resetSection(section) {
      const id = String(section?.id || "")
      if (!id || this.busySection) return
      const title = String(section?.title || "this section")
      if (!(await GalaxyConfirm({ title: "Reset to defaults?", message: `Reset ${title} to defaults?`, confirmLabel: "Reset", danger: true }))) return
      this.busySection = id
      try {
        const p = await api.resetTroubleshootSection(id)
        showSnackbar(p?.message || `${title} reset.`)
        await this.load(false)
      } catch (e) {
        showSnackbar(e?.message || "Failed to reset section.", "error")
      } finally {
        this.busySection = ""
      }
    },
    async copyReport() {
      const lines = []
      lines.push("StarPilot Troubleshoot Report")
      lines.push(`Generated: ${new Date().toISOString()}`)
      lines.push(`Onroad: ${this.isOnroad ? "Yes" : "No"}`)
      lines.push(`Only non-default values: ${this.onlyNonDefault ? "Yes" : "No"}`)
      if (this.vehicleStatus?.summary) {
        lines.push("")
        lines.push("Vehicle Fault Status")
        lines.push(`Summary: ${this.vehicleStatus.summary}`)
        for (const item of this.vehicleStatus.items || []) lines.push(`- ${item.label}: ${this.formatValue(item.value)}`)
      }
      lines.push("")
      lines.push("Snapshot")
      for (const item of this.snapshot) lines.push(`- ${item.label}: ${this.formatValue(item.value)}`)
      for (const section of this.visibleSections) {
        lines.push("")
        lines.push(section.title)
        for (const item of this.itemsVisible(section)) {
          const learned = this.formatLearnedValue(item.learnedValue)
          lines.push(`- ${item.label}: ${this.formatValue(item.value)} (default: ${this.formatValue(item.defaultValue)}${learned ? `, learned: ${learned}` : ""})`)
        }
      }
      const text = lines.join("\n")
      try {
        if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text)
        else { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove() }
        showSnackbar("Troubleshoot report copied to clipboard.")
      } catch (e) {
        showSnackbar("Failed to copy report.", "error")
      }
    },
  },
  template: `
    <div>
      <section class="gx-card">
        <div style="padding: var(--sp-3); display:grid; gap:8px;">
          <p style="margin:0; color:var(--text-muted);">Quick diagnostics snapshot for weird behavior reports and copy-ready debug logs.</p>
          <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="refreshing" @click="load(true)"><i v-if="refreshing" class="bi bi-arrow-repeat gx-spin"></i><i v-else class="bi bi-arrow-clockwise"></i> {{ refreshing ? 'Refreshing...' : 'Refresh' }}</button>
            <button type="button" class="gx-btn gx-btn--tonal" @click="copyReport"><i class="bi bi-clipboard"></i> Copy to Clipboard</button>
          </div>
          <div class="gx-row" style="border:none; border-radius:0; min-height:0;">
            <div class="gx-row__info"><span class="gx-row__label" style="font-size:var(--fs-base); font-weight:var(--fw-medium);">Only non-default values</span></div>
            <label class="gx-switch">
              <input type="checkbox" v-model="onlyNonDefault" />
              <span class="gx-switch__track"></span>
              <span class="gx-switch__thumb"></span>
            </label>
          </div>
          <GxNotice v-if="error" tone="danger" :text="error" style="margin:var(--sp-2) 0 0;" />
          <div class="gx-row__desc"><strong>Onroad:</strong> {{ isOnroad ? 'Yes' : 'No' }}</div>
          <div class="gx-row__desc"><strong>Changed Settings:</strong> {{ countNonDefault }}</div>
        </div>
      </section>

      <div v-if="loading" class="gx-loading">Loading troubleshoot data...</div>

      <template v-else>
        <section class="gx-card">
          <div class="gx-section__header">
            <i class="bi bi-car-front"></i>
            <span class="gx-section__title">Vehicle Fault Status</span>
            <span class="gx-chip" :style="'background:' + statusText().color + (statusText().label==='Live' ? ';color:var(--black);' : '')">{{ statusText().label }}</span>
          </div>
          <div style="padding: var(--sp-3); display:grid; gap:8px;">
            <p style="margin:0;">{{ vehicleStatus?.summary || 'Vehicle fault status unavailable.' }}</p>
            <div style="display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:8px;">
              <div v-for="item in vehicleStatus?.items || []" :key="item.label" class="gx-row" style="border:none; background:var(--surface); border-radius:var(--radius-md); padding:8px 10px;">
                <div class="gx-row__info"><span class="gx-row__label">{{ item.label }}</span></div>
                <span class="gx-row__value" :style="'color:' + severity(item.severity)">{{ formatValue(item.value) }}</span>
              </div>
            </div>
          </div>
        </section>

        <section class="gx-card">
          <div class="gx-section__header">
            <i class="bi bi-camera"></i>
            <span class="gx-section__title">Snapshot</span>
          </div>
          <div v-if="!snapshot.length" class="gx-empty">No snapshot data.</div>
          <div v-else style="display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:8px; padding:0 var(--sp-3) var(--sp-3);">
            <div v-for="item in snapshot" :key="item.label" class="gx-row" style="border:none; background:var(--surface); border-radius:var(--radius-md); padding:8px 10px;">
              <div class="gx-row__info"><span class="gx-row__label">{{ item.label }}</span></div>
              <span class="gx-row__value">{{ formatValue(item.value) }}</span>
            </div>
          </div>
        </section>

        <section v-for="section in visibleSections" :key="section.id" class="gx-card">
          <div class="gx-section__header">
            <i class="bi bi-sliders"></i>
            <span class="gx-section__title">{{ section.title }}</span>
            <button v-if="section.resettable" type="button" class="gx-btn gx-btn--text" style="color:var(--error);" :disabled="busySection === section.id" @click="resetSection(section)">{{ busySection === section.id ? 'Resetting...' : 'Reset to Default' }}</button>
          </div>
          <div v-if="!itemsVisible(section).length" class="gx-empty">No settings are currently different from their defaults.</div>
          <div v-else style="display:grid; gap:8px; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); padding:0 var(--sp-3) var(--sp-3);">
            <div v-for="item in itemsVisible(section)" :key="item.label" class="gx-row"
              :class="{ 'gx-diagnostic-row--changed': isChanged(item) }"
              style="border:none; background:var(--surface); border-radius:var(--radius-md); margin:0; padding:10px 12px; flex-direction:column; align-items:stretch; gap:8px;">
              <div style="display:flex; align-items:center; gap:6px; min-width:0;">
                <span class="gx-row__label" style="font-size:var(--fs-sm); overflow-wrap:anywhere;">{{ item.label }}</span>
                <span v-if="isChanged(item)" class="gx-chip" style="background:var(--warning);color:var(--black); flex:none;">Changed</span>
              </div>
              <div style="display:grid; gap:2px; font-size:var(--fs-sm);">
                <span><span style="color:var(--text-muted);">current </span><b style="overflow-wrap:anywhere;">{{ formatValue(item.value) }}</b></span>
                <span style="color:var(--text-muted); overflow-wrap:anywhere;">default {{ formatValue(item.defaultValue) }}</span>
                <span v-if="section.hasLearnedColumn && formatLearnedValue(item.learnedValue)" style="color:var(--text-muted); overflow-wrap:anywhere;">learned {{ formatLearnedValue(item.learnedValue) }}</span>
              </div>
            </div>
          </div>
        </section>

        <section v-if="onlyNonDefault && countNonDefault === 0" class="gx-card"><div class="gx-empty">No settings are currently different from their defaults.</div></section>
      </template>
    </div>
  `,
}
