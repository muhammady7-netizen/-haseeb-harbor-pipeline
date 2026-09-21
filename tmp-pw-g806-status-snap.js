/**
 * Session C g806 — status via profile SNAPSHOT (shared profile busy).
 * Read-only: do not Accept from snapshot; only report Oracle/GLM/Harbor/version.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SRC = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const SNAP = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile-g806-snap';
const TRAINER = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const STEM = 'gen-g806-leadership-brief-rhetorical-style-audit';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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
  // Fresh snapshot (exclude locks)
  if (fs.existsSync(SNAP)) {
    try {
      execSync(`powershell -NoProfile -Command "Remove-Item -LiteralPath '${SNAP}' -Recurse -Force -ErrorAction SilentlyContinue"`, {
        stdio: 'ignore',
      });
    } catch {}
  }
  fs.mkdirSync(SNAP, { recursive: true });
  execSync(
    `robocopy "${SRC}" "${SNAP}" /E /XD Cache Code Cache GPUCache GrShaderCache ShaderCache "Crashpad" "SingletonCookie" "SingletonLock" "SingletonSocket" /NFL /NDL /NJH /NJS /nc /ns /np`,
    { stdio: 'ignore' }
  );
  // Drop lock leftovers if copied
  for (const f of ['SingletonLock', 'SingletonCookie', 'SingletonSocket', 'lockfile']) {
    try {
      fs.unlinkSync(path.join(SNAP, f));
    } catch {}
  }

  const browser = await chromium.launchPersistentContext(SNAP, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
  console.log(JSON.stringify({ event: 'LAUNCHED_SNAP' }));
  const page = browser.pages()[0] || (await browser.newPage());
  page.setDefaultTimeout(90000);

  await page.goto(TRAINER, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await sleep(8000);
  for (let s = 0; s < 14; s++) {
    await page.mouse.wheel(0, 1400);
    await sleep(250);
  }
  await sleep(2000);
  let t = await body(page);
  fs.writeFileSync(path.join(OUT, 'g806-snap-home.txt'), t);

  const titles = page.getByText(STEM, { exact: false });
  const tn = await titles.count();
  console.log(JSON.stringify({ event: 'stem_count', tn }));
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
    }
  }

  t = await body(page);
  fs.writeFileSync(path.join(OUT, 'g806-snap-task.txt'), t);
  const head = t.replace(/\s+/g, ' ').slice(0, 2200);
  const version = (t.match(/\bv([0-9]+)\s*[·.]\s*latest/i) || [])[1] || null;
  const oraclePass = /Oracle\s+Passed|Oracle.*?Passed\s+1\.0|ORACLE GOLDEN REPLAY[\s\S]{0,120}Passed/i.test(t);
  const oracleFail = /Oracle\s+Failed|Oracle.*?Failed/i.test(t);
  const glmM =
    t.match(/GLM[^\n]{0,60}?(\d)\s*\/\s*4/i) ||
    t.match(/(\d)\s*\/\s*4/);
  const glmPass = glmM ? glmM[1] + '/4' : null;
  const blockers = (t.match(/(\d+)\s+blocking/i) || [])[1] || null;
  const running = /Running now|running now|Running…|GLM-5\.2\s*[×xX]?\s*4[^\n]{0,40}Running/i.test(t);
  const readySubmit = /Ready to submit|Submit to pipeline|Accept/i.test(t) && !running;
  const status = {
    event: 'STATUS',
    onTask: onTask(t),
    version,
    oraclePass,
    oracleFail,
    glmPass,
    blockers,
    running,
    readySubmit,
    slotsFull: /3 run slots are currently in use/i.test(t),
    head,
  };
  fs.writeFileSync(path.join(OUT, 'g806-snap-status.json'), JSON.stringify(status, null, 2));
  console.log(JSON.stringify(status));
  await browser.close().catch(() => null);
})().catch((e) => {
  console.error(JSON.stringify({ event: 'ERROR', message: String(e) }));
  process.exit(1);
});
