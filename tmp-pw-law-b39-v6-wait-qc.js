/**
 * law-b39 headless: wait for QC bundle read, open newest task, start PreQC + Oracle-GLM.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ZIP =
  'C:/Users/Haseeb Mirza/Downloads/law-b39-l16-custody-letter-instruction-audit.zip';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function dump(name, text) {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(
    path.join(OUT, name),
    typeof text === 'string' ? text : JSON.stringify(text, null, 2)
  );
}
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
async function clickEnabled(page, re) {
  const loc = page.getByRole('button', { name: re }).first();
  if (!(await loc.count())) return { ok: false, reason: 'missing' };
  const disabled =
    (await loc.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
    (await loc.isDisabled().catch(() => false));
  if (disabled) {
    const title = await loc.getAttribute('title').catch(() => '');
    return { ok: false, reason: 'disabled', title };
  }
  await loc.click({ timeout: 15000 });
  return { ok: true };
}

(async () => {
  const result = { ok: false, step: 'start', url: null, errors: [] };
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
    result.step = 'goto';
    await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(6000);

    let t = await body(page);
    // If still reading or no fresh upload, re-upload and wait longer
    if (/reading the bundle/i.test(t) || true) {
      result.step = 'reupload';
      const input = page.locator('input[type="file"]').first();
      if (!(await input.count())) throw new Error('no file input');
      await input.setInputFiles(ZIP);
      console.log(JSON.stringify({ event: 'reupload_set' }));

      // Wait up to ~3 min for reading to finish / navigate / new card
      let done = false;
      for (let i = 0; i < 36; i++) {
        await sleep(5000);
        t = await body(page);
        const url = page.url();
        dump('law-b39-v6-poll.txt', `i=${i}\nurl=${url}\n` + t.slice(0, 4000));
        console.log(JSON.stringify({ event: 'poll', i, url, reading: /reading the bundle/i.test(t) }));
        if (url.includes('task=content-')) {
          done = true;
          break;
        }
        if (!/reading the bundle/i.test(t) && i > 2) {
          // look for error toast
          if (/invalid|error|failed|could not/i.test(t.slice(0, 1500))) {
            await page.screenshot({ path: path.join(OUT, 'law-b39-v6-upload-err.png'), fullPage: true });
            dump('law-b39-v6-upload-err.txt', t.slice(0, 8000));
          }
          break;
        }
      }
      await page.screenshot({ path: path.join(OUT, 'law-b39-v6-after-wait.png'), fullPage: true });
    }

    result.url = page.url();
    t = await body(page);

    // Open newest law-b39 task if still on list
    if (!page.url().includes('task=content-')) {
      result.step = 'open_latest';
      // Prefer first "Open task" near law-b39-l16
      const openBtns = page.getByRole('button', { name: /Open task/i });
      const n = await openBtns.count();
      console.log(JSON.stringify({ event: 'open_buttons', n }));
      // Click first Open task (most recent)
      if (n > 0) {
        await openBtns.first().click();
        await sleep(8000);
      } else {
        // try link
        const link = page.getByText('law-b39-l16-custody-letter-instruction-audit').first();
        if (await link.count()) {
          await link.click();
          await sleep(8000);
        }
      }
    }

    result.url = page.url();
    t = await body(page);
    dump('law-b39-v6-task.txt', t.slice(0, 12000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v6-task.png'), fullPage: true });
    console.log(JSON.stringify({ event: 'on_task', url: result.url }));

    // PreQC
    result.step = 'preqc';
    let r = await clickEnabled(page, /Run Client PreQC|Run PreQC|Start PreQC|Client PreQC/i);
    if (!r.ok) r = await clickEnabled(page, /PreQC/i);
    console.log(JSON.stringify({ event: 'preqc', ...r }));
    await sleep(5000);
    // confirm start if modal
    const confirm = page.getByRole('button', { name: /^Confirm$/i }).first();
    if (await confirm.count()) {
      const bt = await body(page);
      if (/preqc|pre-qc|start|run/i.test(bt) && !/false positive|dismiss/i.test(bt)) {
        await confirm.click().catch(() => {});
        await sleep(4000);
      }
    }
    await page.screenshot({ path: path.join(OUT, 'law-b39-v6-preqc.png'), fullPage: true });
    dump('law-b39-v6-preqc.txt', (await body(page)).slice(0, 10000));

    // Poll PreQC briefly then try GLM
    for (let i = 0; i < 24; i++) {
      await sleep(10000);
      t = await body(page);
      dump('law-b39-v6-preqc-poll.txt', `i=${i}\n` + t.slice(0, 5000));
      const glm = await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i);
      console.log(JSON.stringify({ event: 'glm_try', i, ...glm }));
      if (glm.ok) {
        await sleep(8000);
        break;
      }
      // if slots full, keep waiting
      if (/slots? are currently in use|queue/i.test(t)) {
        console.log(JSON.stringify({ event: 'slots_busy', i }));
        continue;
      }
      // if PreQC still running
      if (/PreQC.*(running|in progress|pending)/i.test(t)) continue;
      // if PreQC failed, dump and stop
      if (/PreQC.*(fail|error)/i.test(t)) break;
      // if already has findings / report, still try GLM once more then stop
      if (i >= 6 && !/PreQC.*(running|in progress)/i.test(t)) break;
    }

    t = await body(page);
    result.url = page.url();
    result.finalSnippet = t.slice(0, 2500);
    dump('law-b39-v6-final.txt', t.slice(0, 12000));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v6-final.png'), fullPage: true });
    result.ok = true;
    result.step = 'done';
    dump('law-b39-v6-result.json', result);
    console.log(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.errors.push(String(e && e.stack ? e.stack : e));
    dump('law-b39-v6-result.json', result);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v6-error.png'), fullPage: true }).catch(() => {});
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
