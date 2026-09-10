
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const cfg = {"jobs": [{"id": "NONC-B1-1001634", "short": "gen-g806", "pack_name": "gen-g806-leadership-brief-rhetorical-style-audit", "work_root": "C:/Users/Haseeb Mirza/Documents/Codex/2026-08-17/this-is-the-very-beginning-of/tasks/NONC-B1-1001634", "pack_path": "C:/Users/Haseeb Mirza/Documents/Codex/2026-08-17/this-is-the-very-beginning-of/tasks/NONC-B1-1001634/gen-g806-leadership-brief-rhetorical-style-audit", "status": "final_running", "session": "C", "canonical_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-gen-g806.zip", "next_action": "Dismiss PreQC; poll until GLM finishes", "notes": "TRACKING: Final QC only (skip PreQC). content-58a3a86e Evaluation=glm. Headless finalqc waiter on shared chrome-profile (Session B queue holds profile).", "history": [{"at": "2026-09-08T19:09:10Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T19:09:11Z", "status": "preqc_clean", "note": "PreQC PASS; ready to package"}, {"at": "2026-09-08T19:09:28Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-08T21:41:05Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T21:41:06Z", "status": "preqc_clean", "note": "PreQC PASS; ready to package"}, {"at": "2026-09-08T21:41:48Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-08T22:29:31Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T22:29:32Z", "status": "preqc_clean", "note": "PreQC PASS; ready to package"}, {"at": "2026-09-08T22:30:15Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-08T22:32:56Z", "status": "final_running", "note": "v1 uploaded; review.csv OK; PreQC NEEDS_REVIEW; Oracle+GLM started (run_id: evaluation-0b62409e79b14e70)"}, {"at": "2026-09-09T17:52:13Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T17:55:18Z", "status": "final_running", "note": "v1 re-uploaded with fixed verifier (SC-10/32/35/36\u2192none, SC-50\u2192RUNTIME_OUT_OF_BAND); Oracle+GLM started"}, {"at": "2026-09-09T19:22:13Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T19:26:27Z", "status": "final_running", "note": "v1 re-uploaded with fixed result verifier checks (53/15/7/11); Oracle+GLM started"}, {"at": "2026-09-09T20:42:13Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T20:48:38Z", "status": "needs_densify", "note": "Densified: 15 new scripts (SC-101-115) with edge cases; 114 verifiers; Oracle sim 114/114 PASS; re-uploading"}, {"at": "2026-09-09T21:09:14Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T21:14:07Z", "status": "final_running", "note": "Densified v1 (15 new scripts, 114 verifiers); Oracle+GLM started"}, {"at": "2026-09-09T22:52:13Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T22:53:49Z", "status": "final_running", "note": "v1 (129 scripts, 144 verifiers); Oracle+GLM started"}, {"at": "2026-09-10T15:17:25Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T15:21:50Z", "status": "needs_densify", "note": "v2 (159 scripts, 174 verifiers, 30 new edge-case scripts); uploaded + queued"}, {"at": "2026-09-10T16:19:51Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T16:25:01Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T16:26:55Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T17:13:22Z", "status": "final_running", "note": "REWRITE: brief coherence evaluation (8 briefs, 82 sentences, 35 verifiers); Oracle+GLM started"}, {"at": "2026-09-10T18:34:38Z", "status": "final_running", "note": "Session C locked to gen-g806 ONLY. gen-g734 and gen-g986 released \u2014 do not work those in Chat C."}, {"at": "2026-09-10T19:30:49Z", "status": "ready_final", "note": "Fixed task.toml org/name + solve.sh mount path; local oracle coherence5 = 1.0 (35/35). Re-package for portal re-upload."}, {"at": "2026-09-10T19:31:36Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T19:31:57Z", "status": "ready_final", "note": "Packaged fixed zip (obi/ name + solve.sh SOLUTION_DIR). Local oracle 1.0. Awaiting portal re-upload + Oracle+GLM\u00d74."}, {"at": "2026-09-10T19:36:56Z", "status": "final_running", "note": "Fixed zip uploaded (content-58a3a86e). Shared opencode chrome-profile headless. Starting/confirming PreQC+Oracle+GLM in portal queue (cap ~3-4)."}, {"at": "2026-09-10T20:06:58Z", "status": "final_running", "note": "Fixed zip uploaded (content-58a3a86e). Shared opencode chrome-profile headless. Starting/confirming PreQC+Oracle+GLM in portal queue (cap ~3-4)."}, {"at": "2026-09-10T20:19:20Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T20:27:44Z", "status": "ready_final", "note": "content-58a3a86e uploaded (fixed solve.sh+obi name). Portal: 3 run slots full. Looping until slot frees then PreQC+Oracle+GLM. Session C only."}, {"at": "2026-09-10T20:41:11Z", "status": "final_running", "note": "PreQC+QC-Oracle-GLM RUNNING on content-58a3a86e. Oracle Waiting, GLM Waiting. Fixed zip. ~50min expected."}, {"at": "2026-09-10T20:58:40Z", "status": "ready_final", "note": "Re-queue via pipeline.qc_queue (headless, no Chrome churn)."}, {"at": "2026-09-10T21:03:03Z", "status": "final_running", "note": "Headless qc_queue: content-58a3a86e-v1. PreQC Review required (7). Evaluation=glm; slots full."}, {"at": "2026-09-10T21:44:37Z", "status": "final_running", "note": "TRACKING: Final QC only (skip PreQC). content-58a3a86e Evaluation=glm. Headless finalqc waiter on shared chrome-profile (Session B queue holds profile)."}], "updated_at": "2026-09-10T21:44:37Z", "last_preqc": {"at": "2026-09-08T22:29:32Z", "out_dir": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\NONC-B1-1001634\\2026-09-08T222931Z", "qc_verdict": "PASS", "full_model": false, "must_fix_count": 0, "finding_counts": {"INFO": 3, "P0": 0, "P1": 0, "P2": 0}, "verdict_md": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\NONC-B1-1001634\\2026-09-08T222931Z\\verdict.md", "findings_csv": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\NONC-B1-1001634\\2026-09-08T222931Z\\findings.csv"}, "packaged_at": "2026-09-10T20:19:20Z", "portal": {"task_url": "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1", "version": "v1", "watch": true, "last_check_at": "2026-09-10T20:41:11Z", "phase": "glm_or_oracle_running", "checks": [{"at": "2026-09-08T22:32:56Z", "phase": "oracle_running", "running": true, "note": "v1 uploaded; review.csv OK; PreQC NEEDS_REVIEW; Oracle+GLM started (run_id: evaluation-0b62409e79b14e70)", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T17:55:18Z", "phase": "oracle_running", "running": true, "note": "v1 re-uploaded with fixed verifier (SC-10/32/35/36\u2192none, SC-50\u2192RUNTIME_OUT_OF_BAND); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T19:26:27Z", "phase": "oracle_running", "running": true, "note": "v1 re-uploaded with fixed result verifier checks (53/15/7/11); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T21:14:07Z", "phase": "oracle_running", "running": true, "note": "Densified v1 (15 new scripts, 114 verifiers); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T22:53:49Z", "phase": "oracle_running", "running": true, "note": "v1 (129 scripts, 144 verifiers); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T17:13:22Z", "phase": "oracle_running", "running": true, "note": "REWRITE: brief coherence evaluation (8 briefs, 82 sentences, 35 verifiers); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T19:36:56Z", "phase": "glm_or_oracle_running", "running": true, "note": "Fixed zip uploaded (content-58a3a86e). Shared opencode chrome-profile headless. Starting/confirming PreQC+Oracle+GLM in portal queue (cap ~3-4).", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T20:06:58Z", "phase": "glm_or_oracle_running", "running": true, "note": "Fixed zip uploaded (content-58a3a86e). Shared opencode chrome-profile headless. Starting/confirming PreQC+Oracle+GLM in portal queue (cap ~3-4).", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T20:41:11Z", "phase": "glm_or_oracle_running", "running": true, "note": "PreQC+QC-Oracle-GLM RUNNING on content-58a3a86e. Oracle Waiting, GLM Waiting. Fixed zip. ~50min expected.", "glm_pass": null, "oracle": null}]}, "_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-gen-g806.zip"}], "maxEval": 1, "trainer": "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#", "profile": "C:/Users/Haseeb Mirza/.config/opencode/chrome-profile", "resultsPath": "tmp-pw/queue-results-ALL.json"};

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
  // Wait out "preparing upload…" then SPA task page / new version chrome
  let t = '';
  for (let i = 0; i < 90; i++) {
    await sleep(2000);
    const url = page.url();
    t = await bodyText(page);
    if (/preparing upload/i.test(t)) {
      if (i % 5 === 0) console.log(JSON.stringify({ event: 'upload_wait', short, i }));
      continue;
    }
    if (url !== before && /#task=/.test(url)) break;
    if (/Client [Pp]reQC|Run QC-Oracle-GLM|Upload new version/.test(t) && /v\d+|latest/.test(t)) break;
    if (i >= 5 && !/preparing upload/i.test(t)) break;
  }
  fs.writeFileSync('tmp-pw/queue-' + short + '-after-upload.txt', t);
  console.log(JSON.stringify({ event: 'after_upload', short, url: page.url(), head: t.slice(0, 600) }));
  return t;
}

