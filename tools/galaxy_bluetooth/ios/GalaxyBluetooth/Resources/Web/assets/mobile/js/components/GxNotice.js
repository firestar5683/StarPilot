export const GxNotice = {
  name: "GxNotice",
  props: {
    tone: { type: String, default: "warn" },
    icon: { type: String, default: "bi-exclamation-triangle-fill" },
    title: { type: String, default: "" },
    text: { type: String, default: "" },
  },
  computed: {
    toneClass() {
      const t = ["warn", "info", "danger"].includes(this.tone) ? this.tone : "warn"
      return "gx-alert--" + t
    },
  },
  template: `
    <div class="gx-alert" :class="toneClass" role="status">
      <i class="bi gx-alert__icon" :class="icon"></i>
      <div class="gx-alert__body">
        <strong v-if="title">{{ title }}</strong>
        <span><slot>{{ text }}</slot></span>
      </div>
    </div>
  `,
}
