const { chromium } = require('./tmp-pw/node_modules/playwright');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const URL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-d09f3e79ded320c787b15498063ef758-v1';
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const b = await chromium.launchPersistentContext(PROFILE, { headless: true, channel: 'chrome', args: ['--disable-blink-features=AutomationControlled'] });
  const p = b.pages()[0] || await b.newPage();
  await p.goto(URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(10000);
  const t = await p.locator('body').innerText();
  require('fs').writeFileSync('tmp-pw/a-f39-follow.txt', t);
  console.log(JSON.stringify({
    url: p.url(),
    onTask: /fin-f39-distributable-profits/i.test(t) && /Upload new version/i.test(t),
    lastRun: (t.match(/Last run:[^\n]+/i)||[])[0],
    oracle: (t.match(/Oracle (Passed|Failed|Waiting|Running)[^\n]{0,50}/i)||[])[0],
    glm: (t.match(/GLM-5\.2 ×4[^\n]{0,90}/)||[])[0],
    tooEasy: /TOO_EASY/i.test(t),
    findings: (t.match(/\d+ trainer finding/i)||[])[0],
    qcRunning: /QC running/i.test(t.slice(0, 2500)),
  }));
})().catch(e => { console.error('FAIL', String(e).slice(0,200)); process.exit(1); });
