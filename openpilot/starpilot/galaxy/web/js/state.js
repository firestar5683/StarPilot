// Centered page-level loading, empty, and unavailable states. Inline feedback uses GxNotice.
export const GxState = {
  name: "GxState",
  props: { loading: Boolean, title: String, tone: { type: String, default: "info" } },
  template: `<section class="gx-card gx-message" :role="tone === 'danger' ? 'alert' : 'status'" :aria-busy="loading || undefined">
    <span v-if="loading" class="gx-spinner" aria-hidden="true"></span>
    <h3 v-if="title">{{ title }}</h3><div class="gx-message__body"><slot /></div>
    <div v-if="$slots.actions" class="gx-actions gx-message__actions"><slot name="actions" /></div>
  </section>`,
}
