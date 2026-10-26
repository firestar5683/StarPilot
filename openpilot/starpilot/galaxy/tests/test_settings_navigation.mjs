import assert from 'node:assert/strict'
import { SettingsPage, SETTINGS_SECTIONS } from '../web/js/settings.js'
import { OnroadLayoutPage } from '../web/js/onroad-layout.js'
const wheel=SETTINGS_SECTIONS.find(s=>s.id==='wheel')
function fixture() {
 const loads=[]
 const vm={busy:false,state:{layoutOpen:false,favoritesOpen:false,query:'',searchOpen:false,section:'visual',data:{page:'hub'}},$refs:{},sections:SETTINGS_SECTIONS,
 feed:{active:false,start(page){this.active=true;loads.push(page)},load(page){loads.push(page)}}}
 for(const name of ['selectCategory','selectSection','requestRouteLeave'])vm[name]=SettingsPage.methods[name].bind(vm)
 return {vm,loads}
}
{
 const {vm,loads}=fixture();vm.busy=true;vm.selectCategory(wheel);assert.deepEqual(loads,[])
 vm.busy=false;vm.$refs.cloudProvider={busy:true};vm.selectCategory(wheel);assert.deepEqual(loads,[])
}
{
 const {vm,loads}=fixture();vm.state.favoritesOpen=true;vm.$refs.favoritesEditor={busy:true}
 vm.selectCategory(wheel);assert.equal(vm.state.favoritesOpen,true);assert.deepEqual(loads,[])
 vm.$refs.favoritesEditor.busy=false;vm.selectCategory(wheel)
 assert.equal(vm.state.favoritesOpen,false);assert.deepEqual(loads,['wheel'])
}
{
 const {vm,loads}=fixture();vm.state.layoutOpen=true
 const editor={state:{status:'ready',discard:null,leavePresentation:null},dirty:true,inlineLeavePrompt:false,busy:false}
 for(const name of ['requestLeave','leave','cancelLeave'])editor[name]=OnroadLayoutPage.methods[name].bind(editor)
 vm.$refs.layoutEditor=editor
 vm.selectCategory(wheel)
 assert.equal(vm.state.layoutOpen,true);assert.deepEqual(loads,[]);assert.equal(typeof editor.state.discard,'function')
 editor.cancelLeave();assert.equal(editor.state.discard,null);assert.equal(vm.state.layoutOpen,true)
 vm.selectCategory(wheel);editor.leave(editor.state.discard)
 assert.equal(vm.state.layoutOpen,false);assert.deepEqual(loads,['wheel'])
}
{
 const {vm,loads}=fixture();vm.state.layoutOpen=true
 const editor={state:{status:'saving'},inlineLeavePrompt:false}
 editor.requestLeave=OnroadLayoutPage.methods.requestLeave.bind(editor);vm.$refs.layoutEditor=editor
 vm.selectCategory(wheel);assert.equal(vm.state.layoutOpen,true);assert.deepEqual(loads,[])
}
console.log('PASS: category switches respect settings/cloud/Quick Select saving and layout dirty/cancel/discard/saving guards')


// A direct deep link exposes every real ancestor, including flat personality IDs.
const { settingsTrailPages } = await import('../web/js/settings.js')
const { route } = await import('../web/js/route-state.js')
assert.deepEqual(settingsTrailPages('hub'), [])
assert.deepEqual(settingsTrailPages('lane/activation/modes'), ['lane','lane/activation','lane/activation/modes'])
assert.deepEqual(settingsTrailPages('relaxed/following'), ['profiles','relaxed','relaxed/following'])
const props={initialPage:'hub',initialSection:null,navigationPath:true,unauthorized(){}}
route.view={settings:{key:'hub:',page:'lane/activation/modes',section:'lateral',query:'obsolete filter',searchOpen:true,parents:['hub','lane','lane/activation'],developerOpen:false},scroll:{x:0,y:512}}
const restored={...SettingsPage.setup(props),...props,mode:'local'}
assert.equal(restored.restoredPage,'lane/activation/modes')
assert.equal(restored.state.data,null,'restored navigation must fetch current setting values')
assert.equal(restored.state.query,'','removed search must not leave an invisible filter')
assert.equal(restored.state.searchOpen,false)
const scroll=[];globalThis.window={scrollTo:(...args)=>scroll.push(args)}
let started
restored.feed={active:true,async start(page){started=page},stop(){this.active=false}}
await SettingsPage.mounted.call(restored)
assert.equal(started,'lane/activation/modes');assert.deepEqual(scroll,[[0,512]])
restored.state.data={page:'lane/activation/modes',title:'Modes',rows:[]}
restored.pathRequest=new AbortController()
SettingsPage.beforeUnmount.call(restored)
assert.equal(restored.pathRequest.signal.aborted,true)
assert.equal(restored.feed.active,false)
assert.equal(route.view.settings.page,'lane/activation/modes')
assert.equal(route.view.settings.data,undefined)

const loads=[]
const vm={navigationPath:true,busy:false,initialPage:'hub',state:{status:'ready',query:'',data:{page:'lane/activation/modes',title:'Modes'},pageTitles:{lane:'Lane Centering','lane/activation':'Activation Conditions'},parents:[]},activeSection:SETTINGS_SECTIONS[0],feed:{load:p=>loads.push(p)}}
vm.navigationItems=SettingsPage.computed.navigationItems.call(vm)
vm.jumpToPage=SettingsPage.methods.jumpToPage.bind(vm)
assert.deepEqual(vm.navigationItems.map(x=>x.id),['section','lane','lane/activation','lane/activation/modes'])
vm.jumpToPage('unrelated');assert.equal(loads.length,0)
vm.busy=true;vm.jumpToPage('lane');assert.equal(loads.length,0)
vm.busy=false;vm.state.status='loading';vm.jumpToPage('lane');assert.equal(loads.length,0)
vm.state.status='ready';vm.jumpToPage('lane');assert.deepEqual(loads,['lane']);assert.deepEqual(vm.state.parents,['hub'])

// Missing titles use a separate GET and do not replace the settings page or feed.
const originalFetch=globalThis.fetch, requests=[]
const meta={feed:{active:true,stop(){this.active=false}},state:{data:{page:'lane/activation/modes'},pageTitles:{}},unauthorized(){throw new Error('unexpected auth failure')}}
meta.rememberPathPage=SettingsPage.methods.rememberPathPage.bind(meta)
try {
 globalThis.fetch=async (url,options)=>{requests.push({url,options});const page=decodeURIComponent(url.split('/pages/')[1]);return {ok:true,status:200,json:async()=>({page,title:page==='lane'?'Lane Centering':'Activation Conditions',rows:[]})}}
 await SettingsPage.methods.loadPathTitles.call(meta)
 assert.equal(requests.length,2);assert.equal(meta.feed.active,true);assert.equal(meta.state.data.page,'lane/activation/modes')
 assert.equal(meta.state.pageTitles.lane,'Lane Centering');assert.equal(meta.pathRequest,null)
 assert.ok(requests.every(r=>!r.options.method && r.options.credentials==='same-origin' && r.options.signal))
 let expired=0;meta.state.pageTitles={};meta.unauthorized=()=>expired++
 globalThis.fetch=async()=>({status:401,ok:false})
 await SettingsPage.methods.loadPathTitles.call(meta)
 assert.equal(expired,1);assert.equal(meta.feed.active,false)
} finally {globalThis.fetch=originalFetch}
console.log('PASS: hierarchy jumps, restored page/scroll, fresh values, hidden-filter reset, metadata auth and cancellation')
