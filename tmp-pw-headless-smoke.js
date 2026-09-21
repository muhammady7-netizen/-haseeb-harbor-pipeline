const { chromium } = require('./tmp-pw/node_modules/playwright');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  try {
    const browser = await chromium.launchPersistentContext(profile, {
      headless: true,
      // no channel: use bundled chromium
      args: ['--disable-blink-features=AutomationControlled'],
    });
    const page = browser.pages()[0] || await browser.newPage();
    await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    const t = await page.locator('body').innerText();
    console.log(JSON.stringify({ ok: true, url: page.url(), head: t.slice(0, 500) }));
    await browser.close();
  } catch (e) {
    console.log(JSON.stringify({ ok: false, error: String(e).slice(0, 500) }));
    process.exit(1);
  }
})();
