"""Long-poll c227 v3 until QC-Oracle-GLM finishes (up to ~90 min)."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
V3 = "shannon-continue-38a6f7358d4da27c27af3b2a-v3"


async def main() -> None:
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            channel="chrome",
            headless=True,
            accept_downloads=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(2000)
        await page.evaluate(f"window.location.hash = 'task={V3}'")
        await page.wait_for_timeout(4000)
        sel = page.locator("select")
        if await sel.count():
            try:
                await sel.first.select_option(value=V3)
            except Exception:
                pass

        for i in range(120):  # 120 * 45s ≈ 90 min
            await page.wait_for_timeout(45000)
            text = await page.inner_text("body")
            low = text.lower()
            m_or = re.search(r"QC-Oracle-GLM[\s\S]{0,300}", text, re.I)
            m_ev = re.search(r"5\s*Evaluation[\s\S]{0,100}|Evaluation[\s\S]{0,100}", text, re.I)
            ora = " ".join((m_or.group(0) if m_or else "").split())[:240]
            ev = " ".join((m_ev.group(0) if m_ev else "").split())[:120]
            print(f"poll{i} ev={ev}", flush=True)
            print(f"       ora={ora}", flush=True)

            ora_low = ora.lower()
            finished = (
                m_or is not None
                and "running" not in ora_low
                and "not run yet" not in ora_low
                and "starting" not in ora_low
            )
            # also catch terminal outcomes in page
            if any(
                k in low
                for k in (
                    "oracle 1.0",
                    "glm 0/4",
                    "glm 1/4",
                    "glm 2/4",
                    "glm 3/4",
                    "glm 4/4",
                    "delivery gate",
                )
            ) and "running now" not in low:
                finished = True

            if i % 4 == 0:
                (OUT / f"portal-c227-contpoll{i}.txt").write_text(text[:50000], encoding="utf-8")
                await page.screenshot(
                    path=str(OUT / f"portal-c227-contpoll{i}.png"), full_page=True
                )

            if finished:
                (OUT / "portal-c227-oracle-done.txt").write_text(text[:80000], encoding="utf-8")
                await page.screenshot(
                    path=str(OUT / "portal-c227-oracle-done.png"), full_page=True
                )
                print("DONE_SIGNAL", flush=True)
                print("FINAL", " ".join(text.split())[:2000], flush=True)
                break
        else:
            text = await page.inner_text("body")
            (OUT / "portal-c227-oracle-timeout.txt").write_text(text[:80000], encoding="utf-8")
            print("TIMEOUT", " ".join(text.split())[:1500], flush=True)

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
