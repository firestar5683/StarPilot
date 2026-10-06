import { GxNotice } from "./notice.js"
import { requestJson } from "./startup.js"

export const RecordingActions = {
  components: { GxNotice },
  props: { recording: { type: Object, required: true }, all: Boolean,
    unauthorized: { type: Function, required: true } },
  emits: ["changed"],
  data: () => ({ action: "", name: "", busy: false, error: "", includePreserved: false }),
  methods: {
    edit(action) {
      this.action = action
      this.name = this.recording.displayName || this.recording.routeId
      this.error = ""
    },
    async save(action = this.action) {
      if (this.busy) return
      this.busy = true
      this.error = ""
      const payload = this.all ? { action: "delete-all", confirmed: true, includePreserved: this.includePreserved } : { action, routeId: this.recording.routeId,
        ...(action === "rename" ? { name: this.name } : action === "preserve" ? { preserved: !this.recording.preserved } : { confirmed: true }) }
      try {
        await requestJson("./api/recordings/action", {
          request: { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) },
        })
        this.action = ""
        this.$emit("changed")
      } catch (error) {
        if (error.status === 401) this.unauthorized()
        else this.error = error.status === 409 ? "Turn off the vehicle before managing recordings." :
          error.message || "Recording action failed. Refresh the library before trying again."
      } finally { this.busy = false }
    },
  },
  template: `
    <div class="gx-recordings__actions">
      <template v-if="!all">
        <button class="gx-icon-btn" :aria-label="recording.preserved ? 'Unpreserve drive' : 'Preserve drive'" :title="recording.preserved ? 'Unpreserve' : 'Preserve'" :disabled="busy" @click="save('preserve')"><i class="bi" :class="recording.preserved ? 'bi-heart-fill' : 'bi-heart'"></i></button>
        <slot></slot>
        <button class="gx-icon-btn" aria-label="Rename drive" title="Rename" :disabled="busy" @click="edit('rename')"><i class="bi bi-pencil"></i></button>
        <button class="gx-icon-btn gx-recordings__danger" aria-label="Delete drive" title="Delete" :disabled="busy" @click="edit('delete')"><i class="bi bi-trash"></i></button>
      </template>
      <template v-else>
        <button class="gx-btn gx-btn--tonal" :disabled="busy" @click="includePreserved=false; edit('delete')">Delete non-preserved</button>
        <button class="gx-btn gx-btn--tonal gx-recordings__danger" :disabled="busy" @click="includePreserved=true; edit('delete')">Delete all including preserved</button>
      </template>
      <GxNotice tone="danger" v-if="error && !action">{{ error }}</GxNotice>
      <Teleport to="body"><div v-if="action" class="gx-settings__modal" role="dialog" aria-modal="true" :aria-label="action === 'rename' ? 'Rename recording' : 'Delete recording'">
        <form class="gx-card gx-settings__dialog" @submit.prevent="save()">
          <h3>{{ action === 'rename' ? 'Rename recording' : 'Delete recording?' }}</h3>
          <label v-if="action === 'rename'">Name<input class="gx-field" v-model="name" maxlength="128" required :disabled="busy" /></label>
          <p v-else>Delete {{ recording.displayName || recording.routeId }}? This cannot be undone.</p>
          <p v-if="all">{{ includePreserved ? "Preserved drives will also be deleted." : "Preserved drives will be kept." }}</p>
          <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice>
          <div class="gx-settings__controls"><button type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="action=''">Cancel</button>
            <button class="gx-btn" :disabled="busy">{{ action === 'rename' ? 'Save name' : 'Delete recording' }}</button></div>
        </form>
      </div></Teleport>
    </div>`,
}
