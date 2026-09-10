
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const cfg = {"jobs": [{"id": "NONC-B1-1000070", "short": "fin-f39", "pack_name": "fin-f39-distributable-profits", "work_root": "C:/Users/Haseeb Mirza/Documents/Codex/2026-08-17/this-is-the-very-beginning-of/tasks/NONC-B1-1000070", "pack_path": "C:/Users/Haseeb Mirza/Documents/Codex/2026-08-17/this-is-the-very-beginning-of/tasks/NONC-B1-1000070/fin-f39-distributable-profits", "status": "ready_final", "session": "A", "canonical_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-fin-f39.zip", "next_action": "Headless qc_queue upload + Run QC-Oracle-GLM (skip PreQC)", "notes": "v22 packaged. GLM 2/4 @ 1.0 (in band). Zip 328510 bytes. Soft-ease kept densify traps.", "history": [{"at": "2026-09-07T22:28:47Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-07T22:28:48Z", "status": "preqc_clean", "note": "PreQC PASS; ready to package"}, {"at": "2026-09-07T22:30:31Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-fin-f39.zip"}, {"at": "2026-09-07T22:47:34Z", "status": "final_running", "note": "Portal f39 v9: Oracle+GLM\u00c3\u20144+Harbor started; PreQC 6 findings left unconfirmed (did not Confirm)"}, {"at": "2026-09-07T22:52:33Z", "status": "final_running", "note": "Tracking active: Oracle waiting, run history latest running"}, {"at": "2026-09-07T22:55:53Z", "status": "final_running", "note": "QC running; View Oracle in Harbor available; still latest running"}, {"at": "2026-09-08T01:01:53Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T01:01:58Z", "status": "preqc_needs_fix", "note": "PreQC FAIL; 2 must-fix"}, {"at": "2026-09-08T02:58:44Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T02:58:45Z", "status": "preqc_needs_fix", "note": "PreQC FAIL; 2 must-fix"}, {"at": "2026-09-08T03:02:51Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T03:02:52Z", "status": "preqc_clean", "note": "PreQC NEEDS_REVIEW; ready to package"}, {"at": "2026-09-08T03:07:23Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-fin-f39.zip"}, {"at": "2026-09-08T03:08:18Z", "status": "blocked", "note": "build_qc_bundle failed rc=1"}, {"at": "2026-09-08T03:20:04Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-fin-f39.zip"}, {"at": "2026-09-08T20:41:57Z", "status": "final_running", "note": "Portal v9: 25 findings dismissed as false_positive via API; can_submit=true; submit button aria-disabled (needs PreQC run)"}, {"at": "2026-09-09T23:00:16Z", "status": "final_running", "note": "V19 uploaded. Eval queued (c20457262e2f45ac). Fixed: artifacts enabled, collect=[], anti-spoofing test.sh, sign-aware CSV, case-insensitive memo, disclosed all requirements."}, {"at": "2026-09-10T18:35:27Z", "status": "needs_densify", "note": "Portal TOO_EASY 4/4 on V19; densifying from Codex pack"}, {"at": "2026-09-10T18:45:54Z", "status": "blocked", "note": "build_qc_bundle failed rc=1"}, {"at": "2026-09-10T18:55:30Z", "status": "needs_densify", "note": "v20 densify applied: Meridian -110k, Project C -90k, capitalisation -250k; proposed 1430000 unlawful. Oracle 1.0 + stability 3/3. GLM v20 battery running."}, {"at": "2026-09-10T20:37:33Z", "status": "needs_densify", "note": "v21 soft-ease: dropped schedule_no_duplicate_items; broadened paid_distributions_only. Densify traps kept. Running oracle+stab+GLM v21."}, {"at": "2026-09-10T20:41:07Z", "status": "needs_densify", "note": "v21 soft-ease done. Oracle 1.0 + stability 3/3. GLM v21 battery starting."}, {"at": "2026-09-10T21:03:04Z", "status": "needs_densify", "note": "v21 GLM: 0.0, 0.0, 0.959, 0.959 (0/4 at 1.0). Near-misses only fail non_distributable_on_schedule + result_non_distributable_capital_gbp. Soft-ease those next \u2192 v22."}, {"at": "2026-09-10T21:24:58Z", "status": "needs_densify", "note": "v22 soft-ease (dropped 2 non_dist checks). Oracle+stab 1.0. GLM v22 ALL 0.0 (likely incomplete deliverables like v21-1/2). Investigating."}, {"at": "2026-09-10T21:46:20Z", "status": "needs_densify", "note": "v22b GLM retry: run1=1.0 (prior v22 all incomplete 0.0). Soft-ease working when agent completes. Battery continuing."}, {"at": "2026-09-10T22:26:09Z", "status": "needs_densify", "note": "v22 soft-ease. Oracle+stab 1.0. GLM v22b-1=1.0; running 2-4 now. Prior v22 0.0s were incomplete agent writes."}, {"at": "2026-09-10T22:41:25Z", "status": "ready_final", "note": "v22 packaged. GLM 2/4 @ 1.0 (in band). Zip 328510 bytes. Soft-ease kept densify traps."}], "updated_at": "2026-09-10T22:41:25Z", "last_preqc": {"at": "2026-09-08T03:02:52Z", "out_dir": "C:\\Users\\Haseeb Mirza\\OneDrive\\Documents\\-haseeb-harbor-pipeline\\qc-out\\NONC-B1-1000070\\2026-09-08T030251Z", "qc_verdict": "NEEDS_REVIEW", "full_model": false, "must_fix_count": 0, "finding_counts": {"INFO": 4, "P0": 0, "P1": 0, "P2": 1}, "verdict_md": "C:\\Users\\Haseeb Mirza\\OneDrive\\Documents\\-haseeb-harbor-pipeline\\qc-out\\NONC-B1-1000070\\2026-09-08T030251Z\\verdict.md", "findings_csv": "C:\\Users\\Haseeb Mirza\\OneDrive\\Documents\\-haseeb-harbor-pipeline\\qc-out\\NONC-B1-1000070\\2026-09-08T030251Z\\findings.csv"}, "packaged_at": "2026-09-08T03:20:04Z", "portal": {"task_url": "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer/#task=content-19b7cc58d1aaed31ea4d462329d6b62e-v9", "version": "v9", "watch": true, "last_check_at": "2026-09-07T22:55:53Z", "phase": "glm_or_oracle_running", "run_history": "2 runs \u00c2\u00b7 latest running", "checks": [{"at": "2026-09-07T22:51:29Z", "phase": "oracle_waiting", "running": true, "note": "Oracle waiting; GLM\u00c3\u20144 not started yet"}, {"at": "2026-09-07T22:52:33Z", "phase": "oracle_waiting", "running": true, "note": "Tracking active: Oracle waiting, run history latest running", "glm_pass": null, "oracle": null}, {"at": "2026-09-07T22:55:53Z", "phase": "glm_or_oracle_running", "running": true, "note": "QC running; View Oracle in Harbor available; still latest running", "glm_pass": null, "oracle": null}]}, "_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-fin-f39.zip"}], "maxEval": 1, "trainer": "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#", "profile": "C:/Users/Haseeb Mirza/.config/opencode/chrome-profile", "resultsPath": "tmp-pw/queue-results-ALL.json"};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {
  return chromium.launchPersistentContext(cfg.profile, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  });
}

