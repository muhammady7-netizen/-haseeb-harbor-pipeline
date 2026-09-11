/**
 * Download GLM run 1 trajectory zip for h40 v16 analysis.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'health-h40-critical-result-acknowledgement';
const SHORT = '20cfa5';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  const row = page
    .locator('div,li,a,article,section')
    .filter({ hasText: new RegExp(`${STEM}#${SHORT}`, 'i') })
    .first();
  if (await row.count()) {
    const openBtn = row.getByRole('button', { name: /^Open$/i }).first();
    if (await openBtn.count()) await openBtn.click({ force: true });
    else await row.click({ force: true });
  } else {
    await page.getByRole('button', { name: /^Open$/i }).first().click({ force: true });
  }
  await sleep(8000);
  const t = await page.locator('body').innerText();
  fs.writeFileSync(path.join(OUT, 'h40-v16-traj-page.txt'), `URL=${page.url()}\n\n${t}`);

  // Try download link near "trajectory"
  const dl = page.getByRole('link', { name: /trajectory/i }).nth(1); // GLM run 1 often 2nd
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 60000 }),
    dl.click({ timeout: 15000 }).catch(async () => {
      // fallback: any trajectory download button
      await page.getByText(/trajectory \(\.zip\)/i).nth(1).click({ timeout: 15000 });
    }),
  ]);
  const dest = path.join(OUT, 'h40-v16-glm1-trajectory.zip');
  await download.saveAs(dest);
  console.log(JSON.stringify({ event: 'downloaded', dest, size: fs.statSync(dest).size }));
  await browser.close().catch(() => {});
})().catch(async (e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e).slice(0, 400) }));
  process.exit(1);
});
