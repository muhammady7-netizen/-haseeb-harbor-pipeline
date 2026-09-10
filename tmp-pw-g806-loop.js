/**
 * Session C — open latest gen-g806 on portal and start PreQC + Oracle+GLM when slots free.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ZIP = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g806.zip';
const HOME = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const DIRECT =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1';
const OUT = 'tmp-pw';
const MAX_ROUNDS = 60;
const WAIT_MS = 75000;

function dump(name, text) {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(`${OUT}/${name}`, text);
}

async function launch() {
  return chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
  });
}

async function clickBtn(page, label) {
  const btn = page.getByRole('button', {
    name: new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'),
  });
  const n = await btn.count();
  console.log('btn', label, n);
  if (!n) return false;
  await btn.first().click({ timeout: 10000 });
  console.log('clicked', label);
  await page.waitForTimeout(4000);
  return true;
}

async function openG806(page) {
  // Try direct deep link first
  await page.goto(DIRECT, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(6000);
  let body = await page.locator('body').innerText();
  if (/Upload new version|Run QC-Oracle-GLM|Run client preQC|Client PreQC/i.test(body) &&
      /gen-g806/i.test(body) &&
      !/Drop a task here/i.test(body)) {
    return body;
  }

  // Fall back: home list → first Open next to gen-g806
  await page.goto(HOME, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(6000);
  body = await page.locator('body').innerText();
  dump('g806-home.txt', body);

  // Portal cards use plain "Open" text, not button roles.
  // Prefer the latest g806 card (#772487 / 12:35 AM), else first g806 Open.
  const prefer = page.locator('xpath=//*[contains(.,"gen-g806-leadership-brief-rhetorical-style-audit") and contains(.,"772487")]').first();
  const anyG806 = page.locator('xpath=//*[contains(.,"gen-g806-leadership-brief-rhetorical-style-audit")]').first();
  const card = (await prefer.count()) ? prefer : anyG806;
  if (await card.count()) {
    await card.scrollIntoViewIfNeeded().catch(() => {});
    const openInCard = card.getByText(/^Open$/i).first();
    if (await openInCard.count()) {
      await openInCard.click({ timeout: 10000 });
      console.log('clicked Open inside g806 card');
      await page.waitForTimeout(8000);
      return page.locator('body').innerText();
    }
  }

  // Absolute fallback: nth Open on page matching order of recent tasks
  // From home dump, g806#772487 is the 4th Open (0-index 3) after g857, f53, c227
  const opens = page.getByText(/^Open$/i);
  const n = await opens.count();
  console.log('Open text nodes', n);
  if (n >= 4) {
    await opens.nth(3).click();
    console.log('clicked Open nth=3 (g806 slot heuristic)');
    await page.waitForTimeout(8000);
  } else if (n > 0) {
    await opens.first().click();
    console.log('clicked first Open text');
    await page.waitForTimeout(8000);
  }
  return page.locator('body').innerText();
}

async function oneRound(round) {
  let browser;
  try {
    browser = await launch();
  } catch (e) {
    console.log('LAUNCH_BUSY', String(e).slice(0, 180));
    return { status: 'busy' };
  }

  try {
    const page = browser.pages()[0] || (await browser.newPage());
    let body = await openG806(page);
    dump(`g806-task-${round}.txt`, body);
    console.log('ROUND', round, 'URL', page.url());
    console.log(body.slice(0, 1400));

    if (/accounts\.google|Enter your email/i.test(page.url() + body)) {
      try { await browser.close(); } catch {}
      return { status: 'need_login' };
    }

    // Still on home?
    if (/Drop a task here/i.test(body)) {
      console.log('STILL_HOME');
      try { await browser.close(); } catch {}
      return { status: 'still_home' };
    }

    if (/3 run slots are currently in use/i.test(body)) {
      console.log('SLOTS_FULL');
      // Still try PreQC — it does NOT consume eval slots per portal text
      await clickBtn(page, 'Run client preQC');
      await clickBtn(page, 'Re-run client preQC');
      body = await page.locator('body').innerText();
      dump(`g806-slotsfull-${round}.txt`, body);
      try { await browser.close(); } catch {}
      return { status: 'slots_full', url: page.url() };
    }

    // Detect running / done
    if (/QC-Oracle-GLM check[\s\S]{0,120}(Running|In progress|queued)/i.test(body) ||
        /Evaluation[\s\S]{0,40}(running|in progress)/i.test(body)) {
      console.log('EVAL_RUNNING');
      try { await browser.close(); } catch {}
      return { status: 'eval_running', url: page.url(), body };
    }

    if (/Oracle\s*(Passed|1\.0)/i.test(body) && /GLM-5\.2/i.test(body)) {
      console.log('EVAL_COMPLETE_SIGNAL');
      dump(`g806-complete-${round}.txt`, body);
      try { await browser.close(); } catch {}
      return { status: 'eval_complete', url: page.url(), body };
    }

    // Upload if needed (failed prior / changes needed)
    if (/Upload new version/i.test(body) && /Oracle Failed|changes needed|below_1\.0/i.test(body)) {
      const up = page.getByText(/Upload new version/i).first();
      if (await up.count()) {
        await up.click();
        await page.waitForTimeout(1500);
      }
      const inputs = page.locator('input[type="file"]');
      if (await inputs.count()) {
        await inputs.first().setInputFiles(ZIP);
        console.log('uploaded');
        await page.waitForTimeout(12000);
        body = await page.locator('body').innerText();
        dump(`g806-uploaded-${round}.txt`, body);
      }
    }

    await clickBtn(page, 'Run client preQC');
    await clickBtn(page, 'Re-run client preQC');
    const started =
      (await clickBtn(page, 'Run QC-Oracle-GLM')) ||
      (await clickBtn(page, 'Re-run QC-Oracle-GLM'));

    await page.waitForTimeout(8000);
    body = await page.locator('body').innerText();
    dump(`g806-started-${round}.txt`, body);
    console.log('AFTER_START', page.url());
    console.log(body.slice(0, 1800));
    try { await browser.close(); } catch {}
    return { status: started ? 'started' : 'no_click', url: page.url() };
  } catch (e) {
    console.log('ROUND_FAIL', String(e).slice(0, 250));
    try { if (browser) await browser.close(); } catch {}
    return { status: 'error', error: String(e) };
  }
}

(async () => {
  for (let round = 1; round <= MAX_ROUNDS; round++) {
    console.log('\n==== ROUND', round, '/', MAX_ROUNDS, '====');
    const r = await oneRound(round);
    console.log('RESULT', r.status, r.url || '');
    dump(
      'g806-loop-status.json',
      JSON.stringify({ round, at: new Date().toISOString(), status: r.status, url: r.url || null }, null, 2),
    );
    if (r.status === 'need_login') process.exit(2);
    if (r.status === 'eval_complete') {
      console.log('EVAL_COMPLETE — stop loop for manual accept review');
      process.exit(0);
    }
    console.log('sleep', WAIT_MS);
    await new Promise((res) => setTimeout(res, WAIT_MS));
  }
  console.log('DONE_MAX_ROUNDS');
})().catch((e) => {
  console.error('FATAL', e);
  process.exit(1);
});
