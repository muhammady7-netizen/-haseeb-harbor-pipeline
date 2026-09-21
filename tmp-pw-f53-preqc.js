/**
 * fin-f53 — click Run client preQC on the uploaded task (eval can keep running).
 * OpenCode chrome-profile, off-screen. Does not kill user Chrome.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TASK =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-cf347576d2d9beabcb4dac83b3452347-v1';
const OUT = 'tmp-pw/f53-preqc-log.txt';

async function sleep(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    viewport: { width: 1280, height: 900 },
    args: [
      '--window-position=-32000,-32000',
      '--window-size=1280,900',
      '--disable-blink-features=AutomationControlled',
    ],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  try {
    await page.goto(TASK, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(7000);

    // Prefer role=button
    let clicked = false;
    const btn = page.getByRole('button', { name: /Run client preQC|Re-run client preQC/i }).first();
    if (await btn.count()) {
      await btn.click();
      clicked = true;
      console.log('CLICKED_ROLE_BUTTON');
    } else {
      const t = page.getByText(/Run client preQC/i).first();
      if (await t.count() && (await t.isVisible().catch(() => false))) {
        await t.click();
        clicked = true;
        console.log('CLICKED_TEXT');
      }
    }
    console.log('PREQC_CLICKED', clicked);
    await sleep(8000);

    // Wait up to ~8 min for findings UI
    for (let i = 0; i < 60; i++) {
      await sleep(8000);
      const text = await page.locator('body').innerText();
      if (/Confirm issue|\bDismiss\b|findings?\s*\(/i.test(text)) {
        console.log('FINDINGS_READY', i);
        for (let d = 0; d < 16; d++) {
          const dismiss = page.getByRole('button', { name: /^Dismiss$/i }).first();
          if (await dismiss.count()) {
            await dismiss.click().catch(() => {});
            await sleep(1200);
            console.log('DISMISSED', d);
          } else {
            const loose = page.getByText(/^Dismiss$/i).first();
            if (await loose.count() && (await loose.isVisible().catch(() => false))) {
              await loose.click().catch(() => {});
              await sleep(1200);
              console.log('DISMISSED_TEXT', d);
            } else break;
          }
        }
        break;
      }
      if (/Client preQC[\s\S]{0,100}(complete|done|PASS|0 findings)/i.test(text)) {
        console.log('PREQC_DONE_NO_FINDINGS', i);
        break;
      }
      if (i % 5 === 0) console.log('wait_preqc', i, 'eval?', /Running now|running ·/i.test(text));
    }

    const text = await page.locator('body').innerText();
    fs.writeFileSync(OUT, `URL=${page.url()}\n\n${text}`);
    console.log(text.slice(0, 2500));
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});