async function openLatest(page, nameStem) {
  await page.goto(cfg.trainer, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(4000);
  // Prefer exact task title near top of list (no mouse.wheel — unstable under contention)
  const link = page.getByText(nameStem, { exact: false }).first();
  if (!(await link.count())) {
    console.log(JSON.stringify({ event: 'open_miss', nameStem }));
    return '';
  }
  await link.scrollIntoViewIfNeeded().catch(() => {});
  await link.click({ timeout: 15000 });
  await sleep(7000);
  const t = await bodyText(page);
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
  for (let i = 0; i < 60; i++) {
    const t = await bodyText(page);
    const full = /\d+\s+runs? in flight|run slots? are currently in use|already have \d+ runs/i.test(t);
    if (!full) {
      console.log(JSON.stringify({ event: 'slot_free', short, i }));
      return true;
    }
    if (i % 3 === 0) console.log(JSON.stringify({ event: 'slot_wait', short, i }));
    await sleep(30000);
    await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => null);
    await sleep(4000);
  }
  console.log(JSON.stringify({ event: 'slot_timeout', short }));
  return false;
}

async function startGates(page, short) {
  // PreQC is optional/advisory (STRICT-RULES.md + sessions/README.md) — skip it.
  // Go straight to final QC: QC-Oracle-GLM.
  await ensureReviewRecord(page, short);
  await waitForEvalSlot(page, short);
  let ev = await clickIfVisible(page, /Re-run QC-Oracle-GLM/i);
  if (!ev) ev = await clickIfVisible(page, /Run QC-Oracle-GLM/i);
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
