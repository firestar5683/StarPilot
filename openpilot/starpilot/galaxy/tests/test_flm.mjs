import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { FlmLiveEditor, validLiveFlm, validGmEvidence, gmEventSeries, FlmFeed, FlmPage, flmChart, selectableSegments, validFlmReport, validFlmStatus } from '../web/js/flm.js'

const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve() }
const route = '1234abcd--0123456789'
const segment = `${route}--0`
const inventory = { schemaVersion: 1, source: 'local', partialHistory: true, scanIncomplete: true,
  routes: [{ routeId: route, segmentCount: 2, segments: [
    { number: 0, segmentName: segment, files: { rlog: true, qlog: true, fcamera: false, dcamera: false, ecamera: false, qcamera: false } },
    { number: 1, segmentName: `${route}--1`, files: { rlog: false, qlog: true, fcamera: false, dcamera: false, ecamera: false, qcamera: false } },
  ] }] }
assert.deepEqual(selectableSegments(inventory), [{ routeId: route, number: 0, name: segment }])
assert.deepEqual(selectableSegments({ ...inventory, routes: [] }), [])
assert.deepEqual(selectableSegments({ ...inventory, routes: [{ ...inventory.routes[0], segments: [{ ...inventory.routes[0].segments[0], segmentName: '../unsafe' }] }] }), [])

const operation = { version: 1, operationId: 'owner:1', state: 'running', selected: 1, processed: 0, errorCode: null }
assert.equal(validFlmStatus({ ...operation, state: 'idle', operationId: null, selected: 0 }), true)
assert.equal(validFlmStatus(operation), true)
assert.equal(validFlmStatus({ ...operation, processed: 2 }), false)
assert.equal(validFlmStatus({ ...operation, operationId: '<script>' }), false)
const points = [
  { mono_ns: 1e9, desired_lat_accel: 0, actual_lat_accel: .1, continuity_id: 0 },
  { mono_ns: 1.1e9, desired_lat_accel: .3, actual_lat_accel: .2, continuity_id: 0 },
  { mono_ns: 1.5e9, desired_lat_accel: -.2, actual_lat_accel: -.1, continuity_id: 1 },
  { mono_ns: 1.6e9, desired_lat_accel: -.3, actual_lat_accel: -.2, continuity_id: 1 },
]
const geometry = flmChart(points)
assert.equal(geometry.valid, true)
assert.deepEqual(geometry.paths.map((paths) => paths.length), [2, 2], 'recorded continuity break splits both lines')
assert.equal(geometry.duration, '0.6')
assert.equal(flmChart([{ ...points[0], desired_lat_accel: Infinity }]).valid, false)
assert.equal(flmChart([points[0], { ...points[1], continuity_id: 0, mono_ns: points[0].mono_ns }]).paths[0].length, 0,
  'repeated source time cannot form a line')
const report = { schemaVersion: 1, purpose: 'offline_tracking_diagnostics', operationId: 'owner:1',
  tuneRecommendation: null, vehicleQualification: false, segments: [{ source: { segmentName: segment, sha256: 'a'.repeat(64), compressedBytes: 120, codec: 'zst' },
    analysis: { route, number: 0, status: 'measured', car_params_sha256: 'b'.repeat(64), messages: 10, torque_frames: 4,
      eligible_samples: 4, exclusions: [['driver_override_or_boundary', 2]], mean_abs_error: .12,
      root_mean_square_error: .18, series: points, windows: [], windows_truncated: false } }] }
