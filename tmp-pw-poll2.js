const { chromium } = require('./tmp-pw/node_modules/playwright');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
  });
  const page = browser.pages()[0] || await browser.newPage();
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(6000);
  // Scroll/load submitted list and capture all mentions of c251 and g857
  for (let i = 0; i < 8; i++) {
    await page.mouse.wheel(0, 2000);
    await page.waitForTimeout(800);
  }
  const rootText = await page.locator('body').innerText();
  const lines = rootText.split(/\n+/);
  const hits = [];
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (/c251|g857|pdf-form|department-directory|taxonomy/i.test(l)) {
      hits.push({ i, chunk: lines.slice(Math.max(0,i-1), i+8).join(' | ') });
    }
  }
  // Click into each task by text if possible
  const targets = [
    'code-c251-pdf-form-field-conversion-audit',
    'gen-g857-department-directory-categorization-audit',
  ];
  const details = [];
  for (const name of targets) {
    await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    for (let i = 0; i < 10; i++) { await page.mouse.wheel(0, 1800); await page.waitForTimeout(500); }
    const link = page.getByText(name, { exact: false }).first();
    if (await link.count()) {
      await link.click();
      await page.waitForTimeout(7000);
      const text = await page.locator('body').innerText();
      details.push({ name, url: page.url(), text: text.slice(0, 8000) });
    } else {
      details.push({ name, error: 'not found in list' });
    }
  }
  require('fs').writeFileSync('tmp-pw/portal-poll2.json', JSON.stringify({ hits, details }, null, 2));
  console.log(JSON.stringify({ hitCount: hits.length, hits: hits.slice(0, 20), detailHeads: details.map(d => ({ name: d.name, url: d.url, head: (d.text||d.error||'').slice(0, 1200) })) }, null, 2));
  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
