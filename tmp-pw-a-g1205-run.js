const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const URL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-85cfa7f72f124d9edf685f508d5192be-v1';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true, channel: 'chrome', args: ['--disable-blink-features=AutomationControlled']
  });
  const page = browser.pages()[0] || await browser.newPage();
  // Prefer list open for reliability
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  const label = page.getByText('gen-g1205-meal-prep-cost-claim-recompute-audit#5192be', { exact: false }).first();
  await label.scrollIntoViewIfNeeded().catch(()=>{});
  const row = label.locator('xpath=ancestor::*[.//button[normalize-space()="Open"]][1]');
  const openBtn = row.getByRole('button', { name: /^Open$/i }).first();
  if (await openBtn.count()) await openBtn.click({ force: true });
  else await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(10000);
  let t = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/a-g1205-before-run.txt', t);
  const slotsFull = /run slots? are currently in use/i.test(t);
  console.log(JSON.stringify({ url: page.url(), slotsFull, hasRun: /Run QC-Oracle-GLM/i.test(t), hasRerun: /Re-run QC-Oracle-GLM/i.test(t), oracle: (t.match(/Oracle[^\n]{0,60}/i)||[])[0] }));
  if (!slotsFull) {
    const btn = page.locator('button:has-text("Run QC-Oracle-GLM"), button:has-text("Re-run QC-Oracle-GLM")').first();
    if (await btn.count()) {
      const disabled = (await btn.getAttribute('aria-disabled')) === 'true';
      console.log(JSON.stringify({ event: 'btn', disabled, title: await btn.getAttribute('title') }));
      if (!disabled) {
        await btn.click({ force: true });
        console.log(JSON.stringify({ event: 'clicked' }));
        await sleep(12000);
      }
    }
  }
  t = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/a-g1205-after-run.txt', t);
  console.log(JSON.stringify({
    url: page.url(),
    lastRun: (t.match(/Last run:[^\n]+/i)||[])[0],
    oracle: (t.match(/Oracle (Passed|Failed|Waiting|Running)[^\n]{0,50}/i)||[])[0],
    glm: (t.match(/GLM-5\.2 ×4[^\n]{0,80}/)||[])[0],
    evalLabel: /Evaluation\nevaluation/i.test(t) || /oracle/i.test(t),
  }));
})().catch(e => { console.error(String(e).slice(0,350)); process.exit(1); });
