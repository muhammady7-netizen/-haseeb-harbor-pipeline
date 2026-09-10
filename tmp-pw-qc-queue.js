
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const cfg = {"jobs": [{"id": "NONC-B1-1001562", "short": "gen-g734", "pack_name": "gen-g734-cms-publish-readiness-audit", "work_root": "C:/Users/Haseeb Mirza/Documents/Codex/2026-08-17/this-is-the-very-beginning-of/tasks/NONC-B1-1001562", "pack_path": "C:/Users/Haseeb Mirza/Documents/Codex/2026-08-17/this-is-the-very-beginning-of/tasks/NONC-B1-1001562/gen-g734-cms-publish-readiness-audit", "status": "final_running", "session": null, "canonical_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-gen-g734.zip", "next_action": "Wait portal Oracle+GLM; dismiss PreQC only", "notes": "Headless qc_queue uploaded (content-86163925). Continuing gates via pipeline.qc_queue.", "history": [{"at": "2026-09-08T19:09:08Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T19:09:10Z", "status": "preqc_needs_fix", "note": "PreQC FAIL; 1 must-fix"}, {"at": "2026-09-08T19:18:25Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T19:18:26Z", "status": "preqc_clean", "note": "PreQC PASS; ready to package"}, {"at": "2026-09-08T19:18:41Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T19:18:42Z", "status": "preqc_clean", "note": "PreQC PASS; ready to package"}, {"at": "2026-09-08T19:19:14Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-08T21:40:29Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T21:40:30Z", "status": "preqc_clean", "note": "PreQC NEEDS_REVIEW; ready to package"}, {"at": "2026-09-08T21:41:05Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-08T22:06:55Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T22:06:57Z", "status": "preqc_clean", "note": "PreQC NEEDS_REVIEW; ready to package"}, {"at": "2026-09-08T22:07:38Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-08T22:11:32Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T22:11:34Z", "status": "preqc_clean", "note": "PreQC NEEDS_REVIEW; ready to package"}, {"at": "2026-09-08T22:12:12Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-08T22:14:48Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T22:14:49Z", "status": "preqc_clean", "note": "PreQC NEEDS_REVIEW; ready to package"}, {"at": "2026-09-08T22:15:25Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-08T22:27:08Z", "status": "final_running", "note": "v4 uploaded; review.csv OK; PreQC NEEDS_REVIEW; Oracle+GLM started (run_id: evaluation-9ba2bc2ab50a418e)"}, {"at": "2026-09-09T17:38:12Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-09T17:55:18Z", "status": "final_running", "note": "v1 re-uploaded with finding-code memo checks; Oracle running"}, {"at": "2026-09-09T18:07:13Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-09T18:10:41Z", "status": "final_running", "note": "v9 uploaded with wider memo regex (finding codes pass gold); Oracle+GLM started"}, {"at": "2026-09-09T19:51:12Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-09T19:54:23Z", "status": "final_running", "note": "v1 (no memo checks, 80 verifiers); Oracle+GLM started"}, {"at": "2026-09-09T20:48:37Z", "status": "final_running", "note": "Oracle PASSED (80/80 checks after removing memo checks); GLM x4 running"}, {"at": "2026-09-09T21:08:35Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-09T21:10:05Z", "status": "needs_densify", "note": "Densified: 10 new posts (P-73-82) with edge cases; 89 verifiers; Oracle sim 89/89 PASS"}, {"at": "2026-09-09T21:14:06Z", "status": "final_running", "note": "Densified v1 (10 new posts, 89 verifiers); Oracle+GLM started"}, {"at": "2026-09-09T21:48:44Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-09T21:50:10Z", "status": "final_running", "note": "Fixed finding_count bug (67->78); re-uploaded; Oracle+GLM started"}, {"at": "2026-09-10T15:13:55Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-10T15:15:20Z", "status": "final_running", "note": "v1 (98 posts, 178 verifiers, 30 new edge-case posts P-83-111); Oracle+GLM started"}, {"at": "2026-09-10T15:21:50Z", "status": "final_running", "note": "v1 (98 posts, 178 verifiers, 30 new edge-case posts); Oracle running"}, {"at": "2026-09-10T15:58:18Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"at": "2026-09-10T18:34:38Z", "status": "ready_final", "note": "Released from Session C. Do not work in Chat C."}, {"at": "2026-09-10T20:53:04Z", "status": "final_running", "note": "Headless qc_queue uploaded (content-86163925). Continuing gates via pipeline.qc_queue."}], "updated_at": "2026-09-10T20:53:04Z", "last_preqc": {"at": "2026-09-08T22:14:49Z", "out_dir": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\NONC-B1-1001562\\2026-09-08T221448Z", "qc_verdict": "NEEDS_REVIEW", "full_model": false, "must_fix_count": 0, "finding_counts": {"INFO": 4, "P0": 0, "P1": 0, "P2": 1}, "verdict_md": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\NONC-B1-1001562\\2026-09-08T221448Z\\verdict.md", "findings_csv": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\NONC-B1-1001562\\2026-09-08T221448Z\\findings.csv"}, "packaged_at": "2026-09-10T15:58:18Z", "portal": {"task_url": "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-89240b92d486fd7b8ee6dad5adb91f97-v9", "version": "v1", "watch": true, "last_check_at": "2026-09-10T15:21:50Z", "phase": "oracle_running", "checks": [{"at": "2026-09-08T22:27:08Z", "phase": "oracle_running", "running": true, "note": "v4 uploaded; review.csv OK; PreQC NEEDS_REVIEW; Oracle+GLM started (run_id: evaluation-9ba2bc2ab50a418e)", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T17:55:18Z", "phase": "oracle_running", "running": true, "note": "v1 re-uploaded with finding-code memo checks; Oracle running", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T18:10:41Z", "phase": "oracle_running", "running": true, "note": "v9 uploaded with wider memo regex (finding codes pass gold); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T19:54:23Z", "phase": "oracle_running", "running": true, "note": "v1 (no memo checks, 80 verifiers); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T20:48:37Z", "phase": "glm_running", "running": true, "note": "Oracle PASSED (80/80 checks after removing memo checks); GLM x4 running", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T21:14:06Z", "phase": "oracle_running", "running": true, "note": "Densified v1 (10 new posts, 89 verifiers); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T21:50:10Z", "phase": "oracle_running", "running": true, "note": "Fixed finding_count bug (67->78); re-uploaded; Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T15:15:20Z", "phase": "oracle_running", "running": true, "note": "v1 (98 posts, 178 verifiers, 30 new edge-case posts P-83-111); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T15:21:50Z", "phase": "oracle_running", "running": true, "note": "v1 (98 posts, 178 verifiers, 30 new edge-case posts); Oracle running", "glm_pass": null, "oracle": null}]}, "_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-gen-g734.zip"}, {"id": "NONC-B1-1001634", "short": "gen-g806", "pack_name": "gen-g806-leadership-brief-rhetorical-style-audit", "work_root": "C:/Users/Haseeb Mirza/Documents/Codex/2026-08-17/this-is-the-very-beginning-of/tasks/NONC-B1-1001634", "pack_path": "C:/Users/Haseeb Mirza/Documents/Codex/2026-08-17/this-is-the-very-beginning-of/tasks/NONC-B1-1001634/gen-g806-leadership-brief-rhetorical-style-audit", "status": "final_running", "session": "C", "canonical_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-gen-g806.zip", "next_action": "Keep polling portal until Oracle+GLM\u00d74 finishes", "notes": "PreQC+QC-Oracle-GLM RUNNING on content-58a3a86e. Oracle Waiting, GLM Waiting. Fixed zip. ~50min expected.", "history": [{"at": "2026-09-08T19:09:10Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T19:09:11Z", "status": "preqc_clean", "note": "PreQC PASS; ready to package"}, {"at": "2026-09-08T19:09:28Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-08T21:41:05Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T21:41:06Z", "status": "preqc_clean", "note": "PreQC PASS; ready to package"}, {"at": "2026-09-08T21:41:48Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-08T22:29:31Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-08T22:29:32Z", "status": "preqc_clean", "note": "PreQC PASS; ready to package"}, {"at": "2026-09-08T22:30:15Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-08T22:32:56Z", "status": "final_running", "note": "v1 uploaded; review.csv OK; PreQC NEEDS_REVIEW; Oracle+GLM started (run_id: evaluation-0b62409e79b14e70)"}, {"at": "2026-09-09T17:52:13Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T17:55:18Z", "status": "final_running", "note": "v1 re-uploaded with fixed verifier (SC-10/32/35/36\u2192none, SC-50\u2192RUNTIME_OUT_OF_BAND); Oracle+GLM started"}, {"at": "2026-09-09T19:22:13Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T19:26:27Z", "status": "final_running", "note": "v1 re-uploaded with fixed result verifier checks (53/15/7/11); Oracle+GLM started"}, {"at": "2026-09-09T20:42:13Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T20:48:38Z", "status": "needs_densify", "note": "Densified: 15 new scripts (SC-101-115) with edge cases; 114 verifiers; Oracle sim 114/114 PASS; re-uploading"}, {"at": "2026-09-09T21:09:14Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T21:14:07Z", "status": "final_running", "note": "Densified v1 (15 new scripts, 114 verifiers); Oracle+GLM started"}, {"at": "2026-09-09T22:52:13Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-09T22:53:49Z", "status": "final_running", "note": "v1 (129 scripts, 144 verifiers); Oracle+GLM started"}, {"at": "2026-09-10T15:17:25Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T15:21:50Z", "status": "needs_densify", "note": "v2 (159 scripts, 174 verifiers, 30 new edge-case scripts); uploaded + queued"}, {"at": "2026-09-10T16:19:51Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T16:25:01Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T16:26:55Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T17:13:22Z", "status": "final_running", "note": "REWRITE: brief coherence evaluation (8 briefs, 82 sentences, 35 verifiers); Oracle+GLM started"}, {"at": "2026-09-10T18:34:38Z", "status": "final_running", "note": "Session C locked to gen-g806 ONLY. gen-g734 and gen-g986 released \u2014 do not work those in Chat C."}, {"at": "2026-09-10T19:30:49Z", "status": "ready_final", "note": "Fixed task.toml org/name + solve.sh mount path; local oracle coherence5 = 1.0 (35/35). Re-package for portal re-upload."}, {"at": "2026-09-10T19:31:36Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T19:31:57Z", "status": "ready_final", "note": "Packaged fixed zip (obi/ name + solve.sh SOLUTION_DIR). Local oracle 1.0. Awaiting portal re-upload + Oracle+GLM\u00d74."}, {"at": "2026-09-10T19:36:56Z", "status": "final_running", "note": "Fixed zip uploaded (content-58a3a86e). Shared opencode chrome-profile headless. Starting/confirming PreQC+Oracle+GLM in portal queue (cap ~3-4)."}, {"at": "2026-09-10T20:06:58Z", "status": "final_running", "note": "Fixed zip uploaded (content-58a3a86e). Shared opencode chrome-profile headless. Starting/confirming PreQC+Oracle+GLM in portal queue (cap ~3-4)."}, {"at": "2026-09-10T20:19:20Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"at": "2026-09-10T20:27:44Z", "status": "ready_final", "note": "content-58a3a86e uploaded (fixed solve.sh+obi name). Portal: 3 run slots full. Looping until slot frees then PreQC+Oracle+GLM. Session C only."}, {"at": "2026-09-10T20:41:11Z", "status": "final_running", "note": "PreQC+QC-Oracle-GLM RUNNING on content-58a3a86e. Oracle Waiting, GLM Waiting. Fixed zip. ~50min expected."}], "updated_at": "2026-09-10T20:41:11Z", "last_preqc": {"at": "2026-09-08T22:29:32Z", "out_dir": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\NONC-B1-1001634\\2026-09-08T222931Z", "qc_verdict": "PASS", "full_model": false, "must_fix_count": 0, "finding_counts": {"INFO": 3, "P0": 0, "P1": 0, "P2": 0}, "verdict_md": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\NONC-B1-1001634\\2026-09-08T222931Z\\verdict.md", "findings_csv": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\NONC-B1-1001634\\2026-09-08T222931Z\\findings.csv"}, "packaged_at": "2026-09-10T20:19:20Z", "portal": {"task_url": "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-58a3a86e0067ef5b91601705a8772487-v1", "version": "v1", "watch": true, "last_check_at": "2026-09-10T20:41:11Z", "phase": "glm_or_oracle_running", "checks": [{"at": "2026-09-08T22:32:56Z", "phase": "oracle_running", "running": true, "note": "v1 uploaded; review.csv OK; PreQC NEEDS_REVIEW; Oracle+GLM started (run_id: evaluation-0b62409e79b14e70)", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T17:55:18Z", "phase": "oracle_running", "running": true, "note": "v1 re-uploaded with fixed verifier (SC-10/32/35/36\u2192none, SC-50\u2192RUNTIME_OUT_OF_BAND); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T19:26:27Z", "phase": "oracle_running", "running": true, "note": "v1 re-uploaded with fixed result verifier checks (53/15/7/11); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T21:14:07Z", "phase": "oracle_running", "running": true, "note": "Densified v1 (15 new scripts, 114 verifiers); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T22:53:49Z", "phase": "oracle_running", "running": true, "note": "v1 (129 scripts, 144 verifiers); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T17:13:22Z", "phase": "oracle_running", "running": true, "note": "REWRITE: brief coherence evaluation (8 briefs, 82 sentences, 35 verifiers); Oracle+GLM started", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T19:36:56Z", "phase": "glm_or_oracle_running", "running": true, "note": "Fixed zip uploaded (content-58a3a86e). Shared opencode chrome-profile headless. Starting/confirming PreQC+Oracle+GLM in portal queue (cap ~3-4).", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T20:06:58Z", "phase": "glm_or_oracle_running", "running": true, "note": "Fixed zip uploaded (content-58a3a86e). Shared opencode chrome-profile headless. Starting/confirming PreQC+Oracle+GLM in portal queue (cap ~3-4).", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T20:41:11Z", "phase": "glm_or_oracle_running", "running": true, "note": "PreQC+QC-Oracle-GLM RUNNING on content-58a3a86e. Oracle Waiting, GLM Waiting. Fixed zip. ~50min expected.", "glm_pass": null, "oracle": null}]}, "_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-gen-g806.zip"}, {"id": "NONC-B1-1001684", "short": "gen-g857", "pack_name": "gen-g857-department-directory-categorization-audit", "work_root": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\ework\\gen-g857-portal", "pack_path": "C:\\Users\\Haseeb Mirza\\Documents\\Codex\\haseeb-pipeline\\qc-out\\ework\\gen-g857-portal\\gen-g857-department-directory-categorization-audit", "status": "final_running", "session": "F", "canonical_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-gen-g857.zip", "next_action": "Upload canonical_zip to V2 trainer, Dismiss portal PreQC, run Oracle+GLM\u00d74. URL: https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#", "notes": "Switched to OpenCode-style keepchrome (1 headless Chrome, never close/reopen). Polling v2 Oracle + c251 gates. max-eval 3.", "history": [{"at": "2026-09-09T07:24:40Z", "status": "final_running", "note": "v3 eval started (CRLF fix); Oracle waiting; ~50min total"}, {"at": "2026-09-09T07:25:08Z", "status": "needs_densify", "note": "GLM 4/4 too easy"}, {"at": "2026-09-09T07:25:08Z", "status": "needs_densify", "note": "v4 Oracle passes (gold fixed 64->121 depts); GLM 4/4 too easy; needs harder traps"}, {"at": "2026-09-09T08:15:53Z", "status": "final_running", "note": "gen-g857 v5 uploaded (content-d5630788). Clicked Run client preQC + Run QC-Oracle-GLM on portal. Waiting for eval to start."}, {"at": "2026-09-09T08:21:07Z", "status": "preqc_running", "note": "Densified gen-g857 v4 source: added 5 trap depts (121-125). 137 verifier checks. Running PreQC."}, {"at": "2026-09-09T08:21:34Z", "status": "preqc_running", "note": ""}, {"at": "2026-09-09T08:21:58Z", "status": "preqc_needs_fix", "note": "PreQC FAIL; 7 must-fix"}, {"at": "2026-09-09T08:26:28Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g857.zip"}, {"at": "2026-09-09T08:27:30Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g857.zip"}, {"at": "2026-09-09T08:32:20Z", "status": "final_running", "note": "gen-g857 v6 uploaded with 5 trap depts (121-125). 137 verifier checks, 126 departments. PreQC + QC-Oracle-GLM started on portal."}, {"at": "2026-09-09T08:38:10Z", "status": "final_running", "note": "v1 (36fa5f0b) NEW content family with legacy-exclusion rule + 15 new trap depts. PreQC done (1 advisory). QC-Oracle-GLM running."}, {"at": "2026-09-09T08:43:31Z", "status": "final_running", "note": "v6 Oracle PASSED! GLM\u00d74 running 659s. 5 trap depts (121-125) should trip GLM. Waiting for difficulty result."}, {"at": "2026-09-09T09:04:08Z", "status": "needs_densify", "note": "GLM 4/4 too easy"}, {"at": "2026-09-09T09:39:05Z", "status": "final_running", "note": "v1 (ed239145) fixed verifier regex (15 assertions). PreQC done. QC-Oracle-GLM starting."}, {"at": "2026-09-09T10:53:02Z", "status": "final_running", "note": "v1 (ed239145) re-running QC-Oracle-GLM after previous eval ERRORED (infrastructure failure, not difficulty). Oracle passed, GLM 0/4 was due to error. 3 PreQC findings advisory (legacy rule, sort-order, regex permissiveness)."}, {"at": "2026-09-09T13:01:14Z", "status": "final_running", "note": "v7 (2a489be4) uploaded with README, golden_results.json, golden_trajectory.json, instruction mentions legacy rule. QC-Oracle-GLM running."}, {"at": "2026-09-09T17:32:10Z", "status": "final_running", "note": "gen-g857 v7 re-run QC-Oracle-GLM (content-2a489be4)"}, {"at": "2026-09-09T17:54:31Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g857.zip"}, {"at": "2026-09-09T18:28:38Z", "status": "accepted", "note": "gen-g857 #1e1bf1 submitted on portal (Ready to submit \u2192 Submit clicked)"}, {"at": "2026-09-09T18:37:38Z", "status": "uploaded", "note": "gen-g857 submitted to pipeline Sep 9 11:34 PM \u2014 Final QC Running, awaiting verdict"}, {"at": "2026-09-09T18:46:48Z", "status": "final_running", "note": "Pipeline error on first submission (Sep 9 11:34 PM) \u2014 awaiting retry/verdict"}, {"at": "2026-09-09T19:21:12Z", "status": "final_running", "note": "gen-g857 v7 uploaded (84 depts, 110 checks, no legacy issues, stability evidence included) + eval started"}, {"at": "2026-09-09T21:53:00Z", "status": "needs_densify", "note": "Fixed: renamed traps, removed contrived aliases, removed undisclosed memo checks, added CSV format requirement. 104 depts, 123 checks. Needs fresh GLM runs."}, {"at": "2026-09-09T22:15:46Z", "status": "ready_final", "note": "All fixes: tightened regexes, cross-check test, eval evidence (Oracle 1.0, GLM 2/4, Stability 3x1.0), fixed memo+review.csv"}, {"at": "2026-09-10T15:27:27Z", "status": "final_running", "note": "gen-g857 v9 uploaded (#312d0a) + PreQC + eval started. 123 checks, tightened memo, no-pipe, no stale evals."}, {"at": "2026-09-10T15:48:16Z", "status": "final_running", "note": "gen-g857 v9 eval STARTED (platform runs fresh Oracle+GLM x4)"}, {"at": "2026-09-10T16:23:57Z", "status": "ready_final", "note": "REBUILT from scratch: Department Taxonomy Migration task (30 people, 16 nodes, 69 checks). Correct task spec."}, {"at": "2026-09-10T16:26:57Z", "status": "final_running", "note": "gen-g857 taxonomy migration v1 uploaded (#a41d17) + PreQC + eval started. 69 checks, 30 people, 16 nodes."}, {"at": "2026-09-10T17:10:18Z", "status": "final_running", "note": "gen-g857 taxonomy migration v1 eval running (correct task, 69 checks)"}, {"at": "2026-09-10T17:53:20Z", "status": "final_running", "note": "gen-g857 taxonomy migration eval clicked (slots were free)"}, {"at": "2026-09-10T18:37:56Z", "status": "final_running", "note": "Session F: synced pack_path + zips to Downloads portal upload; extracted under qc-out/ework"}, {"at": "2026-09-10T19:27:46Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g857.zip"}, {"at": "2026-09-10T19:33:55Z", "status": "ready_final", "note": "Hardened for 6 PreQC gaps (unmapped schema, status regex, headcount schema, cycle grading, dup keys, rollup pytest). Zip ready at Downloads. Portal upload blocked by Chrome profile contention from other sessions."}, {"at": "2026-09-10T20:25:38Z", "status": "ready_final", "note": "Packaged UPLOAD-THIS-TO-QC-gen-g857.zip"}, {"at": "2026-09-10T20:27:52Z", "status": "ready_final", "note": "TRACKING: hardened zip ready. Portal 3/3 eval slots busy \u2014 queued. Will click PreQC+Oracle when slot frees. Prior upload often landed on old #a41d17."}, {"at": "2026-09-10T20:30:16Z", "status": "ready_final", "note": "UPLOADED v2 #fae8c6 (content-2a489be4...-v2). PreQC not run yet. Waiting for portal slot (3/3 busy: c227, f53, old g857 a41d17, g806). Tracker polling."}, {"at": "2026-09-10T20:33:39Z", "status": "ready_final", "note": "TRACK: v2 #fae8c6 uploaded. PreQC click attempted (may still show not-run). Oracle blocked 3/3 slots. Profile held by g806-loop \u2014 waiting to reclaim. c251 #1ddef3 still needs gates."}, {"at": "2026-09-10T20:43:17Z", "status": "ready_final", "note": "AUTO: v2 #fae8c6 up. PreQC clicked earlier. Oracle waiting slots. Durable f-loop started amid profile contention (B/h40)."}, {"at": "2026-09-10T20:46:01Z", "status": "final_running", "note": "AUTO: v2 #fae8c6 PreQC done (8 findings, leave unconfirmed). QC-Oracle-GLM RUNNING. Polling. c251 still blocked on slots."}, {"at": "2026-09-10T20:52:43Z", "status": "final_running", "note": "Switched to OpenCode-style keepchrome (1 headless Chrome, never close/reopen). Polling v2 Oracle + c251 gates. max-eval 3."}], "updated_at": "2026-09-10T20:52:43Z", "last_preqc": {"at": "2026-09-09T08:21:58Z", "out_dir": "C:\\Users\\Haseeb Mirza\\OneDrive\\Documents\\-haseeb-harbor-pipeline\\qc-out\\NONC-B1-1001684\\2026-09-09T082134Z", "qc_verdict": "FAIL", "full_model": false, "must_fix_count": 7, "finding_counts": {"INFO": 5, "P0": 0, "P1": 7, "P2": 1}, "verdict_md": "C:\\Users\\Haseeb Mirza\\OneDrive\\Documents\\-haseeb-harbor-pipeline\\qc-out\\NONC-B1-1001684\\2026-09-09T082134Z\\verdict.md", "findings_csv": "C:\\Users\\Haseeb Mirza\\OneDrive\\Documents\\-haseeb-harbor-pipeline\\qc-out\\NONC-B1-1001684\\2026-09-09T082134Z\\findings.csv"}, "packaged_at": "2026-09-10T20:25:38Z", "portal": {"version": "v1", "watch": true, "last_check_at": "2026-09-10T17:53:20Z", "phase": "glm_or_oracle_running", "checks": [{"at": "2026-09-08T21:57:39Z", "phase": "glm_or_oracle_running", "running": true, "note": "Portal: QC-Oracle-GLM started for gen-g857 v1 (content-5eb1eb1f)", "glm_pass": null, "oracle": null}, {"at": "2026-09-08T22:10:51Z", "phase": "complete", "running": false, "note": "TOO_EASY: 4/4 GLM passed, needs densification", "glm_pass": "4/4", "oracle": "1.0"}, {"at": "2026-09-08T22:27:42Z", "phase": "glm_or_oracle_running", "running": true, "note": "Densified gen-g857 v2 uploaded + PreQC + QC-Oracle-GLM started (content-d5630788)", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T06:02:26Z", "phase": "oracle_running", "running": true, "note": "v2 (content-d5630788) PreQC done (QC incomplete 0 findings, advisory); QC-Oracle-GLM eval started 06:02", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T06:07:06Z", "phase": "oracle_running", "running": true, "note": "gen-g857 v2 (content-d5630788) Oracle running 293s, GLM waiting. Client PreQC incomplete (advisory).", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T06:17:13Z", "phase": "oracle_running", "running": true, "note": "v2 Oracle running 901s, waiting for cloud capacity. GLM waiting. No update for 11m.", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T06:25:28Z", "phase": "oracle_running", "running": true, "note": "Re-running QC-Oracle-GLM on v1 (local Oracle passed 1.0; portal failure was transient)", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T06:57:10Z", "phase": "oracle_running", "running": true, "note": "v4 uploaded with CORRECT densified gold (121 depts, was 64 in stale zip). PreQC done. QC-Oracle-GLM running \u00e2\u20ac\u201d Oracle should pass now.", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T07:24:40Z", "phase": "oracle_running", "running": true, "note": "v3 eval started (CRLF fix); Oracle waiting; ~50min total", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T07:25:08Z", "phase": "complete", "running": false, "note": "v4 Oracle PASSES (fixed stale gold). GLM 4/4 too easy. Needs densification to trip GLM.", "glm_pass": "4/4", "oracle": "1.0"}, {"at": "2026-09-09T08:15:53Z", "phase": "preqc_running", "running": true, "note": "gen-g857 v5 uploaded (content-d5630788). Clicked Run client preQC + Run QC-Oracle-GLM on portal. Waiting for eval to start.", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T08:32:20Z", "phase": "preqc_running", "running": true, "note": "gen-g857 v6 uploaded with 5 trap depts (121-125). 137 verifier checks, 126 departments. PreQC + QC-Oracle-GLM started on portal.", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T08:38:10Z", "phase": "oracle_running", "running": true, "note": "v1 (36fa5f0b) NEW content family with legacy-exclusion rule + 15 new trap depts. PreQC done (1 advisory). QC-Oracle-GLM running.", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T08:43:31Z", "phase": "glm_running", "running": true, "note": "v6 Oracle PASSED! GLM\u00d74 running 659s. 5 trap depts (121-125) should trip GLM. Waiting for difficulty result.", "glm_pass": null, "oracle": "1.0"}, {"at": "2026-09-09T09:04:08Z", "phase": "complete", "running": false, "note": "v6 Oracle PASSED but GLM 4/4 still too easy. 5 traps not enough. Other PC uploaded v1 (36fa5f0b) with 15 traps + legacy-exclusion rule. Checking that version.", "glm_pass": "4/4", "oracle": "1.0"}, {"at": "2026-09-09T09:39:05Z", "phase": "oracle_running", "running": true, "note": "v1 (ed239145) fixed verifier regex (15 assertions). PreQC done. QC-Oracle-GLM starting.", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T10:53:02Z", "phase": "oracle_running", "running": true, "note": "v1 (ed239145) re-running QC-Oracle-GLM after previous eval ERRORED (infrastructure failure, not difficulty). Oracle passed, GLM 0/4 was due to error. 3 PreQC findings advisory (legacy rule, sort-order, regex permissiveness).", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T13:01:14Z", "phase": "oracle_running", "running": true, "note": "v7 (2a489be4) uploaded with README, golden_results.json, golden_trajectory.json, instruction mentions legacy rule. QC-Oracle-GLM running.", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T17:32:10Z", "phase": "glm_or_oracle_running", "running": true, "note": "gen-g857 v7 re-run QC-Oracle-GLM (content-2a489be4)", "glm_pass": null, "oracle": null}, {"at": "2026-09-09T19:21:12Z", "phase": "glm_or_oracle_running", "running": true, "note": "gen-g857 v7 uploaded (84 depts, 110 checks, no legacy issues, stability evidence included) + eval started", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T15:27:27Z", "phase": "glm_or_oracle_running", "running": true, "note": "gen-g857 v9 uploaded (#312d0a) + PreQC + eval started. 123 checks, tightened memo, no-pipe, no stale evals.", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T15:48:16Z", "phase": "glm_or_oracle_running", "running": true, "note": "gen-g857 v9 eval STARTED (platform runs fresh Oracle+GLM x4)", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T16:26:57Z", "phase": "glm_or_oracle_running", "running": true, "note": "gen-g857 taxonomy migration v1 uploaded (#a41d17) + PreQC + eval started. 69 checks, 30 people, 16 nodes.", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T17:10:18Z", "phase": "glm_or_oracle_running", "running": true, "note": "gen-g857 taxonomy migration v1 eval running (correct task, 69 checks)", "glm_pass": null, "oracle": null}, {"at": "2026-09-10T17:53:20Z", "phase": "glm_or_oracle_running", "running": true, "note": "gen-g857 taxonomy migration eval clicked (slots were free)", "glm_pass": null, "oracle": null}], "glm_pass": "4/4", "oracle": "1.0", "task_url": "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-2a489be4b73a943d11d2c52efefae8c6-v1"}, "_zip": "C:\\Users\\Haseeb Mirza\\Downloads\\UPLOAD-THIS-TO-QC-gen-g857.zip"}], "maxEval": 4, "trainer": "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#", "profile": "C:/Users/Haseeb Mirza/.config/opencode/chrome-profile"};

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

async function startGates(page, short) {
  const pre = await clickIfVisible(page, /Run client preQC|Re-run client preQC/i);
  // Dismiss advisory PreQC findings only — never Confirm
  for (let i = 0; i < 8; i++) {
    if (!(await clickIfVisible(page, /^Dismiss$/i))) break;
  }
  let ev = await clickIfVisible(page, /Re-run QC-Oracle-GLM/i);
  if (!ev) ev = await clickIfVisible(page, /Run QC-Oracle-GLM/i);
  const t = await bodyText(page);
  fs.writeFileSync('tmp-pw/queue-' + short + '-gates.txt', t);
  console.log(JSON.stringify({ event: 'gates', short, preqc: pre, oracle: ev, head: t.slice(0, 900) }));
  return { pre, ev, t };
}

(async () => {
  let browser = await launch();
  let page = await ensurePage(browser);
  const results = [];

  await page.goto(cfg.trainer, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(5000);
  let root = await bodyText(page);
  if (/accounts\.google\.com/i.test(page.url()) || (/Sign in/i.test(root) && !/muhammad\.y7@turing\.com/i.test(root))) {
    console.log(JSON.stringify({ event: 'login_required' }));
    fs.writeFileSync('tmp-pw/queue-login-required.txt', root);
    await browser.close().catch(() => {});
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
      // Relaunch if previous job closed the context
      try {
        page = await ensurePage(browser);
        await page.evaluate(() => true);
      } catch (_) {
        console.log(JSON.stringify({ event: 'relaunch', short }));
        await browser.close().catch(() => {});
        browser = await launch();
        page = await ensurePage(browser);
      }

      if (status === 'ready_final') {
        await uploadZip(page, zip, short);
      }

      // If upload already landed on task page, skip list open
      let opened = '';
      if (/#task=/.test(page.url())) {
        opened = await bodyText(page);
        console.log(JSON.stringify({ event: 'already_on_task', short, url: page.url() }));
      } else {
        opened = await openLatest(page, stem);
        if (!opened) opened = await openLatest(page, short);
      }

      if (startedEvals >= cfg.maxEval) {
        console.log(JSON.stringify({ event: 'defer_eval', short, reason: 'max_eval' }));
        results.push({ short, deferred: true, uploaded: status === 'ready_final' });
        continue;
      }

      const g = await startGates(page, short);
      if (g.ev) startedEvals += 1;
      results.push({ short, uploaded: status === 'ready_final', gates: !!(g.pre || g.ev), preqc: g.pre, oracle: g.ev });
    } catch (e) {
      console.log(JSON.stringify({ event: 'error', short, error: String(e) }));
      results.push({ short, error: String(e) });
      await browser.close().catch(() => {});
      try {
        browser = await launch();
        page = await ensurePage(browser);
      } catch (e2) {
        console.log(JSON.stringify({ event: 'relaunch_failed', error: String(e2) }));
        break;
      }
    }
  }

  fs.writeFileSync('tmp-pw/queue-results.json', JSON.stringify(results, null, 2));
  console.log(JSON.stringify({ event: 'done', results }));
  // OpenCode-style: do NOT close Chrome — keep shared profile warm for the queue.
  // Process exits; persistent context may drop with it on some hosts, so prefer
  // tmp-pw-*-keepchrome.js for long polls. Here we at least avoid intentional close.
})().catch((e) => {
  console.error(JSON.stringify({ event: 'fatal', error: String(e) }));
  process.exit(1);
});
