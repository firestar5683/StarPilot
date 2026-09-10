import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'
const source=fs.readFileSync(new URL('../assets/mobile/js/views/SystemTools.js',import.meta.url),'utf8')
const method=source.slice(source.indexOf('    async onRestoreFile('),source.indexOf('    async resetDefault('))
function setup(confirm=async()=>true) {
  const calls=[],messages=[]
  const context=vm.createContext({api:{restoreToggles:async data=>{calls.push(data);return {}}},GalaxyConfirm:confirm,showSnackbar:(...args)=>messages.push(args)})
  vm.runInContext('globalThis.instance={isOnroad:false,'+method+'}',context)
  return {instance:context.instance,calls,messages}
}
const event=(text=async()=>'{"format":"starpilot-backup"}')=>({target:{value:'chosen',files:[{size:100,text}]}})
test('file read failure reports an error without dispatch',async()=>{
  const {instance,calls,messages}=setup()
  await instance.onRestoreFile(event(async()=>{throw Error('read failed')}))
  assert.equal(calls.length,0)
  assert.equal(messages[0][0],'read failed')
})
test('road state is rechecked after confirmation',async()=>{
  const state=setup(async()=>{state.instance.isOnroad=true;return true})
  await state.instance.onRestoreFile(event())
  assert.equal(state.calls.length,0)
  assert.match(state.messages[0][0],/Park/)
})
test('cancel leaves saved state alone and successful confirm dispatches once',async()=>{
  const canceled=setup(async()=>false)
  await canceled.instance.onRestoreFile(event())
  assert.equal(canceled.calls.length,0)
  const accepted=setup()
  await accepted.instance.onRestoreFile(event())
  assert.equal(accepted.calls.length,1)
  assert.equal(accepted.calls[0].format,'starpilot-backup')
})
