const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const jobs = [
  ['gen-g1205', 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-85cfa7f72f124d9edf685f508d5192be-v1'],
  ['the-thread', 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-5cc146d448ffc4f0a07bba4ad679dd1f-v1'],
];
(async () => {
  const b = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const p = b.pages()[0] || (await b.newPage());
  for (const [short, url] of jobs) {
    await p.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(12000);
    let t = await p.locator('body').innerText();
    if (/Recent tasks/i.test(t) && !/Upload new version/i.test(t)) {
      await p.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(12000);
      t = await p.locator('body').innerText();
    }
    fs.writeFileSync(`tmp-pw/a-now-${short}.txt`, t);
    let clicked = false;
    const slotsFull = /run slots? are currently in use/i.test(t);
    if (
      short === 'the-thread' &&
      !slotsFull &&
      /Re-run QC-Oracle-GLM/i.test(t) &&
      /errored|crashed/i.test(t) &&
      !/Oracle Running/i.test(t)
    ) {
      const btn = p.locator('button:has-text("Re-run QC-Oracle-GLM")').first();
      if ((await btn.count()) && (await btn.getAttribute('aria-disabled')) !== 'true') {
        await btn.click({ force: true });
        clicked = true;
        await sleep(10000);
        t = await p.locator('body').innerText();
      }
    }
    console.log(
      JSON.stringify({
        short,
        clicked,
        url: p.url(),
        lastRun: (t.match(/Last run:[^\n]+/i) || [])[0],
        oracle: (t.match(/Oracle (Passed|Failed|Waiting|Running)[^\n]{0,50}/i) || [])[0],
        glm: (t.match(/GLM-5\.2[^\n]{0,100}/) || [])[0],
        findings: (t.match(/\d+ trainer finding/i) || [])[0],
        tooEasy: /TOO_EASY/i.test(t),
        changes: /Changes needed|Finalization held/i.test(t),
        slotsFull,
        rewards: [...t.matchAll(/reward [0-9.]+/g)].map((m) => m[0]).slice(0, 5),
        packName: /fin-f39|g1205|the-thread|meal-prep|hands-back/i.test(t.slice(0, 800)),
      })
    );
  }
})().catch((e) => {
  console.error(String(e).slice(0, 300));
  process.exit(1);
});
