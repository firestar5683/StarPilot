import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { AndroidAutoFeed, AndroidAutoPage, validPairingStatus, validPromptInput, uploadPackage,
  expiryInfo, packagePreflight, importProblem, installChecks } from "../web/js/android-auto.js"

const setup = { enabled: true, bluetoothEnabled: true, parked: true, installReady: true, serviceReady: true,
  identity: { installed: true, message: "Package ready" },
  import: { state: "idle" }, maxUploadBytes: 200 * 1024 * 1024 }
const prompt = { id: "a".repeat(32), kind: "confirmation", value: "123456", displayOnly: false }
const pairing = { active: true, receiver: { address: "AA:BB:CC:DD:EE:FF", name: "Car" }, prompt, approved: false }

assert.equal(validPairingStatus(pairing), true)
assert.equal(validPairingStatus({ ...pairing, receiver: { ...pairing.receiver, address: "bad" } }), false)
assert.equal(validPairingStatus({ ...pairing, prompt: { ...prompt, id: "bad" } }), false)
assert.equal(validPromptInput({ kind: "pin" }, "1234"), true)
assert.equal(validPromptInput({ kind: "pin" }, "\n"), false)
assert.equal(validPromptInput({ kind: "passkey" }, "1234567"), false)
assert.equal(validPromptInput(prompt, ""), true)
assert.match(AndroidAutoPage.template, /Check that this code matches your car/)
assert.match(AndroidAutoPage.template, /Cancel Search \/ Pairing/)
assert.match(AndroidAutoPage.template, /Wired USB setup is unavailable/)
assert.doesNotMatch(AndroidAutoPage.template, /v-html|autoaccept/i)
const app = readFileSync(new URL("../web/js/app.js", import.meta.url), "utf8")
assert.match(app, /AndroidAutoPage v-else-if="route\.path === '\/android-auto'"/)

const replies = {
  "./api/android-auto/setup": setup,
  "./api/android-auto/pairing/status": { pairing, selectedReceiver: null },
  "./api/android-auto/receivers": { receivers: [{ address: "AA:BB:CC:DD:EE:FF", name: "Saved car" }] },
}
const calls = [], states = [], timers = new Map()
let timerId = 0
const response = (body, code = 200) => ({ status: code, ok: code >= 200 && code < 300, json: async () => structuredClone(body) })
const feed = new AndroidAutoFeed({ publish: (value) => states.push(value),
  uploader: async (path, options, progress) => { calls.push([path, options]); progress({ loaded: 16, total: 32 }); return response({ ok: true }) },
  fetcher: async (path, options) => {
    calls.push([path, options])
    return response(replies[path] || { ok: true })
  }, later: (fn, ms) => { timers.set(++timerId, { fn, ms }); return timerId }, cancelTimer: (id) => timers.delete(id) })
await feed.start()
assert.equal(feed.setup.identity.installed, true)
assert.equal(feed.pairing.prompt.value, "123456")
assert.deepEqual(calls.slice(0, 2).map(([path]) => path), ["./api/android-auto/setup", "./api/android-auto/pairing/status"])
assert(calls.every(([, options]) => options.credentials === "same-origin"))
assert([...timers.values()].some((timer) => timer.ms === 1000))
await feed.action("./api/android-auto/pairing/response", { prompt_id: prompt.id, accepted: true, value: "" })
assert.deepEqual(JSON.parse(calls.find(([path]) => path.endsWith("/response"))[1].body),
  { prompt_id: prompt.id, accepted: true, value: "" })
