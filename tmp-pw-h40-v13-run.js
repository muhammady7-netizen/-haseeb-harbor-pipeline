/**
 * h40 v11: headless upload + Final QC only (skip PreQC) + track to Harbor settle.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-health-h40.zip';
const STEM = 'health-h40-critical-result-acknowledgement';
const OUT = path.join(__dirname, 'tmp-pw');
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

async function openLatest(page) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(4500);
  // prefer newest card: first STEM match near top
  const link = page.getByText(STEM, { exact: false }).first();
  await link.click({ timeout: 20000 });
  await sleep(8000);
  return body(page);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  let browser = await launch();
  let page = browser.pages()[0] || (await browser.newPage());

  // UPLOAD
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(4000);
  await page.locator('input[type="file"]').first().setInputFiles(ZIP);
  console.log(JSON.stringify({ event: 'upload_started' }));
  for (let i = 0; i < 90; i++) {
    await sleep(2000);
    const t = await body(page);
    if (/preparing upload/i.test(t)) continue;
    break;
  }
  let t = await body(page);
  fs.writeFileSync(path.join(OUT, 'h40-v13-after-upload.txt'), `URL=${page.url()}\n\n${t}`);
  console.log(JSON.stringify({ event: 'upload_settled', url: page.url(), head: t.slice(0, 400) }));

  // OPEN LATEST + START FINAL QC (skip PreQC)
  let started = false;
  for (let i = 0; i < 40; i++) {
    try {
      if (!browser) {
        browser = await launch();
        page = browser.pages()[0] || (await browser.newPage());
      }
      t = await openLatest(page);
      fs.writeFileSync(path.join(OUT, `h40-v13-open-${i}.txt`), `URL=${page.url()}\n\n${t}`);
      console.log(
        JSON.stringify({
          event: 'open',
          i,
          url: page.url(),
          busy: /run slots are currently in use/i.test(t),
          head: t.replace(/\s+/g, ' ').slice(0, 280),
        })
      );
      // ONLY Final QC
      started = await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i);
      if (started) {
        t = await body(page);
        fs.writeFileSync(path.join(OUT, 'h40-v13-gates-started.txt'), `URL=${page.url()}\n\n${t}`);
        console.log(JSON.stringify({ event: 'final_qc_started', url: page.url() }));
        break;
      }
    } catch (e) {
      console.log(JSON.stringify({ event: 'open_error', i, error: String(e).slice(0, 200) }));
      await browser.close().catch(() => {});
      browser = null;
    }
    await sleep(20000);
  }
  if (!started) {
    console.log(JSON.stringify({ event: 'defer_final_qc', reason: 'slots_busy' }));
  }
  await browser?.close().catch(() => {});

  // TRACK until Harbor settles
  for (let i = 0; i < 100; i++) {
    clearLocks();
    browser = await launch();
    try {
      page = browser.pages()[0] || (await browser.newPage());
      t = await openLatest(page);
      fs.writeFileSync(path.join(OUT, 'h40-v13-live.txt'), `URL=${page.url()}\n\n${t}`);
      const oraclePass = /Oracle\s+Passed/i.test(t);
      const oracleFail = /Oracle\s+Failed/i.test(t);
      const score = /Passed\s+([\d.]+)\s+on/i.exec(t)?.[1];
      const glm = /Completed\s*Â·\s*(\d)\/4\s+passed/i.exec(t)?.[1];
      const running = /Running now|Oracle Running|GLM-5\.2[^\n]*Running|Harbor Check[\s\S]{0,40}running/i.test(t);
      const harborFail = /Harbor Check[\s\S]{0,120}FAIL|blocking finding/i.test(t);
      const ready = /READY_FOR_FINALIZATION/i.test(t);
      const changes = /changes needed/i.test(t);
      const s = {
        oracle: oracleFail ? 'FAIL' : oraclePass ? score || '1.0' : null,
        glm: glm ? `${glm}/4` : null,
        running,
        harborFail,
        ready,
        changes,
      };
      console.log(JSON.stringify({ event: 'poll', i, url: page.url(), ...s }));
      fs.writeFileSync(
        path.join(OUT, 'h40-v13-track-status.json'),
        JSON.stringify({ at: new Date().toISOString(), ...s, url: page.url() }, null, 2)
      );
      if ((s.oracle || s.ready || s.harborFail || s.changes) && !s.running) {
        // wait until not running OR harbor disposition present
        if (s.harborFail || s.ready || s.changes || /trainer finding/i.test(t)) {
          console.log(JSON.stringify({ event: 'done', ...s }));
          fs.writeFileSync(path.join(OUT, 'h40-v13-final-done.txt'), `URL=${page.url()}\n\n${t}`);
          await browser.close().catch(() => {});
          process.exit(0);
        }
      }
      // if Final QC never started and button free, start it
      if (!started && !running) {
        const ok = await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i);
        if (ok) {
          started = true;
          console.log(JSON.stringify({ event: 'final_qc_started_late', url: page.url() }));
        }
      }
    } catch (e) {
      console.log(JSON.stringify({ event: 'poll_error', i, error: String(e).slice(0, 200) }));
    } finally {
      await browser.close().catch(() => {});
    }
    await sleep(45000);
  }
  console.log(JSON.stringify({ event: 'timeout' }));
  process.exit(2);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});

