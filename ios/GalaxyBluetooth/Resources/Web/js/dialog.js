// Native modal behavior provides focus trapping, Escape, and focus restoration.
export const GxDialog = {
  inheritAttrs: false,
  props: { labelledby: { type: String, required: true }, describedby: String, alert: Boolean },
  emits: ["close"],
  mounted() { this.$refs.dialog.showModal() },
  beforeUnmount() { this.$refs.dialog.close() },
  methods: {
    backdrop(event) {
      if (event.target !== this.$refs.dialog) return
      const rect = event.target.getBoundingClientRect()
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) this.$emit("close")
    },
  },
  template: `<Teleport to="body"><dialog ref="dialog" v-bind="$attrs" class="gx-card gx-settings__dialog gx-dialog"
    :role="alert ? 'alertdialog' : 'dialog'" :aria-labelledby="labelledby" :aria-describedby="describedby"
    @cancel.prevent="$emit('close')" @click="backdrop"><slot></slot></dialog></Teleport>`,
}
