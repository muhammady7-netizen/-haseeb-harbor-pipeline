"""Hard-rejoin poller: relaunch Chrome if it dies; never re-fire gates."""
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
    try:
        await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    except Exception:
        pass
    print(f"DUMP {tag}", " ".join(text.split())[:550], flush=True)
    return text


def on_task(text: str) -> bool:
    low = text.lower()
    return "harbor package" in low and "code-c227-table-bloat" in low


def parse_status(text: str) -> tuple[str, str, bool]:
    m_or = re.search(r"QC-Oracle-GLM[\s\S]{0,550}", text, re.I)
    ora = " ".join((m_or.group(0) if m_or else "").split())[:340]
    m_ex = re.search(
        r"ORACLE GOLDEN REPLAY[\s\S]{0,220}|GLM-5\.2[\s\S]{0,260}",
        text,
        re.I,
    )
    ex = " ".join((m_ex.group(0) if m_ex else "").split())[:240]
    low = text.lower()
    running = any(
        k in low
        for k in (
            "running now",
            "oracle running",
            "glm-5.2 ×4 difficulty running",
            "4 scored glm runs are in progress",
            "waiting for oracle",
            "starting…",
            "starting now",
        )
    )
    return ora, ex, running


def has_terminal(text: str) -> bool:
    low = text.lower()
    if any(
        k in low
        for k in (
            "too_easy",
            "too_hard",
            "glm 0/4",
            "glm 1/4",
            "glm 2/4",
            "glm 3/4",
            "glm 4/4",
            "trainer changes required",
            "ready for finalization",
        )
    ):
        # avoid false positive while still running
        if "running now" in low or "runs are in progress" in low:
            return False
        return True
    # Completed without TOO_EASY string sometimes
    if "oracle passed" in low and "glm-5.2" in low and "completed" in low and "running" not in low:
        return True
    return False


async def session_once(poll_from: int) -> tuple[str, int]:
    """Returns ('done'|'continue'|'crash', next_poll_index)."""
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            channel="chrome",
            headless=True,
            accept_downloads=True,
        )
        try:
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
            await asyncio.sleep(3)
            await page.evaluate(f"window.location.hash = 'task={V6}'")
            await asyncio.sleep(5)
            text = await dump(page, f"hard-open-{poll_from}")
            if not on_task(text):
                await page.goto(
                    f"{HOME}#task={V6}", wait_until="domcontentloaded", timeout=120000
                )
                await asyncio.sleep(6)
                text = await dump(page, f"hard-open2-{poll_from}")
            if not on_task(text):
                print("OPEN_FAIL", flush=True)
                return "continue", poll_from

            for i in range(poll_from, poll_from + 20):
                text = await page.inner_text("body")
                ora, ex, running = parse_status(text)
                print(f"poll{i} {ora}", flush=True)
                print(f"       {ex} running={running}", flush=True)
                if i % 4 == 0:
                    await dump(page, f"v6hard{i}")
                if has_terminal(text):
                    await dump(page, "v6-oracle-done")
                    print("DONE_SIGNAL", flush=True)
                    print("FINAL", " ".join(text.split())[:4000], flush=True)
                    return "done", i
                await asyncio.sleep(45)
            return "continue", poll_from + 20
        except Exception as e:
            print("session_crash", type(e).__name__, e, flush=True)
            return "crash", poll_from
        finally:
            try:
                await ctx.close()
            except Exception:
                pass


async def main() -> None:
    poll = 0
    for round_i in range(40):  # up to ~40 sessions
        print(f"SESSION {round_i} poll={poll}", flush=True)
        status, poll = await session_once(poll)
        if status == "done":
            return
        await asyncio.sleep(5)
    print("TIMEOUT", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
