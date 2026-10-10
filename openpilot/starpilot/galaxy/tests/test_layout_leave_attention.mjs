import assert from "node:assert/strict"
import { OnroadLayoutPage } from "../web/js/onroad-layout.js"

for (const projection of [false, true]) {
  assert.equal(OnroadLayoutPage.computed.inlineLeavePrompt.call({ projection, pendingLeave: true, state: { leavePresentation: "inline" } }), true)
}
let flashes = 0
const pendingAction = () => {}
const pending = { inlineLeavePrompt: true, state: { discard: pendingAction }, flashLeavePrompt() { flashes++ } }
OnroadLayoutPage.methods.requestLeave.call(pending, () => {})
assert.equal(flashes, 1)
assert.equal(pending.state.discard, pendingAction)

const originalWindow = globalThis.window
try {
  let reduced = false, focuses = 0
  const scrolls = []
  globalThis.window = { matchMedia: () => ({ matches: reduced }) }
  const vm = { $refs: { leaveBar: {
    scrollIntoView(options) { scrolls.push(options) },
    querySelector() { return { focus(options) { assert.equal(options.preventScroll, true); focuses++ } } },
  } } }
  OnroadLayoutPage.methods.flashLeavePrompt.call(vm)
  assert.equal(scrolls.at(-1).behavior, "smooth")
  reduced = true
  OnroadLayoutPage.methods.flashLeavePrompt.call(vm)
  assert.equal(scrolls.at(-1).behavior, "instant")
  assert.equal(focuses, 2)

} finally {
  if (originalWindow === undefined) delete globalThis.window
  else globalThis.window = originalWindow
}
console.log("Layout leave attention: both targets, repeated navigation, focus restoration, reduced motion passed")
