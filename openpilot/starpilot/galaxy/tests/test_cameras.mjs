import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { CamerasPage, CameraSnapshotFeed } from "../web/js/cameras.js"
import { SettingsFeed, SettingsPage } from "../web/js/settings.js"

const requests = []
const states = []
const feed = new SettingsFeed({ publish: (state) => states.push(state),
  fetcher: (url, options) => new Promise((resolve) => requests.push({ url, options, resolve })),
  later: () => 1, cancelTimer: () => {} })
feed.start("pip")
assert.equal(requests[0].url, "./api/settings/pages/pip")
assert.equal(feed.page, "pip")
feed.stop()
requests[0].resolve({ ok: true, status: 200, json: async () => ({ page: "pip", rows: [] }) })
await Promise.resolve()
await Promise.resolve()
assert.equal(states.at(-1).status, "idle") // Hidden or signed-out page cannot restore saved values.

const mounted = { mode: "local", initialPage: "pip", state: { developerOpen: false }, feed: { start(page) { assert.equal(page, "pip") } } }
SettingsPage.mounted.call(mounted)
let returned = 0
const page = { initialPage: "pip", returnTo: () => returned++, state: { query: "anything", data: { page: "pip" } },
  feed: { load() { throw new Error("Root PiP Back must return to Cameras") } } }
SettingsPage.methods.back.call(page)
assert.equal(returned, 1)
assert.equal(page.state.query, "")

assert.match(CamerasPage.template, /Adjust the camera crop with a live cabin preview/)
assert.doesNotMatch(CamerasPage.template, /live camera preview is unavailable/)
assert.match(CamerasPage.template, /Sentry[\s\S]*View motion events/)
assert.match(CamerasPage.template, /Saved motion settings/)
assert.match(CamerasPage.template, /V-ASM[\s\S]*Open saved settings/)
assert.match(CamerasPage.template, /live camera image and current warning status are unavailable/)
assert.match(CamerasPage.template, /snapshots.capture\(camera\)/)
assert.match(SettingsPage.template, /\{\{ title \}\}/)
const app = readFileSync(new URL("../web/js/app.js", import.meta.url), "utf8")
assert.match(app, /<PipPage v-else-if="route\.path === '\/cameras\/pip'"/)
assert.match(app, /route\.path === '\/cameras\/sentry-settings'[\s\S]*initial-page="sentry"/)
assert.match(app, /CamerasPage v-else-if="route\.path === '\/cameras'"/)

const captures = [], snapshots = [], revoked = []
let timer
const camera = new CameraSnapshotFeed({ publish: (value) => snapshots.push(value), unauthorized: () => snapshots.push("unauthorized"),
  fetcher: (url, options) => new Promise((resolve) => captures.push({ url, options, resolve })),
  createURL: () => "blob:camera", revokeURL: (url) => revoked.push(url),
  later: (fn) => { timer = fn; return 1 }, cancelTimer: () => {} })
const pending = camera.capture("cabin")
assert.equal(captures[0].url, "./api/cameras/snapshot")
assert.deepEqual(JSON.parse(captures[0].options.body), { camera: "cabin" })
captures[0].resolve({ ok: true, status: 200, headers: new Map([["Content-Type", "image/jpeg; charset=binary"]]), blob: async () => ({ size: 100 }) })
await pending
assert.equal(snapshots.at(-1).image, "blob:camera")
camera.stop()
assert.deepEqual(revoked, ["blob:camera"])
const late = camera.capture("wide")
camera.stop()
assert.equal(captures[1].options.signal.aborted, true)
captures[1].resolve({ ok: true, status: 200, headers: new Map([["Content-Type", "image/jpeg"]]), blob: async () => ({ size: 100 }) })
await late
assert.equal(snapshots.at(-1).image, "")
const timed = camera.capture("cabin")
timer()
captures[2].resolve({ status: 401 })
await timed
assert.match(snapshots.at(-1).error, /timed out/)
