"""Headless Harbor QC upload/eval queue.

Uses the ONE shared Shannon Chrome profile (same as opencode Playwright MCP).
Runs headless so no profile window pops on screen. Never taskkill user's Chrome.

Portal QC-Oracle-GLM allows up to 4 concurrent evals; --max-eval defaults to 4.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = Path.home() / ".config" / "opencode" / "chrome-profile"
TRAINER = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#"
PW = ROOT / "tmp-pw" / "node_modules" / "playwright"

# Fallback display names when pack_name missing
PACK_STEM = {
    "gen-g857": "gen-g857-department-directory-categorization-audit",
    "code-c251": "code-c251-pdf-form-field-conversion-audit",
    "code-c249": "code-c249-recurring-report-source-selection-audit",
    "code-c227": "code-c227-table-bloat-maintenance-audit",
    "gen-g734": "gen-g734-cms-publish-readiness-audit",
    "gen-g806": "gen-g806-leadership-brief-rhetorical-style-audit",
    "gen-g826": "gen-g826-tender-document-brand-style-audit",
    "gen-g986": "gen-g986-festival-key-art-billing-parity-audit",
    "gen-g1205": "gen-g1205-meal-prep-cost-claim-recompute-audit",
    "health-h34": "health-h34-randomisation-balance",
    "health-h40": "health-h40-critical-result-acknowledgement",
    "fin-f33": "fin-f33-cash-pool-interest-allocation",
    "fin-f39": "fin-f39-distributable-profits",
    "fin-f44": "fin-f44-facility-interest-review",
    "fin-f53": "fin-f53-deposit-account-fee-assessment-audit",
    "fin-f55": "fin-f55",
    "the-thread": "the-thread-hands-back-its-own-opener",
}


def load_registry() -> dict:
    return json.loads((ROOT / "registry.json").read_text(encoding="utf-8-sig"))


def resolve_zip(task: dict) -> Path | None:
    short = task["short"]
    cands = []
    if task.get("canonical_zip"):
        cands.append(Path(task["canonical_zip"]))
    cands += [
        ROOT / "canonical-zips" / f"UPLOAD-THIS-TO-QC-{short}.zip",
        Path.home() / "Downloads" / f"UPLOAD-THIS-TO-QC-{short}.zip",
        ROOT
        / "sessions"
        / str(task.get("session") or "")
        / "zips"
        / f"UPLOAD-THIS-TO-QC-{short}.zip",
    ]
    for p in cands:
        if p.is_file():
            return p
    return None


def stem_for(task: dict) -> str:
    if task.get("pack_name"):
        return str(task["pack_name"])
    pp = task.get("pack_path") or ""
    if pp:
        return Path(pp).name
    return PACK_STEM.get(task["short"], task["short"])


def queue_tasks(reg: dict, only: set[str] | None) -> list[dict]:
    out = []
    for t in reg.get("tasks", []):
        if only and t.get("short") not in only and t.get("id") not in only:
            continue
        st = t.get("status")
        if st not in ("ready_final", "final_running"):
            continue
        z = resolve_zip(t)
        if not z:
            continue
        row = {**t, "_zip": str(z), "pack_name": stem_for(t)}
        out.append(row)
    out.sort(
        key=lambda t: (0 if t.get("status") == "ready_final" else 1, t.get("short") or "")
    )
    return out


def write_runner_js(
    path: Path, jobs: list[dict], max_eval: int, *, results_path: str
) -> None:
    payload = json.dumps(
        {
            "jobs": jobs,
            "maxEval": max_eval,
            "trainer": TRAINER,
            "profile": str(PROFILE).replace("\\", "/"),
            "resultsPath": results_path.replace("\\", "/"),
        }
    )
    path.write_text(
        f"""
const {{ chromium }} = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const cfg = {payload};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {{
  return chromium.launchPersistentContext(cfg.profile, {{
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    args: ['--disable-blink-features=AutomationControlled'],
  }});
}}

async function bodyText(page) {{
  return await page.locator('body').innerText().catch(() => '');
}}