assert.equal(validFlmReport(report, 'owner:1'), true)
assert.equal(validFlmReport({ ...report, operationId: 'owner:0' }, 'owner:1'), false)
assert.equal(validFlmReport({ ...report, tuneRecommendation: {} }, 'owner:1'), false)
assert.equal(validFlmReport({ ...report, segments: [{ ...report.segments[0], analysis: { ...report.segments[0].analysis, mean_abs_error: Infinity } }] }, 'owner:1'), false)
for (const status of ['insufficient_samples', 'missing_car_params', 'unsupported_car', 'unsupported_controller']) {
  assert.equal(validFlmReport({ ...report, segments: [{ ...report.segments[0], analysis: { ...report.segments[0].analysis,
    status, mean_abs_error: null, root_mean_square_error: null, series: [] } }] }, 'owner:1'), true)
}
assert.match(FlmPage.template, /scan was incomplete|scan was incomplete/i)
assert.match(FlmPage.template, /No tune recommendation/)
assert.doesNotMatch(FlmPage.template, /v-html|Apply tune|Save tune|Cloud/)
const app = readFileSync(new URL('../web/js/app.js', import.meta.url), 'utf8')
assert.match(app, /route\.path === '\/tuning\/flm'/)
globalThis.document = { createElement: () => ({
  set innerHTML(value) {
    this.textContent = value.replaceAll('&amp;', '&')
    this.children = [{ getAttribute: () => this.textContent.match(/foo="([\s\S]*?)"/)?.[1] ?? '' }]
  }, textContent: '', children: [],
}) }
const { compile, reactive, computed } = await import('../web/vendor/vue/vue.esm-browser.js')
const reactivePage = reactive({ selected: [segment], busy: false, requesting: false,
  operation: { ...operation, state: 'completed', processed: 1 } })
Object.defineProperty(reactivePage, 'analysisAvailable', { get: () => FlmPage.computed.analysisAvailable.call(reactivePage) })
const canAnalyze = computed(() => FlmPage.computed.canAnalyze.call(reactivePage))
assert.equal(canAnalyze.value, true)
reactivePage.requesting = true
assert.equal(canAnalyze.value, false, 'Analyze stays locked while completed report is still loading')
assert.equal(reactivePage.analysisAvailable, true, 'background reads do not change the appearance of Analyze')
reactivePage.requesting = false
assert.equal(canAnalyze.value, true, 'Vue recomputes after report request retires')
const rendered = JSON.stringify(compile(FlmPage.template)({ ...FlmPage.data(), ...FlmPage.methods, unauthorized: () => {},
  mode: 'local', inventoryStatus: 'ready', inventory,
  inventoryError: '', available: selectableSegments(inventory), operation: { ...operation, state: 'completed', processed: 1 },
  report, operationError: '', busy: false, requesting: false, selected: [segment], analysisAvailable: true, canAnalyze: true, operationFeed: {},
  inventoryFeed: {}, toggle: () => {}, analyze: () => {}, resultLabel: FlmPage.methods.resultLabel,
  metric: FlmPage.methods.metric, exclusions: FlmPage.methods.exclusions, go: () => {} }, []))
assert.match(rendered, /FLM/)
assert.match(rendered, /Mean absolute error/)
assert.match(rendered, /No tune recommendation/)
assert.match(rendered, /Desired/)
assert.match(rendered, /Actual/)
assert.match(rendered, /1234abcd--0123456789--0/)

function fixture() {
  const requests = [], states = [], timers = new Map()
  let next = 0, revoked = 0
  const feed = new FlmFeed({ publish: (state) => states.push(state), unauthorized: () => revoked++,
    fetcher: (url, options) => new Promise((resolve) => requests.push({ url, options, resolve })),
    later: (fn, ms) => { timers.set(++next, { fn, ms }); return next }, cancelTimer: (id) => timers.delete(id) })
  async function reply(index, body, code = 200) {
    requests[index].resolve({ status: code, ok: code === 200, json: async () => body })
    await flush()
  }
  return { feed, requests, states, timers, reply, get revoked() { return revoked } }
}

