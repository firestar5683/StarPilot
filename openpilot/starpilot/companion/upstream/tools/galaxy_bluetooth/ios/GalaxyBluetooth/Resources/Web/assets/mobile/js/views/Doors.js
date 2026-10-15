import { api, showSnackbar } from "../api.js"

export const Doors = {
  name: "Doors",
  data() { return { busy: "" } },
  methods: {
    async act(action) {
      if (this.busy) return
      this.busy = action
      try {
        const payload = await api.postAction(`/api/doors/${action}`)
        showSnackbar(payload?.message || (action === "lock" ? "Doors locked!" : "Doors unlocked!"))
      } catch (e) {
        showSnackbar(e?.message || (action === "lock" ? "Failed to lock doors." : "Failed to unlock doors."), "error")
      } finally {
        this.busy = ""
      }
    },
  },
  template: `
    <div>
      <h2 style="margin-top:0;">Lock/Unlock Doors</h2>
      <section class="gx-card">
        <div style="padding: var(--sp-4); display:grid; gap:12px; text-align:center;">
          <i class="bi bi-car-front" style="font-size:2rem; color:var(--primary);"></i>
          <p style="margin:0; color:var(--text-muted);">Remotely lock or unlock your car doors using the buttons below.</p>
          <div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap;">
            <button type="button" class="gx-btn" :disabled="!!busy" @click="act('lock')"><i class="bi bi-lock-fill"></i> Lock Doors</button>
            <button type="button" class="gx-btn gx-btn--tonal" :disabled="!!busy" @click="act('unlock')"><i class="bi bi-unlock-fill"></i> Unlock Doors</button>
          </div>
        </div>
      </section>
    </div>
  `,
}
