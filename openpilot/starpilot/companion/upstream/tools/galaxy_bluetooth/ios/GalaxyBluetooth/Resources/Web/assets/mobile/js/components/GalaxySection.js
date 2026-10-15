export const GalaxySection = {
  name: "GalaxySection",
  props: {
    title: { type: String, required: true },
    icon: { type: String, default: "bi-toggles" },
    count: { type: [Number, String], default: "" },
    defaultOpen: { type: Boolean, default: true },
    collapsible: { type: Boolean, default: true },
  },
  data() { return { open: this.defaultOpen } },
  template: `
    <section class="gx-card">
      <div class="gx-section__header" v-if="collapsible" role="button" tabindex="0"
        @click="open = !open" @keydown.enter="open = !open" @keydown.space.prevent="open = !open">
        <i class="bi" :class="icon"></i>
        <span class="gx-section__title">{{ title }}</span>
        <span v-if="count !== ''" class="gx-section__count">{{ count }}</span>
        <i class="bi bi-chevron-down gx-chevron" :class="{ open }"></i>
      </div>
      <div v-else class="gx-section__header">
        <i class="bi" :class="icon"></i>
        <span class="gx-section__title">{{ title }}</span>
        <span v-if="count !== ''" class="gx-section__count">{{ count }}</span>
      </div>
      <transition name="gx-collapse">
        <div v-show="!collapsible || open" class="gx-section__body">
          <slot />
        </div>
      </transition>
    </section>
  `,
}
