/**
 * Poll gen-g806 until QC finishes. Opens task card, not just home.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const { execSync } = require('child_process');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const DIRECT =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1';
const HOME = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const WAIT_MS = 8 * 60 * 1000;
const MAX = 15;

function dump(n, t) {
  fs.mkdirSync('tmp-pw', { recursive: true });
  fs.writeFileSync(`tmp-pw/${n}`, t);
}

function freeChrome() {
  try {
    execSync(
      `powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name='chrome.exe'\\" | Where-Object { $_.CommandLine -match 'opencode[/\\\\]chrome-profile' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue }; Start-Sleep 1; Get-ChildItem $env:USERPROFILE\\.config\\opencode\\chrome-profile -Filter Singleton* -Force -EA SilentlyContinue | Remove-Item -Force -EA SilentlyContinue"`,
      { stdio: 'ignore' },
    );
  } catch {}
}

async function openTask(page) {
  await page.goto(DIRECT, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(7000);
  let body = await page.locator('body').innerText();
  if (!/Drop a task here/i.test(body) && /gen-g806|QC-Oracle-GLM|Client PreQC/i.test(body)) {
    return body;
  }
  await page.goto(HOME, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(6000);
  const opens = page.getByText(/^Open$/i);
  const n = await opens.count();
  console.log('Open count', n);
  // recent order: g857, f53, c227, g806#772487
  const idx = n >= 4 ? 3 : 0;
  await opens.nth(idx).click();
  console.log('clicked Open', idx);
  await page.waitForTimeout(8000);
  return page.locator('body').innerText();
}

async function poll(round) {
  freeChrome();
  await new Promise((r) => setTimeout(r, 2500));
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
  });
  try {
    const page = browser.pages()[0] || (await browser.newPage());
    const body = await openTask(page);
    dump(`g806-poll-${round}.txt`, body);
    console.log('POLL', round, page.url());
    console.log(body.slice(0, 1800));

    const onHome = /Drop a task here/i.test(body);
    const running =
      !onHome &&
      (/Running now|Oracle Waiting|Waiting for Oracle|QC running|running ·/i.test(body) ||
        /Execution status — Oracle then GLM/i.test(body));
    const oracleFail =
      !onHome && /Oracle Failed|below_1\.0|Trainer changes required/i.test(body);
    const oraclePass =
      !onHome &&
      (/ORACLE GOLDEN REPLAY[\s\S]{0,200}(Passed|1\.0|Pass)/i.test(body) ||
        /Oracle\s+Passed/i.test(body));
    let glmPass = null;
    if (!onHome) {
      const m = body.match(/GLM-5\.2[^\n]{0,120}?(\d)\s*\/\s*4/i);
      if (m) glmPass = `${m[1]}/4`;
    }
    const listRunning = onHome && /gen-g806[\s\S]{0,120}QC running/i.test(body);

    const status = {
      round,
      at: new Date().toISOString(),
      url: page.url(),
      onHome,
      running: running || listRunning,
      oracleFail,
      oraclePass,
      glmPass,
    };
    dump('g806-loop-status.json', JSON.stringify(status, null, 2));
    console.log('STATUS', JSON.stringify(status));

    await browser.close();
    freeChrome();
    return status;
  } catch (e) {
    console.log('POLL_FAIL', String(e).slice(0, 300));
    try {
      await browser.close();
    } catch {}
    freeChrome();
    return { error: String(e) };
  }
}

(async () => {
  for (let i = 1; i <= MAX; i++) {
    console.log('\n==== POLL', i, '/', MAX, '====');
    const s = await poll(i);
    if (s.oracleFail) {
      console.log('ORACLE_FAILED');
      process.exit(10);
    }
    if (!s.running && s.oraclePass && s.glmPass) {
      console.log('EVAL_DONE', s.glmPass);
      process.exit(0);
    }
    if (!s.running && !s.onHome && /latest (Changes required|Needs|Pass)/i.test(fs.readFileSync(`tmp-pw/g806-poll-${i}.txt`, 'utf8'))) {
      console.log('EVAL_FINISHED_GATE');
      process.exit(0);
    }
    if (i < MAX) {
      console.log('sleep_ms', WAIT_MS);
      await new Promise((r) => setTimeout(r, WAIT_MS));
    }
  }
  console.log('POLL_MAX');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
