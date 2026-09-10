import assert from 'node:assert/strict';
globalThis.HTMLElement = class {};
globalThis.customElements = {get:()=>true};
const {topModelRows} = await import('../assets/components/home/top_models.js');
const {visibleDrivingMetrics} = await import('../assets/components/tools/model_metrics.js');
const stats = {available:true,assistedMeters:16093.44,interventionMeters:8046.72,disengagementMeters:16093.44,interventions:2,disengagements:0};
assert.deepEqual(visibleDrivingMetrics({stats:{...stats,assistedMeters:0,interventionMeters:0,disengagementMeters:0}}),[]);
assert.equal(visibleDrivingMetrics({stats}).length,3);
assert.equal(visibleDrivingMetrics({stats:{...stats,available:false}}).length,0);
const models=[{value:'a',label:'Alpha',stats},{value:'none',stats:{...stats,interventions:0}},{value:'unused',stats:{...stats,interventionMeters:0}},{value:'invalid',stats:{...stats,interventions:null}},{value:'unknown',stats:{available:false}},{value:'string',stats:{...stats,interventionMeters:'8000'}}];
const rows=topModelRows(models);
assert.deepEqual(rows.map(r=>r.id),['a','none']);
assert.equal(rows[0].metric,'2.5 mi · 2 events');
assert.equal(rows[0].sample,'Recorded sample: 5.0 mi');
assert.equal(rows[0].total,'Total recorded assisted: 10.0 mi');
assert.equal(topModelRows(models,'disengagements')[0].total,rows[0].total);
// Identical display labels are not identities. Never pool totals by name,
// infer assisted distance from event exposure, or coerce invalid/missing data.
const sameNames = [
  {value:'model-a',label:'Same name',stats:{...stats,assistedMeters:1609.344}},
  {value:'model-b',label:'Same name',stats:{...stats,assistedMeters:3218.688}},
];
assert.deepEqual(topModelRows(sameNames).map(r=>[r.id,r.total]),[
  ['model-a','Total recorded assisted: 1.0 mi'],
  ['model-b','Total recorded assisted: 2.0 mi'],
]);
for (const assistedMeters of [null,undefined,-1,NaN,Infinity,'1609.344']) {
  assert.equal(topModelRows([{value:'invalid-total',stats:{...stats,assistedMeters}}])[0].total,'Total recorded assisted: —');
}
assert.equal(topModelRows([{value:'zero-total',stats:{...stats,assistedMeters:0}}])[0].total,'Total recorded assisted: 0.0 mi');
assert.equal(topModelRows([{value:'unavailable',stats:{...stats,available:false}}]).length,0);
assert.equal(rows[1].metric,'No events · 5.0 mi');
assert.equal(rows[1].ratio,null);
assert.deepEqual(topModelRows(null),[]);
assert.equal(topModelRows(models,'disengagements')[0].metric,'No events · 10.0 mi');
console.log('Top model exposure eligibility, measured ordering, zero-event semantics, invalid data and unused card metrics passed');
