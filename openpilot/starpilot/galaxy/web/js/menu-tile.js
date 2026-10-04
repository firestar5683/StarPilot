// One submenu entry used by Tools, Logs & Diagnostics and Plots & Analysis so
// the icon alignment, hover and press feedback are identical everywhere.
export const MenuTile = {
  name: "MenuTile",
  props: {
    icon: { type: String, default: "" },
    title: { type: String, required: true },
    description: { type: String, default: "" },
    availability: { type: String, default: "" },
    disabled: { type: Boolean, default: false },
  },
  emits: ["select"],
  template: `<button type="button" class="gx-menu-tile" :disabled="disabled" @click="!disabled && $emit('select')">
    <i class="bi" :class="icon" aria-hidden="true"></i>
    <span>{{ title }}</span>
    <small v-if="description">{{ description }}</small>
    <small v-if="availability" class="gx-menu-tile__availability">{{ availability }}</small>
  </button>`,
}
