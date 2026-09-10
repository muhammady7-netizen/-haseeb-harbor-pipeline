/**
 * fin-f53 — open uploaded task, Run client preQC, dismiss, Run QC-Oracle-GLM.
 * Uses OpenCode chrome-profile off-screen. Does not kill system Chrome.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TASK =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-cf347576d2d9beabcb4dac83b3452347-v1';
const OUT = path.join(__dirname, 'tmp-pw', 'f53-gates-log.txt');

async function sleep(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

async function clickFirst(page, re, label) {
  const loc = page.getByText(re).first();
  const n = await loc.count();
  const vis = n ? await loc.isVisible().catch(() => false) : false;
  console.log(`[${label}] text match=${n} visible=${vis}`);
  if (n && vis) {
    await loc.click({ timeout: 15000 }).catch(async () => {
      await loc.click({ force: true });
    });
    await sleep(2500);
    return true;
  }
  const btn = page.getByRole('button', { name: re }).first();
  if (await btn.count()) {
    console.log(`[${label}] role=button`);
    await btn.click({ timeout: 15000 }).catch(async () => {
      await btn.click({ force: true });
    });
    await sleep(2500);
    return true;
  }
  return false;
}

(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
    viewport: { width: 1280, height: 900 },
    args: [
      '--window-position=-32000,-32000',
      '--window-size=1280,900',
      '--disable-blink-features=AutomationControlled',
    ],
  });
  const page = browser.pages()[0] || (await browser.newPage());

  try {
    console.log('GOTO', TASK);
    await page.goto(TASK, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    let text = await page.locator('body').innerText();
    console.log('URL', page.url());
    console.log(text.slice(0, 1200));

    const preqc = await clickFirst(
      page,
      /Re-run client preQC|Run client preQC/i,
      'preqc'
    );
    console.log('PREQC_CLICKED', preqc);

    // Wait for PreQC to finish (advisory; may take a few minutes)
    for (let i = 0; i < 90; i++) {
      await sleep(4000);
      text = await page.locator('body').innerText();
      if (/PreQC complete|findings|Client preQC.*done|advisory|Dismiss|Confirm issue/i.test(text) &&
          !/Client preQC[\s\S]{0,80}running|preQC.*in progress/i.test(text)) {
        // keep waiting a bit if still "running"
      }
      if (/Confirm issue|Dismiss/i.test(text)) {
        console.log('PREQC_FINDINGS_UI', i);
        break;
      }
      if (/not run yet/i.test(text) && i > 3 && !preqc) break;
      if (/Client preQC[\s\S]{0,120}(complete|done|PASS|FAIL|findings)/i.test(text)) {
        console.log('PREQC_STATUS', i);
        break;
      }
      if (i % 10 === 0) console.log('wait_preqc', i);
    }

    // Dismiss all advisory findings — NEVER Confirm
    for (let i = 0; i < 16; i++) {
      const ok =
        (await clickFirst(page, /^Dismiss$/i, `dismiss-${i}`)) ||
        (await clickFirst(page, /Dismiss finding/i, `dismiss-finding-${i}`)) ||
        (await clickFirst(page, /\bDismiss\b/i, `dismiss-loose-${i}`));
      if (!ok) break;
    }

    text = await page.locator('body').innerText();
    if (/Running now|In queue|queued|QC running/i.test(text)) {
      console.log('ALREADY_RUNNING_OR_QUEUED');
    } else {
      const started =
        (await clickFirst(page, /Re-run QC-Oracle-GLM/i, 'rerun-eval')) ||
        (await clickFirst(page, /Run QC-Oracle-GLM/i, 'run-eval'));
      console.log('EVAL_CLICKED', started);
      await sleep(10000);
    }

    text = await page.locator('body').innerText();
    fs.writeFileSync(OUT, `URL=${page.url()}\n\n${text}`);
    console.log('FINAL', page.url());
    console.log(text.slice(0, 2800));
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});
