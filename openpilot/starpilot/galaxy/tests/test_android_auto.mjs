import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { AndroidAutoFeed, AndroidAutoPage, validPairingStatus, validPromptInput, uploadPackage } from "../web/js/android-auto.js"

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
assert.match(AndroidAutoPage.template, /Start Projection/)
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
for (const [field, reason] of [['installReady', /display|encoder/], ['enabled', /Enable/],
                             ['serviceReady', /service/], ['bluetoothEnabled', /Bluetooth/], ['parked', /Park/]]) {
  const blocked = page({ ...setup, [field]: false })
  assert.match(blocked.pairingReason, reason)
}
assert.equal(page(setup).pairingReason, '')

// The legacy parked field carries the server's connectivity admission. Effective
// offroad permits setup while the car is powered; no browser ignition veto applies.
const poweredCalls = []
let admitted = false
const powered = new AndroidAutoFeed({ publish: () => {}, later: () => 1, cancelTimer: () => {},
  fetcher: async (path, options) => {
    poweredCalls.push([path, options])
    return response(path.endsWith("/setup") ? { ...setup, parked: admitted } :
      path.endsWith("/status") ? { pairing: { active: false, receiver: null, prompt: null, approved: false }, selectedReceiver: null } : {})
  },
  uploader: async (path) => { poweredCalls.push([path]); return response({ ok: true }) },
})
await powered.start()
assert.equal(await powered.setEnabled(true), false)
assert.equal(await powered.action("./api/android-auto/pairing"), false)
admitted = true
await powered.refresh()
assert.equal(await powered.setEnabled(true), true)
assert.equal(await powered.upload({ size: 32 }), true)
assert.equal(await powered.action("./api/android-auto/pairing"), true)
assert(poweredCalls.some(([path]) => path.endsWith("/upload")))
assert.match(AndroidAutoPage.template, /offroad mode or Park/)
assert.match(page({ ...setup, parked: false }).pairingReason, /offroad mode or Park/)
powered.stop()
