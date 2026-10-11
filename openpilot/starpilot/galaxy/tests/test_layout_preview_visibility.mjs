import assert from "node:assert/strict"
import { OnroadLayoutPage } from "../web/js/onroad-layout.js"

const originalStorage = globalThis.localStorage
const saved = new Map()
const editor = projection => {
  const vm = { ...OnroadLayoutPage.setup({ projection, mode: "local", unauthorized() {} }), projection }
  for (const name of ["previewHidden", "togglePreviewVisibility"])
    vm[name] = OnroadLayoutPage.methods[name].bind(vm)
  return vm
}
try {
  globalThis.localStorage = { getItem: key => saved.get(key) ?? null, setItem: (key, value) => saved.set(key, value) }
  for (const projection of [false, true]) {
    const vm = editor(projection)
    assert.equal(vm.previewHidden("stopped_timer"), true)
    assert.equal(vm.previewHidden("current_speed"), false, "targets have separate preferences")
    vm.togglePreviewVisibility("stopped_timer")
    vm.togglePreviewVisibility("current_speed")
    vm.state.profile = "compact"
    vm.togglePreviewVisibility("driver_monitor")
    const reopened = editor(projection)
    assert.equal(reopened.previewHidden("stopped_timer"), false, "explicitly showing the timer survives reopening")
    assert.equal(reopened.previewHidden("current_speed"), true)
    assert.equal(reopened.previewHidden("driver_monitor"), false)
    reopened.state.profile = "compact"
    assert.equal(reopened.previewHidden("driver_monitor"), true)
    assert.equal(reopened.previewHidden("current_speed"), false, "profiles have separate preferences")
    assert.equal(reopened.state.draft, null, "visibility is independent of the saved driving layout")
  }
  const aa = editor(true)
  const before = [...saved]
  aa.togglePreviewVisibility("car_exit")
  assert.equal(aa.previewHidden("car_exit"), false)
  assert.deepEqual([...saved], before)

  for (const stored of ["broken JSON", "null", JSON.stringify({ large: [true], compact: "invalid" }),
    JSON.stringify({ large: { stopped_timer: "false", current_speed: 1 } })]) {
    globalThis.localStorage.getItem = () => stored
    const vm = editor(false)
    assert.equal(vm.previewHidden("stopped_timer"), true)
    assert.equal(vm.previewHidden("current_speed"), false)
  }
  globalThis.localStorage = {
    getItem() { throw new Error("Storage unavailable") },
    setItem() { throw new Error("Storage unavailable") },
  }
  const unavailable = editor(false)
  unavailable.togglePreviewVisibility("current_speed")
  assert.equal(unavailable.previewHidden("current_speed"), true)
} finally {
  if (originalStorage === undefined) delete globalThis.localStorage
  else globalThis.localStorage = originalStorage
}
console.log("Preview visibility: persistence, target/profile isolation, timer default, required exit and unavailable storage passed")
