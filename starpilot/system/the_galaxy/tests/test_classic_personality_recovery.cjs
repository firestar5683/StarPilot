// Exact shipped functions, synthetic transport only; no device or real Params.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const path=require('path');
const source=fs.readFileSync(path.resolve(__dirname,'../assets/components/tools/device_settings.js'),'utf8');
function setup(mode){
 let stored=[1,1,1], calls=[],failed=false;
 const c={window:{location:{pathname:'/device_settings'}},state:{values:{IsOnroad:false,IsOffroad:true},personalityMigrationRequired:false,personalityUpdating:{},personalityProfiles:{standard:{acceleration:{preset:'custom',curve:[1,1,1]}}}},uiContextPollInflight:null,personalityViewGeneration:0,personalityUpdateKey:(p,k)=>p+':'+k,showParamSnackbar:()=>{},PERSONALITY_CATEGORY_DEFINITIONS:{acceleration:{label:'Acceleration'}},fetch:async(url,opts={})=>{
 calls.push(opts.method||'GET');
 if(opts.method==='PUT'){
  stored=JSON.parse(opts.body).curve;
  if(!failed){failed=true;if(mode==='navigate')c.window.location.pathname='/models';if(mode==='malformed')return {ok:true,json:async()=>{throw Error('malformed')}};throw Error('accepted response lost');}
 }
 if(mode==='readFailure'&&opts.method!=='PUT')throw Error('read failed');
 return {ok:true,json:async()=>url.includes('params/all')?{IsOnroad:false,IsOffroad:true}:{profiles:{standard:{acceleration:{preset:'custom',curve:stored}}},bounds:{},options:{},speed_breakpoints_mph:{acceleration:[0,10,20]} }};
 }};
 vm.createContext(c);
 // Keep helper and save together to exercise production recovery, not a test copy.
 const start=source.indexOf('async function recoverPersonalitySave(');
 vm.runInContext(source.slice(start<0?source.indexOf('async function savePersonalityCategory('):start,source.indexOf('\nfunction updatePersonalityPreset(')),c);
 return {c,calls,stored:()=>stored};
}
(async()=>{
 for(const mode of ['lost','malformed']){
  const {c,calls,stored}=setup(mode);
  assert.equal(await c.savePersonalityCategory('standard','acceleration','custom',[2,1,1]),false);
  assert.deepEqual(c.state.personalityProfiles.standard.acceleration.curve,[2,1,1],mode+' must read saved state');
  assert(calls.includes('GET'));
  const next=[...c.state.personalityProfiles.standard.acceleration.curve];next[1]=3;
  assert.equal(await c.savePersonalityCategory('standard','acceleration','custom',next),true);
  assert.deepEqual(stored(),[2,3,1]);
 }
 const {c,calls}=setup('readFailure');
 await c.savePersonalityCategory('standard','acceleration','custom',[2,1,1]);
 assert(c.state.personalityProfilesError,'failed recovery locks editor');
 await c.savePersonalityCategory('standard','acceleration','custom',[1,3,1]);
 assert.equal(calls.filter(x=>x==='PUT').length,1,'no second write until recovery');
 const nav=setup('navigate');await nav.c.savePersonalityCategory('standard','acceleration','custom',[2,1,1]);
 assert.deepEqual(nav.calls,['PUT'],'no late navigation readback');
 assert(nav.c.state.personalityProfilesError,'remount cannot author stale state');
 nav.c.window.location.pathname='/device_settings';nav.c.personalityViewGeneration++;
 assert.equal(await nav.c.recoverPersonalitySave(),true);
 assert.deepEqual(nav.c.state.personalityProfiles.standard.acceleration.curve,[2,1,1]);
 for(const reason of ['onroad','navigation']){
   const pending=setup('lost');let release;
   pending.c.uiContextPollInflight=new Promise(resolve=>release=resolve);
   const save=pending.c.savePersonalityCategory('standard','acceleration','custom',[2,1,1]);
   if(reason==='onroad')pending.c.state.values.IsOnroad=true;
   else pending.c.personalityViewGeneration++;
   release();assert.equal(await save,false);assert.deepEqual(pending.calls,[],'pre-send context recheck');
 }
 console.log('PASS lost response, malformed response, locked recovery failure, navigation/remount and pending-context suppression');
})().catch(e=>{console.error(e);process.exitCode=1});
