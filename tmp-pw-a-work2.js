/** Open g1205 #5192be from Recent tasks + confirm the-thread after rerun */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function openHash(page, marker) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);
  const label = page.getByText(marker, { exact: false }).first();
  if (!(await label.count())) return { ok: false, reason: 'missing' };
  await label.scrollIntoViewIfNeeded().catch(() => {});
  const row = label.locator('xpath=ancestor::*[self::div or self::li or self::article][1]');
  const openBtn = row.getByRole('button', { name: /^Open$/i }).first();
  if (await openBtn.count()) await openBtn.click({ force: true });
  else await label.click({ force: true });
  await sleep(8000);
  return { ok: /#task=/.test(page.url()), url: page.url() };
}

function snap(t) {
  return {
    lastRun: (t.match(/Last run:[^\n]+/i) || [])[0],
    oracle: (t.match(/Oracle (Passed|Failed|Waiting|Running)[^\n]{0,60}/i) || [])[0],
    glm: (t.match(/GLM-5\.2[^\n]{0,110}/) || [])[0],
    slotsFull: /run slots? are currently in use/i.test(t),
    tooEasy: /TOO_EASY/i.test(t),
    findings: (t.match(/\d+ trainer finding/i) || [])[0],
    changes: /Changes needed|Finalization held/i.test(t),
    rewards: [...t.matchAll(/reward [^\t\n]+/g)].map((m) => m[0]).slice(0, 5),
  };
}

(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());

  // g1205 via list hash (matches content ...5192be)
  let o = await openHash(page, 'gen-g1205-meal-prep-cost-claim-recompute-audit#5192be');
  let t = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/a-work2-g1205.txt', t);
  console.log(JSON.stringify({ short: 'gen-g1205', ...o, ...snap(t) }));

  // the-thread direct
  await page.goto(
    'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-5cc146d448ffc4f0a07bba4ad679dd1f-v1',
    { waitUntil: 'domcontentloaded', timeout: 120000 }
  );
  await sleep(8000);
  t = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/a-work2-thread.txt', t);
  let s = snap(t);
  let clicked = false;
  if (!s.slotsFull && (/errored|crashed/i.test(t) || /Oracle Waiting/i.test(t)) && !/Oracle Running|Running now/i.test(t)) {
    const btn = page.locator('button:has-text("Re-run QC-Oracle-GLM")').first();
    if ((await btn.count()) && (await btn.getAttribute('aria-disabled')) !== 'true') {
      await btn.click({ force: true });
      clicked = true;
      await sleep(10000);
      t = await page.locator('body').innerText();
      s = snap(t);
    }
  }
  console.log(JSON.stringify({ short: 'the-thread', clicked, url: page.url(), ...s }));
})().catch((e) => {
  console.error(String(e).slice(0, 350));
  process.exit(1);
});
