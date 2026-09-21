"""Wait for c227 new version to finish opening, then run PreQC + QC-Oracle-GLM."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
TASK_HASH = "content-a6f663b04ba9599d834b0d6495bcfd6e-v1"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:25000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    snip = " ".join(text.split())[:500]
    print(f"DUMP {tag} :: {snip}")
    return text


async def click_run(page, names: tuple[str, ...], tag: str) -> bool:
    for name in names:
        # Prefer exact button roles
        candidates = [
            page.get_by_role("button", name=re.compile(re.escape(name), re.I)),
            page.locator("button").filter(has_text=re.compile(name, re.I)),
            page.get_by_text(re.compile(name, re.I)),
        ]
        for loc in candidates:
            try:
                n = await loc.count()
            except Exception:
                n = 0
            if not n:
                continue
            for i in range(min(n, 3)):
                el = loc.nth(i)
                try:
                    if not await el.is_visible():
                        continue
                    await el.scroll_into_view_if_needed()
                    await el.click(timeout=8000, force=True)
                    print(f"CLICKED_{tag}", name, "idx", i)
                    await page.wait_for_timeout(2500)
                    for conf in ("Confirm", "Run", "Yes", "Start", "OK", "Continue"):
                        c = page.get_by_role("button", name=re.compile(f"^{conf}$", re.I))
                        if await c.count():
                            try:
                                await c.first.click(timeout=2500, force=True)
                                print(f"CONFIRM_{tag}", conf)
                                await page.wait_for_timeout(1500)
                            except Exception:
                                pass
                    return True
                except Exception as e:
                    print(f"click err {tag}", name, i, type(e).__name__, e)
    return False


async def main() -> None:
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            channel="chrome",
            headless=True,
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(2000)
        await page.evaluate(f"window.location.hash = 'task={TASK_HASH}'")
        await page.wait_for_timeout(4000)

        # Poll until version finishes opening
        ready = False
        for i in range(24):  # up to ~2 min
            text = await page.inner_text("body")
            low = text.lower()
            opening = "opening new version" in low or "uploading" in low
            print(f"poll {i} opening={opening} preqc_not={'not run yet' in low}")
            if not opening and ("code-c227" in low or "table-bloat" in low):
                ready = True
                if i >= 2:
                    break
            await page.wait_for_timeout(5000)
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await page.evaluate(f"window.location.hash = 'task={TASK_HASH}'")
            await page.wait_for_timeout(2000)

        text = await dump(page, "ready")
        print("READY", ready)

        # Switch to latest version if version picker present
        for lab in ("latest", "Switch version", "v2", "v3"):
            loc = page.get_by_text(re.compile(lab, re.I))
            if await loc.count():
                print("version-ish", lab, await loc.count())

        preqc = await click_run(
            page,
            (
                "Re-run client preQC",
                "Run client preQC",
                "Client preQC",
            ),
            "PREQC",
        )
        await page.wait_for_timeout(4000)
        oracle = await click_run(
            page,
            (
                "Re-run QC-Oracle-GLM",
                "Run QC-Oracle-GLM",
                "QC-Oracle-GLM",
            ),
            "ORACLE",
        )
        await page.wait_for_timeout(8000)
        text = await dump(page, "triggered")
        print("TRIGGER", {"preqc": preqc, "oracle": oracle})
        # Extract status lines
        for pat in (
            r"Client [Pp]reQC.{0,80}",
            r"QC-Oracle-GLM.{0,120}",
            r"Evaluation.{0,80}",
            r"opening new version.{0,40}",
            r"v\d+.{0,40}",
        ):
            m = re.search(pat, text)
            if m:
                print("HIT", m.group(0).replace("\n", " ")[:160])
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
