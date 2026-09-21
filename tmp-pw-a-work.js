const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const JOBS = [
  {
    short: 'gen-g1205',
    url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-85cfa7f72f124d9edf685f508d5192be-v1',
    mayStart: false,
  },
  {
    short: 'the-thread',
    url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-5cc146d448ffc4f0a07bba4ad679dd1f-v1',
    mayStart: true,
  },
];
function snap(t) {
  return {
    slotsFull: /run slots? are currently in use|\d+\s+runs?\s+in flight/i.test(t),
    lastRun: (t.match(/Last run:[^\n]+/i) || [])[0] || null,
    oracle: (t.match(/Oracle (Passed|Failed|Waiting|Running)[^\n]{0,50}/i) || t.match(/Oracle[^\n]{0,70}/i) || [])[0] || null,
    glm: (t.match(/GLM-5\.2[^\n]{0,100}/) || [])[0] || null,
    tooEasy: /TOO_EASY|4\/4 passed/i.test(t),
    findings: (t.match(/\d+ trainer finding\(s\)/i) || [])[0] || null,
    changes: /Changes needed|Finalization held/i.test(t),
    crashed: /crashed|HARBOR_STAGE_ERROR/i.test(t),
    rewards: [...t.matchAll(/reward [^\t\n]+/g)].map((m) => m[0]).slice(0, 6),
  };
}
(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  const results = [];
  for (const job of JOBS) {
    await page.goto(job.url, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    let t = await page.locator('body').innerText().catch(() => '');
    fs.writeFileSync(`tmp-pw/a-work-${job.short}.txt`, t);
    let s = snap(t);
    let clicked = false;
    const idleFail = s.crashed || /Last run:\s*errored/i.test(t) || (/Oracle Waiting/i.test(t) && /crashed/i.test(t));
    const notRunning = !/Oracle Running|Running now|queued/i.test(t) && !/GLM-5\.2.{0,40}(Running|queued|Completed)/i.test(t);
    if (job.mayStart && !s.slotsFull && (idleFail || notRunning) && !s.tooEasy) {
      const btn = page.locator('button:has-text("Re-run QC-Oracle-GLM"), button:has-text("Run QC-Oracle-GLM")').first();
      if (await btn.count()) {
        const disabled = (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true';
        if (!disabled) {
          await btn.click({ force: true });
          clicked = true;
          await sleep(10000);
          t = await page.locator('body').innerText().catch(() => '');
          fs.writeFileSync(`tmp-pw/a-work-${job.short}-after.txt`, t);
          s = snap(t);
        }
      }
    }
    results.push({ short: job.short, url: page.url(), clicked, ...s });
    console.log(JSON.stringify(results[results.length - 1]));
  }
  fs.writeFileSync('tmp-pw/a-work-status.json', JSON.stringify(results, null, 2));
})().catch((e) => {
  console.error(String(e).slice(0, 400));
  process.exit(1);
});
