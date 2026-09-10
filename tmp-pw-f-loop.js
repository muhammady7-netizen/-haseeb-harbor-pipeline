/**
 * Session F durable portal driver — gen-g857 v2 + code-c251.
 * Shared OpenCode chrome-profile; retries if stolen; waits on 3-slot limit.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const G857 =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2a489be4b73a943d11d2c52efefae8c6-v2';
const C251 =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-db0490a135ad1cc1e0d71549021ddef3-v1';
const ROOT = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = 'tmp-pw';
const MAX_ROUNDS = 50;
const WAIT_MS = 60000;

function dump(name, text) {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(`${OUT}/${name}`, text);
}
function log(o) {
  const line = typeof o === 'string' ? o : JSON.stringify(o);
  console.log(line);
  fs.appendFileSync(`${OUT}/f-loop.log`, line + '\n');
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {
  let last;
  for (let i = 0; i < 8; i++) {
    try {
      return await chromium.launchPersistentContext(PROFILE, {
        headless: true,
        channel: 'chrome',
        acceptDownloads: true,
      });
    } catch (e) {
      last = e;
      log({ event: 'LAUNCH_BUSY', i, error: String(e).slice(0, 160) });
      await sleep(3000 + i * 1500);
    }
  }
  throw last;
}

async function clickBtn(page, label) {
  const re = new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
  const btn = page.getByRole('button', { name: re }).first();
  const n = await btn.count();
  if (!n) {
    log({ event: 'btn_missing', label });
    return false;
  }
  const disabled = await btn.getAttribute('aria-disabled').catch(() => null);
  const title = await btn.getAttribute('title').catch(() => '');
  if (disabled === 'true' || /slots are currently in use/i.test(title || '')) {
    log({ event: 'btn_disabled', label, title });
    return false;
  }
  try {
    await btn.click({ timeout: 10000 });
    log({ event: 'clicked', label });
    await sleep(4000);
    return true;
  } catch (e) {
    log({ event: 'click_fail', label, error: String(e).slice(0, 120) });
    return false;
  }
}

async function driveTask(page, name, url, expectRe) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(7000);
  let body = await page.locator('body').innerText().catch(() => '');
  dump(`f-${name}-body.txt`, body);
  if (/accounts\.google|Enter your email/i.test(page.url() + body)) {
    return { status: 'need_login' };
  }
  if (!expectRe.test(body)) {
    log({ event: 'wrong_page', name, url: page.url(), head: body.slice(0, 200) });
    return { status: 'wrong_page' };
  }

  const slotsFull = /3 run slots are currently in use/i.test(body);
  const already =
    /QC-Oracle-GLM[\s\S]{0,200}(running|in progress|queued)/i.test(body) ||
    /Evaluation[\s\S]{0,80}(running|in progress)/i.test(body) ||
    /Client preQC[\s\S]{0,120}(running|in progress)/i.test(body);

  if (already) {
    log({ event: 'already_inflight', name });
    return { status: 'inflight', slotsFull, url: page.url() };
  }

  const pre = (await clickBtn(page, 'Run client preQC')) || (await clickBtn(page, 'Re-run client preQC'));
  const ev = (await clickBtn(page, 'Run QC-Oracle-GLM')) || (await clickBtn(page, 'Re-run QC-Oracle-GLM'));
  await sleep(6000);
  body = await page.locator('body').innerText().catch(() => '');
  dump(`f-${name}-after.txt`, body);
  const running =
    /running|queued|in progress/i.test(body) ||
    /Client PreQC[\s\S]{0,80}(Review required|Complete|Passed)/i.test(body);
  log({
    event: 'task',
    name,
    pre,
    ev,
    slotsFull: slotsFull || /slots are currently in use/i.test(body),
    running,
    url: page.url(),
    head: body.slice(0, 500),
  });
  return {
    status: pre || ev || running ? 'started' : slotsFull ? 'slots_full' : 'clicked_none',
    pre,
    ev,
    running,
    slotsFull,
    url: page.url(),
  };
}

async function oneRound(round) {
  let browser;
  try {
    browser = await launch();
  } catch (e) {
    return { status: 'busy', error: String(e).slice(0, 200) };
  }
  try {
    const page = browser.pages()[0] || (await browser.newPage());
    await page.goto(ROOT, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(5000);
    const root = await page.locator('body').innerText().catch(() => '');
    dump(`f-root-${round}.txt`, root);
    const hits = root
      .split(/\n+/)
      .filter((l) => /QC running|g857|c251|queued|fae8c6|1ddef3/i.test(l))
      .slice(0, 20);
    log({ event: 'root', round, hits });

    const g857 = await driveTask(page, 'g857', G857, /gen-g857/i);
    const c251 = await driveTask(page, 'c251', C251, /code-c251/i);
    const status = { round, at: new Date().toISOString(), g857, c251 };
    dump('f-loop-status.json', JSON.stringify(status, null, 2));
    dump('track-status.json', JSON.stringify(status, null, 2));

    await sleep(8000);
    try {
      await browser.close();
    } catch (_) {}
    return status;
  } catch (e) {
    log({ event: 'ROUND_FAIL', error: String(e).slice(0, 300) });
    try {
      if (browser) await browser.close();
    } catch (_) {}
    return { status: 'error', error: String(e).slice(0, 300) };
  }
}

(async () => {
  fs.writeFileSync(`${OUT}/f-loop.log`, '');
  for (let round = 1; round <= MAX_ROUNDS; round++) {
    log(`\n==== F ROUND ${round}/${MAX_ROUNDS} ====`);
    const r = await oneRound(round);
    log({ event: 'RESULT', round, g857: r.g857 && r.g857.status, c251: r.c251 && r.c251.status });

    if ((r.g857 && r.g857.status === 'need_login') || (r.c251 && r.c251.status === 'need_login')) {
      process.exit(2);
    }
    const gOk = r.g857 && ['started', 'inflight'].includes(r.g857.status);
    const cOk = r.c251 && ['started', 'inflight'].includes(r.c251.status);
    if (gOk && cOk) {
      log({ event: 'BOTH_ADVANCING' });
      // keep polling a few more rounds for completion tracking
    }
    log(`sleep ${WAIT_MS}`);
    await sleep(WAIT_MS);
  }
  log('DONE_MAX_ROUNDS');
  process.exit(0);
})().catch((e) => {
  console.error('FATAL', e);
  process.exit(1);
});
