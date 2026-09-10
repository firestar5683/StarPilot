import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const path = new URL('../assets/components/tools/model_metrics.js', import.meta.url);
const m = await import('data:text/javascript;base64,' + readFileSync(path).toString('base64'));
const stats = {available:true, assistedMeters:16093.44, interventionMeters:12874.752, disengagementMeters:16093.44, interventions:2, disengagements:4};
assert.deepEqual(m.drivingMetrics({stats}).map(x=>x.value), ['10.0 mi','4.0 mi · 2 events','2.5 mi · 4 events']);
assert.deepEqual(m.drivingMetrics({}).map(x=>x.value), ['—','—','—']);
assert.equal(m.trackingStatus({}), 'Not tracked yet');
assert.equal(m.trackingStatus({stats:{available:false,status:'error'}}), 'Statistics unavailable');
assert.equal(m.trackingStatus({stats:{...stats,trackingStatus:'resource_limited'}}), 'Tracking limited — coverage lost');
assert.equal(m.trackingStatus({stats:{available:false,trackingStatus:'resource_limited'}}), 'Tracking limited — coverage lost');
assert.equal(m.drivingMetrics({stats:{...stats,interventions:0}})[1].value, 'No events · 8.0 mi');
assert.equal(m.metricSortValue({stats:{...stats,interventions:0}}, 'interventions'),null);
assert.equal(m.compareMetrics({stats},{stats:{...stats,interventions:0}},'interventions'),-1);
assert.equal(m.compareMetrics({}, {stats}, 'distance'),1);
for (const bad of [NaN,Infinity,-1,null,undefined,'100']) assert.equal(m.milesText(bad),'—');
assert.equal(m.fileSizeText({fileSizeBytes:1500000000}), '1.50 GB');
assert.equal(m.fileSizeText({declaredSizeBytes:500000000}), '500.0 MB · declared');
assert.equal(m.fileSizeText({modelSize:4}), 'Unavailable');
assert.equal(m.fileSizeText({fileSizeBytes:true}), 'Unavailable');
assert.equal(m.fileSizeText({partial:true,downloadedBytes:250000000,declaredSizeBytes:500000000}), 'Partial: 250.0 MB / 500.0 MB');
assert.ok(m.fileSizeText({fileSizeBytes:100,declaredSizeBytes:200}).includes('size mismatch'));
for (const filter of ['gpu','comma','both']) {
 assert.equal(m.matchesHardware({requiresGpu:true}, filter),filter!=='comma');
 assert.equal(m.matchesHardware({requiresGpu:false}, filter),filter!=='gpu');
 assert.equal(m.matchesHardware({}, filter),filter==='both');
}
console.log('Model metrics formatting, null handling, event ratios, comparison sorting, file sizes and hardware filters passed');

const measured = {percent:75, durationSeconds:10.4, engagedSeconds:7.8, measurementScope:'runtime_intervals', coverage:'partial'};
const engage = m.modelManagerMetrics({stats}, measured).find(metric => metric.label === 'Engage percentage');
assert.equal(engage.value, '75%');
assert.match(engage.description, /verified recorded intervals/);
assert.equal(m.modelManagerMetrics({stats}, {percent:100, durationSeconds:10})[1].value, '—');
assert.equal(m.modelManagerMetrics({stats})[1].value, '—');
