import assert from 'node:assert/strict'
import { api } from '../assets/mobile/js/api.js'
const calls=[]
const state={mode:'chill',locked:false,experimental_confirmed:false,action_expires_at:123,values:{ExperimentalMode:false,ConditionalExperimental:false,ConditionalChill:false}}
const originalFetch=globalThis.fetch
try {
  globalThis.fetch=async (url,init={})=>{calls.push({url,init});return {ok:true,json:async()=>url==='/api/longitudinal_mode'?state:{mode:'experimental'}}}
  await api.activateFavoriteAction('__starpilot_favorite_action__:longitudinal_cycle')
  assert.equal(calls.length,2)
  const body=JSON.parse(calls[1].init.body)
  assert.equal(body.acknowledged,true)
  assert.equal(body.expires_at,state.action_expires_at)
  assert.deepEqual(body.expected,state.values)
  calls.length=0
  await api.activateFavoriteAction('__starpilot_controller_action__:set_speed',42)
  assert.equal(calls.length,1)
  assert.deepEqual(JSON.parse(calls[0].init.body),{key:'__starpilot_controller_action__:set_speed',value:42})
  calls.length=0;state.locked=true
  await assert.rejects(api.activateFavoriteAction('__starpilot_favorite_action__:longitudinal_cycle'))
  assert.equal(calls.length,1,'A locked snapshot must never dispatch an action')
} finally { globalThis.fetch=originalFetch }
console.log('Browser acknowledgement, exact snapshot, expiry, payload and lock checks passed.')
