const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const url = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-0f5e7ea213cebcd75662f8b0281f1da7-v1';
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = await browser.newPage();
  for (let i = 0; i < 60; i++) {
    try {
      await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
      await page.waitForTimeout(3000);
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
      await page.waitForTimeout(12000);
      await page.evaluate((u) => { location.hash = u.split('#')[1]; }, url);
      await page.waitForTimeout(5000);
      const text = await page.locator('body').innerText();
      const isTask = /health-h40-critical-result-acknowledgement/i.test(text) && /Oracle/i.test(text);
      const running = isTask && /Running now|running ·/i.test(text);
      const oracle = (text.match(/Oracle Passed|Oracle Failed|Oracle[^\n]{0,40}/i) || [''])[0];
      const glm = (text.match(/GLM-5\.2 ×4 difficulty[^\n]*/i) || [''])[0];
      console.log('T' + i, new Date().toISOString(), 'task=' + isTask, 'running=' + running, '|', oracle, '|', glm);
      if (isTask && !running) {
        fs.writeFileSync('tmp-pw/h40-eval-complete.txt', text);
        console.log('DONE');
        console.log(text.slice(0, 5000));
        break;
      }
    } catch (e) {
      console.log('T' + i, 'ERR', String(e).slice(0, 200));
    }
    await page.waitForTimeout(45000);
  }
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
