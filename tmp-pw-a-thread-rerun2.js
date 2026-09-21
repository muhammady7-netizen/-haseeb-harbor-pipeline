const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const URL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-5cc146d448ffc4f0a07bba4ad679dd1f-v1';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true, channel: 'chrome', args: ['--disable-blink-features=AutomationControlled']
  });
  const page = browser.pages()[0] || await browser.newPage();
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(10000);
  const btn = page.getByRole('button', { name: /Re-run QC-Oracle-GLM/i }).first();
  console.log(JSON.stringify({ count: await btn.count(), visible: await btn.isVisible().catch(()=>false), disabled: await btn.getAttribute('aria-disabled').catch(()=>null), title: await btn.getAttribute('title').catch(()=>null) }));
  if (await btn.count()) {
    await btn.scrollIntoViewIfNeeded().catch(()=>{});
    await btn.click({ force: true, timeout: 15000 });
    console.log(JSON.stringify({ event: 'clicked' }));
  } else {
    const t = page.getByText(/Re-run QC-Oracle-GLM/i).first();
    await t.click({ force: true, timeout: 15000 });
    console.log(JSON.stringify({ event: 'clicked_text' }));
  }
  await sleep(12000);
  const body = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/a-thread-after-rerun2.txt', body);
  console.log(JSON.stringify({
    url: page.url(),
    running: /Running now|queued|running ·/i.test(body),
    waiting: /Oracle Waiting|GLM-5\.2 .{0,40}Waiting/i.test(body),
    failed: /crashed|Oracle Failed/i.test(body),
    snippet: (body.match(/QC-Oracle-GLM check[\s\S]{0,400}/)||[])[0]
  }));
})().catch(e => { console.error(e); process.exit(1); });