assert.equal(await feed.upload({ size: setup.maxUploadBytes + 1 }), false)
assert.match(feed.error, /size limit/)
const packageFile = { size: 32 }
assert.equal(await feed.upload(packageFile), true)
assert.equal(calls.find(([path]) => path.endsWith("/upload"))[1].body, packageFile)
assert.equal(await feed.removePackage(), true)
assert.equal(calls.find(([path]) => path.endsWith("/identity"))[1].method, "DELETE")
assert.match(AndroidAutoPage.template, /Delete Package/)
feed.stop(true)
assert(calls.some(([path, options]) => path.endsWith("/cancel") && options.keepalive))
await feed.start()
replies["./api/android-auto/pairing/status"] = {
  pairing: { active: false, receiver: null, prompt: null, approved: false }, selectedReceiver: null,
  runtime: { state: "idle", running: false, auto_connect: false },
}
await feed.refresh()
assert.equal(await feed.loadReceivers(), true)
assert.deepEqual(feed.receivers, [{ address: "AA:BB:CC:DD:EE:FF", name: "Saved car" }])
assert.equal(await feed.control("select_receiver", { address: "AA:BB:CC:DD:EE:FF" }), true)
assert.deepEqual(JSON.parse(calls.find(([path]) => path.endsWith("/control"))[1].body),
  { action: "select_receiver", address: "AA:BB:CC:DD:EE:FF" })
assert.match(AndroidAutoPage.template, /Connect to car/)
assert.match(AndroidAutoPage.template, />Disconnect</)
assert.match(AndroidAutoPage.template, /Automatic Connection/)
assert.equal(await feed.setEnabled(false), true)
assert.deepEqual(JSON.parse(calls.find(([path]) => path.endsWith("/enable"))[1].body), { enabled: false })
feed.stop()
replies["./api/android-auto/pairing/status"] = { pairing: { active: false, receiver: null, prompt: null, approved: false },
  selectedReceiver: null }
await feed.start()
assert.equal(feed.pairing.active, false, "reconnect must discard the old prompt")
replies["./api/android-auto/pairing/status"].selectedReceiver = { address: "AA:BB:CC:DD:EE:FF", name: "My car" }
await feed.refresh()
assert.equal(feed.selected.name, "My car")
feed.stop()

const expiredReplies = { pairing, selectedReceiver: null }
const expired = new AndroidAutoFeed({ publish: () => {}, fetcher: async (path) => response(path.endsWith("/setup") ? setup : expiredReplies),
  later: () => 1, cancelTimer: () => {} })
await expired.start()
expiredReplies.pairing = { active: false, receiver: null, prompt: null, approved: false }
await expired.refresh()
assert.equal(expired.endReason, "ended")
expired.stop()

let release
const stale = new AndroidAutoFeed({ publish: () => {}, fetcher: () => new Promise((resolve) => { release = resolve }),
  later: () => 1, cancelTimer: () => {} })
const loading = stale.start()
stale.stop()
release(response(setup))
await loading
assert.equal(stale.setup, null)

let revoked = 0
const unauthorized = new AndroidAutoFeed({ publish: () => {}, unauthorized: () => revoked++,
  fetcher: async () => response({ error: "Sign in" }, 401), later: () => 1, cancelTimer: () => {} })
await unauthorized.start()
assert.equal(revoked, 1)
assert.equal(unauthorized.active, false)

const timeoutTimers = new Map()
let timeoutId = 0
const timedOut = new AndroidAutoFeed({ publish: () => {}, fetcher: (_path, options) => new Promise((_resolve, reject) => {
  options.signal.addEventListener("abort", () => reject(new Error("aborted")))
}), later: (fn, ms) => { timeoutTimers.set(++timeoutId, { fn, ms }); return timeoutId },
cancelTimer: (id) => timeoutTimers.delete(id) })
const waitForTimeout = timedOut.start()
const timeout = [...timeoutTimers.values()][0]
assert.equal(timeout.ms, 8000)
timeout.fn()
await waitForTimeout
assert.match(timedOut.error, /too long/)
timedOut.stop()

const parked = new AndroidAutoFeed({ publish: () => {}, fetcher: async (path) => response(path.endsWith("/setup") ?
  { ...setup, parked: false } : { pairing: { active: false, receiver: null, prompt: null, approved: false },
    selectedReceiver: null }),
  later: () => 1, cancelTimer: () => {} })
