// Exact Big Dipper methods with a synthetic CAS server and real layout/fixture.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'../../../..');
const source=fs.readFileSync(path.join(__dirname,'../assets/mobile/js/components/PersonalityProfiles.js'),'utf8').replace(/^import .*\n/gm,'').replace('export const PersonalityProfiles =','globalThis.PersonalityProfiles =');
const clone=x=>JSON.parse(JSON.stringify(x));
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'browser/fixtures/personality_profiles.json')));
const layout=JSON.parse(fs.readFileSync(path.join(root,'starpilot/common/assets/device_settings_layout.json')));
let server=clone(data),puts=0;
const values={IsOnroad:false,IsOffroad:true};
const context={personalityProfileParamKey:p=>p[0].toUpperCase()+p.slice(1)+'PersonalityProfile',showSnackbar:()=>{},api:{getParams:async()=>values,getLayout:async()=>layout,getPersonalityProfiles:async()=>clone(server),savePersonalityProfile:async payload=>{
 puts++;
 assert(payload.expected,'shipped editor must opt into CAS');
 if(JSON.stringify(payload.expected)!==JSON.stringify(server.profiles[payload.profile][payload.category]))throw Error('409 Saved profile changed');
 server.profiles[payload.profile][payload.category]={preset:payload.preset,curve:payload.curve};
}}};
vm.createContext(context);vm.runInContext(source,context);
const component=context.PersonalityProfiles;
const instance={...component.data(),...component.methods,$emit:()=>{}};
for(const [name,get] of Object.entries(component.computed))if(typeof get==='function')Object.defineProperty(instance,name,{get});
(async()=>{
 await instance.load();assert(instance.ready);
 // Another editor/restore changes the category after this editor loaded.
 server.profiles.standard.acceleration={preset:'custom',curve:[2,...Array(9).fill(1)]};
 instance.drafts.standardacceleration=[1,3,...Array(8).fill(1)];
 await instance.saveCurve('standard','acceleration');
 assert.equal(puts,1);assert.equal(server.profiles.standard.acceleration.curve[0],2);
 assert.deepEqual(instance.data.profiles.standard.acceleration,server.profiles.standard.acceleration);
 assert(instance.ready&&!instance.busy&&!instance.curvePending);
 assert(/verified saved state/.test(instance.notice));
 assert(!instance.drafts.standardacceleration);
 // A subsequent edit uses the reconciled snapshot and preserves the other point.
 instance.drafts.standardacceleration=[2,3,...Array(8).fill(1)];
 await instance.saveCurve('standard','acceleration');
 assert.equal(puts,2);assert.deepEqual(server.profiles.standard.acceleration.curve.slice(0,2),[2,3]);
 console.log('PASS exact Big Dipper saveCurve/write/load CAS conflict reconciliation and subsequent preserved edit');
})().catch(e=>{console.error(e);process.exitCode=1});
