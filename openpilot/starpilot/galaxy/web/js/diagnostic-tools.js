import { GxNotice } from "./notice.js"
import { requestJson } from "./startup.js"
import { connectionError } from "./polling.js"
import { reactive } from "../vendor/vue/vue.esm-browser.js"
import { LocalAccess } from "./local-access.js"

const text = (value, max = 1024) => typeof value === "string" && value.length <= max
const rows = value => Array.isArray(value) && value.length <= 128 && value.every(row => row && text(row.label, 128) && text(row.value))
export function validTroubleshoot(value) {
  return !!value && value.schemaVersion === 1 && [null, "parked", "driving", "standby"].includes(value.device?.state) &&
    typeof value.vehicle?.available === "boolean" && typeof value.vehicle.longitudinal === "boolean" &&
    ["fingerprint", "brand", "steering"].every(key => text(value.vehicle[key])) && rows(value.snapshot) &&
    Array.isArray(value.sections) && value.sections.length <= 32 &&
    value.sections.every(section => text(section.title, 128) && rows(section.rows)) && text(value.note, 2048)
}
export function validTmux(value) {
  return !!value && typeof value.available === "boolean" && text(value.reason) && text(value.pane, 128) &&
    typeof value.truncated === "boolean" && typeof value.text === "string" &&
    new TextEncoder().encode(value.text).length <= 65536 && value.text.split("\n").length <= 301
}
export function troubleshootReport(data) {
  if (!data) return ""
  return ["StarPilot Troubleshoot", `Device: ${data.device.state || "Unavailable"}`,
    `Vehicle: ${data.vehicle.available ? data.vehicle.fingerprint : "Unavailable"}`,
    `Brand: ${data.vehicle.brand}`, `Longitudinal: ${data.vehicle.longitudinal ? "Available" : "Unavailable"}`, `Steering: ${data.vehicle.steering}`,
    ...data.snapshot.map(row => `${row.label}: ${row.value}`),
    ...data.sections.flatMap(section => ["", section.title, ...section.rows.map(row => `${row.label}: ${row.value}`)]),
    "", data.note].join("\n")
}

export class DiagnosticFeed {
  constructor({ endpoint, validate, publish, unauthorized = () => {}, interval = 0,
    fetcher = (...args) => fetch(...args), later = (fn, ms) => setTimeout(fn, ms), cancel = id => clearTimeout(id) }) {
    Object.assign(this, { endpoint, validate, publish, unauthorized, interval, fetcher, later, cancel })
    this.active = false; this.visible = true; this.live = true; this.data = null
    this.request = this.timer = null; this.generation = 0
  }
  start(mode, visible = true) { this.stop(); this.mode = mode; this.visible = visible; this.active = true
    if (mode !== "local") { this.data = null; this.publish({ data: null, error: "This tool is unavailable in sample mode.", loading: false }); return }
    if (visible) return this.refresh()
  }
  cancelPending() { this.generation++; this.request?.abort(); this.request = null
    if (this.timer !== null) this.cancel(this.timer)
    this.timer = null
  }
  stop() { this.active = false; this.cancelPending() }
  setVisible(value) { this.visible = value; this.cancelPending(); if (value && this.active && this.live) return this.refresh() }
  setLive(value) { this.live = value; this.cancelPending(); this.publish({ live: value, loading: false }); if (value && this.visible) return this.refresh() }
  async refresh() {
    if (!this.active || !this.visible || this.mode !== "local" || this.request) return
    if (this.timer !== null) this.cancel(this.timer)
    this.timer = null
    const generation = ++this.generation, request = new AbortController()
    this.request = request; this.publish({ loading: !this.data })
    try {
      const data = await requestJson(this.endpoint, { fetcher: this.fetcher, timeout: 4000, later: this.later, cancel: this.cancel, request: { signal: request.signal } })
      if (!this.active || generation !== this.generation) return
      if (!this.validate(data)) throw new Error("Unsupported diagnostic response")
      this.data = data; this.publish({ data, error: "" })
    } catch (error) {
      if (this.active && generation === this.generation) {
        if (error.status === 401 || ["setup_required", "access_unavailable"].includes(error.code)) { this.stop(); this.unauthorized(); return }
        this.publish({ error: connectionError(error) })
      }
    } finally {
      if (this.active && generation === this.generation) {
        this.request = null; this.publish({ loading: false })
        if (this.interval && this.live && this.visible) this.timer = this.later(() => { this.timer = null; this.refresh() }, this.interval)
      }
    }
  }
}

