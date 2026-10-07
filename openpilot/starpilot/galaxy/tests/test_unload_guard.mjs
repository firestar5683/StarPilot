import assert from "node:assert/strict"
import { guardUnload } from "../web/js/unload-guard.js"

globalThis.window = new EventTarget()
let dirty = true
const stop = guardUnload(() => dirty)
const attempt = () => {
  const event = new Event("beforeunload", { cancelable: true })
  // Browsers expose a writable returnValue on BeforeUnloadEvent; Node's Event does not.
  Object.defineProperty(event, "returnValue", { value: "", writable: true })
  return window.dispatchEvent(event)
}
assert.equal(attempt(), false, "Live reload must defer while a draft is dirty")
dirty = false
assert.equal(attempt(), true, "Saving or discarding allows the pending reload")
dirty = true
stop()
assert.equal(attempt(), true, "An unmounted page must release its guard")
console.log("Unsaved draft unload guard passed")