const normal = fixture()
normal.feed.start()
assert.equal(normal.requests[0].url, './api/flm/status')
await normal.reply(0, { version: 1, operationId: null, state: 'idle', selected: 0, processed: 0, errorCode: null })
normal.feed.startAnalysis([segment])
assert.equal(normal.requests[1].url, './api/flm/start')
assert.deepEqual(JSON.parse(normal.requests[1].options.body), { segments: [segment] })
await normal.reply(1, operation)
assert.equal(normal.requests[2].url, './api/flm/status')
await normal.reply(2, operation)
assert.equal(normal.feed.status.state, 'running')
normal.feed.cancelAnalysis()
assert.equal(normal.requests[3].url, './api/flm/cancel')
assert.deepEqual(JSON.parse(normal.requests[3].options.body), { operationId: 'owner:1' })
await normal.reply(3, { ...operation, state: 'canceled' })
await normal.reply(4, { ...operation, state: 'canceled' })
assert.equal(normal.feed.status.state, 'canceled')
normal.feed.stop()

const completed = fixture()
completed.feed.start()
await completed.reply(0, { ...operation, state: 'completed', processed: 1 })
assert.equal(completed.requests[1].url, './api/flm/report?operationId=owner%3A1')
assert.equal(completed.states.at(-1).requesting, true)
await completed.reply(1, report)
assert.equal(completed.feed.report.segments.length, 1)
assert.equal(completed.states.at(-1).requesting, false, 'retired report request is published')
completed.feed.stop()

const immediate = fixture()
immediate.feed.start()
await immediate.reply(0, { version: 1, operationId: null, state: 'idle', selected: 0, processed: 0, errorCode: null })
immediate.feed.startAnalysis([segment])
await immediate.reply(1, { ...operation, state: 'completed', processed: 1 })
assert.equal(immediate.feed.status.state, 'completed', 'start preserves an already-completed owner snapshot')
assert.equal(immediate.feed.status.processed, 1)
await immediate.reply(2, { ...operation, state: 'completed', processed: 1 })
await immediate.reply(3, report)
assert.equal(immediate.feed.report.operationId, 'owner:1')
immediate.feed.stop()

const revoked = fixture()
revoked.feed.start()
await revoked.reply(0, { code: 'setup_required' }, 503)
assert.equal(revoked.revoked, 1)
assert.equal(revoked.feed.report, null)
const logout = fixture()
logout.feed.start()
await logout.reply(0, {}, 401)
assert.equal(logout.revoked, 1)
const revokedMutation = fixture()
revokedMutation.feed.start()
await revokedMutation.reply(0, { version: 1, operationId: null, state: 'idle', selected: 0, processed: 0, errorCode: null })
revokedMutation.feed.startAnalysis([segment])
await revokedMutation.reply(1, { code: 'access_unavailable' }, 503)
assert.equal(revokedMutation.revoked, 1)
assert.equal(revokedMutation.feed.report, null)

const lateReport = fixture()
lateReport.feed.start()
await lateReport.reply(0, { ...operation, state: 'completed', processed: 1 })
lateReport.feed.stop()
await lateReport.reply(1, report)
assert.equal(lateReport.feed.report, null, 'report cannot reappear after page hide or logout')

const late = fixture()
late.feed.start()
late.feed.stop()
late.feed.start()
await late.reply(1, { version: 1, operationId: null, state: 'idle', selected: 0, processed: 0, errorCode: null })
const count = late.states.length
await late.reply(0, { ...operation, state: 'completed', processed: 1 })
assert.equal(late.states.length, count)
assert.equal(late.feed.status.state, 'idle')
late.feed.stop()

const timeout = fixture()
timeout.feed.start()
const [timeoutId, deadline] = [...timeout.timers.entries()][0]
timeout.timers.delete(timeoutId)
deadline.fn()
await flush()
assert.match(timeout.feed.error, /timed out/)
timeout.feed.refresh()
assert.equal(timeout.requests.length, 2)
await timeout.reply(1, { version: 1, operationId: null, state: 'idle', selected: 0, processed: 0, errorCode: null })
await timeout.reply(0, operation)
assert.equal(timeout.feed.status.state, 'idle', 'late response cannot overwrite refreshed status')
timeout.feed.stop()

