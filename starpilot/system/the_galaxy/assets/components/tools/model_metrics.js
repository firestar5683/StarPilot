// Statistics presentation only; no telemetry or settings writes.
const METRES_PER_MILE = 1609.344;
function distance(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
}
function count(value) {
  return Number.isSafeInteger(value) && value >= 0 ? value : null;
}
export function milesText(metres) {
  const value = distance(metres);
  if (value === null) return "—";
  return `${(value / METRES_PER_MILE).toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1})} mi`;
}
function eventMetric(stats, metresKey, countKey) {
  if (stats?.eventRatesComparable === false) return '—';
  const metres = distance(stats?.[metresKey]);
  const events = count(stats?.[countKey]);
  if (metres === null || events === null) return "—";
  if (events === 0) return metres > 0 ? `No events · ${milesText(metres)}` : "—";
  return `${milesText(metres / events)} · ${events.toLocaleString()} ${events === 1 ? "event" : "events"}`;
}
// Cards omit unused/invalid metrics; history retains its fixed columns.
export function visibleDrivingMetrics(model) {
  const stats = model?.stats?.available === true ? model.stats : null;
  const fields = ["assistedMeters", "interventionMeters", "disengagementMeters"];
  return drivingMetrics(model).filter((metric, index) =>
    distance(stats?.[fields[index]]) > 0 && metric.value !== "—");
}
export function drivingMetrics(model) {
  const stats = model?.stats?.available === true ? model.stats : null;
  return [
    { label: "Assisted distance", value: milesText(stats?.assistedMeters), primary: true },
    { label: "Avg mi / intervention", value: eventMetric(stats, "interventionMeters", "interventions") },
    { label: "Avg mi / disengagement", value: eventMetric(stats, "disengagementMeters", "disengagements") },
  ];
}
export function trackingStatus(model) {
  const stats = model?.stats;
  if (!stats) return "Not tracked yet";
  if (stats.trackingStatus === "resource_limited") return "Tracking limited — coverage lost";
  if (["unavailable", "telemetry_unavailable"].includes(stats.trackingStatus)) return "Tracking unavailable";
  if (stats.available !== true) return stats.status === "not_started" ? "Not tracked yet" : "Statistics unavailable";
  if (stats.eventRatesComparable === false) return stats.definitionStatus === 'mixed'
    ? 'Mixed measurement definitions — event averages unavailable' : 'Unknown measurement definitions — event averages unavailable';
  if (stats.definitionStatus === 'historical') return `Historical measurement definition v${stats.definitionVersion} — excluded from current event rankings`;
  if (stats.assistedMeters === 0 && stats.interventions === 0 && stats.disengagements === 0) return stats.usedInPairs ? "Recorded in Model Lab pairs" : "Not driven yet";
  return stats.incomplete ? "Partial coverage — tracking gaps" : stats.trackingStatus === "inactive" ? "Tracking inactive" : "";
}
export function metricSortValue(model, mode) {
  const stats = model?.stats;
  if (stats?.available !== true) return null;
  if (mode === "distance") return distance(stats.assistedMeters);
  if (stats.eventRatesComparable === false || stats.definitionStatus === 'historical') return null;
  const key = mode === "interventions" ? "interventions" : "disengagements";
  const exposure = distance(stats[mode === "interventions" ? "interventionMeters" : "disengagementMeters"]);
  const events = count(stats[key]);
  return exposure !== null && events > 0 ? exposure / events : null;
}
export async function readModelHistory(model, offset = 0, period = 'all', mode = 'all') {
  const response = await fetch(`/api/models/stats?model=${encodeURIComponent(model)}&limit=20&offset=${offset}&period=${encodeURIComponent(period)}&mode=${encodeURIComponent(mode)}`);
  if (!response.ok) throw new Error("Drive history unavailable");
  const data = await response.json();
  if (data.available !== true && data.status !== "not_started") throw new Error("Drive history unavailable");
  return { rows: Array.isArray(data.history) ? data.history : [], more: data.hasMore === true };
}
function definitionLabel(stats) {
  if (stats?.eventRatesComparable === false) return ` · ${stats.definitionStatus === 'mixed' ? 'Mixed' : 'Unknown'} measurement definitions`;
  if (stats?.definitionVersion) return ` · Definition v${stats.definitionVersion} (${stats.interventionReleaseSeconds} s rearm)`;
  return '';
}
export function historyRow(entry) {
  const timestamp = typeof entry.started === "number" ? new Date(entry.started * 1000) : null;
  const date = timestamp && Number.isFinite(timestamp.getTime()) ? timestamp.toLocaleString() : "Date unavailable";
  const roles = entry.identity?.roles || [];
  const configuration = roles.map(role => `${role.modelId} (${role.backend}) · ${role.artifactVerified ? 'Revision' : 'Unverified load'} ${role.artifact || 'unknown'}`).join(" + ");
  const mode = entry.mode === "aol" ? "Lateral only" : "Assistance";
  const metrics = drivingMetrics({stats:entry.stats});
  const gaps = count(entry.gaps) ?? 0;
  const coverage = gaps > 0 ? ` · ${gaps} tracking gap${gaps === 1 ? '' : 's'}` : entry.stats?.incomplete ? " · Incomplete telemetry" : "";
  return {
    title: `${date} · ${mode}${entry.complete ? "" : " · Open/incomplete"}${coverage}`,
    configuration: `${configuration}${definitionLabel(entry.stats)}`,
    counts: `Steering ${count(entry.stats?.steering) ?? '—'} · Brake ${count(entry.stats?.brake) ?? '—'} · Accelerator ${count(entry.stats?.gas) ?? '—'}`,
    values: `${metrics[0].value} · ${metrics[1].value} / intervention · ${metrics[2].value} / disengagement`,
  };
}
export function compareMetrics(a, b, mode) {
  const left = metricSortValue(a, mode), right = metricSortValue(b, mode);
  if (left === null) return right === null ? 0 : 1;
  if (right === null) return -1;
  return right - left;
}

// New Galaxy card presentation; preserve detailed history/Home formatting.
export function modelManagerMetrics(model, engagement) {
  const stats = model?.stats?.available === true ? model.stats : null;
  if (!(distance(stats?.assistedMeters) > 0) && !(engagement?.durationSeconds > 0)) return [];
  const percent = engagement?.measurementScope === 'runtime_intervals' && typeof engagement?.percent === 'number' && Number.isFinite(engagement.percent)
    && engagement.percent >= 0 && engagement.percent <= 100 && engagement.durationSeconds > 0
    ? `${engagement.percent.toLocaleString(undefined, {maximumFractionDigits: 1})}%` : '—';
  const average = (metresKey, countKey) => {
    if (stats?.eventRatesComparable === false) return '—';
    const metres = distance(stats?.[metresKey]), events = count(stats?.[countKey]);
    return metres !== null && events > 0 ? milesText(metres / events) : '—';
  };
  return [
    {label: 'Assisted distance', value: milesText(stats?.assistedMeters), primary: true},
    {label: 'Engage percentage', value: percent, description: 'Measured engagement over verified recorded intervals for this model. Partial coverage: missing telemetry, model switches and Model Lab pairs are excluded; older routes may be unavailable.'},
    {label: 'Avg mi / intervention', value: average('interventionMeters', 'interventions')},
    {label: 'Avg mi / disengagement', value: average('disengagementMeters', 'disengagements')},
  ];
}
