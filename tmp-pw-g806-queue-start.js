/**
 * Shared OpenCode chrome-profile driver for Harbor V2.
 * - Reuses ~/.config/opencode/chrome-profile (Shannon login saved)
 * - Does NOT kill Chrome / does NOT close the browser at end
 * - headless:true so no extra visible window pops for the user
 * Session C: gen-g806 only
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g806.zip';
const TASK_URL =
  process.env.G806_URL ||
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1';
const OUT = 'tmp-pw';
const MAX_RUNNING = 4; // portal queue cap across all sessions

function dump(name, text) {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(`${OUT}/${name}`, text);
}

async function bodyText(page) {
  return page.locator('body').innerText();
}

async function clickIfPresent(page, label) {
  const btn = page.getByRole('button', {
    name: new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'),
  });
  const n = await btn.count();
  console.log('btn', label, n);
  if (!n) return false;
  await btn.first().click({ timeout: 8000 });
  console.log('clicked', label);
  await page.waitForTimeout(4000);
  return true;
}

(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  // Prefer existing page; do not open extra tabs if one exists
  const page = browser.pages()[0] || (await browser.newPage());

  await page.goto(TASK_URL, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(7000);
  let body = await bodyText(page);
  dump('g806-queue-before.txt', body);
  console.log('URL', page.url());
  console.log('HEAD\n', body.slice(0, 1600));

  if (/accounts\.google\.com|Enter your email/i.test(page.url() + body)) {
    console.log('NEED_LOGIN — open headed once via OpenCode playwright MCP');
    dump('g806-need-login.txt', page.url() + '\n' + body.slice(0, 2000));
    // leave browser running; do not close
    process.exit(2);
  }

  // Count rough running/queued from All tasks if visible
  const runningish = (body.match(/\b(running|in progress|queued)\b/gi) || []).length;
  console.log('status_tokens', runningish);

  // If package not yet the fixed one, upload
  const needsUpload =
    /Oracle Failed|below_1\.0|changes needed|Upload new version/i.test(body) &&
    !/Client PreQC[\s\S]{0,80}running|QC-Oracle-GLM[\s\S]{0,80}running/i.test(body);

  if (needsUpload && /Upload new version/i.test(body)) {
    const uploadNew = page.getByText(/Upload new version/i).first();
    if (await uploadNew.count()) {
      await uploadNew.click();
      await page.waitForTimeout(2000);
    }
    const inputs = page.locator('input[type="file"]');
    if (await inputs.count()) {
      await inputs.first().setInputFiles(ZIP);
      console.log('uploaded zip');
      await page.waitForTimeout(12000);
      body = await bodyText(page);
      dump('g806-queue-after-upload.txt', body);
      console.log('AFTER UPLOAD URL', page.url());
      console.log(body.slice(0, 1200));
    }
  }

  // Start gates (portal enforces 3–4 concurrent Oracle+GLM)
  await clickIfPresent(page, 'Run client preQC');
  await page.waitForTimeout(3000);
  await clickIfPresent(page, 'Re-run client preQC');
  await page.waitForTimeout(2000);
  const startedOracle =
    (await clickIfPresent(page, 'Run QC-Oracle-GLM')) ||
    (await clickIfPresent(page, 'Re-run QC-Oracle-GLM'));

  await page.waitForTimeout(8000);
  body = await bodyText(page);
  dump('g806-queue-after-start.txt', body);
  console.log('AFTER START URL', page.url());
  console.log(body.slice(0, 2200));
  console.log('startedOracle', startedOracle, 'MAX_RUNNING', MAX_RUNNING);

  // Intentionally do NOT browser.close() — keep shared profile session warm
  // Detach so Node can exit without killing Chrome
  // Playwright persistent context keeps Chrome if we don't close; exit process.
  process.exit(0);
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});
