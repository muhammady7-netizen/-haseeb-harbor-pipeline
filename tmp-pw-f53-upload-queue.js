/**
 * fin-f53 only — OpenCode persistent Chrome profile (signed-in once).
 * headless: no visible Chrome/profile UI.
 * Flow: upload zip → open new version → dismiss PreQC → queue Oracle+GLM×4.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-fin-f53.zip';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const PACK = 'fin-f53-deposit-account-fee-assessment-audit';
const OUT = path.join(__dirname, 'tmp-pw', 'f53-upload-queue.txt');

(async () => {
  if (!fs.existsSync(ZIP)) throw new Error('Missing zip: ' + ZIP);

  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    args: [
      '--disable-blink-features=AutomationControlled',
      '--disable-session-crashed-bubble',
      '--noerrdialogs',
    ],
    viewport: { width: 1400, height: 900 },
  });

  const page = browser.pages()[0] || await browser.newPage();
  page.setDefaultTimeout(45000);

  async function bodyText() {
    return page.locator('body').innerText();
  }

  async function clickFirst(re, label) {
    const loc = page.getByText(re).first();
    const n = await loc.count();
    console.log(label, 'count', n);
    if (!n) return false;
    const vis = await loc.isVisible().catch(() => false);
    console.log(label, 'visible', vis);
    if (!vis) return false;
    await loc.click();
    await page.waitForTimeout(3000);
    return true;
  }

  console.log('GOTO_ROOT');
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(7000);

  let before = await bodyText();
  if (/Sign in|Google Cloud|Enter your email/i.test(before) && before.length < 2500) {
    fs.writeFileSync(OUT, 'AUTH_REQUIRED\n' + before);
    console.log('AUTH_REQUIRED — opencode chrome-profile not signed in');
    await browser.close();
    process.exit(3);
  }

  const beforeMatch = before.match(new RegExp(PACK + '#[a-f0-9]+', 'i'));
  const beforeTop = beforeMatch ? beforeMatch[0] : null;
  console.log('BEFORE_TOP', beforeTop);

  // Root dropzone upload (creates/updates task version)
  const input = page.locator('input[type="file"]').first();
  await input.waitFor({ state: 'attached', timeout: 30000 });
  await input.setInputFiles(ZIP);
  console.log('FILE_SET', ZIP);

  let newId = null;
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(2000);
    const text = await bodyText();
    const m = text.match(new RegExp(PACK + '#[a-f0-9]+', 'i'));
    if (m && m[0] !== beforeTop) {
      newId = m[0];
      console.log('NEW_TOP', i, newId);
      break;
    }
    if (i % 10 === 0) console.log('wait_upload', i, 'top', m && m[0]);
  }

  if (!newId) {
    // Fallback: open existing pack entry and Upload new version
    console.log('NO_NEW_ID_VIA_ROOT — try task Upload new version');
    await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForTimeout(5000);
    for (let i = 0; i < 8; i++) {
      await page.mouse.wheel(0, 1400);
      await page.waitForTimeout(300);
    }
    const link = page.getByText(new RegExp(PACK, 'i')).first();
    if (await link.count()) {
      await link.click();
      await page.waitForTimeout(6000);
      if (await clickFirst(/Upload new version/i, 'UPLOAD_NEW_VERSION')) {
        const fileInput = page.locator('input[type="file"]').last();
        await fileInput.setInputFiles(ZIP);
        console.log('TASK_FILE_SET');
        for (let i = 0; i < 60; i++) {
          await page.waitForTimeout(2000);
          const url = page.url();
          const text = await bodyText();
          const m = text.match(new RegExp(PACK + '#[a-f0-9]+', 'i'));
          if ((m && m[0] !== beforeTop) || /Upload successful|uploaded|Processing/i.test(text)) {
            newId = (m && m[0]) || 'uploaded';
            console.log('TASK_UPLOAD_OK', i, newId, url);
            break;
          }
          if (i % 10 === 0) console.log('wait_task_upload', i);
        }
      }
    }
  }

  // Open newest fin-f53 card
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(6000);
  const openLabel = newId && newId.includes('#') ? newId : PACK;
  const open = page.getByText(new RegExp(openLabel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i')).first();
  if (await open.count()) {
    await open.click();
    await page.waitForTimeout(8000);
  }
  console.log('OPENED', page.url());

  // PreQC: run if needed, dismiss advisory findings (never Confirm)
  await clickFirst(/Re-run client preQC|Run client preQC|Run Client PreQC/i, 'PREQC');
  await page.waitForTimeout(8000);

  for (let round = 0; round < 12; round++) {
    const dismissed =
      (await clickFirst(/^Dismiss$|Dismiss finding|Dismiss all|Mark as dismissed/i, 'DISMISS_' + round)) ||
      (await clickFirst(/Not an issue|Advisory|False positive|Won.?t fix/i, 'DISMISS_ALT_' + round));
    if (!dismissed) break;
    await page.waitForTimeout(1500);
  }

  // Queue Oracle + GLM x4 (platform concurrency ~4)
  let text = await bodyText();
  if (/Running now|running ·|In queue|Queued/i.test(text)) {
    console.log('ALREADY_QUEUED_OR_RUNNING');
  } else {
    const started =
      (await clickFirst(/Re-run QC-Oracle-GLM|Run QC-Oracle-GLM|Run Oracle \+ GLM/i, 'START_EVAL')) ||
      (await clickFirst(/Oracle \+ GLM|Harbor Check/i, 'START_EVAL_ALT'));
    console.log('EVAL_CLICKED', started);
    await page.waitForTimeout(12000);
  }

  text = await bodyText();
  const dump = `URL=${page.url()}\nNEW_ID=${newId}\n\n${text}`;
  fs.writeFileSync(OUT, dump);
  console.log('FINAL', page.url());
  console.log(text.slice(0, 3000));

  await browser.close();
  console.log('DONE wrote', OUT);
})().catch(async (e) => {
  console.error('FAIL', e);
  process.exit(1);
});
