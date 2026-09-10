const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
  const url = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-0f5e7ea213cebcd75662f8b0281f1da7-v1';
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || await browser.newPage();
  for (let i = 0; i < 40; i++) { // ~20-30 min
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForTimeout(10000);
    const text = await page.locator('body').innerText();
    const running = /Running now|running ·|Harbor Check started|waiting for cloud/i.test(text) && !/Trainer changes required|READY_FOR_FINALIZATION|Submit to pipeline/i.test(text.split('NEEDS ATTENTION')[0] || text);
    const harborDone = /Harbor Check|FINAL VALIDATION/i.test(text) && !/harbor — waiting for cloud|Harbor Check started[\s\S]*waiting for cloud/i.test(text);
    const oracle = (text.match(/Oracle[^\n]{0,60}/i) || [''])[0];
    const glm = (text.match(/GLM-5\.2 ×4 difficulty[^\n]*/i) || [''])[0];
    const block = /NEEDS ATTENTION|blocking issue|Oracle Failed|TOO_EASY|changes needed/i.test(text);
    const ready = /READY_FOR_FINALIZATION|can_submit|Submit to pipeline/i.test(text);
    console.log('T' + i, new Date().toISOString(), 'running=' + /Running now|running ·/i.test(text), '|', oracle, '|', glm);
    if (!/Running now|running ·/i.test(text)) {
      fs.writeFileSync('tmp-pw/h40-eval-complete.txt', text);
      console.log('DONE');
      console.log(text.slice(0, 4500));
      break;
    }
    await page.waitForTimeout(30000);
  }
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
