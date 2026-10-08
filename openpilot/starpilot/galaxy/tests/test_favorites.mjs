import assert from "node:assert/strict"
import { FavoritesFeed, FavoritesPage, validFavorites } from "../web/js/favorites.js"
import { SettingsPage, SETTINGS_SECTIONS } from "../web/js/settings.js"

const BOOKMARK = "__starpilot_controller_action__:bookmark"
const SET_SPEED = "__starpilot_controller_action__:set_speed"
const empty = () => ({ enabled: false, show_onroad: false, key: null, label: "" })
const snapshot = () => ({ revision: "source-1", editable: true, valid: true, slots: [empty(), empty(), empty()],
  options: [{ key: BOOKMARK, label: "Bookmark", kind: "action", section: "Actions", available: false, reason: "Use on device" },
    { key: "RainbowPath", label: "Rainbow Road", kind: "toggle", section: "Visual", available: false, reason: "Parked only" }],
  states: [0, 1, 2].map((index) => ({ index, kind: "action", stateLabel: "Not assigned", available: false, reason: "Choose a control" })) })
const copy = (data) => JSON.parse(JSON.stringify(data))
const flush = async () => { for (let i = 0; i < 10; i++) await Promise.resolve() }

function fixture() {
  const requests = [], updates = [], timers = new Map(); let timer = 0, unauthorized = 0
  const feed = new FavoritesFeed({ publish: (value) => updates.push(value), unauthorized: () => { unauthorized++ },
    fetcher: (url, options) => new Promise((resolve) => requests.push({ url, options, resolve })),
    later: (fn) => { timers.set(++timer, fn); return timer }, cancelTimer: (id) => timers.delete(id) })
  async function reply(index, body = snapshot(), status = 200) {
    requests[index].resolve({ ok: status === 200, status, json: async () => body }); await flush()
  }
  return { feed, requests, updates, timers, reply, get unauthorized() { return unauthorized } }
}

assert.equal(validFavorites(snapshot()), true)
assert.equal(validFavorites({ ...snapshot(), slots: [] }), false)
assert.equal(validFavorites({ ...snapshot(), editable: "yes" }), false)
assert.equal(validFavorites({ ...snapshot(), states: [] }), false)
const duplicate = snapshot(); duplicate.options.push(duplicate.options[0]); assert.equal(validFavorites(duplicate), false)

const normal = fixture(); normal.feed.start(); await normal.reply(0)
assert.equal(normal.requests[0].url, "./api/favorites/slots")
normal.feed.update(0, { key: "arbitrary" }); assert.equal(normal.requests.length, 1)
normal.feed.update(0, { key: BOOKMARK })
normal.feed.load(); normal.feed.update(1, { key: "RainbowPath" })
assert.equal(normal.requests.length, 2)
let body = JSON.parse(normal.requests[1].options.body)
assert.equal(normal.requests[1].options.method, "POST")
assert.equal(normal.requests[1].options.credentials, "same-origin")
assert.equal(body.revision, "source-1")
assert.deepEqual(body.slots[0], { enabled: false, show_onroad: false, key: BOOKMARK, label: "Bookmark" })
assert.deepEqual(body.slots[1], empty())
assert.equal(normal.feed.data.slots[0].key, null) // No optimistic activation or overwrite of saved state.
await normal.reply(1, { ...snapshot(), slots: body.slots, revision: "source-2" })
normal.feed.update(0, { enabled: true }); body = JSON.parse(normal.requests[2].options.body)
assert.equal(body.revision, "source-2")
assert.equal(body.slots[0].enabled, true)
await normal.reply(2, { ...snapshot(), slots: body.slots, revision: "source-3" })
normal.feed.update(0, { show_onroad: true }); body = JSON.parse(normal.requests[3].options.body)
assert.equal(body.slots[0].show_onroad, true)
assert.ok(normal.requests.every(({ url }) => url === "./api/favorites/slots")) // Configuration has no action endpoint.
await normal.reply(3, { ...snapshot(), slots: body.slots, revision: "source-4" })
normal.feed.update(0, { key: null }); body = JSON.parse(normal.requests[4].options.body)
assert.deepEqual(body.slots[0], empty())

const legacy = fixture(); legacy.feed.start()
const data = snapshot(); data.slots[1] = { enabled: true, show_onroad: true, key: SET_SPEED, label: "45 mph", value: 45 }
await legacy.reply(0, data)
legacy.feed.update(0, { key: BOOKMARK }); body = JSON.parse(legacy.requests[1].options.body)
assert.deepEqual(body.slots[1], data.slots[1])
await legacy.reply(1, { ...data, slots: body.slots })
legacy.feed.update(1, { key: "RainbowPath" }); body = JSON.parse(legacy.requests[2].options.body)
assert.equal(Object.hasOwn(body.slots[1], "value"), false)
assert.equal(body.slots[1].label, "Rainbow Road")

