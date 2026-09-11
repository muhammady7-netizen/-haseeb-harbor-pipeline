const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function openMarker(page, marker) {
  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(6000);
  const label = page.getByText(marker, { exact: false }).first();
  if (!(await label.count())) return { ok: false };
  await label.scrollIntoViewIfNeeded().catch(() => {});
  const row = label.locator('xpath=ancestor::*[.//button[normalize-space()="Open"]][1]');
  const openBtn = row.getByRole('button', { name: /^Open$/i }).first();
  if (await openBtn.count()) await openBtn.click({ force: true, timeout: 15000 });
  else {
    // click arrow next to row
    await label.click({ force: true });
  }
  await sleep(10000);
  return { ok: /#task=/.test(page.url()) && /Upload new version/i.test(await page.locator('body').innerText()), url: page.url() };
}

function snap(t) {
  return {
    lastRun: (t.match(/Last run:[^\n]+/i) || [])[0],
    oracle: (t.match(/Oracle (Passed|Failed|Waiting|Running)[^\n]{0,60}/i) || [])[0],
    glm: (t.match(/GLM-5\.2 ×4[^\n]{0,80}/) || [])[0],
    findings: (t.match(/\d+ trainer finding\(s\)/i) || [])[0],
    tooEasy: /TOO_EASY/i.test(t),
    held: /Finalization held/i.test(t),
    rewards: [...t.matchAll(/reward [0-9.]+/g)].map((m) => m[0]).slice(0, 6),
  };
}

(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());

  for (const [short, marker] of [
    ['gen-g1205', 'gen-g1205-meal-prep-cost-claim-recompute-audit#5192be'],
    ['the-thread', 'the-thread-hands-back-its-own-opener#79dd1f'],
    ['fin-f39', 'fin-f39-distributable-profits'],
  ]) {
    const o = await openMarker(page, marker);
    const t = await page.locator('body').innerText();
    fs.writeFileSync(`tmp-pw/a-open-${short}.txt`, t);
    console.log(JSON.stringify({ short, ...o, ...snap(t), head: t.slice(0, 500).replace(/\n/g, ' | ') }));
  }
})().catch((e) => {
  console.error(String(e).slice(0, 400));
  process.exit(1);
});
