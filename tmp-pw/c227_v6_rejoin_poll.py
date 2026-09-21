"""Reconnect to c227 v6 and poll QC-Oracle-GLM until finished (do not re-fire)."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
V6 = "shannon-continue-38a6f7358d4da27c27af3b2a-v6"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:80000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag}", " ".join(text.split())[:600], flush=True)
    return text


def on_task_page(text: str) -> bool:
    low = text.lower()
    return "harbor package" in low and "code-c227-table-bloat-maintenance-audit" in low


async def open_task(page) -> str:
    await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
    await page.wait_for_timeout(3000)
    await page.evaluate(f"window.location.hash = 'task={V6}'")
    await page.wait_for_timeout(5000)
    text = await dump(page, "rejoin-hash")
    if on_task_page(text):
        return text
    await page.goto(f"{HOME}#task={V6}", wait_until="domcontentloaded", timeout=120000)
    await page.wait_for_timeout(6000)
    return await dump(page, "rejoin-hash2")


async def main() -> None:
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            channel="chrome",
            headless=True,
            accept_downloads=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        text = await open_task(page)
        if not on_task_page(text):
            print("OPEN_FAIL", flush=True)
            await ctx.close()
            raise SystemExit(2)
        print("OPEN_OK", flush=True)

        for i in range(180):
            try:
                text = await page.inner_text("body")
            except Exception as e:
                print("read_fail", e, flush=True)
                text = await open_task(page)
            m_or = re.search(r"QC-Oracle-GLM[\s\S]{0,550}", text, re.I)
            ora = " ".join((m_or.group(0) if m_or else "").split())[:340]
            # also pull execution status block
            m_ex = re.search(
                r"ORACLE GOLDEN REPLAY[\s\S]{0,200}|GLM-5\.2[\s\S]{0,200}",
                text,
                re.I,
            )
            ex = " ".join((m_ex.group(0) if m_ex else "").split())[:200]
            print(f"poll{i} {ora}", flush=True)
            print(f"       {ex}", flush=True)
            if i % 4 == 0:
                await dump(page, f"v6rejoin{i}")

            ora_low = ora.lower()
            page_low = text.lower()
            still_running = any(
                k in ora_low or k in page_low
                for k in ("running now", "running…", "starting", "waiting for oracle", "oracle running")
            )
            has_result = any(
                k in page_low
                for k in (
                    "oracle 1.0",
                    "oracle 0.",
                    "glm 0/4",
                    "glm 1/4",
                    "glm 2/4",
                    "glm 3/4",
                    "glm 4/4",
                    "too_easy",
                    "too_hard",
                    "trainer changes required",
                    "ready for finalization",
                )
            )
            if has_result and not still_running:
                await dump(page, "v6-oracle-done")
                print("DONE_SIGNAL", flush=True)
                print("FINAL", " ".join(text.split())[:3500], flush=True)
                break
            # sleep via asyncio, not page, so browser death doesn't kill wait
            await asyncio.sleep(45)
            # refresh page periodically to avoid SPA stall
            if i > 0 and i % 10 == 0:
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=120000)
                    await page.wait_for_timeout(4000)
                except Exception as e:
                    print("reload_fail", e, flush=True)
                    text = await open_task(page)
        else:
            await dump(page, "v6-oracle-timeout")
            print("TIMEOUT", flush=True)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
