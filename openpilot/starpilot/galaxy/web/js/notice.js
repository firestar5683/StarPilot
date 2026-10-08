// Shared status/warning banner used across Galaxy pages (ported from the
// original Galaxy "GxNotice" pattern so every page uses one consistent look).
export const GxNotice = {
  name: "GxNotice",
  props: {
    tone: { type: String, default: "info" },
    icon: { type: String, default: "" },
    busy: Boolean,
    title: { type: String, default: "" },
  },
  computed: {
    toneClass() { return `gx-alert--${["info", "success", "warn", "danger"].includes(this.tone) ? this.tone : "info"}` },
    iconClass() {
      if (this.icon) return this.icon
      if (this.tone === "success") return "bi-check-circle"
      return this.tone === "danger" ? "bi-x-octagon" : this.tone === "warn" ? "bi-exclamation-triangle" : "bi-info-circle"
    },
  },
  template: `<div class="gx-alert" :class="toneClass" :role="tone === 'danger' ? 'alert' : 'status'">
    <span v-if="busy" class="gx-spinner gx-alert__icon" aria-hidden="true"></span>
    <i v-else class="bi gx-alert__icon" :class="iconClass" aria-hidden="true"></i>
    <div class="gx-alert__body"><strong v-if="title">{{ title }}</strong><div class="gx-alert__text"><slot /></div></div>
  </div>`,
}
