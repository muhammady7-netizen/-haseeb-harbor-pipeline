/**
 * h40 v15: headless upload + Final QC only (skip PreQC) + track until settle.
 * After upload, opens latest health-h40 card and polls Oracle/GLM/Harbor.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-health-h40.zip';
const STEM = 'health-h40-critical-result-acknowledgement';
const OUT = path.join(__dirname, 'tmp-pw');
const TAG = 'h40-v16';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function clearLocks() {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
}

async function launch() {
  clearLocks();
  return chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
}

async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function clickEnabled(page, re) {
  const loc = page.getByRole('button', { name: re }).first();
  if (!(await loc.count())) return false;
  const disabled =
    (await loc.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
    (await loc.isDisabled().catch(() => false));
  if (disabled) {
    console.log(
      JSON.stringify({
        event: 'btn_disabled',
        name: String(re),
        title: await loc.getAttribute('title').catch(() => ''),
      })
    );
    return false;
  }
  await loc.click({ timeout: 15000 });
  await sleep(5000);
  return true;
}

async function openLatestH40(page) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  const row = page
    .locator('div,li,a,article,section')
    .filter({ hasText: new RegExp(STEM, 'i') })
    .first();
  if (await row.count()) {
    await row.scrollIntoViewIfNeeded().catch(() => {});
    const openBtn = row.getByRole('button', { name: /^Open$/i }).first();
    const openTxt = row.getByText(/^Open$/).first();
    if (await openBtn.count()) await openBtn.click({ force: true, timeout: 15000 });
    else if (await openTxt.count()) await openTxt.click({ force: true, timeout: 15000 });
    else await row.click({ force: true, timeout: 15000 });
  } else {
    await page.getByText(STEM, { exact: false }).first().click({ force: true, timeout: 15000 });
  }
  await sleep(8000);
  const latest = page.getByText(/v\d+\s*\(latest\)/i).first();
  if (await latest.count()) {
    try {
      await latest.click({ timeout: 5000 });
      await sleep(4000);
    } catch {}
  }
  if (/Yes, this is v\d+/i.test(await body(page))) {
    await page.getByRole('button', { name: /Yes, this is v\d+/i }).first().click().catch(() => null);
    await sleep(4000);
  }
  return body(page);
}

function onTaskPage(t) {
  return /Upload new version/i.test(t) && new RegExp(STEM, 'i').test(t) && !(/Drop a task here/i.test(t) && !/Upload new version/i.test(t));
}

function summarize(t, okPage) {
  const oraclePass = /Oracle\s+Passed/i.test(t);
  const oracleFail = /Oracle\s+Failed/i.test(t);
  const score = /Passed\s+([\d.]+)\s+on/i.exec(t)?.[1];
  const glm =
    /Completed\s*Â·\s*(?:TOO_EASY\s*Â·\s*)?(\d)\/4\s+passed/i.exec(t)?.[1] ||
    /Completed\s*Â·\s*(\d)\/4\s+passed/i.exec(t)?.[1];
  const tooEasy = okPage && /TOO_EASY|Difficulty is too easy/i.test(t);
  const running =
    okPage &&
    /Running now|Oracle Running|GLM-5\.2[^\n]*Running|starting now|4 scored GLM runs are in progress|Harbor Check[\s\S]{0,40}running/i.test(
      t
    );
  const harborFail =
    okPage && /Harbor Check[\s\S]{0,120}FAIL|Finalization held: \d+ blocking/i.test(t);
  const ready = okPage && /READY_FOR_FINALIZATION/i.test(t);
  return {
    oracle: oracleFail ? 'FAIL' : oraclePass ? score || '1.0' : null,
    glm: glm ? `${glm}/4` : null,
    tooEasy,
    running,
    harborFail,
    ready,
  };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  let browser = await launch();
  let page = browser.pages()[0] || (await browser.newPage());

  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(4000);
  let t = await body(page);
  if (/accounts\.google\.com|Sign in with Google/i.test(t) && !/muhammad\.y7@turing\.com/i.test(t)) {
    console.log(JSON.stringify({ event: 'login_required' }));
    fs.writeFileSync(path.join(OUT, `${TAG}-login.txt`), t);
    await browser.close().catch(() => {});
    process.exit(2);
  }

  await page.locator('input[type="file"]').first().setInputFiles(ZIP);
  console.log(JSON.stringify({ event: 'upload_started', zip: ZIP }));
  for (let i = 0; i < 120; i++) {
    await sleep(2000);
    t = await body(page);
    const url = page.url();
    if (/preparing upload|uploading|reading the bundle/i.test(t)) {
      if (i % 5 === 0) console.log(JSON.stringify({ event: 'upload_wait', i }));
      continue;
    }
    if (/#task=/.test(url) || /Upload new version/i.test(t)) break;
  }
  fs.writeFileSync(path.join(OUT, `${TAG}-after-upload.txt`), `URL=${page.url()}\n\n${t}`);
  console.log(JSON.stringify({ event: 'after_upload', url: page.url() }));

  // Ensure on task page
  if (!/Upload new version/i.test(t)) {
    t = await openLatestH40(page);
    fs.writeFileSync(path.join(OUT, `${TAG}-opened.txt`), `URL=${page.url()}\n\n${t}`);
  }

  // Skip PreQC â€” go straight to Final QC
  for (let attempt = 0; attempt < 40; attempt++) {
    t = await body(page);
    const okPage = onTaskPage(t);
    if (!okPage) {
      t = await openLatestH40(page);
    }
    const s = summarize(t, true);
    const url = page.url();
    fs.writeFileSync(path.join(OUT, `${TAG}-live.txt`), `URL=${url}\n\n${t}`);
    console.log(JSON.stringify({ event: 'poll', attempt, url, ...s }));

    if (!s.running && !s.oracle && !s.tooEasy && !s.ready) {
      const started = await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i);
      if (started) {
        console.log(JSON.stringify({ event: 'final_qc_started' }));
        fs.writeFileSync(path.join(OUT, `${TAG}-gates-started.txt`), `URL=${page.url()}\n\n${await body(page)}`);
      }
    }

    if (!s.running && (s.oracle || s.tooEasy || s.harborFail || s.ready)) {
      console.log(JSON.stringify({ event: 'done', url, ...s }));
      fs.writeFileSync(path.join(OUT, `${TAG}-final-done.txt`), `URL=${url}\n\n${t}`);
      await browser.close().catch(() => {});
      process.exit(0);
    }

    await browser.close().catch(() => {});
    await sleep(45000);
    browser = await launch();
    page = browser.pages()[0] || (await browser.newPage());
    t = await openLatestH40(page);
  }

  console.log(JSON.stringify({ event: 'timeout' }));
  await browser.close().catch(() => {});
  process.exit(2);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});

