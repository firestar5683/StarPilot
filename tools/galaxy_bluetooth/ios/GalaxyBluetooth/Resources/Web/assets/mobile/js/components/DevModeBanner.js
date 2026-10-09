import { navigate } from "../store.js"

export const DevModeBanner = {
  name: "DevModeBanner",
  props: {
    hiddenCount: { type: Number, default: 0 },
    devModeOn: { type: Boolean, default: false },
  },
  computed: {
    visible() { return !this.devModeOn && this.hiddenCount > 0 },
  },
  methods: {
    unlock() { navigate("/settings/developer") },
  },
  template: `
    <div v-if="visible" class="gx-alert gx-alert--warn" role="status">
      <i class="bi bi-shield-lock gx-alert__icon"></i>
      <div class="gx-alert__body">
        <strong>{{ hiddenCount }} advanced setting{{ hiddenCount !== 1 ? "s" : "" }} hidden.</strong>
        <span>Want more advanced features or missing a few toggles? Enable Developer Mode whenever you’re ready.</span>
      </div>
      <button type="button" class="gx-btn gx-btn--tonal" @click="unlock">Go to Developer Tab</button>
    </div>
  `,
}