async function ensurePage(browser) {{
  const pages = browser.pages();
  return pages[0] || (await browser.newPage());
}}

async function clickIfVisible(page, re) {{
  // Prefer role=button; skip aria-disabled / disabled (portal slot cap).
  const btn = page.getByRole('button', {{ name: re }}).first();
  if (await btn.count()) {{
    const disabled =
      (await btn.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await btn.isDisabled().catch(() => false));
    if (disabled) {{
      const title = await btn.getAttribute('title').catch(() => '');
      console.log(JSON.stringify({{ event: 'btn_disabled', re: String(re), title }}));
      return false;
    }}
    if (await btn.isVisible().catch(() => false)) {{
      await btn.click({{ timeout: 10000 }});
      await sleep(3000);
      return true;
    }}
  }}
  const loc = page.getByText(re).first();
  if ((await loc.count()) && (await loc.isVisible().catch(() => false))) {{
    const disabled =
      (await loc.getAttribute('aria-disabled').catch(() => null)) === 'true' ||
      (await loc.isDisabled().catch(() => false));
    if (disabled) {{
      console.log(JSON.stringify({{ event: 'text_disabled', re: String(re) }}));
      return false;
    }}
    try {{
      await loc.click({{ timeout: 8000, force: true }});
      await sleep(3000);
      return true;
    }} catch (e) {{
      console.log(JSON.stringify({{ event: 'click_skip', re: String(re), error: String(e).slice(0, 180) }}));
      return false;
    }}
  }}
  return false;
}}

async function uploadZip(page, zipPath, short) {{
  await page.goto(cfg.trainer, {{ waitUntil: 'domcontentloaded', timeout: 90000 }});
  await sleep(4000);
  const before = page.url();
  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(zipPath);
  console.log(JSON.stringify({{ event: 'upload_started', short, zipPath }}));
  let t = '';
  for (let i = 0; i < 120; i++) {{
    await sleep(2000);
    const url = page.url();
    t = await bodyText(page);
    // Accept version-link dialog for same task name
    if (/Yes, this is v\\d+/i.test(t)) {{
      await clickIfVisible(page, /Yes, this is v\\d+/i);
      await sleep(3000);
      t = await bodyText(page);
      console.log(JSON.stringify({{ event: 'version_linked', short, url: page.url() }}));
    }}
    if (/preparing upload|reading the bundle|uploading/i.test(t)) {{
      if (i % 5 === 0) console.log(JSON.stringify({{ event: 'upload_wait', short, i }}));
      continue;
    }}
    if (/#task=/.test(url)) break;
    if (/Upload new version|QC-Oracle-GLM|QC check|Delivery Gate|Review record/i.test(t) && /v\\d+|latest/i.test(t)) break;
  }}
  fs.writeFileSync('tmp-pw/queue-' + short + '-after-upload.txt', t);
  console.log(JSON.stringify({{ event: 'after_upload', short, url: page.url(), head: t.slice(0, 600) }}));
  return t;
}}

async function openLatest(page, nameStem) {{
  await page.goto(cfg.trainer, {{ waitUntil: 'domcontentloaded', timeout: 90000 }});
  await sleep(5000);
  // Click the first Recent-task row matching the pack name via its Open control when possible
  const row = page.locator('div,li,a,article').filter({{ hasText: nameStem }}).first();
  if (await row.count()) {{
    await row.scrollIntoViewIfNeeded().catch(() => {{}});
    const openBtn = row.getByRole('button', {{ name: /^Open$/i }}).first();
    const openTxt = row.getByText(/^Open$/).first();
    if (await openBtn.count()) await openBtn.click({{ force: true, timeout: 10000 }}).catch(() => null);
    else if (await openTxt.count()) await openTxt.click({{ force: true, timeout: 10000 }}).catch(() => null);
    else await row.click({{ force: true, timeout: 10000 }}).catch(() => null);
  }} else {{
    const link = page.getByText(nameStem, {{ exact: false }}).first();
    if (!(await link.count())) {{
      console.log(JSON.stringify({{ event: 'open_miss', nameStem }}));
      return '';
    }}
    await link.scrollIntoViewIfNeeded().catch(() => {{}});
    await link.click({{ force: true, timeout: 15000 }}).catch(() => null);
  }}
  await sleep(8000);
  // Version link prompt if present
  let t = await bodyText(page);
  if (/Yes, this is v\\d+/i.test(t)) {{
    await clickIfVisible(page, /Yes, this is v\\d+/i);
    await sleep(3000);
    t = await bodyText(page);
  }}
  fs.writeFileSync('tmp-pw/queue-opened-' + nameStem.slice(0, 40) + '.txt', t);
  console.log(JSON.stringify({{ event: 'opened', nameStem, url: page.url() }}));
  return t;
}}

async function ensureReviewRecord(page, short) {{
  let t = await bodyText(page);
  if (!/Not finished|Check again|Check with QC reviewer/i.test(t)) return t;
  await clickIfVisible(page, /Check again/i);
  await clickIfVisible(page, /Check with QC reviewer/i);
  for (let i = 0; i < 24; i++) {{
    await sleep(5000);
    t = await bodyText(page);
    if (!/Not finished/i.test(t)) break;
    if (i % 4 === 0) {{
      await clickIfVisible(page, /Check again/i);
      await clickIfVisible(page, /Check with QC reviewer/i);
      console.log(JSON.stringify({{ event: 'wait_review', short, i }}));
    }}
  }}
  return t;
}}

async function waitForEvalSlot(page, short) {{
  // Portal disables Oracle when all concurrent slots are full (cap is 4).
  // NEVER page.reload() — it drops the #task= hash and dumps us on the pipeline list.
  const taskUrl = page.url();
  for (let i = 0; i < 60; i++) {{
    const t = await bodyText(page);
    const full = /\\d+\\s+runs? in flight|run slots? are currently in use|already have \\d+ runs/i.test(t);
    if (!full) {{
      console.log(JSON.stringify({{ event: 'slot_free', short, i }}));
      return true;
    }}
    if (i % 3 === 0) console.log(JSON.stringify({{ event: 'slot_wait', short, i }}));
    await sleep(30000);
    // Soft refresh: re-goto the same task URL
    if (/#task=/.test(taskUrl)) {{
      await page.goto(taskUrl, {{ waitUntil: 'domcontentloaded', timeout: 90000 }}).catch(() => null);
      await sleep(4000);
    }}
  }}
  console.log(JSON.stringify({{ event: 'slot_timeout', short }}));
  return false;
}}

