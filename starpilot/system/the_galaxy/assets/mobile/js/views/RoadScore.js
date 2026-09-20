import { GalaxySection } from '../components/GalaxySection.js'

export const RoadScore = {
  name: 'RoadScore', components: { GalaxySection },
  data() { return { status: {}, error: '', busy: false, profile: 'prism', latency: 0, session: null, taps: 0, result: null, timer: null, calibrationTimer: null, clockOffset: 0, uncertainty: null, testMode: false, beat: '', sessionStarted: 0, latencyInitialized: false, outputIdentity: null, testClicks: [], animation: null } },
  mounted() { this.refresh(); this.timer = setInterval(() => this.refresh(), 2000) },
  beforeUnmount() { clearInterval(this.timer); clearInterval(this.calibrationTimer); cancelAnimationFrame(this.animation); if (this.session) this.action('calibration_cancel', {session: this.session}) },
  methods: {
    async refresh() {
      try {
        const response = await fetch('/api/roadscore/status', {cache: 'no-store'})
        if (!response.ok) throw new Error('RoadScore status unavailable')
        this.status = await response.json()
        if (this.outputIdentity !== this.status.output?.id) { this.outputIdentity = this.status.output?.id; this.latencyInitialized = false }
        if (!this.latencyInitialized && Number.isInteger(this.status.latency_ms)) { this.latency = this.status.latency_ms; this.latencyInitialized = true }
        if (!this.busy) this.profile = this.status.selected_profile || this.status.profile || 'prism'
      } catch (error) { this.status = {}; this.error = error.message }
    },
    async action(action, data = {}) {
      this.busy = true; this.error = ''
      try {
        const response = await fetch(`/api/roadscore/${action}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
        const value = await response.json()
        if (!response.ok) throw new Error(value.error || 'Action unavailable')
        return value
      } catch (error) { this.error = error.message; return null }
      finally { this.busy = false; await this.refresh() }
    },
    async quick(action, data = {}) {
      const response = await fetch(`/api/roadscore/${action}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
      const value = await response.json()
      if (!response.ok) throw new Error(value.error || 'Operation unavailable')
      return value
    },
    async start(test = false) {
      this.busy = true; this.error = ''
      try {
        const samples = []
        for (let i = 0; i < 7; i++) {
          const before = performance.now()
          const sample = await this.quick('clock')
          const after = performance.now()
          samples.push({uncertainty: (after - before) / 2, offset: sample.server_ms - (before + after) / 2})
        }
        const best = samples.sort((a,b) => a.uncertainty - b.uncertainty)[0]
        if (best.uncertainty > 25) throw new Error('Connection timing is too uncertain. Try again on a faster connection.')
        this.clockOffset = best.offset; this.uncertainty = best.uncertainty
        const value = await this.quick(test ? 'test' : 'calibration_start', {attended: true})
        this.session = value.session; this.taps = 0; this.result = null; this.testMode = test; this.sessionStarted = performance.now()
        this.calibrationTimer = setInterval(() => this.pollClicks(), 100)
        if (test) this.animateBeat()
      } catch (error) { this.error = error.message }
      finally { this.busy = false }
    },
    async pollClicks() {
      if (!this.session || this.polling) return
      this.polling = true
      const token = this.session
      try {
        const value = await this.quick('calibration_poll', {session: token})
        if (this.session !== token) return
        this.testClicks = value.clicks
        if (performance.now() - this.sessionStarted > (this.testMode ? 14000 : 37000)) await this.cancel()
      } catch (error) { if (this.session === token) { this.error = error.message; this.session = null; clearInterval(this.calibrationTimer) } }
      finally { this.polling = false }
    },
    animateBeat() {
      if (!this.session || !this.testMode) return
      const now = performance.now() + this.clockOffset
      const active = this.testClicks.find(click => now >= click.server_ms && now - click.server_ms < 160)
      this.beat = active ? String(active.beat + 1) : ''
      this.animation = requestAnimationFrame(() => this.animateBeat())
    },
    async tap(event) {
      if (!this.session || this.testMode) return
      const stamp = performance.now()
      try {
        const value = await this.quick('calibration_tap', {session: this.session, server_ms: stamp + this.clockOffset, uncertainty_ms: this.uncertainty})
        this.taps = value.accepted_taps; this.error = ''
      } catch (error) { this.error = error.message }
    },
    async cancel() {
      clearInterval(this.calibrationTimer); cancelAnimationFrame(this.animation)
      const token = this.session; this.session = null; this.beat = ''
      if (token) await this.action('calibration_cancel', {session: token})
    },
    async finish() {
      clearInterval(this.calibrationTimer); cancelAnimationFrame(this.animation)
      const token = this.session; this.session = null
      this.result = await this.action('calibration_result', {session: token})
      if (this.result) this.latency = this.result.latency_ms
    },
    async saveLatency(value) { const result = await this.action('settings', {latency_ms: Number(value)}); if (result) { this.result = null; this.latency = Number(value) } },
  },
  template: `
    <div class="gx-view">
      <h2 style="margin-top:0"><i class="bi bi-music-note-beamed"></i> RoadScore</h2>
      <p style="color:var(--text-muted)">Music shaped by the road.</p>
      <GalaxySection title="Composer" icon="bi-music-note-beamed" :collapsible="false"><div style="padding:16px">
        <div class="gx-row"><div><strong>{{ status.state || 'UNAVAILABLE' }}</strong><div class="gx-row__desc">{{ status.composer ? status.composer.toUpperCase() : 'Composer not connected' }}{{ status.backend ? ' · ' + status.backend : '' }}{{ status.composer && status.profile ? ' · ' + status.profile.toUpperCase() : '' }}</div></div></div>
        <div class="gx-row"><label for="roadscore-style">Next style</label><select class="gx-field" id="roadscore-style" v-model="profile" :disabled="busy || !status.can_edit" @change="action('settings', {profile})"><option v-for="p in status.profiles || []" :value="p.id">{{p.name}}</option></select></div>
        <button class="gx-btn" :disabled="busy || !status.can_prepare" @click="action('prepare')">{{status.preparing ? 'Preparing…' : 'Prepare composer'}}</button>
        <p class="gx-row__desc">{{ status.locked ? 'Controls unlock when the output service confirms playback and judging are idle.' : 'Use the normal RoadScore launcher to prepare or change styles.' }}</p>
      </div></GalaxySection>
      <GalaxySection title="Audio output" icon="bi-speaker" :collapsible="false"><div style="padding:16px">
        <div class="gx-row"><strong>{{status.output?.name || 'Output unavailable'}}</strong><span>{{status.output?.connected ? 'Connected' : 'Not verified'}}</span></div>
        <p class="gx-row__desc">Use Bluetooth settings to select the speaker. RoadScore never changes your output automatically.</p>
        <a href="/mobile/#/bluetooth" class="gx-btn">Bluetooth settings</a>
      </div></GalaxySection>
      <GalaxySection title="Timing correction" icon="bi-clock" :collapsible="false"><div style="padding:16px">
        <p>Current: <strong>{{status.latency_ms == null ? 'Unavailable' : status.latency_ms + ' ms'}}</strong></p>
        <p class="gx-row__desc">Delay music cues on screen to align with heard audio. This cannot make live sound arrive earlier or read ahead on the route.</p>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><button class="gx-btn" :disabled="busy || !status.can_adjust" @click="saveLatency(Math.max(0, (status.latency_ms || 0) - 10))">−10 ms</button><input class="gx-field" aria-label="Timing correction in milliseconds" type="number" min="0" max="1500" step="1" v-model="latency" style="width:100px"><button class="gx-btn" :disabled="busy || !status.can_adjust" @click="saveLatency(Math.min(1500, (status.latency_ms || 0) + 10))">+10 ms</button><button class="gx-btn" :disabled="busy || !status.can_adjust" @click="saveLatency(latency)">Save</button><button class="gx-btn" :disabled="busy || !status.can_adjust" @click="saveLatency(0)">Reset</button></div>
        <p class="gx-row__desc">Park and listen on the selected speaker. Tap along with the clicks. Tap rhythm includes human timing bias; fine-tune afterward.</p>
        <button v-if="!session" class="gx-btn" :disabled="busy || !status.can_calibrate" @click="start(false)">I'm ready · Start clicks</button>
        <template v-else><div v-if="testMode" aria-live="polite" style="font-size:48px;min-height:72px;text-align:center">{{beat || '·'}}</div><button v-if="!testMode" class="gx-btn" style="width:100%;min-height:90px;touch-action:manipulation" @pointerdown.prevent="tap">Tap with each click · {{taps}}</button><button v-if="!testMode" class="gx-btn" :disabled="taps < 8 || busy" @click="finish">Calculate correction</button><button class="gx-btn" @click="cancel">Cancel</button></template>
        <p v-if="result">Suggested correction: {{result.latency_ms}} ms · {{result.accepted_taps}} accepted taps. Review and save above.</p>
        <button class="gx-btn" :disabled="busy || session || !status.can_calibrate" @click="start(true)">Test timing</button>
        <p v-if="!status.can_calibrate" class="gx-row__desc">{{status.session_muted ? 'Audio is muted by the session owner. Unmute intentionally before calibration.' : 'Connect an output and finish playback or judging before calibration.'}}</p>
      </div></GalaxySection>
      <p v-if="error || status.error" role="alert">{{error || status.error}}</p>
    </div>`,
}
