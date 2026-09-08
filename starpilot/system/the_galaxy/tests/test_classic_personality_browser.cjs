// Local-only real DOM smoke. Requires Playwright + its Chromium; no live API.
// PLAYWRIGHT_MODULE can point at an existing isolated Playwright installation.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const repo = path.resolve(__dirname, '../../../..')
const assets = path.join(repo, 'starpilot/system/the_galaxy/assets')
// All API responses below are synthetic. Layout/assets come from this checkout.
const layoutFixture = JSON.parse(fs.readFileSync(path.join(repo, 'starpilot/common/assets/device_settings_layout.json'), 'utf8'))
const fixture = `
const layoutFixture = ${JSON.stringify(layoutFixture)};
const paramsFixture = Object.fromEntries(layoutFixture.flatMap(section => section.params || []).map(param =>
  [param.key, param.data_type === 'bool' ? false : (param.default ?? param.min ?? 0)]));
const jsonResponse = value => new Response(JSON.stringify(value), {status:200});
window.showSnackbar=()=>{};
window.fetch=async (input, init={}) => {
  const url=new URL(input,location.href);
  const method=init.method || 'GET';
  if(method !== 'GET') throw new Error('Unexpected fixture write: '+url.pathname);
  if(url.pathname==='/assets/components/tools/device_settings_layout.json') return jsonResponse(layoutFixture);
  if(url.pathname==='/api/params/defaults' || url.pathname==='/api/flm/workspace') return jsonResponse({});
  if(url.pathname==='/api/params/all') return jsonResponse(paramsFixture);
  if(url.pathname==='/api/favorites/slots') return jsonResponse({options:[],slots:[null,null,null],values:{}});
  if(url.pathname==='/api/favorites/values') return jsonResponse({values:{}});
  if(url.pathname==='/api/params') return new Response(String(paramsFixture[url.searchParams.get('key')] ?? false));
  throw new Error('Unmocked request: '+method+' '+url.pathname);
};
paramsFixture.IsOnroad = ${process.env.GALAXY_DOM_ONROAD === '1'};
paramsFixture.GalaxyDeveloperMode = true;
const profilesFixture = ${JSON.stringify(JSON.parse(fs.readFileSync(path.join(__dirname,'browser/fixtures/personality_profiles.json'))))};
for (const [id,profile] of Object.entries(profilesFixture.profiles)) {
  for (const [category,config] of Object.entries(profile)) {config.preset='custom';config.curve=[...profilesFixture.reference_curves[id][category]];}
}
window.profileWrites=[];
paramsFixture.IsOffroad=true;paramsFixture.CustomPersonalities=true;
for(const key of ['TrafficPersonalityProfile','AggressivePersonalityProfile','StandardPersonalityProfile','RelaxedPersonalityProfile'])paramsFixture[key]=true;
const baseFetch=window.fetch;
window.fetch=async(input,init={})=>{
 const url=new URL(input,location.href);
 if(url.pathname!='/api/personality_profiles')return baseFetch(input,init);
 if(init.method==='PUT') {const body=JSON.parse(init.body);window.profileWrites.push(body);profilesFixture.profiles[body.profile][body.category]={preset:body.preset,curve:body.curve};}
 return jsonResponse(profilesFixture);
};
import {DeviceSettings} from '/assets/components/tools/device_settings.js';
DeviceSettings({params:{section:'longitudinal-speed-following'}})(document.querySelector('#app'));
`
;(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE || undefined, args: ['--no-sandbox'] })
  try {
    const page = await browser.newPage({ hasTouch:true, deviceScaleFactor: Number(process.env.CLASSIC_WIDTH || 1280)<900 ? 3 : 1, viewport: { width: Number(process.env.CLASSIC_WIDTH || 1280), height: 900 } })
    const touch = await page.context().newCDPSession(page);
    const errors = []
    const dialogs = []
    page.on('dialog', dialog => { dialogs.push(dialog.message()); dialog.dismiss() })
    page.on('pageerror', error => errors.push(error.message))
    await page.route('**/*', async route => {
      const url = new URL(route.request().url())
      if (url.hostname !== 'offline.invalid') throw new Error('External access blocked')
      if (url.pathname === '/device_settings') return route.fulfill({contentType:'text/html',body:'<html><head><link rel="stylesheet" href="/assets/components/main.css"><link rel="stylesheet" href="/assets/components/settings.css"><link rel="stylesheet" href="/assets/components/tools/device_settings.css"></head><body><main id="app"></main><script type="module" src="/setup.js"></script></body></html>'})
      if (url.pathname === '/setup.js') return route.fulfill({contentType:'text/javascript',body:fixture})
      if (url.pathname.endsWith('/device_settings.js')) return route.fulfill({contentType:'text/javascript',body:fs.readFileSync(path.join(assets,'components/tools/device_settings.js'),'utf8')+'\nwindow.__auditState=state;'});
      if (url.pathname.startsWith('/assets/')) {
        const file = path.join(assets, url.pathname.slice('/assets/'.length))
        if (fs.existsSync(file) && fs.statSync(file).isFile()) return route.fulfill({path:file})
      }
      return route.fulfill({status:404,body:'not found'})
    })
    await page.goto('http://offline.invalid/device_settings')
    await page.getByRole('button', {name:'Longitudinal (Speed & Following)',exact:true}).click()
    await page.locator('[aria-controls="personality-profiles-panel"]').click();
    await page.locator('.ds-personality-card').first().waitFor();
    assert.equal(await page.locator('.ds-personality-card').count(),4);
    for(const profile of ['traffic','aggressive','standard','relaxed']) {
      const card=page.locator(`.ds-personality-card[data-profile="${profile}"]`);
      await card.locator('.ds-personality-advanced-toggle').click();
      for(const category of ['acceleration','braking','following']) {
        const input=page.locator(`#personality-input-${profile}-${category}-0`);
        await input.waitFor({state:'visible'});
        await page.waitForFunction(()=>!window.__auditState.personalityProfilesLoading && !Object.keys(window.__auditState.personalityUpdating).length);
        const before=await page.evaluate(()=>window.profileWrites.length);
        await input.fill('1.40');await input.press('Tab');
        await page.waitForFunction(n=>window.profileWrites.length===n+1,before,{timeout:5000}).catch(async e=>{console.log(await page.locator('body').innerText());console.log(await page.evaluate(()=>({onroad:window.__auditState.values.IsOnroad,loading:window.__auditState.personalityProfilesLoading,error:window.__auditState.personalityProfilesError,updating:window.__auditState.personalityUpdating,migration:window.__auditState.personalityMigrationRequired})));console.log(errors);throw e;});
        assert.equal(await page.evaluate(()=>window.profileWrites.at(-1).curve[0]),1.4);
        assert.ok(await page.evaluate(()=>Object.hasOwn(window.profileWrites.at(-1),'expected')));
        await page.waitForFunction(()=>!Object.keys(window.__auditState.personalityUpdating).length);
        const canvas=page.locator(`#personality-chart-${profile}-${category}`);await canvas.scrollIntoViewIfNeeded();
        const r=await canvas.boundingBox(); const x=r.x+r.width/2,y=r.y+r.height/2;const phone=Number(process.env.CLASSIC_WIDTH || 1280)<900;
        if(phone) {
          await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
          await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:y-10}]});
        } else {await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x,y-10);}
        assert.equal(await page.evaluate(()=>window.profileWrites.length),before+1,'drag preview wrote before release');
        if(phone) await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});else await page.mouse.up();
        await page.waitForFunction(n=>window.profileWrites.length===n+2,before);
      }
    }
    await page.locator('#personality-chart-relaxed-following').screenshot({path:(process.env.CLASSIC_SCREENSHOT || '/tmp/classic-personality.png').replace('.png','-graph.png')});
    await page.screenshot({path:process.env.CLASSIC_SCREENSHOT || '/tmp/classic-personality.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({surface:'classic',categories:12,numericAutosaves:12,dragAutosaves:12,errors}));
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode=1 })
