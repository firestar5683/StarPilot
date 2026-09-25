import assert from "node:assert/strict"
import { createHash, webcrypto } from "node:crypto"
import { decodeLayoutBackup, encodeLayoutBackup, sha256 } from "../web/js/layout-backup.js"
import { SoftwarePage } from "../web/js/software-status.js"

const layout = { version: 4, palette: { text: "#FFFFFFFF" }, layouts: { large: {}, compact: {} } }
const encoded = await encodeLayoutBackup(layout, webcrypto)
assert.deepEqual(await decodeLayoutBackup(encoded, webcrypto), layout)
assert.deepEqual(await decodeLayoutBackup(encoded, {}), layout) // Plain HTTP has no crypto.subtle.
assert.equal(await encodeLayoutBackup(layout, {}), encoded)
for (const value of ["", "abc", "a".repeat(55), "a".repeat(56), "a".repeat(64), "a".repeat(1024),
  "Café 🚗", "x".repeat(16384)]) {
  const expected = createHash("sha256").update(value).digest("hex")
  assert.equal(await sha256(value, {}), expected)
  assert.equal(await sha256(value, webcrypto), expected)
}
assert.deepEqual(Object.keys(JSON.parse(encoded)), ["format", "version", "document", "sha256"])
assert.doesNotMatch(encoded, /calibration|credential|model/i)

for (const invalid of [
  encoded.replace("#FFFFFFFF", "#000000FF"),
  encoded.replace('"version":1', '"version":2'),
  encoded.replace('"sha256":', '"extra":1,"sha256":'),
  encoded.trimEnd(),
  "x".repeat(32769),
]) {
  await assert.rejects(decodeLayoutBackup(invalid, webcrypto))
}

// The page obtains a fresh revision immediately before the existing owner performs the restore.
const calls = []
const context = { layoutDraft: layout, layoutBusy: false, layoutNotice: "", layoutError: "",
  layoutRequest: async (...args) => {
    calls.push(args)
    return args.length ? { valid: true } : { editable: true, revision: "current-revision" }
  } }
await SoftwarePage.methods.restoreLayout.call(context)
assert.deepEqual(calls, [[], [layout, "current-revision"]])
assert.equal(context.layoutNotice, "Visual layout restored.")
assert.equal(context.layoutDraft, null)

let writes = 0
const moving = { layoutDraft: layout, layoutBusy: false, layoutNotice: "", layoutError: "",
  layoutRequest: async () => { writes++; return { editable: false, revision: "old" } } }
await SoftwarePage.methods.restoreLayout.call(moving)
assert.equal(writes, 1)
assert.match(moving.layoutError, /Park/)

console.log("visual layout backup checks passed")
