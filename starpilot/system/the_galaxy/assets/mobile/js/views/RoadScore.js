import { GalaxySection } from '../components/GalaxySection.js'

export const RoadScore = {
  name: 'RoadScore', components: { GalaxySection },
  data() { return { status: {}, error: '', busy: false, profile: 'prism', latency: 0, session: null, taps: 0, result: null, timer: null, calibrationTimer: null, clockOffset: 0, uncertainty: null, testMode: false, beat: '', sessionStarted: 0, latencyInitialized: false, outputIdentity: null, testClicks: [], animation: null, countIn: 8, bpm: 100, beatIndex: -1, cue: 'Getting ready…', lastTapInput: -1000, targetTaps: 12, finishing: false } },
  mounted() { window.addEventListener('keydown', this.keyTap); this.refresh(); this.timer = setInterval(() => this.refresh(), 2000) },
  beforeUnmount() { window.removeEventListener('keydown', this.keyTap); clearInterval(this.timer); clearInterval(this.calibrationTimer); cancelAnimationFrame(this.animation); if (this.session) this.action('calibration_cancel', {session: this.session}) },
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
        this.targetTaps = value.target_taps || 12; this.finishing = false; this.lastTapInput = -1000; this.session = value.session; this.taps = 0; this.result = null; this.testMode = test; this.sessionStarted = performance.now()
        this.calibrationTimer = setInterval(() => this.pollClicks(), 100)
        this.countIn = value.count_in || 8; this.bpm = value.bpm || 100; this.beatIndex = -1; this.testClicks = []; this.cue = 'Getting ready…'; this.animateBeat()
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
        if (performance.now() - this.sessionStarted > (this.testMode ? 14000 : 55000)) {
          if (!this.testMode && this.taps >= 8) await this.finish()
          else { await this.cancel(); if (!this.testMode) this.error = 'Not enough chime taps. Start again and tap only when you hear each chime.' }
        }
      } catch (error) { if (this.session === token) { this.error = error.message; this.session = null; clearInterval(this.calibrationTimer) } }
      finally { this.polling = false }
    },
    animateBeat() {
      if (!this.session) return
      const now = performance.now() + this.clockOffset
      const first = this.testClicks.find(click => click.beat === 0)
      const index = first ? Math.floor((now - first.server_ms) / (60000 / this.bpm)) : -1
      this.beatIndex = index
      this.beat = index >= 0 && index < this.countIn ? String(index % 4 + 1) : '♪'
      this.cue = index < 0 ? 'Getting ready…' : index < this.countIn && !this.testMode ? `Listen · count-in bar ${Math.floor(index / 4) + 1} of 2` : this.testMode ? 'Watch and listen' : 'Tap once when you hear each chime · wait through the gaps'
      this.animation = requestAnimationFrame(() => this.animateBeat())
    },
    keyTap(event) {
      if (!this.session || this.testMode || event.code !== 'Space') return
      const element = event.target
      if (element?.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(element?.tagName || '')) return
      event.preventDefault()
      if (!event.repeat) this.tap(event)
    },
    async tap(event) {
      if (!this.session || this.testMode || this.beatIndex < this.countIn || this.taps >= this.targetTaps) return
      const stamp = performance.now()
      if (stamp - this.lastTapInput < 150) return
      this.lastTapInput = stamp
      try {
        const value = await this.quick('calibration_tap', {session: this.session, server_ms: stamp + this.clockOffset, uncertainty_ms: this.uncertainty})
        this.taps = value.accepted_taps; this.error = ''; if (this.taps >= this.targetTaps) await this.finish()
      } catch (error) { this.error = error.message }
    },
    async cancel() {
      clearInterval(this.calibrationTimer); cancelAnimationFrame(this.animation)
      const token = this.session; this.session = null; this.beat = ''
      if (token) await this.action('calibration_cancel', {session: token})
    },
    async finish() {
      if (this.finishing || !this.session) return
      this.finishing = true
      clearInterval(this.calibrationTimer); cancelAnimationFrame(this.animation)
      const token = this.session; this.session = null
      this.result = await this.action('calibration_result', {session: token})
      if (this.result) this.latency = this.result.latency_ms
      this.finishing = false
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
        <p class="gx-row__desc">Listen to two full bars (8 clicks), then tap only when you hear each two-tone chime. The gaps vary: wait and listen, don’t keep tapping the beat. Use the screen or Space. After 12 taps, the estimate calculates automatically. It includes your reaction time.</p>
        <button v-if="!session" class="gx-btn" :disabled="busy || !status.can_calibrate" @click="start(false)">I'm ready · Start clicks</button>
        <template v-else><Teleport to="body"><div role="dialog" aria-modal="true" aria-label="Bluetooth timing calibration" style="position:fixed;inset:0;z-index:100000;background:var(--bg-primary,#090914);display:flex;flex-direction:column;padding:24px;gap:16px;text-align:center">
          <strong>{{cue}}</strong><div style="font-size:72px" aria-live="off">{{beat}}</div>
          <button v-if="!testMode" class="gx-btn" style="flex:1;width:100%;touch-action:manipulation;font-size:28px" :disabled="beatIndex < countIn || taps >= 16" @pointerdown.prevent="tap">{{beatIndex < countIn ? 'Listen first' : 'Hear a chime? Tap here or press Space'}}<br>{{taps}} / {{targetTaps}} chimes</button>
          <p>Listen to the speaker, not the screen · one tap per chime</p>
          <button v-if="!testMode" class="gx-btn" :disabled="taps < 8 || busy" @click="finish">Calculate correction</button><button class="gx-btn" @click="cancel">Cancel</button>
        </div></Teleport></template>
        <p v-if="result">Suggested correction: {{result.latency_ms}} ms · {{result.accepted_taps}} accepted taps · {{result.spread_ms}} ms spread. Includes tap reaction time. Review and Save above; the saved value has not changed.</p>
        <button class="gx-btn" :disabled="busy || session || !status.can_calibrate" @click="start(true)">Test timing</button>
        <p v-if="!status.can_calibrate" class="gx-row__desc">{{status.session_muted ? 'Audio is muted by the session owner. Unmute intentionally before calibration.' : 'Connect an output and finish playback or judging before calibration.'}}</p>
      </div></GalaxySection>
      <p v-if="error || status.error" role="alert">{{error || status.error}}</p>
    </div>`,
}
