/**
 * Queue upload to Harbor V2 trainer using the shared OpenCode chrome-profile.
 * - One persistent Chrome (Shannon already signed in)
 * - Off-screen window (not visible)
 * - Upload up to 4 zips, dismiss PreQC (never Confirm), start QC-Oracle-GLM
 * - Do NOT kill chrome.exe globally; only this Playwright context
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const PORTAL = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const OUT = path.join(__dirname, 'tmp-pw', 'queue-upload-log.json');

// Max 4 in this wave (portal queue capacity). Session D = fin-f53 only.
const QUEUE = [
  { short: 'fin-f53', zip: 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-fin-f53.zip' },
];

async function sleep(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

async function clickFirst(page, re, label) {
  const loc = page.getByText(re).first();
  const n = await loc.count();
  const vis = n ? await loc.isVisible().catch(() => false) : false;
  console.log(`[${label}] match=${n} visible=${vis} re=${re}`);
  if (n && vis) {
    await loc.click({ timeout: 10000 }).catch(async () => {
      await loc.click({ force: true }).catch(() => {});
    });
    await sleep(2500);
    return true;
  }
  const btn = page.getByRole('button', { name: re }).first();
  if (await btn.count()) {
    console.log(`[${label}] role=button click`);
    await btn.click().catch(() => {});
    await sleep(2500);
    return true;
  }
  return false;
}

async function dismissPreqcFindings(page, label) {
  // Dismiss / leave unconfirmed — NEVER Confirm portal PreQC
  for (let i = 0; i < 12; i++) {
    const dismissed =
      (await clickFirst(page, /^Dismiss$/i, `${label}-dismiss`)) ||
      (await clickFirst(page, /Dismiss finding/i, `${label}-dismiss-finding`)) ||
      (await clickFirst(page, /\bDismiss\b/i, `${label}-dismiss-loose`));
    if (!dismissed) break;
  }
}

async function uploadOne(page, item) {
  const { short, zip } = item;
  console.log(`\n=== UPLOAD ${short} ===`);
  if (!fs.existsSync(zip)) {
    return { short, ok: false, error: 'zip missing', zip };
  }

  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(5000);

  const body0 = await page.locator('body').innerText();
  if (/accounts\.google\.com|Sign in/i.test(page.url()) || /Sign in with Google/i.test(body0)) {
    return { short, ok: false, error: 'not signed in — chrome-profile session lost', url: page.url() };
  }

  const input = page.locator('input[type="file"]').first();
  if (!(await input.count())) {
    return { short, ok: false, error: 'no file input on portal root', url: page.url() };
  }

  await input.setInputFiles(zip);
  console.log(`[${short}] setInputFiles ok`);
  await sleep(18000);

  let text = await page.locator('body').innerText();
  const urlAfter = page.url();
  fs.writeFileSync(`tmp-pw/queue-${short}-after-upload.txt`, text);

  await dismissPreqcFindings(page, short);

  // Start delivery eval
  const started =
    (await clickFirst(page, /Re-run QC-Oracle-GLM/i, `${short}-rerun`)) ||
    (await clickFirst(page, /Run QC-Oracle-GLM/i, `${short}-run`)) ||
    (await clickFirst(page, /QC-Oracle-GLM/i, `${short}-qc`));

  await sleep(6000);
  text = await page.locator('body').innerText();
  fs.writeFileSync(`tmp-pw/queue-${short}-after-gates.txt`, text);

  const queued = /queue|queued|waiting|running|Oracle|GLM|Harbor/i.test(text);
  return {
    short,
    ok: true,
    zip,
    url: page.url() || urlAfter,
    startedEval: started,
    likelyQueued: queued,
    head: text.slice(0, 900),
  };
}

(async () => {
  fs.mkdirSync('tmp-pw', { recursive: true });
  console.log('Launching persistent Chrome (off-screen) with OpenCode profile...');
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

  // Reuse existing tab if present; avoid spawning extra visible windows
  const page = browser.pages()[0] || (await browser.newPage());
  const results = [];

  try {
    for (const item of QUEUE) {
      try {
        results.push(await uploadOne(page, item));
      } catch (e) {
        console.error(`[${item.short}] FAIL`, e);
        results.push({ short: item.short, ok: false, error: String(e) });
      }
    }
  } finally {
    fs.writeFileSync(OUT, JSON.stringify({ at: new Date().toISOString(), results }, null, 2));
    console.log('\n=== SUMMARY ===');
    console.log(JSON.stringify(results, null, 2));
    // Close only this Playwright context (releases profile lock). Do NOT taskkill chrome.exe.
    await browser.close().catch(() => {});
  }
})().catch((e) => {
  console.error('FATAL', e);
  process.exit(1);
});
