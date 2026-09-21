/**
 * Session C — gen-g806 only.
 * Reuse OpenCode chrome-profile (Shannon login). One Chrome. Never close.
 * Visible only if no other session already owns the profile; otherwise fail soft.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g806.zip';
const URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1';

async function clickBtn(page, label) {
  const btn = page.getByRole('button', {
    name: new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'),
  });
  const n = await btn.count();
  console.log('btn', label, n);
  if (!n) return false;
  await btn.first().click({ timeout: 10000 });
  console.log('clicked', label);
  await page.waitForTimeout(5000);
  return true;
}

(async () => {
  let browser;
  try {
    browser = await chromium.launchPersistentContext(PROFILE, {
      headless: false,
      channel: 'chrome',
      acceptDownloads: true,
      viewport: null,
    });
  } catch (e) {
    console.error('PROFILE_BUSY_OR_FAIL', String(e).slice(0, 300));
    console.error('Another session likely holds OpenCode Chrome — wait and retry.');
    process.exit(3);
  }

  const page = browser.pages()[0] || (await browser.newPage());
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(8000);
  let body = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/g806-live.txt', body);
  console.log('URL', page.url());
  console.log(body.slice(0, 1800));

  if (/accounts\.google|Enter your email/i.test(page.url() + body)) {
    console.log('NEED_LOGIN');
    process.exit(2);
  }

  // Upload only if still on old failed eval state
  if (/Oracle Failed|below_1\.0|changes needed/i.test(body) || /Upload new version/i.test(body)) {
    const up = page.getByText(/Upload new version/i).first();
    if (await up.count()) {
      await up.click();
      await page.waitForTimeout(2000);
    }
    const inputs = page.locator('input[type="file"]');
    if (await inputs.count()) {
      await inputs.first().setInputFiles(ZIP);
      console.log('uploaded');
      await page.waitForTimeout(15000);
      body = await page.locator('body').innerText();
      fs.writeFileSync('tmp-pw/g806-live-after-upload.txt', body);
      console.log('AFTER_UPLOAD', page.url());
      console.log(body.slice(0, 1500));
    }
  }

  await clickBtn(page, 'Run client preQC');
  await clickBtn(page, 'Re-run client preQC');
  await clickBtn(page, 'Run QC-Oracle-GLM');
  await clickBtn(page, 'Re-run QC-Oracle-GLM');

  await page.waitForTimeout(10000);
  body = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/g806-live-after-start.txt', body);
  console.log('AFTER_START', page.url());
  console.log(body.slice(0, 2200));

  // Keep Chrome alive for other sessions — do not close.
  console.log('KEEP_CHROME_OPEN');
  // Disconnect Node without closing Chrome is not fully supported with persistent context;
  // leave process running so Chrome stays up for the shared queue.
  await new Promise(() => {});
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});
