// Exercise shipped component methods with deferred requests; no device I/O.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync(new URL('../assets/mobile/js/views/ModelManager.js', import.meta.url), 'utf8');
const hardware = await import('../assets/components/tools/model_hardware.js');
let status, write, prompt, requests, notices;
const deferred = () => { let resolve, reject; const promise = new Promise((a,b)=>{resolve=a;reject=b}); return {promise,resolve,reject}; };
const payload = (overrides={}) => ({models:[{value:'gpu',requiresGpu:true,gpuAvailable:false,installed:false},{value:'small',requiresGpu:false,installed:true}],activeBigModel:'gpu',activeSmallModel:'small',currentModel:'small',summary:{},...overrides});
const api = {
 getModelStatus: () => status(),
 setActiveModel: (profile,model) => { requests.push({profile,model}); return write(); },
 startModelDownload: (model,allow) => { requests.push({model,allow});return write(); },
 downloadAllModels: allow => { requests.push({all:true,allow});return write(); },
 postAction: action => { requests.push({action});return write(); },
};
const component = new Function('api','showSnackbar','usePolling','GalaxyConfirm','openGalaxyHelpDialog',...Object.keys(hardware), source.replace(/^import .*$/gm,'').replace('export const ModelManager', 'const ModelManager')+';return ModelManager;')(api,(...a)=>notices.push(a),()=>{},()=>{},()=>prompt(),...Object.values(hardware));
function instance() { const vm=component.data();for(const [key,value] of Object.entries(component.methods))vm[key]=value.bind(vm);return vm; }
async function reset() {requests=[];notices=[];status=async()=>payload();write=async()=>({});prompt=async()=>true;const vm=instance();await vm.refresh();return vm;}
// Filters combine without altering the catalogue or selection.
let vm=await reset();vm.hardwareFilter='comma';vm.userFilter='all';vm.communityFilter='all';assert.deepEqual(component.computed.sorted.call(vm).map(m=>m.value),['small']);assert.equal(vm.activeBigModel,'gpu');assert.deepEqual(requests,[]);
// GPU approval is per action; cancellation sends no write and releases busy.
prompt=async()=>false;await vm.runAction('download',vm.models[0]);assert.deepEqual(requests,[]);assert.equal(vm.busy,'');
prompt=async()=>true;await vm.runAction('download',vm.models[0]);assert.deepEqual(requests,[{model:'gpu',allow:true}]);
// Approval must recheck road state, competing downloads and status failures.
for(const changed of [{isOnroad:true},{downloading:true},null]) { vm=await reset();status=changed?async()=>payload(changed):async()=>{throw Error('read failed')};await vm.runAction('download',vm.models[0]);assert.deepEqual(requests,[]);assert.equal(vm.busy,''); }
// Ordinary downloads never reuse approval, and failed writes release busy.
vm=await reset();write=async()=>{throw Error('download failed')};await vm.runAction('download',vm.models[1]);assert.deepEqual(requests,[{model:'small',allow:false}]);assert.equal(vm.busy,'');
vm=await reset();await vm.runAction('downloadAll');assert.deepEqual(requests,[{all:true,allow:true}]);
// A pre-write poll cannot overwrite authoritative post-write selection.
vm=await reset();let old=deferred();status=()=>old.promise;let poll=vm.refresh();write=async()=>({});status=async()=>payload({activeBigModel:''});await vm.runAction('select-big');old.resolve(payload());await poll;assert.equal(vm.activeBigModel,'');assert.equal(vm.selectionUncertain,false);
// An uncertain write plus failed readback locks only selection until retry.
vm=await reset();write=async()=>{throw Error('uncertain write')};status=async()=>{throw Error('read failure')};await vm.runAction('select-big');assert.equal(vm.selectionUncertain,true);await vm.runAction('select-big');assert.equal(requests.length,1);await vm.runAction('cancel');assert.equal(requests.length,2);status=async()=>payload({activeBigModel:''});await vm.refresh();assert.equal(vm.selectionUncertain,false);assert.equal(vm.activeBigModel,'');
// A remount must wait for an already sent write and ignore old notifications.
vm=await reset();const pending=deferred();write=()=>pending.promise;const action=vm.runAction('select-big');component.beforeUnmount.call(vm);const next=instance();let reads=0;status=async()=>{reads++;return payload({activeBigModel:''})};const refreshed=next.refresh();await Promise.resolve();assert.equal(reads,0);pending.resolve({message:'old success'});await action;await refreshed;assert.equal(next.activeBigModel,'');assert.equal(next.selectionUncertain,false);assert.deepEqual(notices,[]);
// Unmounted confirmation and overlapping action cannot submit another request.
vm=await reset();const confirmation=deferred();prompt=()=>confirmation.promise;const downloading=vm.runAction('download',vm.models[0]);await vm.runAction('downloadAll');assert.deepEqual(requests,[]);component.beforeUnmount.call(vm);confirmation.resolve(true);await downloading;assert.deepEqual(requests,[]);
// Two concurrent polls resolve newest-first.
vm=await reset();const a=deferred(),b=deferred();status=()=>a.promise;const first=vm.refresh();status=()=>b.promise;const second=vm.refresh();b.resolve(payload({activeBigModel:'new'}));await second;a.resolve(payload({activeBigModel:'old'}));await first;assert.equal(vm.activeBigModel,'new');
assert.ok(!source.includes('GalaxySelect'));assert.ok(!source.includes('model_metrics'));assert.ok(!source.includes('model_stats'));assert.ok(source.includes('selectionUncertain || status.isOnroad'));
console.log('PASS: 15 hardware/download/selection/lifecycle scenarios against shipped methods');

const {compile} = await import('../assets/vendor/vue/vue.esm-browser.js');
assert.equal(typeof compile(component.template, {onError(error) {throw error;}}), 'function');
console.log('PASS: shipped Vue compiler accepts the native-select Model Manager template');