const props = { mode: { type: String, required: true }, unauthorized: { type: Function, required: true } }
function setup(props, consoleTail) {
  const state = reactive({ loading: false, live: true, data: null, error: "", notice: "" })
  const feed = new DiagnosticFeed({ endpoint: consoleTail ? "./api/tmux/live" : "./api/troubleshoot",
    validate: consoleTail ? validTmux : validTroubleshoot, interval: consoleTail ? 2000 : 10000,
    publish: update => Object.assign(state, update), unauthorized: props.unauthorized })
  return { state, feed }
}
const lifecycle = {
  mounted() { this._visibility = () => this.feed.setVisible(!document.hidden)
    document.addEventListener("visibilitychange", this._visibility); this.feed.start(this.mode, !document.hidden) },
  beforeUnmount() { document.removeEventListener("visibilitychange", this._visibility); this.feed.stop() },
  watch: { mode(value) { this.feed.start(value, !document.hidden) } },
}
const methods = {
  async copyText(value) { try { await navigator.clipboard.writeText(value); this.state.notice = "Visible text copied." }
    catch { this.state.notice = "Copy is unavailable in this browser. Select the visible text to copy it." } },
  saveText(value) { const url = URL.createObjectURL(new Blob([value], { type: "text/plain;charset=utf-8" }))
    const link = document.createElement("a"); link.href = url; link.download = "starpilot-console.txt"; link.click(); URL.revokeObjectURL(url) },
}
export const TroubleshootPage = {
  components: { GxNotice, LocalAccess }, props, emits: ["navigate"], ...lifecycle,
  setup: props => setup(props, false), methods: { ...methods, report: troubleshootReport },
  template: `<section class="gx-settings"><div class="gx-settings__header"><h2>Troubleshoot</h2><button class="gx-btn gx-btn--tonal" @click="$emit('navigate', '/logs')">Logs &amp; Diagnostics</button></div>
    <p>Read-only device, vehicle and selected settings. Change settings in Toggles.</p>
    <div class="gx-settings__controls"><button class="gx-btn gx-btn--tonal" :disabled="!state.data" @click="copyText(report(state.data))">Copy Report</button><button class="gx-btn gx-btn--tonal" @click="$emit('navigate', '/settings')">Toggles</button><button class="gx-btn gx-btn--tonal" @click="$emit('navigate', '/logs/monitor')">System Monitor</button><button class="gx-btn gx-btn--tonal" @click="$emit('navigate', '/logs/crashes')">Crash Reports</button></div>
    <p v-if="state.loading" role="status">Loading report…</p><GxNotice tone="danger" v-if="state.error">{{ state.error }}</GxNotice><p v-if="state.notice" role="status">{{ state.notice }}</p>
    <template v-if="state.data"><section class="gx-card" style="padding:var(--sp-4)"><h3>Device Snapshot</h3><p>State: {{ state.data.device.state || 'Unavailable' }}</p><p>Vehicle: {{ state.data.vehicle.available ? state.data.vehicle.fingerprint : 'Unavailable' }}</p><p>Brand: {{ state.data.vehicle.brand || 'Unavailable' }} · Longitudinal: {{ state.data.vehicle.longitudinal ? 'Available' : 'Unavailable' }} · Steering: {{ state.data.vehicle.steering || 'Unavailable' }}</p><dl><template v-for="row in state.data.snapshot" :key="row.label"><dt>{{ row.label }}</dt><dd>{{ row.value }}</dd></template></dl></section>
      <section v-for="section in state.data.sections" :key="section.title" class="gx-card" style="padding:var(--sp-4)"><h3>{{ section.title }}</h3><dl><template v-for="row in section.rows" :key="row.label"><dt>{{ row.label }}</dt><dd>{{ row.value }}</dd></template></dl></section><p class="gx-note">{{ state.data.note }}</p></template>
    <LocalAccess v-if="state.error" :mode="mode" :on-unauthorized="unauthorized" /></section>`,
}
export const TmuxPage = {
  components: { GxNotice, LocalAccess }, props, emits: ["navigate"], ...lifecycle,
  setup: props => setup(props, true), methods,
  template: `<section class="gx-settings"><div class="gx-settings__header"><h2>tmux Live View</h2><button class="gx-btn gx-btn--tonal" @click="$emit('navigate', '/logs')">Logs &amp; Diagnostics</button></div>
    <p>Read-only launcher console tail. No commands or keyboard input are sent to the comma.</p>
    <div class="gx-settings__controls"><button class="gx-btn gx-btn--tonal" :disabled="mode !== 'local'" @click="feed.setLive(!state.live)">{{ state.live ? 'Pause' : 'Resume' }}</button><button class="gx-btn gx-btn--tonal" :disabled="!state.data?.text" @click="copyText(state.data.text)">Copy Visible Text</button><button class="gx-btn gx-btn--tonal" :disabled="!state.data?.text" @click="saveText(state.data.text)">Save Visible Text</button></div>
    <p role="status">{{ state.live ? 'Live · updates every 2 seconds while visible' : 'Paused' }}</p><p v-if="state.loading" role="status">Loading console…</p><GxNotice tone="danger" v-if="state.error">{{ state.error }}</GxNotice><p v-if="state.notice" role="status">{{ state.notice }}</p>
    <section v-if="state.data" class="gx-card gx-crash-preview" style="padding:var(--sp-4)"><p v-if="!state.data.available">{{ state.data.reason }}</p><p v-else>Pane: {{ state.data.pane }}</p><p v-if="state.data.truncated" class="gx-note">Console tail is limited to 300 lines and 64 KiB.</p><pre style="white-space:pre-wrap;overflow-wrap:anywhere">{{ state.data.text }}</pre></section>
    <LocalAccess v-if="state.error || state.data?.available === false" :mode="mode" :on-unauthorized="unauthorized" /></section>`,
}
