import assert from "node:assert/strict"
import fs from "node:fs"
const source = fs.readFileSync(new URL("../web/js/route-leave.js", import.meta.url), "utf8")
const { createRouteLeave } = await import("data:text/javascript;base64," + Buffer.from(source).toString("base64"))
function fixture(path = "/") {
  let entries = [{path, index:0}], at = 0, shown = path, pending
  const port = { read: () => entries[at], show: () => { shown = entries[at].path },
    push: (path,index) => { entries = entries.slice(0,at+1); entries.push({path,index}); at++ },
    replace: (path,index) => { entries[at] = {path,index} },
    go: (delta) => { at += delta; nav.changed(); nav.changed() } }
  const nav = createRouteLeave(port)
  return {nav, port, shown: () => shown, approve: () => pending(),
    dirty: () => nav.setGuard(callback => { pending = callback }),
    clean: () => nav.setGuard(callback => callback()), busy: () => nav.setGuard(() => {}),
    hash: path => { port.push(path,null); nav.changed(); nav.changed() } }
}
{
 const f=fixture(); f.nav.navigate("/theme_maker"); f.dirty(); f.nav.navigate("/tools")
 assert.equal(f.shown(),"/theme_maker"); f.approve(); assert.equal(f.shown(),"/tools")
}
{
 const f=fixture(); f.nav.navigate("/tools"); f.nav.navigate("/theme_maker"); f.dirty(); f.port.go(-1)
 assert.equal(f.shown(),"/theme_maker"); assert.equal(f.port.read().path,"/theme_maker")
 f.approve(); assert.equal(f.shown(),"/tools"); f.port.go(1); assert.equal(f.shown(),"/tools")
 f.approve(); assert.equal(f.shown(),"/theme_maker")
}
{
 const f=fixture(); f.nav.navigate("/theme_maker"); f.dirty(); f.hash("/settings")
 assert.equal(f.shown(),"/theme_maker"); f.approve(); assert.equal(f.shown(),"/settings")
}
{
 const f=fixture(); f.nav.navigate("/theme_maker"); f.busy(); f.nav.navigate("/tools"); f.port.go(-1)
 assert.equal(f.shown(),"/theme_maker"); assert.equal(f.port.read().path,"/theme_maker")
}
{
 const f=fixture(); f.nav.navigate("/theme_maker"); f.dirty(); f.nav.navigate("/tools"); f.nav.navigate("/settings")
 f.approve(); assert.equal(f.shown(),"/settings"); f.clean(); f.nav.back(); assert.equal(f.shown(),"/theme_maker")
}
{
 const f=fixture(); f.nav.navigate("/settings"); f.dirty(); let editor="old"
 f.nav.navigate("/settings", () => { editor="new" }); assert.equal(editor,"old")
 f.approve(); assert.equal(editor,"new")
}
{
 const f=fixture(); f.nav.navigate("/settings"); let nested=true, requests=[]
 f.nav.setGuard((proceed, {back}) => { requests.push(back); if(back && nested) nested=false; else proceed() })
 f.port.go(-1)
 assert.equal(nested,false); assert.equal(f.shown(),"/settings"); assert.equal(f.port.read().path,"/settings")
 f.nav.back(); assert.equal(f.shown(),"/"); assert.deepEqual(requests,[true,true])
}

{
 const f=fixture('/settings'), nav=f.nav
 let nested=true
 nav.setGuard((proceed,{back})=>{if(back && nested) nested=false;else proceed()})
 nav.ensureBackEntry()
 assert.equal(f.port.read().index,1)
 nav.back();assert.equal(nested,false)
 nav.back();assert.equal(f.shown(),'/')
}

console.log("8 route-leave scenarios passed")
