import assert from 'node:assert/strict'
import { DriveStatePanel, validDriveState } from '../web/js/drive-state.js'
const snapshot=(mode='auto',revision='a'.repeat(32))=>({mode,revision,available:true,effective:'offroad',overrideAllowed:true})
const response=(value,status=200)=>({ok:status===200,json:async()=>value})
const flush=async()=>{for(let i=0;i<10;i++)await Promise.resolve()}
assert(validDriveState(snapshot()))
assert(!validDriveState({...snapshot(),mode:'driving'}))
assert(!validDriveState({...snapshot(),effective:'driving'}))
const requests=[]
globalThis.fetch=(url,options)=>new Promise(resolve=>requests.push({url,options,resolve}))
function panel(){const value={...DriveStatePanel.data(),active:true,generation:0};for(const [key,fn] of Object.entries(DriveStatePanel.methods))value[key]=fn.bind(value);return value}
const value=panel();value.state=snapshot()
const old=value.load();assert.equal(requests.length,1)
const changed=value.change('onroad');assert.equal(requests.length,2)
assert.deepEqual(JSON.parse(requests[1].options.body),{mode:'onroad',revision:'a'.repeat(32)})
assert.equal(requests[0].options.signal.aborted,true)
requests[1].resolve(response(snapshot('onroad','b'.repeat(32))));await flush()
assert.equal(value.state.mode,'onroad');assert.equal(requests.length,3)
requests[0].resolve(response(snapshot('offroad','c'.repeat(32))));await old
assert.equal(value.state.mode,'onroad')
requests[2].resolve(response(snapshot('onroad','b'.repeat(32))));await changed;await flush()
const pending=value.load();const last=requests.at(-1)
DriveStatePanel.beforeUnmount.call(value)
assert.equal(last.options.signal.aborted,true)
last.resolve(response(snapshot('offroad')));await pending
assert.equal(value.state.mode,'onroad')
const denied=panel();const loading=denied.load();requests.at(-1).resolve(response({error:'Sign in to Galaxy'},401));await loading
assert.equal(denied.state,null)
assert.equal(denied.error,'Drive state unavailable')
console.log('PASS: strict status; captured revision; aborted/out-of-order status; requested versus effective; unmount; unauthorized state')

const onroad=panel();onroad.state={...snapshot(),effective:'onroad',overrideAllowed:false}
globalThis.window={confirm:()=>false}
const before=requests.length
await onroad.change('offroad');assert.equal(requests.length,before)
window.confirm=()=>true
const stop=onroad.change('offroad')
assert.equal(requests.length,before+1)
assert.deepEqual(JSON.parse(requests.at(-1).options.body),{mode:'offroad',revision:'a'.repeat(32)})
requests.at(-1).resolve(response({...snapshot('offroad','d'.repeat(32)),effective:'onroad'}));await flush()
assert.equal(DriveStatePanel.computed.pending.call(onroad),true)
requests.at(-1).resolve(response({...snapshot('offroad','d'.repeat(32)),effective:'offroad'}));await stop;await flush()
assert.equal(DriveStatePanel.computed.pending.call(onroad),false)
