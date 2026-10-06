import { GxNotice } from "./notice.js"
export const validDriveState = (value) => !!value && ["auto", "offroad", "onroad"].includes(value.mode) &&
  typeof value.available === "boolean" && typeof value.overrideAllowed === "boolean" &&
  (value.revision === null || typeof value.revision === "string" && /^[0-9a-f]{32}$/.test(value.revision)) &&
  [null, "offroad", "onroad"].includes(value.effective)

export const DriveStatePanel = {
  components: { GxNotice },
  data: () => ({ state: null, error: "", busy: false }),
  computed: {
    pending() { return this.state?.mode !== "auto" && this.state?.effective !== this.state?.mode },
  },
  mounted() {
    this.active = true
    this.generation = 0
    this.load()
    this.timer = setInterval(() => { if (!document.hidden) this.load() }, 1000)
  },
  beforeUnmount() { this.active = false; this.generation++; clearInterval(this.timer); this.controller?.abort() },
  methods: {
    async load() {
      if (this.busy || this.loading || !this.active) return
      this.loading = true
      const generation = ++this.generation
      this.controller = new AbortController()
      const controller = this.controller
      const deadline = setTimeout(() => controller.abort(), 3000)
      try {
        const response = await fetch("./api/drive-state/status", { credentials: "same-origin", cache: "no-store", signal: this.controller.signal })
        const value = await response.json()
        if (!response.ok || !validDriveState(value)) throw new Error(value.error || "Drive state unavailable")
        if (this.active && generation === this.generation) { this.state = value; this.error = "" }
      } catch (error) { if (this.active && generation === this.generation) { this.state = null; this.error = "Drive state unavailable" } }
      finally { clearTimeout(deadline); if (generation === this.generation) this.loading = false }
    },
    async change(mode) {
      if (this.busy || !this.state?.available) return
      if (mode === "onroad" && !this.state.overrideAllowed) { this.error = "Park and disengage, then retry. The device can stay on-road."; return }
      if (mode === "offroad" && this.state.effective === "onroad" &&
          !window.confirm("Switch to Offroad and stop driving services? Disengage and stop safely first. Stay stopped until you return to Auto.")) return
      const revision = this.state.revision
      this.busy = true
      this.loading = false
      const generation = ++this.generation
      this.controller?.abort()
      this.controller = new AbortController()
      const controller = this.controller
      const deadline = setTimeout(() => controller.abort(), 3000)
      try {
        const response = await fetch("./api/drive-state/action", { method: "POST", credentials: "same-origin", cache: "no-store",
          signal: this.controller.signal, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode, revision }) })
        const value = await response.json()
        if (!response.ok || !validDriveState(value)) throw new Error(value.error || "Drive state unavailable")
        if (this.active && generation === this.generation) { this.state = value; this.error = "" }
      } catch (error) { if (this.active && generation === this.generation) this.error = error.message }
      finally { clearTimeout(deadline); this.busy = false; if (this.active && generation === this.generation) this.load() }
    },
  },
  template: `<section class="gx-card gx-force-drive" aria-label="Force Drive State"><h3>Force Drive State</h3>
    <p>Device: {{ state?.effective === "onroad" ? "Onroad" : state?.effective === "offroad" ? "Offroad" : "Checking…" }}</p>
    <p v-if="pending" role="status">Waiting for the device to switch {{ state.mode }}…</p>
    <p>Auto follows the car. Force Offroad stops driving services even when the device is on-road. Disengage and stop safely before forcing Offroad; Force Onroad requires Park and valid vehicle data. Return to Auto restores normal operation.</p>
    <p v-if="state?.available && !state.overrideAllowed" role="status">Force Onroad needs fresh parked, disengaged vehicle data. Force Offroad remains available to stop driving services.</p>
    <GxNotice tone="danger" v-if="state && !state.available">The drive-state manager is unavailable. Reconnect to check again.</GxNotice>
    <div class="gx-force-drive__actions"><button v-for="mode in ['offroad', 'onroad', 'auto']" :key="mode" type="button"
      class="gx-btn" :class="state?.mode === mode ? '' : 'gx-btn--tonal'"
      :disabled="busy || !state?.available || (mode === 'onroad' && !state.overrideAllowed)"
      :aria-pressed="state?.mode === mode" @click="change(mode)">{{ mode === 'auto' ? 'Return to Auto' : mode === 'onroad' ? 'Onroad' : 'Offroad' }}</button></div>
    <GxNotice tone="danger" v-if="error">{{ error }}</GxNotice></section>`,
}
