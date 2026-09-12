import assert from 'node:assert/strict';
import {driveEventCounts} from '../assets/mobile/js/drive_event_counts.js';
globalThis.HTMLElement = class {};
globalThis.customElements = {get:()=>true};
const {topModelRows} = await import('../assets/components/home/top_models.js');
const d=(a,b)=>({date:new Date(a*1000).toISOString(),endDate:new Date(b*1000).toISOString()});
const row=(over={})=>({drive:'one',started:100,updated:200,complete:true,gaps:0,stats:{available:true,interventions:2,disengagements:1},...over});
const h=(rows,more=false)=>({available:true,history:rows,hasMore:more});
const counts=(ds,hs)=>driveEventCounts(ds,hs);
assert.deepEqual(counts([d(90,210)],h([row()])),[{interventions:2,disengagements:1,partial:false}]);
assert.equal(counts([d(90,210)],h([row(),row({mode:'aol'})]))[0].interventions,4);
assert.equal(counts([d(90,210)],h([row({gaps:1})]))[0].partial,true);
assert.equal(counts([d(90,210)],h([row({complete:false})]))[0].partial,true);
for (const invalid of [null, {}, h([]), h([row()],true),h([row({stats:{available:true,interventions:-1,disengagements:1}})])]) {
 assert.equal(counts([d(90,210)],invalid)[0].interventions,null);
}
assert.equal(counts([d(90,150),d(150,210)],h([row()]))[1].interventions,null);
assert.equal(counts([d(90,210),d(95,215)],h([row()]))[0].interventions,null);
assert.equal(counts([d(90,210)],h([row({started:80})]))[0].interventions,null);
assert.equal(counts([d(90,210)],h([row({stats:{available:true,interventions:0,disengagements:0}})]))[0].interventions,0);
assert.equal(counts([d(90,210)],h([row(),row({drive:'old',started:10,updated:20})],true))[0].interventions,2);
const models=[{value:'a',stats:{available:true,assistedMeters:100}},{value:'b',stats:{available:true,assistedMeters:500}},{value:'c',stats:{available:true,assistedMeters:0}},{value:'d',stats:{available:true,assistedMeters:null}}];
assert.deepEqual(topModelRows(models,'distance').map(r=>r.id),['b','a']);
assert.deepEqual(models.map(m=>m.value),['a','b','c','d']);
console.log('PASS: recorded counts, ambiguity, partial/truncated/missing history, zero counts, distance ranking and input preservation');
