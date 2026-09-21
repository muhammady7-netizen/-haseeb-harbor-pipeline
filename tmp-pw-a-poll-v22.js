const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const browser = await chromium.launchPersistentContext(
    process.env.USERPROFILE + '/.config/opencode/chrome-profile',
    { headless: true, channel: 'chrome', args: ['--disable-blink-features=AutomationControlled'] }
  );
  const page = browser.pages()[0] || await browser.newPage();
  const url = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-6513101fd1bccf3a2b340d4a87b24e5f-v1';
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(8000);
  const t = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/a-poll-f39-v22.txt', t);
  console.log(JSON.stringify({
    url: page.url(),
    head: t.slice(0, 2000),
    tooEasy: /TOO_EASY/i.test(t),
    changes: /Changes needed/i.test(t),
    oraclePass: /Oracle\s*Pass/i.test(t),
    glm: [...t.matchAll(/GLM-5\.2[^\n]{0,120}/g)].map(m=>m[0]).slice(0,8),
    rewards: [...t.matchAll(/reward [^\t\n]+/g)].map(m=>m[0]).slice(0,8)
  }, null, 2));
})().catch(e => { console.error(e); process.exit(1); });
