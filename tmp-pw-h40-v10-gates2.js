/**
 * Headless gates for h40 v10 — relaunch context each poll (profile can drop).
 * Uses dedicated chrome-profile-e-h40; headless; no shared-profile fight.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-6183c5072ed5fbd2ff923a821ff077d3-v1';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function clearLocks() {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
}

async function withBrowser(fn) {
  clearLocks();
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  try {
    const page = browser.pages()[0] || (await browser.newPage());
    page.setDefaultTimeout(45000);
    return await fn(page);
  } finally {
    await browser.close().catch(() => {});
  }
}

async function bodyText(page) {
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

(async () => {
  let pre = false;
  let ev = false;
  for (let i = 0; i < 30; i++) {
    try {
      const result = await withBrowser(async (page) => {
        await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
        await sleep(5000);
        if (!/#task=/.test(page.url())) {
          await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
          await sleep(4000);
        }
        // force hash route load
        await page.evaluate((u) => {
          if (location.href !== u) location.href = u;
        }, URL);
        await sleep(4000);
        const t = await bodyText(page);
        fs.writeFileSync(path.join(OUT, `h40-v10-gate2-${i}.txt`), `URL=${page.url()}\n\n${t}`);
        console.log(
          JSON.stringify({
            event: 'poll',
            i,
            url: page.url(),
            busy: /run slots are currently in use/i.test(t),
            head: t.replace(/\s+/g, ' ').slice(0, 350),
          })
        );
        if (!t || t.length < 40) return { empty: true };

        let localEv = await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i);
        let localPre = false;
        if (!localEv) {
          localPre = await clickEnabled(page, /Run client preQC|Re-run client preQC/i);
          localEv = await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i);
        }
        const after = await bodyText(page);
        if (localEv) {
          fs.writeFileSync(
            path.join(OUT, 'h40-v10-gates-started.txt'),
            `URL=${page.url()}\n\n${after}`
          );
        }
        return { pre: localPre, ev: localEv, after: after.slice(0, 800), url: page.url() };
      });

      if (result && result.ev) {
        pre = result.pre;
        ev = true;
        console.log(JSON.stringify({ event: 'started', ...result }));
        break;
      }
      if (result && result.pre) pre = true;
    } catch (e) {
      console.log(JSON.stringify({ event: 'poll_error', i, error: String(e).slice(0, 250) }));
    }
    await sleep(15000);
  }
  console.log(JSON.stringify({ event: 'done', preqc: pre, oracle: ev }));
  process.exit(ev ? 0 : 3);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
