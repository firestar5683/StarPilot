// Read-only association of recorded model-stat fragments with dashboard drives.
// Prefer recorded route IDs. Legacy fragments allow at most two seconds of
// boundary skew, with a unique overlapping route; missing coverage stays unknown.
export function driveEventCounts(drives, history) {
  const unknown = () => ({ interventions: null, disengagements: null, partial: false });
  const result = drives.map(unknown);
  if (history?.available !== true || !Array.isArray(history.history)) return result;
  const rowsToMatch = Array.isArray(history.driveSummaries) ? history.driveSummaries : history.history;
  const hasMore = Array.isArray(history.driveSummaries) ? history.driveSummariesHasMore : history.hasMore;
  const windows = drives.map(d => [Date.parse(d.date) / 1000, Date.parse(d.endDate) / 1000]);
  const groups = new Map();
  for (const row of rowsToMatch) {
    if (!row?.drive) return result;
    if (!groups.has(row.drive)) groups.set(row.drive, []);
    groups.get(row.drive).push(row);
  }
  const oldest = Math.min(...rowsToMatch.map(r => r.started));
  const blocked = new Set();
  for (const rows of groups.values()) {
    const first = rows[0];
    const start = first.started, end = first.updated;
    if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return drives.map(unknown);
    const overlaps = windows.flatMap(([a, b], i) => Number.isFinite(a) && b > a && start < b && end > a ? [i] : []);
    const exact = first.routeName ? drives.flatMap((d, i) =>
      [d.name, ...(d.routeNames || [])].includes(first.routeName) ? [i] : []) : [];
    const index = first.routeName ? exact[0] : overlaps[0];
    const matched = first.routeName ? exact.length === 1 : overlaps.length === 1
      && start >= windows[index][0] - 2 && end <= windows[index][1] + 2;
    if (!matched) { overlaps.forEach(i => blocked.add(i)); continue; }
    // Pagination can cut off more fragments belonging to this same route.
    if (hasMore && windows[index][0] <= oldest + 2) { blocked.add(index); continue; }
    const valid = rows.every(r => r.started === start && r.updated === end && r.routeName === first.routeName && r.stats?.available === true
      && ['interventions', 'disengagements'].every(k => Number.isSafeInteger(r.stats[k]) && r.stats[k] >= 0));
    if (!valid) { blocked.add(index); continue; }
    const target = result[index];
    for (const key of ['interventions', 'disengagements']) {
      target[key] = (target[key] ?? 0) + rows.reduce((n, r) => n + r.stats[key], 0);
      if (!Number.isSafeInteger(target[key])) blocked.add(index);
    }
    target.partial ||= rows.some(r => !r.complete || r.gaps > 0 || r.stats.incomplete);
  }
  blocked.forEach(i => { result[i] = unknown(); });
  return result;
}

export async function readDriveEventHistory(signal) {
  const response = await fetch('/api/models/stats?limit=200', { cache: 'no-store', signal });
  if (!response.ok) throw new Error('Recorded drive counts unavailable');
  return response.json();
}
