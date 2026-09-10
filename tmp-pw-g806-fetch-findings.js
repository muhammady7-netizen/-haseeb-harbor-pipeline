/**
 * Download / dump g806 Harbor finding details (Final QC report).
 * Shared profile, headless, wait if busy.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const DIRECT =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1';
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
    } catch {
      console.log(JSON.stringify({ event: 'BUSY', i }));
      await sleep(20000);
    }
  }
  if (!browser) process.exit(3);

  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);
  await page.goto(DIRECT, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(6000);
  let t = await page.locator('body').innerText().catch(() => '');
  if (/Drop a task here/i.test(t.slice(0, 800))) {
    await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', {
      waitUntil: 'domcontentloaded',
      timeout: 120000,
    });
    await sleep(4000);
    const stem = page.getByText(STEM, { exact: false }).first();
    if (await stem.count()) {
      await stem.click();
      await sleep(8000);
    }
    t = await page.locator('body').innerText().catch(() => '');
  }
  fs.writeFileSync(path.join(OUT, 'g806-findings-page.txt'), t);

  // Expand first few "Review issue" links for detail
  const reviews = page.getByText(/Review issue/i);
  const n = await reviews.count();
  console.log(JSON.stringify({ event: 'review_issue_count', n }));
  const details = [];
  for (let i = 0; i < Math.min(n, 12); i++) {
    await reviews.nth(i).click({ timeout: 8000 }).catch(() => null);
    await sleep(2500);
    const body = await page.locator('body').innerText().catch(() => '');
    fs.writeFileSync(path.join(OUT, `g806-finding-${i}.txt`), body);
    details.push(body.slice(0, 2500));
    // close modal if any
    await page.keyboard.press('Escape').catch(() => null);
    await sleep(800);
  }

  // Try download report zip
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 20000 }).catch(() => [null]),
    page.getByText(/^zip$/i).first().click({ timeout: 8000 }).catch(() => null),
  ]).then((x) => x).catch(() => [null]);
  // fix parallel
  let dl = null;
  try {
    const p = page.waitForEvent('download', { timeout: 25000 });
    const zips = page.getByText(/^zip$/i);
    if (await zips.count()) {
      await zips.nth(1).click(); // oracle report zip often 2nd
      dl = await p;
    }
  } catch {}
  if (dl) {
    const dest = path.join(OUT, 'g806-oracle-report.zip');
    await dl.saveAs(dest);
    console.log(JSON.stringify({ event: 'downloaded', dest }));
  }

  fs.writeFileSync(
    path.join(OUT, 'g806-findings-summary.json'),
    JSON.stringify(
      {
        at: new Date().toISOString(),
        reviewIssues: n,
        glm: /0\/4 passed/i.test(t) ? '0/4' : null,
        oracle: /Oracle Passed/i.test(t),
        head: t.slice(0, 1500),
      },
      null,
      2
    )
  );
  await browser.close().catch(() => {});
  console.log(JSON.stringify({ event: 'DONE' }));
})().catch((e) => {
  console.log(JSON.stringify({ event: 'FATAL', error: String(e).slice(0, 300) }));
  process.exit(1);
});