const mutationLate = fixture()
mutationLate.feed.start()
await mutationLate.reply(0, { version: 1, operationId: null, state: 'idle', selected: 0, processed: 0, errorCode: null })
mutationLate.feed.startAnalysis([segment])
mutationLate.feed.stop()

const priorDocument = globalThis.document
const listeners = new Map()
globalThis.document = { hidden: true, addEventListener: (name, cb) => listeners.set(name, cb),
  removeEventListener: (name, cb) => { if (listeners.get(name) === cb) listeners.delete(name) } }
const page = { mode: 'local', $data: { operation: null, report: null, operationError: '', busy: false },
  unauthorized() { throw new Error('revoked') } }
FlmPage.created.call(page)
const inventoryRequests = [], operationRequests = []
page.inventoryFeed.fetcher = (url, options) => new Promise((resolve) => inventoryRequests.push({ url, options, resolve }))
page.operationFeed.fetcher = (url, options) => new Promise((resolve) => operationRequests.push({ url, options, resolve }))
FlmPage.mounted.call(page)
assert.equal(inventoryRequests.length + operationRequests.length, 0, 'hidden mount makes no filesystem/API request')
document.hidden = false
listeners.get('visibilitychange')()
assert.equal(inventoryRequests.length, 1)
assert.equal(operationRequests.length, 1)
document.hidden = true
listeners.get('visibilitychange')()
assert.equal(page.$data.report, null)
FlmPage.beforeUnmount.call(page)
assert.equal(listeners.size, 0)
globalThis.document = priorDocument
mutationLate.feed.start()
await mutationLate.reply(2, { version: 1, operationId: null, state: 'idle', selected: 0, processed: 0, errorCode: null })
await mutationLate.reply(1, operation)
assert.equal(mutationLate.feed.status.state, 'idle')
assert.equal(mutationLate.feed.busy, false)
assert.equal(mutationLate.states.at(-1).requesting, false, 'old request cleanup cannot mark new generation busy')
mutationLate.feed.stop()

// Analyze is beside the selection, before even a long segment list; no duplicate plots destination.
assert.ok(FlmPage.template.indexOf('@click="analyze"') < FlmPage.template.indexOf('v-for="segment in available"'))
assert.equal(FlmPage.template.includes("go('/tuning/plots')"), false)

// Existing offline analysis remains separate from explicit authenticated parked edits.
const liveSurface = { profile: 'torque_universal', knobs: { ff_gain_left: .3 }, baseValues: null }
const liveState = { version: 1, available: true, editable: true, resettable: true, token: 'a'.repeat(64),
  vehicle: 'CHEVROLET_MALIBU_ASCM', controller: 'starpilot', profile: 'torque_universal',
  knobs: { ff_gain_left: { min: -.4, max: .6 } }, defaults: liveSurface,
  curveDefaults: [.16, .18, .20, .23, .27], manual: '{}', manualConflict: false, preconditions: {}, inactiveKnobs: {},
  state: { saved: { one: { label: 'One', surface: liveSurface } }, active: 'one', applied: true,
    trial: 'b'.repeat(32), baselineActive: null, baselineApplied: false, manual: {}, baselineManual: null, appliedManual: null, cleanupProgress: false } }
assert.equal(validLiveFlm(liveState), true)
for (const bad of [ { ...liveState, token: 'old' }, { ...liveState, curveDefaults: [NaN] },
  { ...liveState, state: { ...liveState.state, active: 'missing' } },
  { ...liveState, defaults: { ...liveSurface, knobs: { ff_gain_left: -.5 } } } ]) assert.equal(validLiveFlm(bad), false)
const editor = { ...FlmLiveEditor.data(), live: liveState, closed: false,
  unauthorized: () => { throw new Error('unexpected auth failure') } }
