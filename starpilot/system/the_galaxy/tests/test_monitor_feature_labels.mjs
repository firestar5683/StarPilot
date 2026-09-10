import assert from 'node:assert/strict';
import {SystemMonitor, processFeature} from '../assets/mobile/js/components/SystemMonitor.js';
assert.equal(typeof processFeature, 'function', 'Monitor must identify feature names');
for (const name of ['starpilot.system.adj_spot_monitor_vision', 'openpilot.starpilot.system.adj_spot_monitor_vision', '/data/openpilot/starpilot/system/adj_spot_monitor_vision.py']) {
  assert.equal(processFeature({name}), 'V-ASM');
}
assert.equal(processFeature({name:'starpilot.system.speed_limit_vision'}), 'Vision Speed Limit Controller');
assert.equal(processFeature({name:'starpilot.system.wheel_controls.wheel_controlsd'}), 'Bluetooth controller actions');
assert.equal(processFeature({name:'openpilot.starpilot.system.model_statsd'}), 'Model statistics');
assert.equal(processFeature({name:'./pandad'}), 'Vehicle CAN communication');
for (const name of ['python', 'bash', 'unknown.adj_spot_monitor_vision', 'constructor', 'toString', '', null]) {
  assert.equal(processFeature({name}), '', 'Do not guess from generic or unknown process names');
}
assert.equal(processFeature({name:'starpilot.system.adj_spot_monitor_vision',kernel:true}), '');
const processes=[
  {name:'starpilot.system.adj_spot_monitor_vision',pid:1,user:'comma',cpu:12,state:'S'},
  {name:'./pandad',pid:2,user:'comma',cpu:30,state:'R'},
  {name:'python',pid:3,user:'root',cpu:40,state:'S'},
];
const view={query:'V-ASM',scope:'comma',sort:'cpu',descending:true,snapshot:{processes},state:SystemMonitor.methods.state};
let rows=SystemMonitor.computed.rows.call(view);
assert.deepEqual(rows.map(p=>p.pid),[1], 'Search must match feature names');
assert.equal(rows[0].name,processes[0].name, 'Raw process name is preserved');
assert.equal(processes[0].feature,undefined, 'Do not mutate the API snapshot');
view.query='';
assert.deepEqual(SystemMonitor.computed.rows.call(view).map(p=>p.pid),[2,1], 'CPU sorting and process scope are preserved');
view.query='2';
assert.deepEqual(SystemMonitor.computed.rows.call(view).map(p=>p.pid),[2]);
assert.match(SystemMonitor.template,/\(\{\{ process\.feature \}\}\)/, 'Render feature names in brackets');
console.log('PASS: feature matching, unknown/kernel exclusions, feature search, raw names, scope, CPU sorting and bracket rendering');
