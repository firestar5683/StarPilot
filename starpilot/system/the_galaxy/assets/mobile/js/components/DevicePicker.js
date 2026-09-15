const SLUG_RE = /^[A-Za-z0-9]{16}$/
const MAX_NAME_LENGTH = 40

export const DevicePicker = {
  name: "DevicePicker",
  data() {
    return {
      devices: [],
      activeSlug: "",
      draftName: "",
      editingSlug: "",
      renameError: "",
      saving: false,
      loading: true,
    }
  },
  computed: {
    hasMultipleDevices() { return this.devices.length > 1 },
  },
  methods: {
    displayName(device, index) {
      return device.name || `Comma ${index + 1}`
    },
    async loadDevices() {
      try {
        const response = await fetch("/_gateway/devices", { cache: "no-store" })
        if (!response.ok) return
        const data = await response.json()
        this.activeSlug = SLUG_RE.test(data?.activeSlug || "") ? data.activeSlug : ""
        this.devices = Array.isArray(data?.devices)
          ? data.devices.filter((device) => SLUG_RE.test(device?.slug || "") && device?.path)
          : []
      } catch (error) {
        // Local Galaxy instances do not have the gateway directory endpoint.
      } finally {
        this.loading = false
      }
    },
    startRename(device, index) {
      this.editingSlug = device.slug
      this.draftName = this.displayName(device, index)
      this.renameError = ""
      this.$nextTick(() => {
        const input = this.$refs.deviceNameInput
        ;(Array.isArray(input) ? input[0] : input)?.focus()
      })
    },
    cancelRename() {
      this.editingSlug = ""
      this.draftName = ""
      this.renameError = ""
    },
    async saveRename(device) {
      if (!device) return
      const name = this.draftName.trim().slice(0, MAX_NAME_LENGTH)
      this.saving = true
      this.renameError = ""
      try {
        const response = await fetch(`/_gateway/devices/${encodeURIComponent(device.slug)}/name`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
        })
        const data = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(data?.error || "Could not save the comma name.")
        this.devices = this.devices.map((item) => item.slug === device.slug ? { ...item, name: data.name } : item)
        this.cancelRename()
      } catch (error) {
        this.renameError = error?.message || "Could not save the comma name."
      } finally {
        this.saving = false
      }
    },
    selectDevice(device) {
      if (!device?.path || device.slug === this.activeSlug) return
      window.location.assign(device.path)
    },
  },
  mounted() {
    this.loadDevices()
  },
  template: `
    <div v-if="!loading && hasMultipleDevices" class="gx-device-picker">
      <div class="gx-device-picker__heading">
        <div>
          <div class="gx-nav-section__title">Commas</div>
          <div class="gx-device-picker__hint">Switch device</div>
        </div>
        <i class="bi bi-arrow-left-right gx-device-picker__heading-icon" aria-hidden="true"></i>
      </div>
      <div v-for="(device, index) in devices" :key="device.slug" class="gx-device-picker__row">
        <a class="gx-nav-item gx-device-picker__item" :class="{ active: device.slug === activeSlug }" :href="device.path"
          :aria-current="device.slug === activeSlug ? 'page' : undefined"
          @click.prevent="selectDevice(device)">
          <i class="bi bi-cpu"></i>
          <span class="gx-device-picker__name">{{ displayName(device, index) }}</span>
          <span v-if="device.slug === activeSlug" class="gx-device-picker__current">Current</span>
        </a>
        <button type="button" class="gx-icon-btn gx-device-picker__rename" :aria-label="'Rename ' + displayName(device, index)"
          :title="'Rename ' + displayName(device, index)" @click="startRename(device, index)">
          <i class="bi bi-pencil" aria-hidden="true"></i>
        </button>
      </div>
      <form v-if="editingSlug" class="gx-device-picker__editor" @submit.prevent="saveRename(devices.find((device) => device.slug === editingSlug))">
        <label class="gx-device-picker__editor-label" for="gx-device-name">Rename comma</label>
        <div class="gx-device-picker__editor-row">
          <input id="gx-device-name" ref="deviceNameInput" v-model="draftName" maxlength="40" autocomplete="off" autofocus />
          <button type="submit" class="gx-device-picker__save" :disabled="saving">{{ saving ? 'Saving…' : 'Save' }}</button>
          <button type="button" class="gx-device-picker__cancel" :disabled="saving" @click="cancelRename">Cancel</button>
        </div>
        <div v-if="renameError" class="gx-device-picker__error">{{ renameError }}</div>
      </form>
    </div>
  `,
}