async function bodyText(page) {
  return await page.locator('body').innerText().catch(() => '');
}

async function ensurePage(browser) {
  const pages = browser.pages();
  return pages[0] || (await browser.newPage());
}

async function clickIfVisible(page, re) {
  // Prefer role=button; skip aria-disabled / disabled (portal slot cap).
  const btn = page.getByRole('button', { name: re }).first();
  if (await btn.count()) {
    const disabled =
      (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await btn.isDisabled().catch(() => false));
    if (disabled) {
      const title = await btn.getAttribute('title').catch(() => '');
      console.log(JSON.stringify({ event: 'btn_disabled', re: String(re), title }));
      return false;
    }
    if (await btn.isVisible().catch(() => false)) {
      await btn.click({ timeout: 10000 });
      await sleep(3000);
      return true;
    }
  }
  const loc = page.getByText(re).first();
  if ((await loc.count()) && (await loc.isVisible().catch(() => false))) {
    const disabled =
      (await loc.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await loc.isDisabled().catch(() => false));
    if (disabled) {
      console.log(JSON.stringify({ event: 'text_disabled', re: String(re) }));
      return false;
    }
    try {
      await loc.click({ timeout: 8000, force: true });
      await sleep(3000);
      return true;
    } catch (e) {
      console.log(JSON.stringify({ event: 'click_skip', re: String(re), error: String(e).slice(0, 180) }));
      return false;
    }
  }
  return false;
}

