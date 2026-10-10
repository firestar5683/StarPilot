import assert from "node:assert/strict"
import { LayoutPreviewFeed, PREVIEW_SCENES } from "../web/js/layout-preview.js"

const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve() }
const document = { version: 1, palette: { text: "#FFFFFFFF" }, layouts: { large: {}, compact: {} } }

function fixture() {
  const requests = [], updates = [], timers = new Map(), revoked = []
  let next = 0, created = 0, unauthorized = 0
  const feed = new LayoutPreviewFeed({ publish: (value) => updates.push(value), unauthorized: () => unauthorized++,
    fetcher: (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject })),
    later: (fn) => { timers.set(++next, fn); return next }, cancelTimer: (id) => timers.delete(id),
    urls: { createObjectURL: () => `blob:${++created}`, revokeObjectURL: (url) => revoked.push(url) } })
  const tick = () => { const [id, fn] = [...timers.entries()].at(-1); timers.delete(id); fn() }
  const reply = async (index, status = 200, type = "image/png") => {
    requests[index].resolve({ ok: status === 200, status, headers: { get: () => type },
      blob: async () => ({ size: 1024 }) }); await flush()
  }
  return { feed, requests, updates, timers, revoked, tick, reply, get unauthorized() { return unauthorized } }
}

assert.deepEqual(PREVIEW_SCENES.map(({ id }) => id), ["engaged", "aol", "long_only", "experimental", "braking",
  "cem_stop_light", "cem_lead", "cem_curve", "slc_pending", "slc_max", "slc_equal",
  "slc_pedal", "slc_retained", "slc_disengaged", "slc_unavailable", "slc_display"])
assert.equal(PREVIEW_SCENES.find(({ id }) => id === "experimental").label, "Manual experimental")
for (const scene of ["cem_stop_light", "cem_lead", "cem_curve", "slc_pending", "slc_max", "slc_equal",
  "slc_pedal", "slc_retained", "slc_disengaged", "slc_unavailable", "slc_display"]) {
  const cem = fixture()
  cem.feed.start(); cem.feed.update(document, "compact", scene); cem.tick()
  assert.equal(JSON.parse(cem.requests[0].options.body).scene, scene)
  await cem.reply(0)
  assert.equal(cem.updates.at(-1).status, "ready")
  cem.feed.stop()
}
const normal = fixture()
normal.feed.start()
normal.feed.update(document, "large", "engaged")
normal.feed.update(document, "compact", "aol")
assert.equal(normal.timers.size, 1)
normal.tick()
assert.equal(normal.requests.length, 1)
assert.equal(normal.requests[0].url, "./api/ui/layout/preview")
assert.deepEqual(JSON.parse(normal.requests[0].options.body), { document, profile: "compact", scene: "aol" })
assert.equal(normal.requests[0].options.credentials, "same-origin")
await normal.reply(0)
assert.equal(normal.updates.at(-1).url, "blob:1")
normal.feed.update(document, "compact", "aol")
assert.equal(normal.timers.size, 0, "identical synchronization does not rerender the preview")

normal.feed.update(document, "large", "braking")
assert.deepEqual(normal.revoked, [])
assert.equal(normal.updates.at(-1).status, "updating")
normal.tick()
const stale = normal.requests[1]
normal.feed.update(document, "large", "experimental")
assert.equal(stale.options.signal.aborted, true)
normal.tick()
assert.equal(normal.requests.length, 2) // The next request waits for the old one to settle.
await normal.reply(1)
assert.equal(normal.requests.length, 3)
assert.equal(normal.updates.at(-1).status, "updating")
await normal.reply(2)
assert.equal(normal.updates.at(-1).url, "blob:2")
normal.feed.update(document, "large", "experimental", true)
assert.deepEqual(normal.revoked, ["blob:1"])
assert.equal(normal.timers.size, 0)
assert.equal(normal.feed.currentUrl, "blob:2", "drag keeps the preview mounted")
assert.equal(normal.updates.at(-1).status, "editing")
normal.feed.update(document, "large", "experimental")
normal.tick(); await normal.reply(3)
normal.feed.stop()
assert.deepEqual(normal.revoked, ["blob:1", "blob:2", "blob:3"])
assert.equal(normal.updates.at(-1).url, null)

const failure = fixture()
failure.feed.start(); failure.feed.update(document, "large", "engaged"); failure.tick(); await failure.reply(0, 503)
assert.equal(failure.updates.at(-1).status, "unavailable")
assert.equal(failure.timers.size, 1) // Recover automatically without hiding the error.
failure.feed.retry(); failure.tick(); await failure.reply(1)
assert.equal(failure.updates.at(-1).status, "ready")
failure.feed.update(document, "large", "braking"); failure.tick(); await failure.reply(2, 200, "text/html")
assert.equal(failure.updates.at(-1).status, "unavailable")
assert.deepEqual(failure.revoked, [])
for (const [status, message] of [[403, /Turn off the vehicle to preview/], [429, /busy/]]) {
  failure.feed.update(document, "large", "engaged"); failure.tick()
  await failure.reply(failure.requests.length - 1, status)
  assert.match(failure.updates.at(-1).error, message)
}

const auth = fixture()
auth.feed.start(); auth.feed.update(document, "large", "engaged"); auth.tick(); await auth.reply(0, 401)
assert.equal(auth.unauthorized, 1)
assert.equal(auth.feed.active, false)

const timeout = fixture()
timeout.feed.start(); timeout.feed.update(document, "large", "engaged"); timeout.tick()
timeout.tick()
assert.equal(timeout.requests[0].options.signal.aborted, true)
timeout.requests[0].reject(new Error("aborted")); await flush()
assert.equal(timeout.updates.at(-1).status, "unavailable")

const late = fixture()
late.feed.start(); late.feed.update(document, "large", "engaged"); late.tick(); late.feed.stop(); await late.reply(0)
assert.equal(late.updates.some((update) => update.url?.startsWith("blob:")), false)
console.log("Native layout preview: debounce, single flight, stale responses, drag fallback, cleanup, retry and auth passed")

const projection = fixture()
projection.feed.start()
const aaDocument = {version: 1, canvas: {width: 1920, height: 1080}, widgets: {}}
projection.feed.update(aaDocument, "projection", "engaged")
projection.tick()
assert.deepEqual(JSON.parse(projection.requests[0].options.body), {document: aaDocument, profile: "projection", scene: "engaged"})
await projection.reply(0)
assert.equal(projection.updates.at(-1).status, "ready")
aaDocument.widgets.current_speed = {x: 800, y: 0, enabled: true}
projection.feed.update(aaDocument, "projection", "engaged")
projection.tick()
await projection.reply(1)
assert.equal(projection.updates.at(-1).status, "ready")
assert.deepEqual(projection.revoked.length, 1)

const hung = fixture()
hung.feed.start(); hung.feed.update(document, "large", "engaged"); hung.tick()
hung.requests[0].resolve({ ok: true, status: 200, headers: { get: () => "image/png" }, blob: () => new Promise(() => {}) })
await flush()
hung.tick(); await flush()
assert.equal(hung.updates.at(-1).status, "unavailable", "body reads have a deadline even when abort is ignored")
hung.tick(); hung.tick()
assert.equal(hung.requests.length, 2, "a timed-out preview recovers automatically")
await hung.reply(1)
assert.equal(hung.updates.at(-1).status, "ready")
hung.feed.stop()
