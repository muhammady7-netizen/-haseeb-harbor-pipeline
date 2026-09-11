/**
 * Session C g806 — portal STATUS via minimal profile clone (cookies/login only).
 * Shared chrome-profile is often BUSY; do not Accept from this clone.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SRC = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const SNAP = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-g806-mini';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'gen-g806-leadership-brief-rhetorical-style-audit';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function ensureMini() {
  fs.mkdirSync(path.join(SNAP, 'Default'), { recursive: true });
  const files = [
    'Local State',
    'Default/Cookies',
    'Default/Cookies-journal',
    'Default/Login Data',
    'Default/Login Data-journal',
    'Default/Preferences',
    'Default/Secure Preferences',
    'Default/Web Data',
    'Default/Web Data-journal',
    'Default/Network/Cookies',
    'Default/Network/Cookies-journal',
  ];
  for (const rel of files) {
    const from = path.join(SRC, rel);
    const to = path.join(SNAP, rel);
    if (!fs.existsSync(from)) continue;
    fs.mkdirSync(path.dirname(to), { recursive: true });
    try {
      fs.copyFileSync(from, to);
    } catch (e) {
      // locked source files: try powershell copy
      try {
        execSync(
          `powershell -NoProfile -Command "Copy-Item -LiteralPath '${from}' -Destination '${to}' -Force"`,
          { stdio: 'ignore' }
        );
      } catch {}
    }
  }
  for (const f of ['SingletonLock', 'SingletonCookie', 'SingletonSocket', 'lockfile']) {
    try {
      fs.unlinkSync(path.join(SNAP, f));
    } catch {}
  }
}

async function body(page) {
  return page.locator('body').innerText().catch(() => '');
}
function onTask(t) {
  return (
    !/Drop a task here/i.test(t.slice(0, 1000)) &&
    /gen-g806-leadership-brief-rhetorical-style-audit/i.test(t.slice(0, 3500)) &&
    /QC check|QC-Oracle-GLM|Upload new version|Client [Pp]reQC/i.test(t)
  );
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  console.log(JSON.stringify({ event: 'COPY_MINI' }));
  ensureMini();
  console.log(JSON.stringify({ event: 'LAUNCH' }));
  const browser = await chromium.launchPersistentContext(SNAP, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  console.log(JSON.stringify({ event: 'LAUNCHED' }));
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);

  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(9000);
  for (let s = 0; s < 14; s++) {
    await page.mouse.wheel(0, 1400);
    await sleep(250);
  }
  await sleep(2000);
  let t = await body(page);
  fs.writeFileSync(path.join(OUT, 'g806-mini-home.txt'), t);
  const loggedOut = /Sign in|Log in|Google|Continue with/i.test(t.slice(0, 1500)) && !/muhammad\.y7@turing\.com/i.test(t);

  const titles = page.getByText(STEM, { exact: false });
  const tn = await titles.count();
  console.log(JSON.stringify({ event: 'stem_count', tn, loggedOut }));
  if (tn > 0) {
    await titles.first().click({ timeout: 20000 });
    await sleep(10000);
  } else {
    const opens = page.getByText(/^Open$/i);
    const n = await opens.count();
    for (let i = 0; i < Math.min(n, 25); i++) {
      await opens.nth(i).click({ timeout: 8000 }).catch(() => null);
      await sleep(6000);
      t = await body(page);
      if (onTask(t)) break;
      await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
      await sleep(4000);
      for (let s = 0; s < 8; s++) {
        await page.mouse.wheel(0, 1200);
        await sleep(200);
      }
    }
  }

  t = await body(page);
  fs.writeFileSync(path.join(OUT, 'g806-mini-task.txt'), t);
  const head = t.replace(/\s+/g, ' ').slice(0, 2500);
  const version = (t.match(/\bv([0-9]+)\s*[·.]\s*latest/i) || [])[1] || null;
  const oraclePass = /Oracle\s+Passed|Passed\s+1\.0/i.test(t);
  const oracleFail = /Oracle\s+Failed/i.test(t);
  const glmM = t.match(/(\d)\s*\/\s*4/);
  const glmPass = glmM ? glmM[1] + '/4' : null;
  const blockers = (t.match(/(\d+)\s+blocking/i) || [])[1] || null;
  const running = /Running now|running now|Running…|still running/i.test(t);
  const status = {
    event: 'STATUS',
    onTask: onTask(t),
    loggedOut,
    version,
    oraclePass,
    oracleFail,
    glmPass,
    blockers,
    running,
    slotsFull: /3 run slots are currently in use/i.test(t),
    head,
  };
  fs.writeFileSync(path.join(OUT, 'g806-mini-status.json'), JSON.stringify(status, null, 2));
  console.log(JSON.stringify(status));
  await browser.close().catch(() => null);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'ERROR', message: String(e && e.stack ? e.stack : e) }));
  process.exit(1);
});
