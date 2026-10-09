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
  let reduced = false, canceled = 0, animations = 0
  const scrolls = []
  globalThis.window = { matchMedia: () => ({ matches: reduced }) }
  const vm = { $refs: { leaveBar: {
    scrollIntoView(options) { scrolls.push(options) },
    animate(frames, options) {
      animations++
      assert.equal(options.duration, 750)
      assert.equal(frames.length, 3)
      return { cancel() { canceled++ } }
    },
  } } }
  OnroadLayoutPage.methods.flashLeavePrompt.call(vm)
  OnroadLayoutPage.methods.flashLeavePrompt.call(vm)
  assert.equal(animations, 2)
  assert.equal(canceled, 1)
  reduced = true
  OnroadLayoutPage.methods.flashLeavePrompt.call(vm)
  assert.equal(animations, 2, "reduced motion does not animate")
  assert.equal(scrolls.at(-1).behavior, "instant")
} finally {
  if (originalWindow === undefined) delete globalThis.window
  else globalThis.window = originalWindow
}
console.log("Layout leave attention: both targets, repeated navigation, restarted pulse, reduced motion passed")
