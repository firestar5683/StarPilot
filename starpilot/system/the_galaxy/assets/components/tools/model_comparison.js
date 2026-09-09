// Read-only comparison state shared by classic and Big Dipper presentations.
import {drivingMetrics, historyRow} from './model_metrics.js';
export async function readComparison(period = 'all', mode = 'all') {
  const response = await fetch(`/api/models/stats?period=${encodeURIComponent(period)}&mode=${encodeURIComponent(mode)}&limit=1`);
  if (!response.ok) throw new Error('Comparison unavailable');
  const result = await response.json();
  if (!result.available && result.status !== 'not_started') throw new Error('Comparison unavailable');
  return Array.isArray(result.comparisons) ? result.comparisons : [];
}
export function comparisonRows(rows, hardware = 'both') {
  return rows.filter(row => (row.identity?.roles || []).every(role => hardware === 'both' || (hardware === 'gpu' ? role.backend === 'chestnut' : role.backend === 'comma')))
    .map(row => ({...historyRow({...row, complete:true}), metrics:drivingMetrics({stats:row.stats}),
      mode:row.mode === 'aol' ? 'Lateral only' : 'Full assistance'}));
}
