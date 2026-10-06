// Familiar actions share a full touch target, accessible name and tooltip.
export const GxIconButton = {
  name: "GxIconButton",
  props: {
    label: { type: String, required: true },
    icon: { type: String, required: true },
  },
  template: `<button type="button" class="gx-icon-btn gx-action-icon" :aria-label="label" :title="label"><i class="bi" :class="icon" aria-hidden="true"></i></button>`,
}