async function startGates(page, short) {{
  // PreQC optional — skip. Prefer Delivery Gate / QC-Oracle-GLM.
  // If still on home/pipeline list, abort gates.
  let t0 = await bodyText(page);
  if (/Submitted to the pipeline/i.test(t0) && !/#task=/.test(page.url())) {{
    console.log(JSON.stringify({{ event: 'gates_abort_wrong_page', short, url: page.url() }}));
    return {{ pre: false, ev: false, t: t0 }};
  }}
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
  console.log(JSON.stringify({{ event: 'gates', short, preqc: false, skipped_preqc: true, oracle: ev, head: t.slice(0, 900) }}));
  return {{ pre: false, ev, t }};
}}

(async () => {{
  // OpenCode-style: ONE headless Chrome for the whole queue. Never close/reopen mid-run.
  let browser = await launch();
  let page = await ensurePage(browser);
  const results = [];
  const outJson = cfg.resultsPath || 'tmp-pw/queue-results.json';

  await page.goto(cfg.trainer, {{ waitUntil: 'domcontentloaded', timeout: 90000 }});
  await sleep(5000);
  let root = await bodyText(page);
  if (/accounts\\.google\\.com/i.test(page.url()) || (/Sign in/i.test(root) && !/muhammad\\.y7@turing\\.com/i.test(root))) {{
    console.log(JSON.stringify({{ event: 'login_required' }}));
    fs.writeFileSync('tmp-pw/queue-login-required.txt', root);
    process.exit(2);
  }}
  console.log(JSON.stringify({{ event: 'logged_in', head: root.slice(0, 400) }}));

  let startedEvals = 0;
  for (const job of cfg.jobs) {{
    const short = job.short;
    const zip = job._zip;
    const status = job.status;
    const stem = job.pack_name || short;
    try {{
      page = await ensurePage(browser);

      if (status === 'ready_final') {{
        await uploadZip(page, zip, short);
      }}

      // Only skip list-open when THIS pack is already on screen (never reuse a sibling task page)
      {{
        const onTask = /#task=/.test(page.url());
        const bodyNow = onTask ? await bodyText(page) : '';
        const esc = (s) => s.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
        const onThis =
          onTask &&
          !/Submitted to the pipeline/i.test(bodyNow) &&
          /Upload new version|Harbor package|QC check|QC-Oracle-GLM/i.test(bodyNow) &&
          (new RegExp(esc(stem), 'i').test(bodyNow) || new RegExp(esc(short), 'i').test(bodyNow));
        if (onThis) {{
          console.log(JSON.stringify({{ event: 'already_on_task', short, url: page.url() }}));
        }} else {{
          if (onTask) console.log(JSON.stringify({{ event: 'wrong_task_page', short, url: page.url() }}));
          let opened = await openLatest(page, stem);
          if (!opened) opened = await openLatest(page, short);
        }}
      }}

      if (startedEvals >= cfg.maxEval) {{
        console.log(JSON.stringify({{ event: 'defer_eval', short, reason: 'max_eval' }}));
        results.push({{ short, deferred: true, uploaded: status === 'ready_final' }});
        continue;
      }}

      const g = await startGates(page, short);
      if (g.ev) startedEvals += 1;
      results.push({{ short, uploaded: status === 'ready_final', gates: !!(g.pre || g.ev), preqc: g.pre, oracle: g.ev, url: page.url() }});
    }} catch (e) {{
      console.log(JSON.stringify({{ event: 'error', short, error: String(e).slice(0, 500) }}));
      results.push({{ short, error: String(e).slice(0, 500) }});
      // Do NOT close/relaunch Chrome — stay on same persistent context.
    }}
  }}

  fs.writeFileSync(outJson, JSON.stringify(results, null, 2));
  console.log(JSON.stringify({{ event: 'done', results, outJson }}));
  // Intentionally leave browser open until process exit (no browser.close()).
}})().catch((e) => {{
  console.error(JSON.stringify({{ event: 'fatal', error: String(e) }}));
  process.exit(1);
}});
""",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Headless Harbor QC queue (shared chrome-profile)")
    ap.add_argument("--max-eval", type=int, default=4, help="Max QC-Oracle-GLM starts this run (portal allows 4)")
    ap.add_argument("--only", default="", help="Comma shorts/ids to include")
    ap.add_argument("--session", default="", help="Optional session filter e.g. F")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not PROFILE.is_dir():
        print("MISSING profile:", PROFILE, file=sys.stderr)
        return 1
    if not PW.exists():
        print("MISSING playwright at", PW, file=sys.stderr)
        return 1

    reg = load_registry()
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None
    jobs = queue_tasks(reg, only)
    if args.session:
        jobs = [j for j in jobs if str(j.get("session") or "") == args.session]

    print(
        json.dumps(
            {
                "profile": str(PROFILE),
                "max_eval": args.max_eval,
                "jobs": [
                    {
                        "short": j["short"],
                        "status": j["status"],
                        "session": j.get("session"),
                        "pack_name": j.get("pack_name"),
                        "zip": j["_zip"],
                    }
                    for j in jobs
                ],
            },
            indent=2,
        )
    )
    if args.dry_run or not jobs:
        return 0

    # Per-session JS so parallel chats don't clobber the shared runner.
    tag = (args.session or "all").strip().upper() or "all"
    js = ROOT / f"tmp-pw-qc-queue-{tag}.js"
    results = f"tmp-pw/queue-results-{tag}.json"
    write_runner_js(js, jobs, args.max_eval, results_path=results)
    print(json.dumps({"runner": str(js), "results": results}))
    proc = subprocess.run(["node", str(js)], cwd=str(ROOT))
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
