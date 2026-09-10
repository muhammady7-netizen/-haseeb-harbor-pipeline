const { chromium } = require('./tmp-pw/node_modules/playwright');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const urls = [
    { short: 'code-c251', url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-45ae46b08b89f238f2e424e824656a79-v1' },
    { short: 'gen-g857', url: 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2a489be4b73a943d11d2c52efefae8c6-v1' },
  ];
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || await browser.newPage();
  const results = [];
  // First land on trainer root
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const rootText = await page.locator('body').innerText().catch(() => '');
  results.push({ short: 'ROOT', url: page.url(), snippet: rootText.slice(0, 2500) });
  for (const t of urls) {
    await page.goto(t.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(8000);
    const text = await page.locator('body').innerText().catch(() => '');
    results.push({ short: t.short, url: page.url(), snippet: text.slice(0, 4000) });
  }
  require('fs').writeFileSync('tmp-pw/portal-poll.json', JSON.stringify(results, null, 2));
  console.log(JSON.stringify(results.map(r => ({ short: r.short, url: r.url, len: (r.snippet||'').length, head: (r.snippet||'').slice(0, 500) })), null, 2));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
