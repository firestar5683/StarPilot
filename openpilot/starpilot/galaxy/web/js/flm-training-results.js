const text = (value, limit = 240) => typeof value === "string" && value.length <= limit
const count = value => value === null || Number.isSafeInteger(value) && value >= 0
const detailValue = (value, depth = 0) => value === null || typeof value === "boolean" ||
  typeof value === "number" && Number.isFinite(value) || text(value, 500) ||
  depth < 2 && (Array.isArray(value) ? value.length <= 16 && value.every(item => detailValue(item, depth + 1)) :
    value && typeof value === "object" && Object.keys(value).length <= 64 &&
    Object.entries(value).every(([key, item]) => text(key, 80) && detailValue(item, depth + 1)))
export function validTrainingResults(value) {
  if (!value || value.version !== 1 || !Array.isArray(value.history) || value.history.length > 20) return false
  if (!value.history.every(row => row && text(row.time, 80) && text(row.status, 64) && text(row.reason) && typeof row.applied === "boolean")) return false
  const row = value.current
  if (row === null) return true
  if (!row || typeof row.fresh !== "boolean" || !Number.isFinite(row.ageSeconds) || row.ageSeconds < 0 ||
      ![true, false, null].includes(row.enabled) || !text(row.status, 64) || !text(row.reason) || !row.progress ||
      ![row.progress.samples, row.progress.blocks, row.progress.requiredBlocks].every(count)) return false
  if (row.fit !== null && (!row.fit || !text(row.fit.status, 64) || !text(row.fit.reason) ||
      ![row.fit.trainWindows, row.fit.heldoutWindows].every(count))) return false
  if (row.application !== null && (!row.application || typeof row.application.applied !== "boolean" || !text(row.application.reason))) return false
  return row.details === undefined || row.details && typeof row.details === "object" && !Array.isArray(row.details) &&
    Object.keys(row.details).length <= 64 && Object.entries(row.details).every(([key, item]) => text(key, 80) &&
      (["Full surface coordinates", "Actual full surface coordinates"].includes(key) ?
        fullCoordinates(item) !== null : detailValue(item)))
}
const labels = { collecting: "Gathering driving examples", unavailable: "Waiting for usable driving data",
  qualifiedFit: "Fit passed validation", qualified: "Fit passed validation", rejected: "Fit did not pass validation",
  fitting: "Evaluating a possible adjustment", applied: "Adjustment applied",
  independent_evidence: "Gathering independently measured driving examples",
  settings_receipt_expired: "Learning paused because its settings confirmation expired",
  no_current_controller_evidence: "Waiting for current steering measurements",
  capturing_steering_evidence: "Recording eligible steering measurements",
  awaiting_different_maneuver: "Current maneuver captured; waiting for a different driving example",
  evaluating_collected_maneuvers: "Checking the collected driving examples",
  whole_physical_event_support: "Too few complete independent event bundles for fitting",
  whole_event_export_support: "Too few complete bundles fit the replay export budget",
  event_storage_packet_support: "Waiting for enough retained storage packets",
  snapshot_context_changed: "Collection context or objective changed; waiting for its next snapshot selection",
  snapshot_preparing: "Complete bundles selected; export is not complete",
  snapshot_not_attempted: "No snapshot selection has run for this collection context",
  snapshot_ready: "Snapshot selected; child qualification is still required",
  no_current_collection_context: "Waiting for a current collection context",
  no_current_physical_context: "Waiting for a current physical context",
  unchanged_storage_since_submission: "Waiting for new storage after the submitted fit",
  event_snapshot_unavailable: "The snapshot could not be prepared",
  report_stale: "Current results are unavailable; this is an earlier report" }
export const readable = value => labels[value] || String(value ?? "Not reported").replaceAll("_", " ")
export const detailText = value => value === null ? "Not reported" : Array.isArray(value) ? value.map(detailText).join(", ") :
  typeof value === "boolean" ? value ? "Yes" : "No" : typeof value === "object" ?
    Object.entries(value).map(([key, item]) => `${readable(key)}: ${detailText(item)}`).join("; ") : String(value)
export const trainingSummary = (report, error = "") => error ? "Live update unavailable. Previous results may be out of date." :
  !report?.current ? "No training results have been reported yet." : !report.current.fresh ?
    "Saved report only. Current learning and application are unknown." : readable(report.current.status)

// Exact canonical order from canonical_surface_adapter.NAMES; no controller imports.
export const SURFACE_NAMES = Object.freeze([
  "ff_gain_left",
  "ff_gain_right",
  "turn_in_boost_left",
  "turn_in_boost_right",
  "unwind_taper_left",
  "unwind_taper_right",
  "center_taper_max",
  "highway_center_taper_max",
  "center_deadband_crawl_deg",
  "center_deadband_low_deg",
  "center_deadband_mid_deg",
  "center_deadband_fast_deg",
  "center_deadband_highway_deg",
  "turn_in_threshold_reduction_left",
  "turn_in_threshold_reduction_right",
  "unwind_threshold_increase_left",
  "unwind_threshold_increase_right",
  "crawl_turn_in_ff_boost_left",
  "crawl_turn_in_ff_boost_right",
  "low_speed_angle_assist_max_torque",
  "curvy_speed_min",
  "curvy_speed_max",
  "curvy_turn_in_trim_speed_min",
  "curvy_turn_in_trim_speed_max",
  "curvy_turn_in_trim_left",
  "curvy_turn_in_trim_right",
  "curvy_unwind_floor_relief_left",
  "curvy_unwind_floor_relief_right",
  "curvy_unwind_extra_reduction_left",
  "curvy_unwind_extra_reduction_right"
])
export const PID_UNSUPPORTED = Object.freeze([
  "turn_in_threshold_reduction_left", "turn_in_threshold_reduction_right",
  "unwind_threshold_increase_left", "unwind_threshold_increase_right",
])
export function fullCoordinates(rows) {
  if (!Array.isArray(rows) || rows.length !== SURFACE_NAMES.length || rows.some((row, i) =>
    !Array.isArray(row) || row.length !== 2 || row[0] !== SURFACE_NAMES[i] ||
    typeof row[1] !== "number" || !Number.isFinite(row[1]) || Math.abs(row[1]) > .25)) return null
  return Object.fromEntries(rows)
}
export function surfaceRows(report, live = false) {
  const details = report?.current?.details || {}
  const learned = fullCoordinates(details["Full surface coordinates"])
  const applied = live && report.current?.application?.applied === true ?
    fullCoordinates(details["Actual full surface coordinates"]) : null
  return SURFACE_NAMES.map(name => ({ name, baseline: 0, learned: learned?.[name] ?? null,
    applied: applied?.[name] ?? null, pidSupported: !PID_UNSUPPORTED.includes(name) }))
}
export const coordinateText = value => value === null ? "Not reported" :
  value === 0 ? "0" : Math.abs(value) < 1e-6 ? value.toExponential(3) : (value > 0 ? "+" : "") + value.toFixed(6).replace(/0+$/, "").replace(/\.$/, "")
