// Existing classic UI: verify only selection/lifecycle compatibility fixes.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../assets/components/tools/model_manager.js',import.meta.url),'utf8');
const notices=[];globalThis.window={location:{pathname:'/manage_models'},showSnackbar:(...a)=>notices.push(a)};
const selects={};globalThis.document={getElementById:id=>selects[id]??=({value:''})};
const api=new Function('reactive','html',source.replace(/^import .*$/gm,'').replace('export function ModelManager','function ModelManager')+';return {state,fetchStatus,runAction};')(x=>x,()=>{});
const payload=(active='gpu')=>({models:[{value:'gpu',installed:true,requiresGpu:true}],activeBigModel:active,activeSmallModel:'small',currentModel:'small',summary:{},isOnroad:false});
const response=(data,ok=true)=>({ok,status:ok?200:503,json:async()=>data});
let active='gpu',failWrite=false,failRead=false,hold=null,writes=[];
globalThis.fetch=async(url,opts)=>{if(opts.method==='PUT'){writes.push(JSON.parse(opts.body));if(failWrite)return response({error:'uncertain'},false);active=writes.at(-1).model;return response({message:'selected'});}if(url==='/api/models/cancel'){writes.push('cancel');return response({});}if(hold){const value=hold;hold=null;return value;}return response(failRead?{error:'read failed'}:payload(active),!failRead);};
await api.fetchStatus();assert.equal(api.state.selectionUncertain,false);assert.equal(selects['mm-active-big-model-select'].value,'gpu');
let release;hold=new Promise(resolve=>release=resolve);const old=api.fetchStatus();await api.runAction('select-big','');release(response(payload('gpu')));await old;assert.equal(api.state.activeBigModel,'');assert.equal(selects['mm-active-big-model-select'].value,'');assert.deepEqual(writes,[{profile:'big',model:''}]);
failWrite=true;failRead=true;await api.runAction('select-big','gpu');assert.equal(api.state.selectionUncertain,true);assert.equal(api.state.actionBusy,false);await api.runAction('select-big','gpu');assert.equal(writes.length,2);await api.runAction('cancel');assert.equal(writes.length,3);
failRead=false;await api.fetchStatus();assert.equal(api.state.selectionUncertain,false);assert.equal(api.state.activeBigModel,'');
window.location.pathname='/elsewhere';await api.runAction('select-big','gpu');assert.equal(writes.length,3);
console.log('PASS: legacy explicit None, stale poll, readback failure lock, retry, cancellation and route guard');
