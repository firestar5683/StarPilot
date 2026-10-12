import assert from "node:assert/strict"
import { AndroidAutoPage, APKMIRROR_URL, DOWNLOAD_LINK, downloadLink, packagePreflight } from "../web/js/android-auto.js"

const release = { version: "17.7.663654-release", url: "https://download.pureapk.com/b/XAPK/Y29t?_fn=QW5k&k=c413", size: 50281364 }
const setup = { enabled: true, installReady: true, identity: { installed: false }, import: { state: "idle" }, maxUploadBytes: 256 * 1048576,
  download: release }
function page(data = setup) {
  const vm = { ...AndroidAutoPage.data(), setup: structuredClone(data) }
  for (const [key, getter] of Object.entries(AndroidAutoPage.computed)) Object.defineProperty(vm, key, { get: () => getter.call(vm) })
  for (const [key, method] of Object.entries(AndroidAutoPage.methods)) vm[key] = method.bind(vm)
  return vm
}

// The comma's APKPure link downloads straight to this browser; anything else falls back to APKMirror.
assert.deepEqual(page().download, { direct: true, url: release.url, version: "17.7.663654", megabytes: 48 })
assert.deepEqual(page({ ...setup, download: null }).download, { direct: false, url: APKMIRROR_URL })
for (const url of [release.url.replace("https:", "http:"), release.url.replace("download.pureapk.com", "evil.test"),
  release.url.replace("/b/XAPK/", "/b/EXE/"), release.url + " x", release.url + "\n", "javascript:alert(1)"]) {
  assert.equal(DOWNLOAD_LINK.test(url), false)
  assert.equal(page({ ...setup, download: { ...release, url } }).download.direct, false)
}
for (const bad of [{ version: "17.8-beta" }, { version: 1 }, { size: 0 }, { size: "50" }]) {
  assert.equal(downloadLink({ ...release, ...bad }).direct, false)
}

// Starting a download clears a stale or rejected file and turns on the Downloads hint.
function file(name, bytes = [0x50, 0x4b, 0x03, 0x04], size = 5 * 1048576) {
  return { name, size, slice(start, end) { assert.deepEqual([start, end], [0, 4]); return new Blob([new Uint8Array(bytes)]) } }
}
const vm = page()
vm.packageFile = file("old.apk")
vm.markDownloadStarted()
assert.equal(vm.packageFile, null)
assert.equal(vm.downloadStarted, true)
vm.openInstall()
assert.equal(vm.downloadStarted, false)

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

// Render the real sheet: one clean flow with a same-tab download link and no sign-in or picture guide.
const { compile } = await import("../web/vendor/vue/vue.esm-browser.js")
const render = compile(AndroidAutoPage.template, { decodeEntities: value => value })
function nodes(vm) {
  const found = []
  const visit = (node) => {
    if (!node || typeof node !== "object") return
    found.push(node)
    if (Array.isArray(node.children)) node.children.forEach(visit)
    else if (node.children && typeof node.children === "object") Object.values(node.children).forEach(slot => { if (typeof slot === "function") slot().forEach(visit) })
  }
  visit(render(vm, []))
  return found
}
const sheet = page()
sheet.installOpen = true
const rendered = nodes(sheet)
const button = rendered.find(node => node.type === "a" && node.props?.href === release.url)
assert(button, "step 1 links the APKPure download")
assert.equal(button.props.target, undefined, "the attachment downloads without leaving Galaxy")
assert.equal(button.props.rel, "noreferrer")
assert.equal(button.props.download, "")
assert.match(JSON.stringify(button.children), /Download Android Auto 17\.7\.663654 · 48 MB/)
assert(!rendered.some(node => node.type === "img"), "no picture guide")
assert(!rendered.some(node => node.type === "input" && node.props?.type !== "file"), "no sign-in fields")
const fallback = page({ ...setup, download: null })
fallback.installOpen = true
const mirror = nodes(fallback).find(node => node.type === "a" && node.props?.href === APKMIRROR_URL)
assert(mirror, "falls back to APKMirror when the comma has no link")
assert.equal(mirror.props.target, "_blank")
for (const gone of [/Google Play/, /sign-in/i, /oauth/i, /renew/i, /apkmirror-\d\.svg/, /installMethod/]) assert.doesNotMatch(AndroidAutoPage.template, gone)
assert.match(AndroidAutoPage.template, /accept="\.apk,\.xapk,\.apkm,\.zip"/)
console.log("Android Auto download: APKPure link, APKMirror fallback, file validation and clean setup sheet passed")
