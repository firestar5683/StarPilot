import assert from 'node:assert/strict'
import { compile } from '../web/vendor/vue/vue.esm-browser.js'
import { OnroadLayoutPage } from '../web/js/onroad-layout.js'
import { BluetoothFeed } from '../web/js/bluetooth.js'
compile(OnroadLayoutPage.template, {decodeEntities: s => s.replaceAll('&amp;', '&')})
assert.deepEqual(OnroadLayoutPage.computed.availableProfiles.call({state:{data:{activeProfile:'compact'}}}), ['compact'])
assert.deepEqual(OnroadLayoutPage.computed.availableProfiles.call({state:{data:{activeProfile:'large'}}}), ['large'])
assert.deepEqual(OnroadLayoutPage.computed.availableProfiles.call({state:{data:{}}}), [])
let selected = null
const vm = {busy:false, dirty:false, state:{drag:null}, hideDevicePreview(){}, $emit(event,target){selected = [event,target]}}
vm.leave = OnroadLayoutPage.methods.leave.bind(vm)
OnroadLayoutPage.methods.requestLeave.call(vm,'projection')
assert.deepEqual(selected,['target','projection'])
assert.ok(OnroadLayoutPage.template.includes('v-if="state.devicePreviewOpen"'))
const status = {version:1,available:true,parked:false,powered:true,discovering:false,errorCode:null,pairing:null,devices:[]}
const calls=[]
const feed = new BluetoothFeed({publish(){},fetcher:async(url,opts)=>{calls.push([url,opts]);return {ok:true,status:200,json:async()=>status}},later(){return 1},cancelTimer(){}})
await feed.start()
for (const [operation, fields] of [['scan',{}], ['pair',{address:'AA:BB:CC:DD:EE:FF'}], ['connect',{address:'AA:BB:CC:DD:EE:FF'}], ['disconnect',{address:'AA:BB:CC:DD:EE:FF'}], ['forget',{address:'AA:BB:CC:DD:EE:FF'}]]) {
 const before=calls.length;await feed.action(operation,fields);assert.equal(calls.length,before+2)
}
const before=calls.length;await feed.action('power',{enabled:false});assert.equal(calls.length,before)
feed.stop()
console.log('Actual Vue template, hardware targets, AA target navigation, onroad Bluetooth operations and radio restart gate PASS')
