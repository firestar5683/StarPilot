export const GalaxyTabs = {
  name: "GalaxyTabs",
  props: {
    items: { type: Object, required: true },
    active: { type: String, default: "" },
  },
  emits: ["select"],
  template: `
    <nav class="gx-tabs" role="tablist" aria-label="View sections">
      <button v-for="(label, key) in items" :key="key" type="button" role="tab"
        :aria-selected="active === key ? 'true' : 'false'"
        class="gx-tab" :class="{ active: active === key }"
        @click="$emit('select', key)">{{ label }}</button>
    </nav>
  `,
}