const speedData = () => {
  const data = snapshot()
  data.options.push({ key: SET_SPEED, label: "Set Speed To", kind: "action", section: "Driving", available: false, reason: "Use on device" })
  data.slots[0] = { enabled: true, show_onroad: false, key: SET_SPEED, label: "Cruise", value: 30 }
  data.slots[1] = { enabled: false, show_onroad: true, key: "OldUnsupportedSetting", label: "Keep me" }
  data.slots[2] = { enabled: true, show_onroad: true, key: SET_SPEED, label: "Other speed", value: 55 }
  return data
}
const speed = fixture(); speed.feed.start(); await speed.reply(0, speedData())
const speedBefore = copy(speed.feed.data)
FavoritesPage.methods.speed.call({ feed: speed.feed }, 0, { target: { value: "45" } })
assert.equal(speed.requests.length, 2, "The speed field must submit its changed value")
body = JSON.parse(speed.requests[1].options.body)
assert.deepEqual(body, { revision: "source-1", slots: [{ ...speedBefore.slots[0], value: 45 }, ...speedBefore.slots.slice(1)] })
assert.equal(speed.requests[1].options.method, "POST")
assert.equal(speed.requests[1].options.credentials, "same-origin")
assert.deepEqual(speed.feed.data, speedBefore) // Wait for confirmation, including speed edits.
speed.feed.update(0, { value: 60 }); assert.equal(speed.requests.length, 2) // Only one write in flight.
const speedSaved = { ...speedBefore, slots: body.slots, revision: "speed-saved" }
await speed.reply(1, speedSaved)
assert.equal(speed.feed.data.slots[0].value, 45)
speed.feed.load(); await speed.reply(2, speedSaved)
assert.equal(speed.feed.data.slots[0].value, 45) // A subsequent read retains the saved target.

for (const value of [undefined, null, "45", true, NaN, Infinity, -Infinity, 4, 146]) {
  speed.feed.update(0, { value })
  assert.equal(speed.requests.length, 3, "Invalid speed patches must not send a request")
}
speed.feed.update(1, { value: 45 }); speed.feed.update(0, { value: 45, arbitrary: true })
assert.equal(speed.requests.length, 3) // Values belong only to Set Speed; unknown fields stay blocked.
for (const value of [5, 145, 45.5]) {
  const bounded = fixture(); bounded.feed.start(); await bounded.reply(0, speedData())
  bounded.feed.update(0, { value })
  assert.equal(JSON.parse(bounded.requests[1].options.body).slots[0].value, value)
  await bounded.reply(1, { ...speedData(), slots: JSON.parse(bounded.requests[1].options.body).slots })
}
const readonlySpeed = fixture(); readonlySpeed.feed.start(); await readonlySpeed.reply(0, { ...speedData(), editable: false })
readonlySpeed.feed.update(0, { value: 45 }); assert.equal(readonlySpeed.requests.length, 1)

const staleSpeed = fixture(); staleSpeed.feed.start(); await staleSpeed.reply(0, speedData())
staleSpeed.feed.update(0, { value: 45 }); await staleSpeed.reply(1, {}, 409)
assert.equal(staleSpeed.feed.data.slots[0].value, 30)
assert.equal(staleSpeed.feed.needsReload, true)
staleSpeed.feed.update(0, { value: 60 }); assert.equal(staleSpeed.requests.length, 2)
const speedTimeout = fixture(); speedTimeout.feed.start(); await speedTimeout.reply(0, speedData())
speedTimeout.feed.update(0, { value: 45 }); speedTimeout.timers.get(speedTimeout.feed.timer)()
assert.equal(speedTimeout.requests[1].options.signal.aborted, true)
await speedTimeout.reply(1, speedSaved)
assert.equal(speedTimeout.feed.data.slots[0].value, 30)
assert.equal(speedTimeout.feed.needsReload, true)

for (const status of [409, 503, 400]) {
  const failed = fixture(); failed.feed.start(); await failed.reply(0)
  failed.feed.update(0, { key: BOOKMARK }); await failed.reply(1, {}, status)
  assert.equal(failed.feed.data.slots[0].key, null)
  assert.equal(failed.feed.needsReload, true)
  failed.feed.update(1, { key: BOOKMARK }); assert.equal(failed.requests.length, 2)
  failed.feed.load(); await failed.reply(2)
  assert.equal(failed.feed.needsReload, false)
}
const timeout = fixture(); timeout.feed.start(); await timeout.reply(0); timeout.feed.update(0, { key: BOOKMARK })
const expire = timeout.timers.get(timeout.feed.timer); expire()
assert.equal(timeout.requests[1].options.signal.aborted, true)
assert.match(timeout.updates.at(-1).error, /Reload to check/)
await timeout.reply(1); assert.equal(timeout.feed.needsReload, true)
const retired = fixture(); retired.feed.start(); retired.feed.stop(); await retired.reply(0)
assert.equal(retired.feed.data, null)
const auth = fixture(); auth.feed.start(); await auth.reply(0, {}, 401); assert.equal(auth.unauthorized, 1)

const calls = [], vm = { state: { data: snapshot() }, feed: { update: (index, patch) => calls.push({ index, patch }) } }
const event = { target: { checked: true } }
FavoritesPage.methods.toggle.call(vm, 0, "enabled", event)
assert.equal(event.target.checked, false)
assert.deepEqual(calls, [{ index: 0, patch: { enabled: true } }])
const visual = SETTINGS_SECTIONS.find(({ id }) => id === "visual")
const rows = SettingsPage.computed.visibleRows.call({ initialPage: "hub", activeSection: visual, state: { data: { page: "hub" }, query: "" } })
assert.equal(rows.filter(({ row }) => row.page === "favorites").length, 1)
const host = { state: {}, feed: { stop() {}, load() { assert.fail("Favorites is not a generic settings page") }, start() {} } }
SettingsPage.methods.open.call(host, "favorites"); assert.equal(host.state.favoritesOpen, true)
SettingsPage.methods.closeFavorites.call(host); assert.equal(host.state.section, "visual")
console.log("Favorites: speed save/readback/validation, exact slot edits, legacy preservation, no activation, races/errors/timeouts/auth, modern switch and Visual navigation passed")
