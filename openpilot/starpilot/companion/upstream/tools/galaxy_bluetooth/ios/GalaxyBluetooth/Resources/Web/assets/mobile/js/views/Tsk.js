import { api, showSnackbar } from "../api.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"

export const Tsk = {
  name: "Tsk",
  data() {
    return { keys: [], selectedKeyName: "", keyName: "", keyValue: "", loading: true }
  },
  async mounted() { await this.load() },
  computed: {
    duplicateName() {
      return this.keys.some((k) => k.name === this.keyName && k.name !== this.selectedKeyName)
    },
  },
  methods: {
    async load() {
      try {
        this.keys = await api.getTskKeys()
      } catch (e) {
        showSnackbar("Failed to load keys...", "error")
      } finally {
        this.loading = false
      }
    },
    selectKey(name) {
      if (!name) { this.selectedKeyName = ""; return }
      const selected = this.keys.find((k) => k.name === name)
      if (selected) {
        this.selectedKeyName = selected.name
        this.keyName = selected.name
        this.keyValue = selected.value
      }
    },
    canSave() {
      const name = this.keyName
      const value = this.keyValue
      if (value.length < 10 || /\s/.test(name) || /\s/.test(value)) return false
      if (this.duplicateName) return false
      const selected = this.keys.find((k) => k.name === this.selectedKeyName)
      if (!selected) return true
      return name !== selected.name || value !== selected.value
    },
    async save() {
      const name = this.keyName.trim()
      const value = this.keyValue.trim()
      if (!this.canSave()) { showSnackbar("Invalid input or duplicate name.", "error"); return }
      const updated = this.keys.filter((k) => k.name !== this.selectedKeyName)
      updated.push({ name, value })
      try {
        this.keys = await api.saveTskKeys(updated)
        this.selectKey(name)
        showSnackbar("Saved key!")
      } catch (e) {
        showSnackbar(e?.data?.error || "Save failed...", "error")
      }
    },
    async remove(name) {
      if (!(await GalaxyConfirm({
        title: "Confirm Delete",
        message: `Are you sure you want to delete the key "${name}"?`,
        confirmLabel: "Yes, Delete",
        danger: true,
      }))) return
      try {
        this.keys = await api.deleteTskKey(name)
        this.keyName = ""
        this.keyValue = ""
        this.selectedKeyName = ""
        showSnackbar("Deleted key!")
      } catch (e) {
        showSnackbar("Delete failed...", "error")
      }
    },
    async apply() {
      const selected = this.keys.find((k) => k.name === this.selectedKeyName)
      if (!selected) { showSnackbar("Select a key from the list first", "error"); return }
      try {
        await api.tskKeySet(selected.name, selected.value)
        showSnackbar("Key applied!")
      } catch (e) {
        showSnackbar("Apply failed...", "error")
      }
    },
  },
  template: `
    <div>
      <h2 style="margin-top:0;">Toyota Security Keys</h2>
      <section class="gx-card">
        <div style="padding: var(--sp-3); display:grid; gap:10px;">
          <div v-if="loading" class="gx-loading">Loading keys...</div>
          <template v-else>
            <label class="gx-row__label" style="font-size:var(--fs-xs);">Select Key</label>
            <GalaxySelect class="gx-field gx-field--full" :value="selectedKeyName" @change="selectKey($event.target.value)">
              <option value="">-- Select a saved key --</option>
              <option v-for="k in keys" :key="k.name" :value="k.name">{{ k.name }}</option>
            </GalaxySelect>

            <label class="gx-row__label" style="font-size:var(--fs-xs);">Key Name</label>
            <input class="gx-field gx-field--full" v-model="keyName" @input="selectedKeyName = ''" placeholder="Enter key name..." autocomplete="off" />
            <div v-if="duplicateName" class="gx-row__desc" style="color:var(--error);">A key with this name already exists.</div>

            <label class="gx-row__label" style="font-size:var(--fs-xs);">Key Value</label>
            <div style="display:flex; gap:8px;">
              <input class="gx-field" style="flex:1;" v-model="keyValue" @input="selectedKeyName = ''" placeholder="Enter key value..." autocomplete="off" />
              <button type="button" class="gx-icon-btn" title="Save key" :disabled="!canSave()" @click="save"><i class="bi bi-save"></i></button>
              <button type="button" class="gx-icon-btn" title="Delete key" style="color:var(--error);" :disabled="!selectedKeyName" @click="remove(selectedKeyName)"><i class="bi bi-trash"></i></button>
            </div>

            <div style="display:flex; justify-content:flex-end; margin-top:8px;">
              <button type="button" class="gx-btn" :disabled="!selectedKeyName" @click="apply"><i class="bi bi-check2-circle"></i> Apply Key</button>
            </div>
          </template>
        </div>
      </section>
    </div>
  `,
}
