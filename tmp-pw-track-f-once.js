const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const G857_V2 =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2a489be4b73a943d11d2c52efefae8c6-v2';
const C251 =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-db0490a135ad1cc1e0d71549021ddef3-v1';
const ROOT = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';

function log(o) {
  const line = JSON.stringify(o);
  console.log(line);
  fs.appendFileSync('tmp-pw/track-once.log', line + '\n');
}

async function softClick(page, label, name, re) {
  const loc = page.getByRole('button', { name: re }).first();
  const alt = page.getByText(re).first();
  const btn = (await loc.count()) ? loc : alt;
  if (!(await btn.count())) {
    log({ event: 'missing', label, name });
    return false;
  }
  const disabled = await btn.getAttribute('aria-disabled').catch(() => null);
  const title = await btn.getAttribute('title').catch(() => '');
  if (disabled === 'true' || /slots are currently in use/i.test(title || '')) {
    log({ event: 'disabled', label, name, title });
    return false;
  }
  try {
    await btn.click({ timeout: 8000 });
    await sleep(4000);
    log({ event: 'clicked', label, name });
    return true;
  } catch (e) {
    log({ event: 'click_fail', label, name, error: String(e).slice(0, 160) });
    return false;
  }
}

async function drive(page, label, url, expectRe) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(6000);
  let t = await page.locator('body').innerText().catch(() => '');
  fs.writeFileSync('tmp-pw/once-' + label + '.txt', t);
  if (!expectRe.test(t)) {
    log({ event: 'wrong', label, url: page.url(), head: t.slice(0, 250) });
    return { ok: false };
  }
  const slotsBusy = /slots are currently in use/i.test(t);
  const preOk = await softClick(page, label, 'preqc', /Run client preQC|Re-run client preQC/i);
  const evOk = await softClick(page, label, 'oracle', /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i);
  t = await page.locator('body').innerText().catch(() => '');
  fs.writeFileSync('tmp-pw/once-' + label + '-after.txt', t);
  const running = /running|queued|in progress|PreQC.*run/i.test(t);
  const findings = /Review required|finding|trainer finding/i.test(t);
  log({
    event: 'result',
    label,
    url: page.url(),
    preOk,
    evOk,
    slotsBusy,
    running,
    findings,
    head: t.slice(0, 600),
  });
  return { ok: preOk || evOk || running, preOk, evOk, slotsBusy, running, findings };
}

async function launchWithRetry() {
  let last;
  for (let i = 0; i < 6; i++) {
    try {
      return await chromium.launchPersistentContext(PROFILE, {
        headless: true,
        channel: 'chrome',
        acceptDownloads: true,
      });
    } catch (e) {
      last = e;
      log({ event: 'launch_retry', i, error: String(e).slice(0, 180) });
      await sleep(2500 + i * 1000);
    }
  }
  throw last;
}

(async () => {
  fs.writeFileSync('tmp-pw/track-once.log', '');
  const browser = await launchWithRetry();
  const page = browser.pages()[0] || (await browser.newPage());
  await page.goto(ROOT, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(4000);
  const root = await page.locator('body').innerText().catch(() => '');
  fs.writeFileSync('tmp-pw/once-root.txt', root);
  const hits = root
    .split(/\n+/)
    .filter((l) => /QC running|g857|c251|slots|queued/i.test(l))
    .slice(0, 25);
  log({ event: 'root', hits });

  const g857 = await drive(page, 'g857', G857_V2, /gen-g857/i);
  const c251 = await drive(page, 'c251', C251, /code-c251/i);
  const status = { at: new Date().toISOString(), g857, c251 };
  fs.writeFileSync('tmp-pw/track-status.json', JSON.stringify(status, null, 2));
  log({ event: 'done', status });
  try {
    await browser.close();
  } catch (_) {}
  const ok = (g857 && g857.ok) || (c251 && c251.ok);
  process.exit(ok ? 0 : 3);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e).slice(0, 400) }));
  process.exit(1);
});
