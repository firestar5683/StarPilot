export const GalaxySheet = {
  name: "GalaxySheet",
  props: {
    open: { type: Boolean, default: false },
    title: { type: String, default: "" },
    icon: { type: String, default: "" },
    bottomsheet: { type: Boolean, default: false },
    scrimClass: { type: String, default: "" },
    sheetClass: { type: String, default: "" },
  },
  emits: ["close"],
  template: `
    <Teleport to="body">
      <transition name="gx-fade">
        <div v-if="open" class="gx-scrim" :class="[scrimClass, { 'gx-scrim--bottomsheet': bottomsheet }]" @click.self="$emit('close')">
          <div class="gx-sheet" :class="sheetClass" role="dialog" aria-modal="true" :aria-label="title">
            <div class="gx-section__header gx-video-player-header" style="cursor:default;">
              <i v-if="icon" class="bi" :class="icon" aria-hidden="true"></i>
              <span class="gx-section__title">{{ title }}</span>
              <button type="button" class="gx-icon-btn" aria-label="Close" @click="$emit('close')"><i class="bi bi-x-lg" aria-hidden="true"></i></button>
            </div>
            <slot />
          </div>
        </div>
      </transition>
    </Teleport>
  `,
}