await parked.start()
assert.equal(await parked.action("./api/android-auto/pairing"), false)

function page(selectedSetup = setup) {
  const vm = { ...AndroidAutoPage.data(), setup: structuredClone(selectedSetup) }
  for (const [key, getter] of Object.entries(AndroidAutoPage.computed)) Object.defineProperty(vm, key, { get: () => getter.call(vm) })
  for (const [key, method] of Object.entries(AndroidAutoPage.methods)) vm[key] = method.bind(vm)
  return vm
}
const uploadPage = page({ ...setup, enabled: false })
const uploadCalls = []
uploadPage.feed = {
  async setEnabled(value) { uploadCalls.push(["enable", value]); uploadPage.setup.enabled = value; return true },
  async upload(file) { uploadCalls.push(["upload", file]); return true },
}
for (const [name, type] of [["android-auto.apk", ""], ["android-auto.xapk", "application/zip"], ["android-auto.apkm", "application/octet-stream"]]) {
  const file = { name, size: 123, type }
  uploadPage.setup.enabled = false
  uploadPage.choosePackage({ target: { files: [file] } })
  assert.equal(uploadPage.packageFile, file)
  assert.equal(uploadPage.uploadReason, "", "valid selection can enable and upload")
  assert.equal(await uploadPage.upload(), true)
  assert.deepEqual(uploadCalls.slice(-2), [["enable", true], ["upload", file]])
}
uploadPage.choosePackage({ target: { files: [{ name: "empty.apk", size: 0 }] } })
assert.match(uploadPage.uploadReason, /empty/)
assert.equal(await uploadPage.upload(), false)
uploadPage.choosePackage({ target: { files: [{ name: "large.apk", size: setup.maxUploadBytes + 1 }] } })
assert.match(uploadPage.uploadReason, /maximum size/)
uploadPage.choosePackage({ target: { files: [{ name: "ok.apk", size: 1 }] } })
uploadPage.setup.parked = false
assert.match(uploadPage.uploadReason, /Park/)
uploadPage.setup.parked = true
uploadPage.busy = true
assert.match(uploadPage.uploadReason, /respond/)
uploadPage.busy = false
uploadPage.setup.enabled = false
uploadPage.setup.installReady = false
assert.match(uploadPage.uploadReason, /installed/)
uploadPage.setup.installReady = true
uploadPage.feed.setEnabled = async () => false
const beforeDeniedEnable = uploadCalls.length
assert.equal(await uploadPage.upload(), false)
assert.equal(uploadCalls.length, beforeDeniedEnable, "failed enable never uploads")
console.log("Android Auto: selected APK/XAPK/APKM, MIME independence, enable/upload sequencing, explicit blockers and feed boundaries passed")

class UploadRequest {
  upload = {}; status = 202; responseText = '{"ok":true}'; headers = {}; sent = null
  open(method, path) { this.method = method; this.path = path }
  setRequestHeader(key, value) { this.headers[key] = value }
  send(value) { this.sent = value }
  abort() { this.onabort() }
}
for (const event of ['load', 'error', 'timeout', 'abort']) {
  const xhr = new UploadRequest(), controller = new AbortController(), progress = []
  const body = { size: 20 * 1024 * 1024 }
  const upload = uploadPackage('./api/android-auto/upload', { body, signal: controller.signal }, p => progress.push(p), () => xhr)
  assert.equal(xhr.sent, body); assert.equal(xhr.withCredentials, true)
  assert.equal(xhr.headers['Content-Type'], 'application/octet-stream')
  xhr.upload.onprogress({ lengthComputable: true, loaded: body.size / 2, total: body.size })
  assert.equal(progress[0].loaded, body.size / 2)
  if (event === 'abort') controller.abort(); else xhr['on' + event]()
  if (event === 'load') assert.deepEqual(await (await upload).json(), { ok: true })
  else await assert.rejects(upload, /interrupted|timed out|canceled/)
}
const alreadyAborted = new AbortController(); alreadyAborted.abort()
const neverSent = new UploadRequest()
await assert.rejects(uploadPackage('upload', { signal: alreadyAborted.signal }, () => {}, () => neverSent), /canceled/)
assert.equal(neverSent.sent, null)
assert.doesNotMatch(AndroidAutoPage.template, /v-if="!localAccess"|Open this comma directly/)
console.log('Remote-capable binary uploader: progress, credentials, failure, timeout and cancellation passed')

