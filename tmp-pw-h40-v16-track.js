/**
 * Strict Final-QC poll for h40 v16 content-2db1ccc / #214042.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2db1ccc90bf524a99a3747075a20cfa5-v1';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'health-h40-critical-result-acknowledgement';
const SHORT = '20cfa5';
const CONTENT = '2db1ccc';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function clearLocks() {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
}

function onTaskPage(t, url) {
  const onHash = /#task=content-2db1ccc/i.test(url);
  const hasUpload = /Upload new version/i.test(t);
  const hasStem = new RegExp(STEM, 'i').test(t);
  const rootDrop = /Drop a task here, or click to browse/i.test(t) && !hasUpload;
  return onHash && hasStem && hasUpload && !rootDrop;
}

async function openv16(page) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  const row = page
    .locator('div,li,a,article,section')
    .filter({ hasText: new RegExp(`${STEM}#${SHORT}|${STEM}[\\s\\S]{0,80}#${SHORT}`, 'i') })
    .first();
  if (await row.count()) {
    await row.scrollIntoViewIfNeeded().catch(() => {});
    const openBtn = row.getByRole('button', { name: /^Open$/i }).first();
    const openTxt = row.getByText(/^Open$/).first();
    if (await openBtn.count()) await openBtn.click({ force: true, timeout: 15000 });
    else if (await openTxt.count()) await openTxt.click({ force: true, timeout: 15000 });
    else await row.click({ force: true, timeout: 15000 });
  } else {
    const exact = page.getByText(new RegExp(`${STEM}#${SHORT}`, 'i')).first();
    if (await exact.count()) await exact.click({ force: true, timeout: 15000 });
    else {
      await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(5000);
      const firstOpen = page.getByRole('button', { name: /^Open$/i }).first();
      if (await firstOpen.count()) await firstOpen.click({ force: true, timeout: 10000 }).catch(() => null);
    }
  }
  await sleep(8000);
  let t = await page.locator('body').innerText();
  if (!/Upload new version/i.test(t)) {
    const firstOpen = page.getByRole('button', { name: /^Open$/i }).first();
    if (await firstOpen.count()) {
      await firstOpen.click({ force: true, timeout: 10000 }).catch(() => null);
      await sleep(8000);
    }
  }
  if (!/#task=content-2db1ccc/i.test(page.url())) {
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(7000);
  }
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  for (let i = 0; i < 120; i++) {
    clearLocks();
    let browser;
    try {
      browser = await chromium.launchPersistentContext(PROFILE, {
        headless: true,
        channel: 'chrome',
        args: ['--disable-blink-features=AutomationControlled'],
      });
      const page = browser.pages()[0] || (await browser.newPage());
      await openv16(page);
      const t = await page.locator('body').innerText();
      fs.writeFileSync(path.join(OUT, 'h40-v16-live.txt'), `URL=${page.url()}\n\n${t}`);
      const okPage = onTaskPage(t, page.url());
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
      const listQc =
        !okPage &&
        new RegExp(`${STEM}#${SHORT}[\\s\\S]{0,80}QC running`, 'i').test(t);
      const s = {
        okPage,
        oracle: oracleFail ? 'FAIL' : oraclePass ? score || '1.0' : null,
        glm: glm ? `${glm}/4` : null,
        tooEasy,
        running: running || listQc,
        harborFail,
        ready,
        listQc,
      };
      console.log(JSON.stringify({ event: 'poll', i, url: page.url(), ...s }));

      if (okPage && !running && (s.oracle || s.tooEasy || s.harborFail || s.ready || s.glm)) {
        // settle only when GLM completed or terminal state
        const settled =
          s.tooEasy ||
          s.ready ||
          s.harborFail ||
          (s.oracle && s.glm) ||
          (s.oracle === 'FAIL');
        if (settled) {
          console.log(JSON.stringify({ event: 'done', ...s }));
          fs.writeFileSync(path.join(OUT, 'h40-v16-final-done.txt'), `URL=${page.url()}\n\n${t}`);
          await browser.close().catch(() => {});
          process.exit(0);
        }
      }
    } catch (e) {
      console.log(JSON.stringify({ event: 'poll_error', i, error: String(e).slice(0, 240) }));
    } finally {
      if (browser) await browser.close().catch(() => {});
    }
    await sleep(45000);
  }
  console.log(JSON.stringify({ event: 'timeout' }));
  process.exit(2);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});

