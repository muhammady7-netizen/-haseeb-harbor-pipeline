const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ROOT = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const G857_V2 = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2a489be4b73a943d11d2c52efefae8c6-v2';
const C251 = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-db0490a135ad1cc1e0d71549021ddef3-v1';
const MAX_ROUNDS = 40; // ~20 min at 30s
const WAIT_MS = 30000;

function log(o) {
  const line = JSON.stringify(o);
  console.log(line);
  fs.appendFileSync('tmp-pw/track-live.log', line + '\n');
}

async function launch() {
  return chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
  });
}

async function ensurePage(browser) {
  const pages = browser.pages();
  return pages[0] || (await browser.newPage());
}

async function goto(page, url) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(5000);
}

async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}

async function softClick(page, label, name, re) {
  const loc = page.getByText(re).first();
  if (!(await loc.count())) {
    log({ event: 'gate_missing', label, name });
    return false;
  }
  const disabled = await loc.getAttribute('aria-disabled').catch(() => null);
  const title = await loc.getAttribute('title').catch(() => '');
  if (disabled === 'true' || /slots are currently in use/i.test(title || '')) {
    log({ event: 'gate_disabled', label, name, title: title || 'aria-disabled' });
    return false;
  }
  try {
    await loc.click({ timeout: 8000 });
    await sleep(5000);
    log({ event: 'gate_clicked', label, name });
    return true;
  } catch (e) {
    log({ event: 'gate_click_fail', label, name, error: String(e).slice(0, 180) });
    return false;
  }
}

async function tryTask(page, label, url, expectRe) {
  await goto(page, url);
  const t = await body(page);
  fs.writeFileSync('tmp-pw/track-' + label + '-live.txt', t);
  if (/accounts\.google\.com/i.test(page.url())) {
    log({ event: 'login_required', label });
    return { ok: false, login: true, slotsBusy: false };
  }
  if (!expectRe.test(t)) {
    log({ event: 'wrong_page', label, url: page.url(), head: t.slice(0, 300) });
    return { ok: false, slotsBusy: /slots are currently in use/i.test(t) };
  }
  const slotsBusy = /slots are currently in use/i.test(t);
  const preOk = await softClick(page, label, 'preqc', /Run client preQC|Re-run client preQC/i);
  const evOk = await softClick(page, label, 'oracle', /Run QC-Oracle-GLM/i);
  const after = await body(page);
  fs.writeFileSync('tmp-pw/track-' + label + '-after.txt', after);
  const running = /QC running|queued|in progress|PreQC running|Running/i.test(after);
  log({
    event: 'task_result',
    label,
    url: page.url(),
    preOk,
    evOk,
    slotsBusy,
    running,
    head: after.slice(0, 500),
  });
  return { ok: preOk || evOk || running, preOk, evOk, slotsBusy, running };
}

async function snapshotRoot(page, tag) {
  await goto(page, ROOT);
  const t = await body(page);
  fs.writeFileSync('tmp-pw/track-' + tag + '.txt', t);
  const running = [];
  for (const line of t.split(/\n+/)) {
    if (/QC running|queued/i.test(line) || /g857|c251|pdf-form|department/i.test(line)) {
      if (/QC running|g857|c251|pdf-form|department|queued|slots/i.test(line)) running.push(line.trim());
    }
  }
  log({ event: 'snapshot', tag, url: page.url(), hits: running.slice(0, 20) });
  return t;
}

(async () => {
  fs.writeFileSync('tmp-pw/track-live.log', '');
  let browser = await launch();
  let page = await ensurePage(browser);
  const status = { g857: null, c251: null, started: new Date().toISOString() };

  for (let round = 0; round < MAX_ROUNDS; round++) {
    try {
      // reconnect if closed
      if (!browser || !browser.pages || browser.pages().length === 0) {
        log({ event: 'relaunch', round });
        try {
          await browser.close().catch(() => {});
        } catch (_) {}
        browser = await launch();
        page = await ensurePage(browser);
      }

      await snapshotRoot(page, 'poll' + round);
      status.g857 = await tryTask(page, 'g857', G857_V2, /gen-g857/i);
      status.c251 = await tryTask(page, 'c251', C251, /code-c251/i);
      status.round = round;
      status.at = new Date().toISOString();
      fs.writeFileSync('tmp-pw/track-status.json', JSON.stringify(status, null, 2));
      log({ event: 'round', round, g857: status.g857, c251: status.c251 });

      const gDone = status.g857 && (status.g857.evOk || status.g857.running);
      const cDone = status.c251 && (status.c251.evOk || status.c251.running || status.c251.preOk);
      // Prefer both gates started
      if (
        status.g857 &&
        status.c251 &&
        (status.g857.preOk || status.g857.evOk || status.g857.running) &&
        (status.c251.preOk || status.c251.evOk || status.c251.running)
      ) {
        log({ event: 'both_started' });
        break;
      }
      // if g857 oracle started and c251 preqc started, good enough to keep waiting outside
      if (gDone && cDone) {
        log({ event: 'progress_enough' });
        break;
      }

      log({ event: 'waiting', round, seconds: WAIT_MS / 1000 });
      await sleep(WAIT_MS);
    } catch (e) {
      const msg = String(e);
      log({ event: 'round_error', round, error: msg.slice(0, 300) });
      if (/closed|Target page|browser has been closed/i.test(msg)) {
        try {
          await browser.close().catch(() => {});
        } catch (_) {}
        browser = null;
        await sleep(5000);
        continue;
      }
      await sleep(10000);
    }
  }

  try {
    if (browser) {
      page = await ensurePage(browser);
      await snapshotRoot(page, 'final');
      await browser.close();
    }
  } catch (_) {}
  log({ event: 'done', status });
  // exit 0 if any progress
  const ok =
    (status.g857 && (status.g857.preOk || status.g857.evOk || status.g857.running)) ||
    (status.c251 && (status.c251.preOk || status.c251.evOk || status.c251.running));
  process.exit(ok ? 0 : 3);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
