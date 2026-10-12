import assert from "node:assert/strict"
import { AndroidAutoPage, APKMIRROR_URL, MIRROR_RELEASE_LINK, mirrorResumeDue, packagePreflight } from "../web/js/android-auto.js"

const latest = { version: "17.9.6640", url: APKMIRROR_URL + "android-auto-17-9-6640-release/" }
const compatible = { version: "17.6.663454-release", url: APKMIRROR_URL + "android-auto-17-6-6634-release/" }
const setup = { enabled: true, installReady: true, identity: { installed: false }, import: { state: "idle" }, maxUploadBytes: 256 * 1048576,
  mirror: { latest, compatible } }
function page(data = setup) {
  const vm = { ...AndroidAutoPage.data(), setup: structuredClone(data) }
  for (const [key, getter] of Object.entries(AndroidAutoPage.computed)) Object.defineProperty(vm, key, { get: () => getter.call(vm) })
  for (const [key, method] of Object.entries(AndroidAutoPage.methods)) vm[key] = method.bind(vm)
  return vm
}
assert.deepEqual(page().mirrorLink, latest)
assert.deepEqual(page({ ...setup, mirror: null }).mirrorLink, { version: "", url: APKMIRROR_URL })
for (const url of [latest.url + "#respond", latest.url + "junk", latest.url + "\n", latest.url.replace("https:", "http:"),
  latest.url.replace("www.apkmirror.com", "evil.test"), latest.url.replace("android-auto/android-auto", "maps/android-auto"), "javascript:alert(1)"]) {
  assert.equal(MIRROR_RELEASE_LINK.test(url), false)
  assert.equal(page({ ...setup, mirror: { latest: { version: "17.9.6640", url } } }).mirrorLink.url, APKMIRROR_URL)
}
assert.equal(page().compatibleMirrorLink, null)
assert.deepEqual(page({ ...setup, import: { state: "failed", code: "UNSUPPORTED_VERSION" } }).compatibleMirrorLink, compatible)
assert.equal(page({ ...setup, import: { code: "UNSUPPORTED_VERSION" }, mirror: { compatible: { ...compatible, url: "https://evil.test/" } } }).compatibleMirrorLink, null)

const stored = new Map()
globalThis.localStorage = { getItem: key => stored.get(key) ?? null, setItem: (key, value) => stored.set(key, value), removeItem: key => stored.delete(key) }
const key = "aa.mirrorOpenedAt"
const vm = page()
vm.markMirrorOpened()
assert.equal(mirrorResumeDue(), true)
vm.resumeMirror()
assert.equal(vm.installOpen, true)
assert.equal(vm.installMethod, "manual")
assert.equal(vm.mirrorResume, true)
let scrolls = 0
vm.$nextTick = callback => callback()
vm.$refs = { mirrorUploadStep: { scrollIntoView(options) { assert.equal(options.block, "nearest"); scrolls++ } } }
AndroidAutoPage.watch['setup.identity.installed'].call(vm, false)
assert.equal(scrolls, 1, "a reloaded page scrolls to the file step once setup status arrives")
vm.closeInstall()
assert.equal(stored.has(key), false)
assert.equal(vm.mirrorResume, false)
for (const age of [0, 30 * 60 * 1000]) {
  stored.set(key, String(Date.now() - age))
  assert.equal(mirrorResumeDue(Number(stored.get(key)) + age), true)
}
for (const value of [String(Date.now() - 30 * 60 * 1000 - 1), String(Date.now() + 60000), "NaN", "", " "]) {
  stored.set(key, value)
  assert.equal(mirrorResumeDue(), false)
  assert.equal(stored.has(key), false)
}
stored.set(key, String(Date.now()))
AndroidAutoPage.watch.installState.call(vm, "done")
assert.equal(stored.has(key), false)
stored.set(key, String(Date.now()))
AndroidAutoPage.watch['setup.identity.installed'].call(vm, true)
assert.equal(stored.has(key), false)

// Exercise both lifecycle hooks, including return to an already mounted tab.
let visibility
globalThis.document = { hidden: false, addEventListener: (event, callback) => { assert.equal(event, "visibilitychange"); visibility = callback }, removeEventListener() {} }
const mounted = page()
let starts = 0, stops = 0
mounted.begin = () => starts++
stored.set(key, String(Date.now()))
AndroidAutoPage.mounted.call(mounted)
assert.equal(mounted.installMethod, "manual")
assert.equal(mounted.mirrorResume, true)
mounted.feed.stop = () => stops++
document.hidden = true; visibility()
assert.equal(stops, 1)
mounted.installOpen = false; mounted.mirrorResume = false
document.hidden = false; visibility()
assert.equal(starts, 2)
assert.equal(mounted.installOpen, true)
assert.equal(mounted.mirrorResume, true)
mounted.closeInstall(); visibility()
assert.equal(mounted.installOpen, false, "an intentional close cancels the resume prompt")
stored.set(key, String(Date.now() - 31 * 60 * 1000)); visibility()
assert.equal(mounted.installOpen, false)
stored.set(key, String(Date.now())); mounted.packageFile = { name: "already-chosen.apk" }; visibility()
assert.equal(mounted.installOpen, false, "returning from the native file picker keeps the selection")
mounted.packageFile = null; mounted.setup.import.state = "running"; visibility()
assert.equal(mounted.installOpen, false, "returning while verifying must not reset progress")
AndroidAutoPage.beforeUnmount.call(mounted)
delete globalThis.document

