/**
 * Headless gates-only for h40 v10 new content URL.
 * Dedicated profile copy; no shared-profile lock fight; headless.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-e-h40';
const URL =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-6183c5072ed5fbd2ff923a821ff077d3-v1';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(60000);

  let pre = false;
  let ev = false;
  for (let i = 0; i < 40; i++) {
    try {
      await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(6000);
      // hash SPA often needs a second navigation
      if (!/#task=/.test(page.url())) {
        await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
        await sleep(5000);
      }
      const t = await bodyText(page);
      fs.writeFileSync(path.join(OUT, `h40-v10-gates-poll-${i}.txt`), `URL=${page.url()}\n\n${t}`);
      const busy = /run slots are currently in use/i.test(t);
      console.log(
        JSON.stringify({
          event: 'poll',
          i,
          busy,
          url: page.url(),
          head: t.slice(0, 400),
        })
      );

      // Prefer Oracle+GLM; PreQC is optional/advisory when slots jammed
      ev = (await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i)) || ev;
      if (!ev) {
        pre = (await clickEnabled(page, /Run client preQC|Re-run client preQC/i)) || pre;
        ev = (await clickEnabled(page, /Run QC-Oracle-GLM|Re-run QC-Oracle-GLM/i)) || ev;
      }
      if (ev) {
        const after = await bodyText(page);
        fs.writeFileSync(
          path.join(OUT, 'h40-v10-gates-started.txt'),
          `URL=${page.url()}\n\n${after}`
        );
        console.log(
          JSON.stringify({
            event: 'started',
            preqc: pre,
            oracle: ev,
            url: page.url(),
            head: after.slice(0, 800),
          })
        );
        break;
      }
    } catch (e) {
      console.log(JSON.stringify({ event: 'poll_error', i, error: String(e).slice(0, 300) }));
    }
    await sleep(20000);
  }

  console.log(JSON.stringify({ event: 'done', preqc: pre, oracle: ev, url: page.url() }));
  await browser.close().catch(() => {});
  process.exit(ev ? 0 : 3);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