for (const [key, method] of Object.entries(FlmLiveEditor.methods)) editor[key] = method.bind(editor)
editor.choose('one')
assert.deepEqual(editor.curve, liveState.curveDefaults, 'curve starts from owner-derived source values')
assert.equal(editor.useCurve, false)
editor.draft.knobs.ff_gain_left = .2
assert.equal(liveState.state.saved.one.surface.knobs.ff_gain_left, .3, 'draft never mutates the server snapshot')
const posted = []
const savedFetch = globalThis.fetch
const savedHidden = document.hidden
try {
  document.hidden = false
  globalThis.fetch = async (url, options) => { posted.push([url, JSON.parse(options.body)]); return { ok: true, status: 200, json: async () => liveState } }
  await editor.action('trial', { id: 'one' })
  assert.deepEqual(posted[0], ['./api/flm/live-action', { action: 'trial', token: liveState.token, id: 'one' }])
  await editor.restore()
  await flush()
  assert.deepEqual(posted[1][1], { action: 'restore', token: liveState.token, trial: liveState.state.trial })
  editor.live = { ...liveState, editable: false }
  await editor.action('trial', { id: 'one' })
  assert.equal(posted.length, 2, 'moving view cannot issue a mutation')
  editor.live = liveState
  document.hidden = true
  await editor.action('disable')
  assert.equal(posted.length, 2, 'hidden editor does not send new requests')
} finally { globalThis.fetch = savedFetch; document.hidden = savedHidden }


const staleRich = { ...liveState, available: false, editable: false, resettable: true,
  controller: 'standard', profile: 'torque_universal', reason: 'Selected controller changed.',
  state: { ...liveState.state, saved: { one: { label: 'Rich', surface: { ...liveSurface, profile: 'gm_bolt_2022_2023' } } } } }
assert.equal(validLiveFlm(staleRich), true, 'stale rich data admits only the exact reset-only owner response')
assert.equal(validLiveFlm({ ...staleRich, editable: true }), false)
assert.equal(validLiveFlm({ ...staleRich, available: true }), false, 'strict editable profile matching remains')
try {
  document.hidden = false
  editor.live = staleRich
  globalThis.fetch = async (url, options) => { posted.push([url, JSON.parse(options.body)]); return { ok: true, status: 200, json: async () => liveState } }
  const count = posted.length
  await editor.action('trial', { id: 'one' })
  assert.equal(posted.length, count)
  await editor.action('reset')
  assert.deepEqual(posted.at(-1)[1], { action: 'reset', token: staleRich.token })
} finally { globalThis.fetch = savedFetch; document.hidden = savedHidden }
const gmEvidence = { fit: false, vehicleQualification: false,
  context: { version: 1, sourceToken: 'a'.repeat(64), capability: { fingerprint: 'CHEVROLET_MALIBU_ASCM', controller: 'starpilot' } },
  summaries: [{ dimensionId: 'understeer:left:mid', severity: 1 }],
  paths: ['baseline_fix', 'cleanup_pass'].map((key) => ({ key, suggestions: [], profiles: [] })) }
assert.equal(validGmEvidence(gmEvidence), true)
assert.equal(validGmEvidence({ ...gmEvidence, fit: true }), false)
assert.equal(validFlmReport({ ...report, purpose: 'gm_flm_evidence_profiles', gmEvidence }, 'owner:1'), true)
assert.equal(validFlmReport({ ...report, purpose: 'gm_flm_evidence_profiles', gmEvidence: { ...gmEvidence, fit: true } }, 'owner:1'), false)
assert.match(FlmPage.template, /Generate GM trials/)
assert.match(FlmLiveEditor.template, /preconditions/)
assert.match(FlmLiveEditor.template, /inactiveKnobs/)

assert.equal(gmEventSeries({ times: [0, .1], desired: [.2, .3], actual: [.1, .2] }).length, 2)
assert.deepEqual(gmEventSeries({ times: [0, 0], desired: [.2, .3], actual: [.1, .2] }), [])
assert.deepEqual(gmEventSeries({ times: [0, .1], desired: [.2, Infinity], actual: [.1, .2] }), [])
