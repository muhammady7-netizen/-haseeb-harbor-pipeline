/**
 * Session F — upload Harbor-fixed g857 as v8, re-run Delivery Gate (QC check).
 * One headless Chrome; never close/reopen mid-run.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g857.zip';
// latest task root (v7 lineage → link as v8 after upload)
const G857 =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2a489be4b73a943d11d2c52efefae8c6';
const OUT = 'tmp-pw';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function log(o) {
  const line = JSON.stringify(o);
  console.log(line);
  fs.appendFileSync(path.join(OUT, 'f-upload-fix.log'), line + '\n');
}

async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function softClick(page, re, label) {
  const btn = page.getByRole('button', { name: re }).first();
  const loc = (await btn.count()) ? btn : page.getByText(re).first();
  if (!(await loc.count())) return false;
  const disabled = await loc.getAttribute('aria-disabled').catch(() => null);
  const title = await loc.getAttribute('title').catch(() => '');
  if (disabled === 'true' || /slots are currently in use/i.test(title || '')) {
    log({ event: 'disabled', label, title });
    return false;
  }
  try {
    await loc.click({ timeout: 10000 });
    await sleep(3500);
    log({ event: 'clicked', label });
    return true;
  } catch (e) {
    log({ event: 'click_fail', label, error: String(e).slice(0, 160) });
    return false;
  }
}

(async () => {
  fs.writeFileSync(path.join(OUT, 'f-upload-fix.log'), '');
  let browser;
  try {
    browser = await chromium.launchPersistentContext(PROFILE, {
      headless: true,
      channel: 'chrome',
      acceptDownloads: true,
      args: ['--disable-blink-features=AutomationControlled'],
    });
  } catch (e) {
    log({ event: 'PROFILE_BUSY', error: String(e).slice(0, 250) });
    process.exit(3);
  }
  const page = browser.pages()[0] || (await browser.newPage());

  await page.goto(G857, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(8000);
  let t = await body(page);
  fs.writeFileSync(path.join(OUT, 'f-upload-g857-before.txt'), t);
  log({ event: 'before', url: page.url(), head: t.slice(0, 600) });

  // Link as v8 if prompt is up
  await softClick(page, /Yes, this is v8/i, 'yes_v8');

  await softClick(page, /Upload a corrected version/i, 'corrected');
  await softClick(page, /Upload new version/i, 'new_version');
  const inputs = page.locator('input[type="file"]');
  if (await inputs.count()) {
    await inputs.first().setInputFiles(ZIP);
    log({ event: 'uploaded', zip: ZIP, size: fs.statSync(ZIP).size });
    await sleep(25000);
  } else {
    log({ event: 'no_file_input' });
  }

  // After upload, link dialog may appear again
  await softClick(page, /Yes, this is v8/i, 'yes_v8_after');
  await softClick(page, /Yes, this is v\d+/i, 'yes_vx_after');

  t = await body(page);
  fs.writeFileSync(path.join(OUT, 'f-upload-g857-after.txt'), t);
  log({ event: 'after_upload', url: page.url(), head: t.slice(0, 800) });

  // Delivery Gate first (QC check), not PreQC
  const delivery =
    (await softClick(page, /^Re-run$/i, 'rerun')) ||
    (await softClick(page, /Re-run QC check/i, 'rerun_qc')) ||
    (await softClick(page, /Run QC check/i, 'run_qc'));
  await sleep(5000);
  const oracle =
    (await softClick(page, /Re-run QC-Oracle-GLM/i, 'oracle-rerun')) ||
    (await softClick(page, /Run QC-Oracle-GLM/i, 'oracle'));

  t = await body(page);
  fs.writeFileSync(path.join(OUT, 'f-upload-g857-gates.txt'), t);
  log({
    event: 'g857_gates',
    delivery,
    oracle,
    head: t.slice(0, 900),
  });

  fs.writeFileSync(
    path.join(OUT, 'f-upload-fix-status.json'),
    JSON.stringify(
      {
        at: new Date().toISOString(),
        delivery,
        oracle,
        url: page.url(),
        zip: ZIP,
      },
      null,
      2
    )
  );
  log({ event: 'KEEP_CHROME' });
  await new Promise(() => {});
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