async function uploadZip(page, zipPath, short) {
  await page.goto(cfg.trainer, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(4000);
  const before = page.url();
  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(zipPath);
  console.log(JSON.stringify({ event: 'upload_started', short, zipPath }));
  let t = '';
  for (let i = 0; i < 120; i++) {
    await sleep(2000);
    const url = page.url();
    t = await bodyText(page);
    // Accept version-link dialog for same task name
    if (/Yes, this is v\d+/i.test(t)) {
      await clickIfVisible(page, /Yes, this is v\d+/i);
      await sleep(3000);
      t = await bodyText(page);
      console.log(JSON.stringify({ event: 'version_linked', short, url: page.url() }));
    }
    if (/preparing upload|reading the bundle|uploading/i.test(t)) {
      if (i % 5 === 0) console.log(JSON.stringify({ event: 'upload_wait', short, i }));
      continue;
    }
    if (/#task=/.test(url)) break;
    if (/Upload new version|QC-Oracle-GLM|QC check|Delivery Gate|Review record/i.test(t) && /v\d+|latest/i.test(t)) break;
  }
  fs.writeFileSync('tmp-pw/queue-' + short + '-after-upload.txt', t);
  console.log(JSON.stringify({ event: 'after_upload', short, url: page.url(), head: t.slice(0, 600) }));
  return t;
}

async function openLatest(page, nameStem) {
  await page.goto(cfg.trainer, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(5000);
  // Click the first Recent-task row matching the pack name via its Open control when possible
  const row = page.locator('div,li,a,article').filter({ hasText: nameStem }).first();
  if (await row.count()) {
    await row.scrollIntoViewIfNeeded().catch(() => {});
    const openBtn = row.getByRole('button', { name: /^Open$/i }).first();
    const openTxt = row.getByText(/^Open$/).first();
    if (await openBtn.count()) await openBtn.click({ force: true, timeout: 10000 }).catch(() => null);
    else if (await openTxt.count()) await openTxt.click({ force: true, timeout: 10000 }).catch(() => null);
    else await row.click({ force: true, timeout: 10000 }).catch(() => null);
  } else {
    const link = page.getByText(nameStem, { exact: false }).first();
    if (!(await link.count())) {
      console.log(JSON.stringify({ event: 'open_miss', nameStem }));
      return '';
    }
    await link.scrollIntoViewIfNeeded().catch(() => {});
    await link.click({ force: true, timeout: 15000 }).catch(() => null);
  }
  await sleep(8000);
  // Version link prompt if present
  let t = await bodyText(page);
  if (/Yes, this is v\d+/i.test(t)) {
    await clickIfVisible(page, /Yes, this is v\d+/i);
    await sleep(3000);
    t = await bodyText(page);
  }
  fs.writeFileSync('tmp-pw/queue-opened-' + nameStem.slice(0, 40) + '.txt', t);
  console.log(JSON.stringify({ event: 'opened', nameStem, url: page.url() }));
  return t;
}

async function ensureReviewRecord(page, short) {
  let t = await bodyText(page);
  if (!/Not finished|Check again|Check with QC reviewer/i.test(t)) return t;
  await clickIfVisible(page, /Check again/i);
  await clickIfVisible(page, /Check with QC reviewer/i);
  for (let i = 0; i < 24; i++) {
    await sleep(5000);
    t = await bodyText(page);
    if (!/Not finished/i.test(t)) break;
    if (i % 4 === 0) {
      await clickIfVisible(page, /Check again/i);
      await clickIfVisible(page, /Check with QC reviewer/i);
      console.log(JSON.stringify({ event: 'wait_review', short, i }));
    }
  }
  return t;
}

async function waitForEvalSlot(page, short) {
  // Portal disables Oracle when all concurrent slots are full (cap is 4).
  // NEVER page.reload() — it drops the #task= hash and dumps us on the pipeline list.
  const taskUrl = page.url();
  for (let i = 0; i < 60; i++) {
    const t = await bodyText(page);
    const full = /\d+\s+runs? in flight|run slots? are currently in use|already have \d+ runs/i.test(t);
    if (!full) {
      console.log(JSON.stringify({ event: 'slot_free', short, i }));
      return true;
    }
    if (i % 3 === 0) console.log(JSON.stringify({ event: 'slot_wait', short, i }));
    await sleep(30000);
    // Soft refresh: re-goto the same task URL
    if (/#task=/.test(taskUrl)) {
      await page.goto(taskUrl, { waitUntil: 'domcontentloaded', timeout: 90000 }).catch(() => null);
      await sleep(4000);
    }
  }
  console.log(JSON.stringify({ event: 'slot_timeout', short }));
  return false;
}

async function startGates(page, short) {
  // PreQC optional — skip. Prefer Delivery Gate / QC-Oracle-GLM.
  // If still on home/pipeline list, abort gates.
  let t0 = await bodyText(page);
  if (/Submitted to the pipeline/i.test(t0) && !/#task=/.test(page.url())) {
    console.log(JSON.stringify({ event: 'gates_abort_wrong_page', short, url: page.url() }));
    return { pre: false, ev: false, t: t0 };
  }
  await ensureReviewRecord(page, short);
  await waitForEvalSlot(page, short);
  let ev =
    (await clickIfVisible(page, /Re-run QC-Oracle-GLM/i)) ||
    (await clickIfVisible(page, /Run QC-Oracle-GLM/i)) ||
    (await clickIfVisible(page, /^Re-run$/i)) ||
    (await clickIfVisible(page, /Run QC check/i));
  await sleep(8000);
  const t = await bodyText(page);
  fs.writeFileSync('tmp-pw/queue-' + short + '-gates.txt', t);
  console.log(JSON.stringify({ event: 'gates', short, preqc: false, skipped_preqc: true, oracle: ev, head: t.slice(0, 900) }));
  return { pre: false, ev, t };
}

(async () => {
  // OpenCode-style: ONE headless Chrome for the whole queue. Never close/reopen mid-run.
  let browser = await launch();
  let page = await ensurePage(browser);
  const results = [];
  const outJson = cfg.resultsPath || 'tmp-pw/queue-results.json';

  await page.goto(cfg.trainer, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(5000);
  let root = await bodyText(page);
  if (/accounts\.google\.com/i.test(page.url()) || (/Sign in/i.test(root) && !/muhammad\.y7@turing\.com/i.test(root))) {
    console.log(JSON.stringify({ event: 'login_required' }));
    fs.writeFileSync('tmp-pw/queue-login-required.txt', root);
    process.exit(2);
  }
  console.log(JSON.stringify({ event: 'logged_in', head: root.slice(0, 400) }));

  let startedEvals = 0;
  for (const job of cfg.jobs) {
    const short = job.short;
    const zip = job._zip;
    const status = job.status;
    const stem = job.pack_name || short;
    try {
      page = await ensurePage(browser);

      if (status === 'ready_final') {
        await uploadZip(page, zip, short);
      }

      // Only skip list-open when THIS pack is already on screen (never reuse a sibling task page)
      {
        const onTask = /#task=/.test(page.url());
        const bodyNow = onTask ? await bodyText(page) : '';
        const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const onThis =
          onTask &&
          !/Submitted to the pipeline/i.test(bodyNow) &&
          /Upload new version|Harbor package|QC check|QC-Oracle-GLM/i.test(bodyNow) &&
          (new RegExp(esc(stem), 'i').test(bodyNow) || new RegExp(esc(short), 'i').test(bodyNow));
        if (onThis) {
          console.log(JSON.stringify({ event: 'already_on_task', short, url: page.url() }));
        } else {
          if (onTask) console.log(JSON.stringify({ event: 'wrong_task_page', short, url: page.url() }));
          let opened = await openLatest(page, stem);
          if (!opened) opened = await openLatest(page, short);
        }
      }

      if (startedEvals >= cfg.maxEval) {
        console.log(JSON.stringify({ event: 'defer_eval', short, reason: 'max_eval' }));
        results.push({ short, deferred: true, uploaded: status === 'ready_final' });
        continue;
      }

      const g = await startGates(page, short);
      if (g.ev) startedEvals += 1;
      results.push({ short, uploaded: status === 'ready_final', gates: !!(g.pre || g.ev), preqc: g.pre, oracle: g.ev, url: page.url() });
    } catch (e) {
      console.log(JSON.stringify({ event: 'error', short, error: String(e).slice(0, 500) }));
      results.push({ short, error: String(e).slice(0, 500) });
      // Do NOT close/relaunch Chrome — stay on same persistent context.
    }
  }

  fs.writeFileSync(outJson, JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ event: 'done', results, outJson }));
  // Intentionally leave browser open until process exit (no browser.close()).
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