// Compile the shipped Vue template, not only its strings: plain <template>
// renders an inert DOM node and hides every setup control in real browsers.
const { compile } = await import('../web/vendor/vue/vue.esm-browser.js')
const render = compile(AndroidAutoPage.template, { decodeEntities: value => value })
const vm = page(setup)
vm.mode = 'local'
vm.installOpen = true  // the package picker lives in the install sheet
const tree = render(vm, [])
const tags = []
function visit(node) {
  if (!node || typeof node !== 'object') return
  if (typeof node.type === 'string') tags.push(node.type)
  if (Array.isArray(node.children)) node.children.forEach(visit)
}
visit(tree)
assert(!tags.includes('template'), 'setup cannot live inside an inert template element')
assert(tags.includes('input') && tags.includes('button'), 'setup renders package selection and actions')
for (const [field, reason] of [['installReady', /display|encoder/],
                             ['serviceReady', /service/], ['bluetoothEnabled', /Bluetooth/], ['parked', /Park/]]) {
  const blocked = page({ ...setup, [field]: false })
  assert.match(blocked.pairingReason, reason)
}
assert.equal(page(setup).pairingReason, '')
// Pairing needs no package; only projection does, and Connect opens the installer instead.
const noPackage = page({ ...setup, identity: { installed: false } })
assert.equal(noPackage.pairingReason, '')
noPackage.selected = { address: "AA:BB:CC:DD:EE:FF", name: "Car" }
noPackage.control = () => assert.fail("projection must not start without a package")
assert.equal(noPackage.connect(), false)
assert.equal(noPackage.installOpen, true)
// Turned off is no blocker either: Find My Car enables Android Auto, then pairs once the service is up.
const off = page({ ...setup, enabled: false, serviceReady: false, identity: { installed: false } })
assert.equal(off.pairingReason, '')
off.feed = { async setEnabled(value) { assert.equal(value, true); return true }, action: async () => assert.fail("paired before the service was up") }
assert.equal(await off.startPairing(), false)
assert.equal(off.pairWhenReady, true)

// Step 1 status: expiry wording by remaining days, and the expired date from the certificate.
assert.deepEqual(expiryInfo({ installed: true, expires: "2027-10-12T00:00:00+00:00", days_left: 372 }, "en-US"),
  { level: "ready", label: "Ready · Valid until Oct 12, 2027" })
assert.deepEqual(expiryInfo({ installed: true, expires: "2027-04-12T00:00:00+00:00", days_left: 9 }, "en-US"),
  { level: "soon", label: "Expires in 9 days (Apr 12)" })
assert.deepEqual(expiryInfo({ installed: false, expired: true, expires: "2026-04-12T00:00:00+00:00" }, "en-US"),
  { level: "expired", label: "Expired on Apr 12, 2026" })
assert.equal(expiryInfo({ installed: false, error: "unusable" }).level, "broken")
assert.equal(expiryInfo({ installed: false }).level, "none")

