/** One-shot Session F portal poll for current content IDs. */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const OUT = 'tmp-pw';
const TASKS = [
  {
    short: 'g857',
    url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-6405280bc2048278c063ca8833d84e3b-v1',
  },
  {
    short: 'c251',
    url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-7ec9d05ada07cb640c53224362e578f5-v1',
  },
];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  let browser;
  try {
    browser = await chromium.launchPersistentContext(PROFILE, {
      headless: true,
      channel: 'chrome',
      args: ['--disable-blink-features=AutomationControlled'],
    });
  } catch (e) {
    console.log(JSON.stringify({ event: 'PROFILE_BUSY', error: String(e).slice(0, 200) }));
    process.exit(3);
  }
  const page = browser.pages()[0] || (await browser.newPage());
  const results = [];
  for (const t of TASKS) {
    await page.goto(t.url, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    const text = await page.locator('body').innerText().catch(() => '');
    fs.writeFileSync(path.join(OUT, `f-poll-${t.short}.txt`), text);
    const snap = {
      short: t.short,
      url: page.url(),
      oracle: (text.match(/Oracle[^\n]{0,80}/i) || [])[0] || null,
      glm: (text.match(/GLM[^\n]{0,120}/i) || [])[0] || null,
      statusLine: (text.match(/Trainer QC status[\s\S]{0,200}/i) || [])[0] || null,
      reviewRequired: /Review required/i.test(text),
      accepted: /Accepted|ready to submit/i.test(text),
      changesNeeded: /Changes needed|Changes required/i.test(text),
      running: /running ·|QC-Oracle-GLM[\s\S]{0,40}running/i.test(text),
      version: (text.match(/\bv(\d+)\s*[·.]\s*latest/i) || [])[1] || null,
      head: text.slice(0, 1200),
    };
    results.push(snap);
    console.log(JSON.stringify(snap));
  }
  fs.writeFileSync(path.join(OUT, 'f-poll-status.json'), JSON.stringify(results, null, 2));
  // keep chrome warm briefly then exit so profile frees for others
  await browser.close();
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
