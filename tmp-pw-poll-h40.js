const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const urls = [
    { short: 'ROOT', url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#' },
    { short: 'h40-reg', url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-30206cd130f05908598fc85c46c30493-v1' },
    { short: 'h40-v2', url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-45ae46b08b89f238f2e424e824656a79-v1' },
  ];
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || await browser.newPage();
  const results = [];
  for (const t of urls) {
    await page.goto(t.url, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(10000);
    const text = await page.locator('body').innerText().catch(() => '');
    results.push({ short: t.short, url: page.url(), snippet: text.slice(0, 6000) });
  }
  fs.writeFileSync('tmp-pw/portal-poll-h40.json', JSON.stringify(results, null, 2));
  for (const r of results) {
    console.log('====', r.short, '====');
    console.log(r.url);
    console.log((r.snippet || '').slice(0, 1800));
    console.log('');
  }
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
