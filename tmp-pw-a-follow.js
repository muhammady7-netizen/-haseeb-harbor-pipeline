const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const JOBS = [
  { short: 'gen-g1205', url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-85cfa7f72f124d9edf685f508d5192be-v1' },
  { short: 'the-thread', url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-5cc146d448ffc4f0a07bba4ad679dd1f-v1', mayRerun: true },
];
(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true, channel: 'chrome', args: ['--disable-blink-features=AutomationControlled']
  });
  const page = browser.pages()[0] || await browser.newPage();
  const out = [];
  for (const job of JOBS) {
    await page.goto(job.url, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    let t = await page.locator('body').innerText();
    const slotsFull = /run slots? are currently in use|\d+\s+runs?\s+in flight/i.test(t);
    if (job.mayRerun && !slotsFull) {
      const btn = page.locator('button:has-text("Re-run QC-Oracle-GLM"), button:has-text("Run QC-Oracle-GLM")').first();
      if (await btn.count()) {
        const disabled = (await btn.getAttribute('aria-disabled').catch(()=>null)) === 'true';
        if (!disabled) { await btn.click({ force: true }); await sleep(8000); t = await page.locator('body').innerText(); }
      }
    }
    fs.writeFileSync(`tmp-pw/a-follow-${job.short}.txt`, t);
    out.push({
      short: job.short,
      url: page.url(),
      slotsFull,
      oraclePass: /Oracle Passed/i.test(t),
      oracleFail: /Oracle Failed|crashed/i.test(t),
      oracleWaiting: /Oracle Waiting/i.test(t),
      glm: (t.match(/GLM-5\.2[^\n]{0,100}/) || [])[0],
      lastRun: (t.match(/Last run:[^\n]+/i) || [])[0],
      changes: /Changes needed|TOO_EASY/i.test(t),
      findings: (t.match(/\d+ trainer finding/i) || [])[0],
    });
  }
  console.log(JSON.stringify(out, null, 2));
})().catch(e => { console.error(e); process.exit(1); });
