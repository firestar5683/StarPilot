import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'
import {driveEventCounts} from '../assets/mobile/js/drive_event_counts.js'
const source=fs.readFileSync(new URL('../assets/mobile/js/views/Home.js',import.meta.url),'utf8')
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r});return {promise,resolve}}
const tick=()=>new Promise(resolve=>setTimeout(resolve,0))
function setup({getStats=async()=>({dashboard:{week:{distanceUnit:'miles'}}}),readHistory=async()=>({available:false})}={}) {
  const context=vm.createContext({api:{getStats},showSnackbar(){},usePolling(){},GalaxyConfirm(){},driveEventCounts,
    readDriveEventHistory:readHistory,AbortController,setTimeout,clearTimeout})
  vm.runInContext(source.replace(/^import .*$/gm,'').replace('export const Home =','globalThis.Home ='),context)
  return {component:context.Home,instance:{...context.Home.data(),...context.Home.methods}}
}
test('last-drive events use route identity when boundaries coincide',()=>{
  const {component}=setup()
  const date='2026-09-10T10:00:00Z',endDate='2026-09-10T10:10:00Z'
  const a={name:'route-a',routeNames:['route-a'],date,endDate,ignored:true}
  const b={name:'route-b',routeNames:['route-b'],date,endDate,duration:600,model:'model-b'}
  const history={available:true,history:[['a',99,9],['b',3,1]].map(([id,interventions,disengagements])=>({
    drive:'drive-'+id,routeName:'route-'+id,started:Date.parse(date)/1000,updated:Date.parse(endDate)/1000,
    complete:true,stats:{available:true,interventions,disengagements}}))}
  const output=component.computed.lastDrive.call({dash:{lastDrive:b,recentDrives:[a,b]},eventHistory:history,unit:'miles'})
  assert.equal(output.footer.find(item=>item.text.endsWith(' interventions')).text,'3 interventions')
  assert.equal(output.footer.find(item=>item.text.endsWith(' disengagements')).text,'1 disengagements')
})
test('optional event history never blocks the ready dashboard or refresh',async()=>{
  const history=deferred()
  const {instance}=setup({readHistory:()=>history.promise})
  const loading=instance.load()
  try {
    await tick()
    assert(instance.payload)
    assert.equal(instance.status,'ready')
    assert.equal(instance.refreshing,false)
  } finally { history.resolve({available:false});await loading;await tick() }
})
test('unmount during main fetch cannot start or apply event requests',async()=>{
  const response=deferred();let historyCalls=0
  const {component,instance}=setup({getStats:()=>response.promise,readHistory:async()=>{historyCalls++;return {available:true}}})
  const loading=instance.load()
  component.beforeUnmount.call(instance)
  response.resolve({dashboard:{}})
  await loading;await tick()
  assert.equal(historyCalls,0)
  assert.equal(instance.eventHistory,null)
})
test('stale or unmounted event responses cannot replace the current result',async()=>{
  const requests=[]
  const {component,instance}=setup({readHistory:()=>{const request=deferred();requests.push(request);return request.promise}})
  await instance.load();await instance.load()
  requests[1].resolve({available:true,marker:'current'});await tick()
  requests[0].resolve({available:true,marker:'stale'});await tick()
  assert.equal(instance.eventHistory.marker,'current')
  await instance.load()
  component.beforeUnmount.call(instance)
  requests[2].resolve({available:true,marker:'unmounted'});await tick()
  assert.notEqual(instance.eventHistory?.marker,'unmounted')
})
