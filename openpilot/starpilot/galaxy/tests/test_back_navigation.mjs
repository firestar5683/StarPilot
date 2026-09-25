import assert from "node:assert/strict"
import { SettingsPage } from "../web/js/settings.js"
import { OnroadLayoutPage } from "../web/js/onroad-layout.js"

const listeners = new Map()
globalThis.window = { scrollTo() {}, addEventListener(name, callback) { listeners.set(name, callback) } }
let current = new URL("https://galaxy.test/app#/cameras/pip")
globalThis.location = { get hash() { return current.hash }, pathname: "/app", search: "" }
const entries = [{ url: current.href, state: null }]
let cursor = 0
globalThis.history = {
  get state() { return entries[cursor].state },
  replaceState(state, _title, url) { current = new URL(url, current); entries[cursor] = { state, url: current.href } },
  pushState(state, _title, url) { entries.splice(cursor + 1); current = new URL(url, current); entries.push({ state, url: current.href }); cursor++ },
  go(delta) { if (cursor + delta >= 0 && cursor + delta < entries.length) { cursor += delta; current = new URL(entries[cursor].url); listeners.get("popstate")() } },
  back() { if (cursor > 0) { cursor--; current = new URL(entries[cursor].url); listeners.get("popstate")() } },
  forward() { if (cursor < entries.length - 1) { cursor++; current = new URL(entries[cursor].url); listeners.get("popstate")() } },
}
const { route, navigate, navigateBack, startRouter } = await import("../web/js/router.js")
startRouter()
navigateBack()
assert.equal(route.path, "/") // A direct link cannot navigate outside Galaxy.
navigate("/settings"); navigate("/appearance"); navigate("/theme_maker")
navigateBack(); assert.equal(route.path, "/appearance")
navigateBack(); assert.equal(route.path, "/settings")
history.forward(); assert.equal(route.path, "/appearance")
navigate("/cameras"); navigate("/cameras/pip")
navigateBack(); assert.equal(route.path, "/cameras")
const length = entries.length
navigate("/cameras"); assert.equal(entries.length, length)

let returned = 0, cancelled = 0
const settings = { busy: false, state: { data: { page: "standard/following" } }, initialPage: "hub", atSectionRoot: false,
  back() { returned++ }, feed: { cancel() { cancelled++ } } }
assert.equal(SettingsPage.methods.navigateBack.call(settings), true)
assert.equal(returned, 1)
settings.atSectionRoot = true
assert.equal(SettingsPage.methods.navigateBack.call(settings), false)
settings.state.pending = {}; settings.busy = true
assert.equal(SettingsPage.methods.navigateBack.call(settings), true)
assert.equal(cancelled, 1)

let closed = 0
const editor = { busy: false, dirty: true, state: { drag: null, discard: null },
  leave: OnroadLayoutPage.methods.leave, hideDevicePreview() {}, $emit(event) { if (event === "close") closed++ } }
settings.state = { layoutOpen: true }; settings.busy = false
settings.$refs = { layoutEditor: { requestLeave(action) { OnroadLayoutPage.methods.requestLeave.call(editor, action) } } }
assert.equal(SettingsPage.methods.navigateBack.call(settings), true)
assert.equal(editor.state.discard, "back"); assert.equal(closed, 0)
editor.state.discard = null // Cancel discard keeps the editor.
assert.equal(closed, 0)
editor.leave("back"); assert.equal(closed, 1)
console.log("Galaxy Back history and editor guard passed")

// Parent is the page actually visited, not a guessed personality parent.
const nested = { initialPage: 'hub', state: { section: 'longitudinal', query: '', parents: [], data: {page: 'hub'} },
  activeSection: {id: 'longitudinal'}, feed: {load(page) { nested.state.data = {page} }} }
SettingsPage.methods.open.call(nested, 'profiles')
SettingsPage.methods.back.call(nested)
assert.equal(nested.state.data.page, 'hub')
SettingsPage.methods.open.call(nested, 'standard')
SettingsPage.methods.open.call(nested, 'standard/following')
SettingsPage.methods.back.call(nested)
assert.equal(nested.state.data.page, 'standard')
SettingsPage.methods.back.call(nested)
assert.equal(nested.state.data.page, 'hub', 'direct personality returns to Longitudinal hub')
SettingsPage.methods.open.call(nested, 'profiles')
SettingsPage.methods.open.call(nested, 'standard')
SettingsPage.methods.back.call(nested)
assert.equal(nested.state.data.page, 'profiles', 'personality opened through planner returns there')
SettingsPage.methods.selectSection.call({...nested,busy:false,feed:{active:true,load(){}}}, {id:'wheel',pages:['wheel']})
assert.deepEqual(nested.state.parents, [], 'changing sections retires nested history')

nested.initialPage = 'profiles'; nested.state.data = {page:'profiles'}
SettingsPage.methods.open.call(nested,'standard')
SettingsPage.methods.open.call(nested,'standard/following')
SettingsPage.methods.back.call(nested)
assert.equal(nested.state.data.page,'standard','dedicated tools also retain each nested parent')
SettingsPage.methods.back.call(nested)
assert.equal(nested.state.data.page,'profiles')
