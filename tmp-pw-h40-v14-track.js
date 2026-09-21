/**
 * Strict Final-QC poll for h40 v14 content-e86ad926 / short #88e6dd only.
 * Opens that Recent-tasks row via its Open control; ignores other h40 versions.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-e86ad926a3cd0b88156a325a0288e6dd-v1';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'health-h40-critical-result-acknowledgement';
const SHORT = '88e6dd';
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
  const onHash = /#task=content-e86ad926/i.test(url);
  const hasUpload = /Upload new version/i.test(t);
  const hasStem = new RegExp(STEM, 'i').test(t);
  const rootDrop = /Drop a task here, or click to browse/i.test(t) && !hasUpload;
  return onHash && hasStem && hasUpload && !rootDrop;
}

async function openV14(page) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);

  // Row that contains BOTH stem and #88e6dd (latest v14 card)
  const row = page
    .locator('div,li,a,article,section')
    .filter({ hasText: new RegExp(`${STEM}#${SHORT}|${STEM}[\\s\\S]{0,80}#${SHORT}`, 'i') })
    .first();

  let opened = false;
  if (await row.count()) {
    await row.scrollIntoViewIfNeeded().catch(() => {});
    const openBtn = row.getByRole('button', { name: /^Open$/i }).first();
    const openTxt = row.getByText(/^Open$/).first();
    if (await openBtn.count()) {
      await openBtn.click({ force: true, timeout: 15000 });
      opened = true;
    } else if (await openTxt.count()) {
      await openTxt.click({ force: true, timeout: 15000 });
      opened = true;
    } else {
      await row.click({ force: true, timeout: 15000 });
      opened = true;
    }
  }

  // Fallback: click exact "stem#88e6dd" text, then first Open if still root
  if (!opened) {
    const exact = page.getByText(new RegExp(`${STEM}#${SHORT}`, 'i')).first();
    if (await exact.count()) {
      await exact.click({ force: true, timeout: 15000 });
      opened = true;
    }
  }
  await sleep(8000);

  let t = await page.locator('body').innerText();
  if (!/Upload new version/i.test(t)) {
    // Top Open is the #88e6dd card when it is first in Recent tasks
    const firstOpen = page.getByRole('button', { name: /^Open$/i }).first();
    if (await firstOpen.count()) {
      await firstOpen.click({ force: true, timeout: 10000 }).catch(() => null);
      await sleep(8000);
      t = await page.locator('body').innerText();
    }
  }

  // Version-link dialog
  if (/Yes, this is v\d+/i.test(t)) {
    await page.getByRole('button', { name: /Yes, this is v\d+/i }).first().click().catch(() => null);
    await sleep(4000);
  }

  if (!/#task=content-e86ad926/i.test(page.url()) || !/Upload new version/i.test(t)) {
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    // SPA often ignores hash alone — click Open again after hash set
    t = await page.locator('body').innerText();
    if (/Drop a task here/i.test(t) && !/Upload new version/i.test(t)) {
      const firstOpen = page.getByRole('button', { name: /^Open$/i }).first();
      if (await firstOpen.count()) {
        await firstOpen.click({ force: true, timeout: 10000 }).catch(() => null);
        await sleep(8000);
      }
    }
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
      await openV14(page);
      const t = await page.locator('body').innerText();
      fs.writeFileSync(path.join(OUT, 'h40-v14-live.txt'), `URL=${page.url()}\n\n${t}`);
      const okPage = onTaskPage(t, page.url());
      const oraclePass = /Oracle\s+Passed/i.test(t);
      const oracleFail = /Oracle\s+Failed/i.test(t);
      const score = /Passed\s+([\d.]+)\s+on/i.exec(t)?.[1];
      const glm = /Completed\s*·\s*(\d)\/4\s+passed/i.exec(t)?.[1];
      const tooEasy = okPage && /TOO_EASY|Difficulty is too easy/i.test(t);
      const running =
        okPage &&
        /Running now|Oracle Running|GLM-5\.2[^\n]*Running|starting now|4 scored GLM runs are in progress|Harbor Check[\s\S]{0,40}running|QC check[\s\S]{0,40}Running/i.test(
          t
        );
      const harborFail =
        okPage && /Harbor Check[\s\S]{0,120}FAIL|Finalization held: \d+ blocking/i.test(t);
      const ready = okPage && /READY_FOR_FINALIZATION/i.test(t);
      const listQc = !okPage && /health-h40-critical-result-acknowledgement#88e6dd[\s\S]{0,80}QC running/i.test(t);
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

      if (okPage && !running) {
        const btn = page
          .getByRole('button', { name: /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i })
          .first();
        if (await btn.count()) {
          const disabled =
            (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
            (await btn.isDisabled().catch(() => false));
          if (!disabled && !s.oracle && !s.tooEasy && !s.ready && !s.harborFail) {
            await btn.click();
            console.log(JSON.stringify({ event: 'final_qc_started' }));
            await sleep(5000);
          } else if (disabled) {
            console.log(
              JSON.stringify({
                event: 'final_qc_wait_slot',
                title: await btn.getAttribute('title').catch(() => ''),
              })
            );
          }
        }
      }

      if (okPage && !running && (s.oracle || s.tooEasy || s.harborFail || s.ready)) {
        console.log(JSON.stringify({ event: 'done', ...s }));
        fs.writeFileSync(path.join(OUT, 'h40-v14-final-done.txt'), `URL=${page.url()}\n\n${t}`);
        await browser.close().catch(() => {});
        process.exit(0);
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
