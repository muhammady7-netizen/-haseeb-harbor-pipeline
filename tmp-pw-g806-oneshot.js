/**
 * Session C one-shot: kill nothing here — caller frees profile.
 * Open latest g806, upload if needed, start PreQC + QC-Oracle-GLM.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g806.zip';
const HOME = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const DIRECT =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1';

function dump(n, t) {
  fs.mkdirSync('tmp-pw', { recursive: true });
  fs.writeFileSync(`tmp-pw/${n}`, t);
}

async function clickBtn(page, label) {
  const btn = page.getByRole('button', {
    name: new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'),
  });
  const n = await btn.count();
  console.log('btn', label, n);
  if (!n) return false;
  await btn.first().click({ timeout: 15000 });
  console.log('clicked', label);
  await page.waitForTimeout(5000);
  return true;
}

(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
  });
  const page = browser.pages()[0] || (await browser.newPage());

  await page.goto(DIRECT, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(8000);
  let body = await page.locator('body').innerText();
  dump('g806-oneshot-1.txt', body);
  console.log('URL1', page.url());
  console.log(body.slice(0, 1500));

  if (/Drop a task here/i.test(body)) {
    await page.goto(HOME, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForTimeout(6000);
    body = await page.locator('body').innerText();
    dump('g806-oneshot-home.txt', body);

    // Click Open for latest g806 (#772487 preferred)
    const opens = page.getByText(/^Open$/i);
    const n = await opens.count();
    console.log('Open count', n);
    // From recent list order: 0=g857, 1=f53, 2=c227, 3=g806#772487
    const idx = n >= 4 ? 3 : 0;
    await opens.nth(idx).click();
    console.log('clicked Open idx', idx);
    await page.waitForTimeout(8000);
    body = await page.locator('body').innerText();
    dump('g806-oneshot-task.txt', body);
    console.log('URL2', page.url());
    console.log(body.slice(0, 1800));
  }

  if (/accounts\.google|Enter your email/i.test(page.url() + body)) {
    console.log('NEED_LOGIN');
    process.exit(2);
  }

  const slotsFull = /3 run slots are currently in use/i.test(body);
  console.log('slotsFull', slotsFull);

  // Upload if prior failure state
  if (/Upload new version/i.test(body)) {
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
      dump('g806-oneshot-uploaded.txt', body);
      console.log('URL3', page.url());
      console.log(body.slice(0, 1500));
    }
  }

  await clickBtn(page, 'Run client preQC');
  await clickBtn(page, 'Re-run client preQC');
  if (!/3 run slots are currently in use/i.test(await page.locator('body').innerText())) {
    await clickBtn(page, 'Run QC-Oracle-GLM');
    await clickBtn(page, 'Re-run QC-Oracle-GLM');
  } else {
    console.log('SLOTS_FULL skip oracle start');
  }

  await page.waitForTimeout(10000);
  body = await page.locator('body').innerText();
  dump('g806-oneshot-final.txt', body);
  console.log('FINAL_URL', page.url());
  console.log(body.slice(0, 2200));
  fs.writeFileSync(
    'tmp-pw/g806-loop-status.json',
    JSON.stringify({ at: new Date().toISOString(), url: page.url(), status: 'oneshot_done' }, null, 2),
  );

  // Keep Chrome open for shared queue — hang
  console.log('KEEP_CHROME_OPEN');
  await new Promise(() => {});
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});
