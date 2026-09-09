// Real Chromium, shipped Arrow/Vue Vitals markup; all readings are test fixtures.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '/opt/data/workspace/galaxy-responsive-evidence/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const root = path.resolve('starpilot/system/the_galaxy');
(async () => {
  const browser = await chromium.launch({headless:true});
  let passed = 0;
  try {
    for (const theme of ['classic', 'dipper']) {
      const page = await browser.newPage({viewport:{width:390,height:844}});
      let mode = 'fresh', requests = 0;
      await page.route('http://fixture/**', async route => {
        const url = new URL(route.request().url());
        if (url.pathname === '/api/vitals/external-gpu') {
          requests++;
          if (mode === 'hang') return; // Abort/expiry must clear a previous sample.
          if (mode === 'error') return route.fulfill({status:503,body:'unavailable'});
          if (mode === 'delay') await new Promise(r => setTimeout(r, 400));
          return route.fulfill({json:mode === 'missing' ? {tempC:null,maxAgeMs:0} : {tempC:73.4,maxAgeMs: mode === 'delay' ? 150 : 1000, memoryUsedBytes:1073741824, memoryTotalBytes:4294967296, memoryMaxAgeMs:mode === 'delay' ? 150 : 1000}});
        }
        if (url.pathname === '/') return route.fulfill({contentType:'text/html',body:'<script type="importmap">{"imports":{"vue":"/assets/vendor/vue/vue.esm-browser.js"}}</script><div id="app"></div>'});
        let source = fs.readFileSync(path.join(root,url.pathname),'utf8');
        if (url.pathname.endsWith('/home/home.js')) source += '\nexport {renderVitals};';
        await route.fulfill({contentType:'text/javascript',body:source});
      });
      await page.goto('http://fixture/');
      await page.evaluate(async theme => {
        const device = {gpuTempC:58,cpuTempC:62,uptimeSeconds:100};
        if (theme === 'classic') {
          const {renderVitals} = await import('/assets/components/home/home.js');
          document.querySelector('#app').innerHTML = renderVitals(device);
        } else {
          const {createApp} = await import('/assets/vendor/vue/vue.esm-browser.js');
          const {Home} = await import('/assets/mobile/js/views/Home.js');
          const start = Home.template.lastIndexOf('<section',Home.template.indexOf('<span>Vitals</span>'));
          const end = Home.template.indexOf('</section>',start) + '</section>'.length;
          createApp({template:Home.template.slice(start,end),data:()=>({device}),computed:{vitalsList:Home.computed.vitalsList}}).mount('#app');
        }
      },theme);
      const metric = page.locator('external-gpu-temperature');
      await metric.waitFor();
      await page.waitForFunction(() => document.querySelector('external-gpu-temperature').textContent === '73°C');
      assert.match(await page.locator('#app').innerText(), /eGPU/);
      assert.match(await page.locator('#app').innerText(), /58 C/);
      if (theme === 'dipper') {
        await page.waitForFunction(() => document.querySelector('external-gpu-memory').textContent === '1.0/4.0 GiB (25%)');
        assert.match(await page.locator('#app').innerText(), /eGPU RAM/);
      }
      passed++;
      mode = 'hang';
      await page.waitForFunction(() => document.querySelector('external-gpu-temperature').textContent === '--');
      passed++;
      if (theme === 'dipper') assert.equal(await page.locator('external-gpu-memory').textContent(), '--');
      mode = 'fresh';
      await page.waitForFunction(() => document.querySelector('external-gpu-temperature').textContent === '73°C');
      passed++;
      mode = 'error';
      await page.waitForFunction(() => document.querySelector('external-gpu-temperature').textContent === '--');
      passed++;
      mode = 'missing';
      await page.waitForTimeout(700);
      assert.equal(await metric.textContent(),'--');
      passed++;
      mode = 'delay';
      await page.waitForTimeout(1100);
      assert.equal(await metric.textContent(),'--');
      passed++;
      await page.evaluate(() => document.querySelector('#app').replaceChildren());
      const count = requests;
      await page.waitForTimeout(1200);
      assert.equal(requests,count);
      passed++;
      await page.close();
    }
    console.log(JSON.stringify({passed, themes:['classic','dipper'], simulatedTelemetry:true}));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
