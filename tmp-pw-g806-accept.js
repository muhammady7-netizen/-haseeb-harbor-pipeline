/**
 * Session C — open latest g806, dump status (Accept vs Harbor blockers).
 * Headless shared profile; wait if busy.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'gen-g806-leadership-brief-rhetorical-style-audit';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  let browser;
  for (let i = 1; i <= 40; i++) {
    try {
      browser = await chromium.launchPersistentContext(PROFILE, {
        headless: true,
        channel: 'chrome',
        acceptDownloads: true,
        args: ['--disable-blink-features=AutomationControlled'],
      });
      console.log(JSON.stringify({ event: 'LAUNCHED', i }));
      break;
    } catch (e) {
      console.log(JSON.stringify({ event: 'BUSY', i }));
      await sleep(20000);
    }
  }
  if (!browser) process.exit(3);
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  let t = await page.locator('body').innerText().catch(() => '');
  fs.writeFileSync(path.join(OUT, 'g806-accept-home.txt'), t);

  const stem = page.getByText(STEM, { exact: false }).first();
  if (await stem.count()) {
    await stem.scrollIntoViewIfNeeded().catch(() => {});
    await stem.click({ timeout: 20000 }).catch(() => null);
    await sleep(8000);
  }
  // Prefer Open near top recent list if still home
  t = await page.locator('body').innerText().catch(() => '');
  if (/Drop a task here/i.test(t.slice(0, 900))) {
    const opens = page.getByText(/^Open$/i);
    const n = await opens.count();
    for (let i = 0; i < Math.min(n, 15); i++) {
      await opens.nth(i).click({ timeout: 8000 }).catch(() => null);
      await sleep(5000);
      t = await page.locator('body').innerText().catch(() => '');
      if (new RegExp(STEM, 'i').test(t.slice(0, 2500)) && !/Drop a task here/i.test(t.slice(0, 800))) break;
      await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(3000);
    }
  }

  t = await page.locator('body').innerText().catch(() => '');
  fs.writeFileSync(path.join(OUT, 'g806-accept-task.txt'), t);
  const summary = {
    url: page.url(),
    oracle: /Oracle Passed/i.test(t),
    oracleFail: /Oracle Failed/i.test(t),
    glm: (t.match(/GLM-5\.2[^\n]{0,60}?(\d)\s*\/\s*4/i) || [])[1] || null,
    blockers: (t.match(/(\d+)\s+blocking/i) || [])[1] || null,
    toDecide: (t.match(/(\d+)\s+to decide/i) || [])[1] || null,
    readySubmit: /Ready to submit|Submit to pipeline|READY_FOR_FINALIZATION/i.test(t),
    accepted: /Accepted|Submitted to the pipeline/i.test(t.slice(0, 3000)),
    running: /Running now|Oracle Waiting|GLM[^\n]{0,40}Waiting/i.test(t),
    version: (t.match(/v(\d+)\s*·\s*latest/i) || [])[0] || null,
    head: t.slice(0, 1200).replace(/\s+/g, ' '),
  };
  fs.writeFileSync(path.join(OUT, 'g806-accept-status.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify({ event: 'STATUS', ...summary }));

  // If ready to submit and no blockers, click Submit / Accept
  if (summary.readySubmit && !summary.blockers && !summary.running) {
    for (const re of [/Submit to pipeline/i, /^Submit$/i, /Accept/i, /Ready to submit/i]) {
      const btn = page.getByRole('button', { name: re }).first();
      if (await btn.count()) {
        const dis =
          (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
          (await btn.isDisabled().catch(() => false));
        if (!dis) {
          await btn.click({ timeout: 15000 });
          console.log(JSON.stringify({ event: 'CLICKED', re: String(re) }));
          await sleep(8000);
          break;
        }
      }
    }
    t = await page.locator('body').innerText().catch(() => '');
    fs.writeFileSync(path.join(OUT, 'g806-accept-after.txt'), t);
    console.log(JSON.stringify({ event: 'AFTER', head: t.slice(0, 800).replace(/\s+/g, ' ') }));
  }

  await browser.close().catch(() => {});
})().catch((e) => {
  console.log(JSON.stringify({ event: 'FATAL', error: String(e).slice(0, 300) }));
  process.exit(1);
});
