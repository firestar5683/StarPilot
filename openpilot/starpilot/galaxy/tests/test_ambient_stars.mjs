import assert from "node:assert/strict"
import { test } from "node:test"
import { spawnAmbientStars } from "../web/js/ambient-stars.js"

test("ambient stars populate the decorative layer once without changing app content", () => {
  const children = []
  const background = {
    ownerDocument: { createElement: (tag) => ({ tag, style: {} }) },
    querySelector: () => children.find((child) => child.className === "galaxy-hero") || null,
    appendChild: (child) => children.push(child),
  }
  assert.equal(spawnAmbientStars(background, () => 0.5), 14)
  assert.equal(children.length, 14)
  assert.deepEqual(children[0], { tag: "i", className: "galaxy-hero",
    style: { left: "50.00%", top: "50.00%", animationDelay: "2.00s", width: "2px", height: "2px" } })
  assert.equal(spawnAmbientStars(background, () => 0), 0)
  assert.equal(children.length, 14)
  assert.equal(spawnAmbientStars(null), 0)
})
