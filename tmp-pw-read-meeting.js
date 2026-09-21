const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const URL = process.env.READ_URL;
(async () => {
  const browser = await chromium.launchPersistentContext(
    process.env.USERPROFILE + '/.config/opencode/chrome-profile',
    { headless: true, channel: 'chrome', args: ['--profile-directory=Profile 10','--disable-blink-features=AutomationControlled'] }
  );
  const page = browser.pages()[0] || await browser.newPage();
  page.on('response', async (res) => {
    try {
      const u = res.url();
      if (/api\.read\.ai|app-backend|sessions|summary|report|recap|transcript/i.test(u) && res.status() < 500) {
        const ct = res.headers()['content-type'] || '';
        if (ct.includes('json') || u.includes('api')) {
          const body = await res.text();
          const name = 'tmp-pw/read-net-' + Buffer.from(u).toString('hex').slice(0,24) + '.json';
          fs.writeFileSync(name, JSON.stringify({url:u,status:res.status(),body: body.slice(0,500000)}, null, 2));
          console.log('CAPTURE', res.status(), u.slice(0,160), 'len', body.length);
        }
      }
    } catch {}
  });
  console.log('goto');
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(12000);
  // dismiss sign-up walls if any
  for (const re of [/Continue with Google/i, /Accept/i, /Got it/i, /Continue/i]) {
    const b = page.getByRole('button', { name: re }).first();
    if (await b.count()) { await b.click().catch(()=>{}); await page.waitForTimeout(3000); }
  }
  await page.waitForTimeout(8000);
  const text = await page.locator('body').innerText().catch(()=> '');
  fs.writeFileSync('tmp-pw/read-meeting-body.txt', text);
  console.log('URL', page.url());
  console.log(text.slice(0, 4000));
  await browser.close().catch(()=>{});
})().catch(e => { console.error('FATAL', e); process.exit(1); });