globalThis.localStorage = { getItem() { throw Error("disabled") }, setItem() { throw Error("disabled") }, removeItem() { throw Error("disabled") } }
assert.equal(mirrorResumeDue(), false)
vm.markMirrorOpened(); vm.resumeMirror(); vm.closeInstall()
delete globalThis.localStorage

const navigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, "navigator")
try {
  for (const [browser, hint] of [
    [{ userAgent: "iPhone" }, "In Files, open Downloads."], [{ userAgent: "Android" }, "Open Downloads."],
    [{ userAgent: "Macintosh", platform: "MacIntel", maxTouchPoints: 5 }, "In Files, open Downloads."],
    [{ userAgent: "Macintosh", platform: "MacIntel", maxTouchPoints: 0 }, ""],
  ]) {
    Object.defineProperty(globalThis, "navigator", { configurable: true, value: browser })
    assert.equal(vm.downloadsHint, hint)
  }
} finally {
  if (navigatorDescriptor) Object.defineProperty(globalThis, "navigator", navigatorDescriptor)
  else delete globalThis.navigator
}

function file(name, bytes = [0x50, 0x4b, 0x03, 0x04], size = 5 * 1048576) {
  return { name, size, slice(start, end) { assert.deepEqual([start, end], [0, 4]); return new Blob([new Uint8Array(bytes)]) } }
}
const select = file => vm.choosePackage({ target: { files: file ? [file] : [] } })
for (const name of ["android-auto.apk", "android-auto.apkm", "android-auto.xapk", "android-auto.zip", "ANDROID-AUTO.ZIP"]) {
  assert.equal(packagePreflight({ name }), "")
  await select(file(name))
  assert.equal(vm.packageError, "")
  assert.equal(vm.packageChecking, false)
  assert.equal(vm.uploadReason, "")
}
for (const invalid of [file("android-auto.apk", [60, 33, 68, 79]), file("android-auto.zip", [0x50, 0x4b]), file("android-auto.apk", [], 5 * 1048576 - 1),
  { name: "android-auto.apk", size: 6 * 1048576, slice() { throw Error("unreadable") } }]) {
  await select(invalid)
  assert.match(vm.packageError, /not the Android Auto download/)
  assert.equal(await vm.upload(), false)
}
await select(file("APKMirror Installer.apk", []))
assert.match(vm.packageError, /Installer/)
await select(file("com.google.android.gms.apk", []))
assert.match(vm.packageError, /Play Services/)

// File validation is asynchronous: uploads wait and a stale result cannot poison a newer selection.
let resolve
const pending = select({ name: "android-auto.apk", size: 6 * 1048576, slice: () => ({ arrayBuffer: () => new Promise(done => { resolve = done }) }) })
assert.equal(vm.packageChecking, true)
assert.equal(await vm.upload(), false)
await select(file("android-auto.zip"))
resolve(new Uint8Array([60, 33, 68, 79]).buffer)
await pending
assert.equal(vm.packageFile.name, "android-auto.zip")
assert.equal(vm.packageError, "")
await select(null)
assert.equal(vm.packageFile, null)
assert.equal(vm.packageMagicError, "")

// Check the real rendered failure card, including link text, URL and click handler.
const { compile } = await import('../web/vendor/vue/vue.esm-browser.js')
const render = compile(AndroidAutoPage.template, { decodeEntities: value => value })
const failed = page({ ...setup, import: { state: "failed", code: "UNSUPPORTED_VERSION", started: 2 } })
Object.assign(failed, { installOpen: true, installMethod: "manual", installAttempted: true, installBaseline: 1 })
// Component slots contain the dialog's actual controls.
const nodes = []
function visit(node) {
  if (!node || typeof node !== "object") return
  nodes.push(node)
  if (Array.isArray(node.children)) node.children.forEach(visit)
  else if (node.children && typeof node.children === "object") Object.values(node.children).forEach(slot => { if (typeof slot === "function") slot().forEach(visit) })
}
visit(render(failed, []))
const recovery = nodes.find(node => node.type === "a" && node.props?.href === compatible.url)
assert(recovery, "unsupported versions show a compatible-release link")
assert.match(recovery.children, /Get Android Auto 17.6.663454-release/)
assert.equal(recovery.props.target, "_blank")
assert.equal(recovery.props.rel, "noopener noreferrer")
assert.equal(typeof recovery.props.onClick, "function")
failed.packageFile = file("previous-rejected.apk")
globalThis.localStorage = { getItem: key => stored.get(key) ?? null, setItem: (key, value) => stored.set(key, value), removeItem: key => stored.delete(key) }
recovery.props.onClick()
assert.equal(failed.packageFile, null)
assert.equal(failed.installState, "failed", "the link stays rendered while its default navigation runs")
failed.resumeMirror()
assert.equal(failed.installMethod, "manual")
assert.equal(failed.mirrorResume, true, "a compatible-release download resumes file selection after failure")
assert.equal(failed.installState, "choose")
delete globalThis.localStorage
assert.match(AndroidAutoPage.template, /accept="\.apk,\.xapk,\.apkm,\.zip"/)
console.log("APKMirror: trusted release links, resume lifecycle, storage failures, platform hints, file validation and recovery card passed")
