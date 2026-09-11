import json
import re
from pathlib import Path

C = Path(r"qc-out/ework/code-c251-portal/code-c251-pdf-form-field-conversion-audit")
G = Path(r"qc-out/ework/gen-g857-portal/gen-g857-department-directory-categorization-audit")


def failed_from_stdout(out: str) -> int:
    m = re.search(r"(\d+) failed", out)
    if m:
        return int(m.group(1))
    if re.search(r"\d+ passed", out) and "failed" not in out.split("=====")[-1].lower():
        return 0
    # "93 passed in"
    if re.search(r"=\s*\d+ passed in", out):
        return 0
    raise ValueError("cannot parse", out[-200:])


for pack, label in [(C, "c251"), (G, "g857")]:
    print("====", label)
    for r in ["r1", "r2", "r3", "r4"]:
        meta = (pack / f"evaluations/glm-5.2/{r}/verifier/reward_meta.txt").read_text()
        out = (pack / f"evaluations/glm-5.2/{r}/verifier/test-stdout.txt").read_text(
            encoding="utf-8", errors="replace"
        )
        failed_meta = int(re.search(r"failed=(\d+)", meta).group(1))
        failed_out = failed_from_stdout(out)
        reward = float(re.search(r"reward=([0-9.]+)", meta).group(1))
        ctrf = json.loads((pack / f"evaluations/glm-5.2/{r}/verifier/ctrf.json").read_text())
        ctrf_f = ctrf["results"]["summary"]["failed"]
        rj = float(
            json.loads((pack / f"evaluations/glm-5.2/{r}/result.json").read_text())[
                "verifier_result"
            ]["rewards"]["reward"]
        )
        summary = json.loads(
            (pack / f"evaluations/glm-5.2/{r}/verifier/verifier_summary.json").read_text()
        )
        ok = failed_meta == failed_out == ctrf_f == summary["failed"] and abs(reward - rj) < 1e-9
        extra = ""
        if label == "c251":
            m = (pack / f"evaluations/glm-5.2/{r}/artifacts/pdf_form_memo.md").read_text(
                encoding="utf-8"
            )
            t = (pack / f"evaluations/glm-5.2/{r}/agent/trajectory.json").read_text()
            extra = (
                f" path_ok={('HASEEB' not in m and 'C:/' not in m)}"
                f" placeholder={('(sample row + standard excerpts)' in t)}"
            )
        print(r, "aligned", ok, "failed", failed_meta, "reward", reward, extra)

print(
    "zips",
    (Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c251.zip").stat().st_size,
    (Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-gen-g857.zip").stat().st_size,
)
by = {v["name"]: v for v in json.loads((G / "tests/verifier.json").read_text())["verifiers"]}
print("hc_root_rolled", by["hc_root_rolled"]["metadata"]["weight"])