// Wrong downloads are caught by name before the upload; the real APKMirror file name passes.
assert.equal(packagePreflight({ name: "com.google.android.projection.gearhead_17.6.663454-release-2025-apkmirror.com.apk" }), "")
assert.match(packagePreflight({ name: "APKMirror Installer (Official)_1.6.apk" }), /Installer/)
assert.match(packagePreflight({ name: "com.google.android.gms_24.apk" }), /Play Services/)
assert.match(packagePreflight({ name: "android-auto.zip" }), /not an Android package/)
const wrongPage = page(setup)
wrongPage.choosePackage({ target: { files: [{ name: "APKMirror Installer.apk", size: 10 }] } })
assert.match(wrongPage.uploadReason, /Installer/)

// Server rejection codes become friendly messages and a failed checklist row.
assert.match(importProblem({ state: "failed", code: "WRONG_APP" }, "Maps.apk"), /Wrong app selected \(Maps\.apk\)/)
assert.match(importProblem({ state: "failed", code: "WRONG_APP" }, "APKMirror Installer.apk"), /Installer/)
assert.match(importProblem({ state: "failed", code: "EXPIRED", expires: "2026-04-12T00:00:00+00:00" }, "", "en-US"), /expired on Apr 12, 2026/)
assert.match(importProblem({ state: "failed", code: "CORRUPT" }), /incomplete or damaged/)
assert.equal(importProblem({ state: "failed", code: "UNSUPPORTED_VERSION", error: "Use version from server" }), "Use version from server")
assert.equal(importProblem({ state: "running" }), "")
const statuses = (job) => installChecks(job, "en-US").map((check) => check.status)
assert.deepEqual(statuses({ state: "running", stage: "searching" }), ["done", "active", "pending", "pending"])
assert.deepEqual(statuses({ state: "running", stage: "installing" }), ["done", "done", "done", "active"])
assert.deepEqual(statuses({ state: "failed", stage: "searching", code: "WRONG_APP" }), ["done", "failed", "pending", "pending"])
assert.deepEqual(statuses({ state: "failed", stage: "verifying", code: "EXPIRED" }), ["done", "done", "done", "failed"])
const done = installChecks({ state: "done", stage: "done", expires: "2027-10-12T00:00:00+00:00" }, "en-US")
assert.deepEqual(done.map((check) => check.status), ["done", "done", "done", "done"])
assert.equal(done[3].label, "Certificate valid until October 12, 2027")

// The install sheet follows only the import this page started, not an older result.
const sheet = page({ ...setup, import: { state: "failed", code: "WRONG_APP", started: 1 } })
assert.equal(sheet.installState, "choose")
sheet.installAttempted = true; sheet.installBaseline = 1
assert.equal(sheet.installState, "choose")
sheet.setup.import = { state: "running", stage: "reading", started: 2 }
assert.equal(sheet.installState, "checking")
sheet.setup.import = { state: "done", stage: "done", started: 2 }
assert.equal(sheet.installState, "done")
console.log("Android Auto: expiry badges, package preflight, friendly rejections and install checklist passed")

// Enabling can finish its refresh after the service is already ready.
const { reactive, watch, nextTick } = await import('../web/vendor/vue/vue.esm-browser.js')
const readyPage = reactive(page({ ...setup, enabled: false, serviceReady: false }))
let pairingCalls = 0
readyPage.feed = {
  async setEnabled() {
    readyPage.setup = { ...readyPage.setup, enabled: true, serviceReady: true }
    await nextTick()
    return true
  },
  async action() { pairingCalls++; return true },
}
const stopReadyWatch = watch(() => readyPage.setup.serviceReady, () => AndroidAutoPage.watch['setup.serviceReady'].call(readyPage))
assert.equal(await readyPage.startPairing(), true)
assert.equal(pairingCalls, 1)
assert.equal(readyPage.pairWhenReady, false)
stopReadyWatch()
const connectingPage = page(setup)
connectingPage.runtime = { running: true, state: 'connecting_bluetooth' }
assert.equal(connectingPage.projecting, false)
connectingPage.runtime.state = 'streaming'
assert.equal(connectingPage.projecting, true)
