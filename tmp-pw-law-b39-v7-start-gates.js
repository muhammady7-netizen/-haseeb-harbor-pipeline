/**
 * law-b39: force-start Client PreQC then QC-Oracle-GLM on the live task.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-802c5cc4bad361c319359364b961613a-v1';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function clearLocks() {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
}
async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function clickExact(page, name) {
  const btn = page.getByRole('button', { name, exact: true }).first();
  if (!(await btn.count())) {
    const loose = page.getByRole('button', { name: new RegExp(name, 'i') }).first();
    if (!(await loose.count())) return { ok: false, reason: 'missing', name };
    const disabled =
      (await loose.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await loose.isDisabled().catch(() => false));
    if (disabled) {
      return {
        ok: false,
        reason: 'disabled',
        name,
        title: await loose.getAttribute('title').catch(() => ''),
      };
    }
    await loose.click({ timeout: 15000 });
    return { ok: true, name, mode: 'loose' };
  }
  const disabled =
    (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
    (await btn.isDisabled().catch(() => false));
  if (disabled) {
    return {
      ok: false,
      reason: 'disabled',
      name,
      title: await btn.getAttribute('title').catch(() => ''),
    };
  }
  await btn.click({ timeout: 15000 });
  return { ok: true, name, mode: 'exact' };
}

(async () => {
  const result = { ok: false, url: URL, errors: [] };
  clearLocks();
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    viewport: { width: 1440, height: 960 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = context.pages()[0] || (await context.newPage());
  try {
    await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(7000);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v7-before.png'), fullPage: true });
    fs.writeFileSync(path.join(OUT, 'law-b39-v7-before.txt'), (await body(page)).slice(0, 10000));

    // List buttons for debug
    const names = await page.getByRole('button').allTextContents();
    fs.writeFileSync(path.join(OUT, 'law-b39-v7-buttons.txt'), names.join('\n'));
    console.log(JSON.stringify({ event: 'buttons', names: names.slice(0, 40) }));

    let r = await clickExact(page, 'Run client preQC');
    console.log(JSON.stringify({ event: 'preqc', ...r }));
    await sleep(3000);
    // confirm dialog if any
    for (const label of ['Confirm', 'Start', 'OK', 'Run']) {
      const c = page.getByRole('button', { name: label, exact: true }).first();
      if (await c.count()) {
        const t = await body(page);
        if (/preqc|pre-qc|client pre/i.test(t) && !/false positive/i.test(t)) {
          await c.click().catch(() => {});
          console.log(JSON.stringify({ event: 'confirm', label }));
          await sleep(2000);
        }
      }
    }
    await sleep(5000);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v7-preqc.png'), fullPage: true });
    fs.writeFileSync(path.join(OUT, 'law-b39-v7-preqc.txt'), (await body(page)).slice(0, 10000));

    // Try GLM immediately (may be blocked until PreQC done / slots)
    r = await clickExact(page, 'Run QC-Oracle-GLM');
    console.log(JSON.stringify({ event: 'glm', ...r }));
    await sleep(3000);
    for (const label of ['Confirm', 'Start', 'OK', 'Run']) {
      const c = page.getByRole('button', { name: label, exact: true }).first();
      if (await c.count()) {
        const t = await body(page);
        if (/oracle|glm|evaluation|slot/i.test(t) && !/false positive/i.test(t)) {
          await c.click().catch(() => {});
          console.log(JSON.stringify({ event: 'confirm_glm', label }));
          await sleep(2000);
        }
      }
    }
    await sleep(8000);

    // Poll up to ~4 min for PreQC progress / GLM start
    for (let i = 0; i < 24; i++) {
      const t = await body(page);
      const status = {
        i,
        preqcRunning: /preqc.*(running|in progress|queued)|Client preQC.*(running|in progress)/i.test(t),
        preqcDone: /Client preQC.*(pass|fail|complete|done)|PreQC.*(pass|fail|complete)/i.test(t),
        glmRunning: /QC-Oracle-GLM.*(running|in progress|queued)|Oracle.*(running|in progress)/i.test(t),
        slots: /slots? are currently in use/i.test(t),
        notYet: /Not run yet/i.test(t),
      };
      console.log(JSON.stringify({ event: 'poll', ...status }));
      fs.writeFileSync(path.join(OUT, 'law-b39-v7-poll.txt'), t.slice(0, 8000));
      if (status.glmRunning || (status.preqcDone && !status.notYet)) break;
      if (!status.glmRunning) {
        const again = await clickExact(page, 'Run QC-Oracle-GLM');
        console.log(JSON.stringify({ event: 'glm_retry', ...again }));
      }
      await sleep(10000);
    }

    const final = await body(page);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v7-final.png'), fullPage: true });
    fs.writeFileSync(path.join(OUT, 'law-b39-v7-final.txt'), final.slice(0, 12000));
    result.ok = true;
    result.snippet = final.slice(0, 2000);
    fs.writeFileSync(path.join(OUT, 'law-b39-v7-result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.errors.push(String(e && e.stack ? e.stack : e));
    fs.writeFileSync(path.join(OUT, 'law-b39-v7-result.json'), JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
