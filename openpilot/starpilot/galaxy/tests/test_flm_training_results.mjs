import assert from "node:assert/strict"
import { validTrainingResults, trainingSummary, detailText } from "../web/js/flm-training-results.js"

const report = () => ({ version: 1, current: { fresh: true, ageSeconds: .1, enabled: true,
  status: "collecting", reason: "independent_evidence", progress: { samples: 140, blocks: 3, requiredBlocks: 16 },
  fit: null, application: { applied: false, reason: "No fit has passed validation" },
  details: { accepted_samples: 140, rejected_reasons: { steering_override: 4 }, coordinates: [0, 0] } }, history: [] })
assert(validTrainingResults(report()))
const counters = report(); counters.current.details.rejected_reasons = Object.fromEntries(Array.from({ length: 24 }, (_, i) => [`reason_${i}`, i]))
assert(validTrainingResults(counters))
assert(validTrainingResults({ version: 1, current: null, history: [] }))
const missing = report(); missing.current.progress.samples = null
assert(validTrainingResults(missing))
assert.equal(detailText(null), "Not reported")
assert.equal(detailText({ steering_override: 4 }), "steering override: 4")
assert.match(trainingSummary({ version: 1, current: null, history: [] }), /No training results/)
const stale = report(); stale.current.fresh = false
assert.match(trainingSummary(stale), /Saved report only/)
assert.match(trainingSummary(report(), "Disconnected"), /out of date/)
for (const mutate of [value => value.current.progress.blocks = -1,
  value => value.current.ageSeconds = Infinity, value => value.current.fit = { status: "rejected", reason: "x" },
  value => value.history = Array.from({ length: 21 }, () => ({ time: "now", status: "collecting", reason: "x", applied: false })),
  value => value.current.details = { invalid: { nested: { deeper: { too_deep: true } } } }]) {
  const value = report(); mutate(value); assert(!validTrainingResults(value))
}
console.log("Training wire validation, bounded details and stale/no-data labels passed")
