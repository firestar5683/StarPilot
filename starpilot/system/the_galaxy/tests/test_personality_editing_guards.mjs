import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../assets/mobile/js/components/PersonalityProfiles.js',import.meta.url),'utf8').replace(/^import .*$/gm,'');
const {PersonalityProfiles:c}=await import('data:text/javascript;base64,'+Buffer.from("const personalityProfileParamKey = () => {}; const api={getParams:async()=>({IsOnroad:false,IsOffroad:true,SafeMode:false}),getPersonalityProfiles:async()=>({editing_locked:false})};\n"+source).toString('base64'));
const ctx={...c.data(),ready:true,values:{IsOnroad:true,IsOffroad:false,SafeMode:false},data:{editing_locked:false}};
for(const [key,computed] of Object.entries(c.computed)) if(typeof computed==='function') Object.defineProperty(ctx,key,{get:()=>computed.call(ctx)});
assert.equal(ctx.locked,false,'known onroad authoring is allowed');
assert.equal(ctx.maintenanceLocked,true,'onroad migration remains disabled');
ctx.data.editing_locked=true;assert.equal(ctx.locked,true,'pending Safe Mode restoration blocks edits');
ctx.data.editing_locked=false;ctx.values.IsOffroad=true;assert.equal(ctx.locked,true,'inconsistent road state blocks edits');
ctx.values.IsOnroad=false;assert.equal(ctx.maintenanceLocked,false,'parked maintenance is available');
ctx.values.SafeMode=true;assert.equal(ctx.locked,true,'Safe Mode blocks authoring');
console.log('Personality editing and maintenance guard checks passed');

ctx.values.SafeMode=false;ctx.data.editing_locked=true;
await c.methods.refreshContext.call(ctx);
assert.equal(ctx.locked,false,'polling clears a completed backend restore lock');
console.log('Backend lock recovery polling passed');
