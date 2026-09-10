import assert from 'node:assert/strict';
import {SystemMonitor} from '../assets/mobile/js/components/SystemMonitor.js';
import {api} from '../assets/mobile/js/api.js';
let now=0, scheduled=[];
globalThis.performance={now:()=>now};
globalThis.document={hidden:false};
globalThis.setTimeout=(fn,delay)=>{const entry={fn,delay};scheduled.push(entry);return entry};
globalThis.clearTimeout=()=>{};
for(const latency of [100,750,1000]) {
 now=0;scheduled=[];
 const view={...SystemMonitor.data(),...SystemMonitor.methods};
 api.systemMonitor=async()=>{now+=latency;return {sampledAt:1,cpuPercent:20,vitals:{gpuTempC:45,hotspotTempC:70,memoryUsedBytes:100,memoryTotalBytes:200,onboardMaxAgeMs:2500,maxAgeMs:2500,memoryMaxAgeMs:2500}}};
 await view.refresh();
 const delay=scheduled.at(-1).delay;
 assert.ok(delay>=100 && delay<=2000,'Bound refresh load');
 const nextResponse=now+delay+latency;
 view.sensorNow=nextResponse-1;
 assert.equal(view.sensor('gpuTempC','onboardMaxAgeMs'),45,`No blank before next healthy response at ${latency}ms latency`);
 view.sensorNow=2501;
 assert.equal(view.sensor('gpuTempC','onboardMaxAgeMs'),null,'Stopped telemetry still expires');
 view.sensorNow=now;view.snapshot.vitals.maxAgeMs=0;
 assert.equal(view.sensor('hotspotTempC','maxAgeMs'),null,'Invalid sensor response is not held');
 view.stopped=true;scheduled=[];await view.refresh();assert.equal(scheduled.length,0);
}
console.log('PASS: delayed healthy responses, bounded polling, stale/invalid expiry and unmount');
