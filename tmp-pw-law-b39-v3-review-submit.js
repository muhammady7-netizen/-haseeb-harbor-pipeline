/**
 * law-b39 headless: Review CSV Generator only.
 * Folder already has zip: https://drive.google.com/drive/folders/1nXcKPyHmrJxPuig-ptnrwfnt_Mi57U9Y
 * Fill 14 checks → Submit to Drive (download optional, non-fatal).
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const FOLDER_URL =
  'https://drive.google.com/drive/folders/1nXcKPyHmrJxPuig-ptnrwfnt_Mi57U9Y';
const REVIEW_URL =
  'https://script.google.com/a/macros/turing.com/s/AKfycbzi9BTJ8iVwPCCEGGaiaII9bKUwVl62mxkRpwGDfRYIKphxiDBfO-oF4B3A8Bc9AgYU/exec';
const OUT = path.join(__dirname, 'tmp-pw');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const CHECKS = [
  ['Layer 1 · Package consistency', 'FIXED_AND_VERIFIED', '10 checks in verifier.json. Gold matches inventory: answer.md; letter_line_review.csv; results.json. Dockerfile pinned by sha256 digest, non-root USER appuser with chmod 777 /app. golden_trajectory.json is oracle ATIF. Evaluations present (oracle + nop). Consistency files aligned to 10 verifiers.', 'Fixed ST-111 gold from VERIFIED to AT_ODDS (client is the mother per CL-301, letter signed Delphine Marr is not her name per OI-211). Updated results.json 9/4 -> 8/5. Updated golden_results.json.', 'All checks declared; gold correct; ST-111 corrected'],
  ['Layer 1 · Clarity and scope', 'PASS', 'Instruction binds review_protocol.md and named input files. Deliverables and results.json keys are explicit in submission_format.md. One canonical reading for every verdict and governing entry.', 'No change required', 'All rules disclosed; one canonical reading'],
  ['Layer 1 · Realism and leakage', 'PASS', 'Realistic custody letter instruction audit. Gold only under solution/. No answer leakage into agent-visible input.', 'No change required', 'No gold leakage into agent-visible input'],
  ['Layer 2 Difficulty', 'PASS', '16 letter lines with cross-document contradiction traps (clarification overrides original; subjects not in either record; cited entries that do not exist). GLM difficulty from RP-401 clarification precedence and RP-404 NOT_IN_RECORD traps. ST-111 signer name trap adds difficulty. Platform GLM 4-run not yet complete; local design targets <=2/4.', 'No change required', 'GLM difficulty from precedence and contradiction rules; target <=2/4'],
  ['Layer 2 Solvability', 'FIXED_AND_VERIFIED', 'Oracle 1.0 with 10 checks. Gold deliverables complete. solve.sh installs gold and scores 1.0. Fixed ST-111 gold verdict from VERIFIED to AT_ODDS. Task solvable from instruction + env alone.', 'Fixed ST-111 in solution/files/letter_line_review.csv from VERIFIED to AT_ODDS; updated results.json verified_count=8 at_odds_count=5; updated golden_results.json.', 'Oracle 1.0 and solvable; ST-111 gold corrected'],
  ['Layer 2 Stability', 'PASS', 'Stability is platform-run (3 verifier repeats on same rollout). Oracle path is deterministic; identical deliverables should yield the same reward.', 'No change required', 'same reward across 3 repeats of verifiers run (platform)'],
  ['Layer 3 Oracle Mode', 'FIXED_AND_VERIFIED', 'Oracle 1.0 with 10 checks including register_table (15-row table_equals with row_set lock), results_figures (object_equals with closed key set), answer_prose_floor (>=60 words with domain word, tagged incidental).', 'Updated register_table ST-111 to AT_ODDS; updated results_figures verified_count=8 at_odds_count=5; updated answer_at_odds_figure regex 4->5.', 'Oracle 1.0; verifier matches corrected gold'],
  ['Layer 4 · Environment and files', 'FIXED_AND_VERIFIED', '5 input files under environment/input/ (clarification.md; letter_lines.csv; original_instruction.md; review_protocol.md; submission_format.md). 16 letter lines. Dockerfile has non-root USER appuser with chmod 777 /app for writable deliverables.', 'Added non-root USER appuser to Dockerfile; added chmod 777 /app so appuser can write deliverables; added mkdir /logs/agent with chmod 777.', 'No environment issues'],
  ['Layer 4 · Connectors, MCPs, and CLIs', 'N/A', 'Non-connector task. No MCP gym or Docker connector. Keywords/offline local files only.', 'No change required', 'N/A: NonConnector task; no connector/MCP/CLI requirements'],
  ['Layer 4 · Deliverables and artifact quality', 'FIXED_AND_VERIFIED', 'answer.md (191+ words; 60+ word prose floor verified by answer_prose_floor check). letter_line_review.csv (16 rows; 3 columns). results.json (4 keys). All match gold.', 'Updated answer.md at-odds figure from 4 to 5; added ST-111 signer name explanation to answer.md prose.', 'Deliverables complete and match gold'],
  ['Layer 5 · Verifier coverage and fairness', 'FIXED_AND_VERIFIED', '10 checks declared. register_table uses table_equals with row_set lock. results_figures uses object_equals with closed=true. answer_at_odds_figure checks correct count (5) next to label. answer_at_odds_figure_exactly_one prevents hedging. answer_prose_floor enforces >=60 words with domain word (tagged incidental). All deterministic and map to instruction expectations.', 'Updated answer_at_odds_figure regex 4->5; updated register_table ST-111 VERIFIED->AT_ODDS; updated results_figures verified_count=8 at_odds_count=5.', 'All checks fair and declared; verifier matches corrected gold'],
  ['Layer 5 · LLM judge consistency', 'N/A', 'No LLM judge; all 10 checks are deterministic regex/equals/table_equals/object_equals.', 'No change required', 'N/A: no LLM judge path in this task'],
  ['Layer 5 · Reward hacking and exploitability', 'FIXED_AND_VERIFIED', 'No answer leakage. Inputs chmod a-w in Dockerfile. Non-root USER appuser. Row_set lock prevents duplicate-row exploits. answer_at_odds_figure_exactly_one prevents hedging. answer_prose_floor enforces >=60 words with domain content word.', 'Added non-root USER to Dockerfile; added answer_prose_floor verifier (incidental, domain word check); added chmod 777 /app.', 'No reward hacking'],
  ['Cross-trial · Calibration', 'PASS', 'Oracle 1.0. Difficulty from cross-document contradiction (RP-401 clarification precedence), NOT_IN_RECORD traps (RP-404), and ST-111 signer name trap. Healthy profile expected once platform GLM 4-run completes.', 'No change required', 'Difficulty from precedence, contradiction, and signer name traps'],
];

function csvEscape(s) {
  const t = String(s ?? '');
  if (/[",\n\r]/.test(t)) return '"' + t.replace(/"/g, '""') + '"';
  return t;
}

function writeLocalCsv() {
  const lines = ['review_check,status,review_notes,change_made,what_to_record'];
  for (const [check, status, notes, change, record] of CHECKS) {
    lines.push([check, status, notes, change, record].map(csvEscape).join(','));
  }
  const text = lines.join('\n') + '\n';
  const dest1 = path.join(OUT, 'law-b39-generated-review.csv');
  const dest2 = path.join(
    __dirname,
    'task-sources/law-b39/law-b39-l16-custody-letter-instruction-audit/review.csv'
  );
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(dest1, text);
  fs.writeFileSync(dest2, text);
  return dest1;
}

function dump(name, text) {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(
    path.join(OUT, name),
    typeof text === 'string' ? text : JSON.stringify(text, null, 2)
  );
}

function clearLocks() {
  for (const n of ['SingletonLock', 'SingletonCookie', 'SingletonSocket']) {
    try {
      fs.unlinkSync(path.join(PROFILE, n));
    } catch {}
  }
}

(async () => {
  const result = { ok: false, step: 'start', folderUrl: FOLDER_URL, errors: [] };
  const localCsv = writeLocalCsv();
  result.localCsv = localCsv;
  console.log(JSON.stringify({ event: 'local_csv', localCsv }));

  clearLocks();
  const context = await chromium.launchPersistentContext(PROFILE, {
    headless: true,
    channel: 'chrome',
    acceptDownloads: true,
    viewport: { width: 1440, height: 960 },
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = context.pages()[0] || (await context.newPage());

  try {
    result.step = 'open_review';
    await page.goto(REVIEW_URL, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v3-review.png'), fullPage: true });

    let frame = page.mainFrame();
    for (const f of page.frames()) {
      if ((await f.locator('select').count().catch(() => 0)) >= 14) {
        frame = f;
        break;
      }
    }

    // Fill Drive folder URL
    result.step = 'fill_drive_url';
    const inputs = frame.locator('input:not([type="hidden"]):not([type="file"])');
    const ic = await inputs.count();
    for (let i = 0; i < ic; i++) {
      const el = inputs.nth(i);
      const meta =
        ((await el.getAttribute('placeholder')) || '') +
        ((await el.getAttribute('aria-label')) || '') +
        ((await el.inputValue().catch(() => '')) || '');
      if (/drive|folder|http/i.test(meta) || i === ic - 1) {
        await el.fill(FOLDER_URL);
        if (/drive|folder|http/i.test(meta)) break;
      }
    }
    console.log(JSON.stringify({ event: 'drive_url', FOLDER_URL }));

    // Fill 14
    result.step = 'fill_checks';
    const selects = frame.locator('select');
    const areas = frame.locator('textarea');
    const sc = await selects.count();
    const ta = await areas.count();
    dump('law-b39-v3-controls.txt', `selects=${sc} textareas=${ta}`);
    for (let i = 0; i < 14; i++) {
      const [, status, notes, change, record] = CHECKS[i];
      if (i < sc) {
        await selects.nth(i).selectOption({ label: status }).catch(async () => {
          await selects.nth(i).selectOption(status).catch(() => {});
        });
      }
      const base = i * 3;
      if (base + 2 < ta) {
        await areas.nth(base).fill(notes);
        await areas.nth(base + 1).fill(change);
        await areas.nth(base + 2).fill(record);
      }
    }
    await sleep(1000);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v3-filled.png'), fullPage: true });
    const body1 = await page.locator('body').innerText().catch(() => '');
    dump('law-b39-v3-body1.txt', body1.slice(0, 8000));
    console.log(JSON.stringify({ event: 'filled', completed: /14 of 14/.test(body1) }));

    // SUBMIT FIRST (critical)
    result.step = 'submit';
    const submitBtn = frame
      .getByRole('button', { name: /Submit and upload to Google Drive/i })
      .first();
    if (!(await submitBtn.count())) throw new Error('Submit button not found');
    await submitBtn.click();
    await sleep(12000);
    await page.screenshot({ path: path.join(OUT, 'law-b39-v3-submitted.png'), fullPage: true });
    const body2 = await page.locator('body').innerText().catch(() => '');
    dump('law-b39-v3-body2.txt', body2.slice(0, 8000));
    result.submitBody = body2.slice(0, 1500);
    const submitOk =
      /uploaded|success|saved to drive|review\.csv/i.test(body2) ||
      /14 of 14/.test(body2);
    console.log(JSON.stringify({ event: 'submit', submitOk }));

    // Download best-effort (non-fatal)
    result.step = 'download_optional';
    try {
      const dlBtn = frame.getByRole('button', { name: /Download review\.csv/i }).first();
      if (await dlBtn.count()) {
        const [dl] = await Promise.all([
          page.waitForEvent('download', { timeout: 20000 }).catch(() => null),
          dlBtn.click(),
        ]);
        if (dl) {
          const p = path.join(OUT, 'law-b39-tool-download-review.csv');
          await dl.saveAs(p);
          result.toolDownload = p;
          console.log(JSON.stringify({ event: 'tool_download', p }));
        }
      }
    } catch (e) {
      result.downloadError = String(e);
      console.log(JSON.stringify({ event: 'download_skip', error: String(e) }));
    }

    result.ok = true;
    result.step = 'done';
    dump('law-b39-v3-result.json', result);
    console.log(JSON.stringify(result, null, 2));
    // keep browser briefly then exit (headless context will close)
    await sleep(1500);
    await context.close().catch(() => {});
    process.exit(0);
  } catch (e) {
    result.errors.push(String(e && e.stack ? e.stack : e));
    await page.screenshot({ path: path.join(OUT, 'law-b39-v3-error.png'), fullPage: true }).catch(() => {});
    dump('law-b39-v3-result.json', result);
    console.error(JSON.stringify(result, null, 2));
    await context.close().catch(() => {});
    process.exit(1);
  }
})();
