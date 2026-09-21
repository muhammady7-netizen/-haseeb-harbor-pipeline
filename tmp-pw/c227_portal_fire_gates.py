"""On shannon-continue c227 task: wait for version open, run PreQC + Oracle-GLM."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
# From last successful upload navigation
TASK = (
    "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
    "#task=shannon-continue-38a6f7358d4da27c27af3b2a-v1"
)


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:30000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag} url={page.url}")
    print("SNIP", " ".join(text.split())[:700])
    return text


async def click_text_button(page, label: str, tag: str) -> bool:
    patterns = [
        page.get_by_role("button", name=re.compile(re.escape(label), re.I)),
        page.locator("button, a, [role='button']").filter(
            has_text=re.compile(rf"^{re.escape(label)}$", re.I)
        ),
        page.get_by_text(re.compile(rf"^{re.escape(label)}$", re.I)),
        page.get_by_text(re.compile(label, re.I)),
    ]
    for loc in patterns:
        try:
            n = await loc.count()
        except Exception:
            continue
        print(f"  probe {label!r} -> {n}")
        for i in range(min(n, 5)):
            el = loc.nth(i)
            try:
                if not await el.is_visible():
                    continue
                box = await el.bounding_box()
                if not box or box["height"] < 1:
                    continue
                await el.scroll_into_view_if_needed()
                await el.click(timeout=8000, force=True)
                print(f"CLICKED_{tag}", label, "via", i)
                await page.wait_for_timeout(2500)
                for conf in ("Confirm", "Run", "Yes", "Start", "OK"):
                    c = page.get_by_role("button", name=re.compile(f"^{conf}$", re.I))
                    if await c.count() and await c.first.is_visible():
                        await c.first.click(timeout=3000, force=True)
                        print(f"CONFIRM_{tag}", conf)
                        await page.wait_for_timeout(1500)
                return True
            except Exception as e:
                print("click err", type(e).__name__, e)
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
        await page.goto(
            "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer",
            wait_until="domcontentloaded",
            timeout=120000,
        )
        await page.wait_for_timeout(2000)
        await page.evaluate(
            "window.location.hash = 'task=shannon-continue-38a6f7358d4da27c27af3b2a-v1'"
        )
        await page.wait_for_timeout(5000)

        # Poll until version open completes
        for i in range(40):
            text = await page.inner_text("body")
            low = text.lower()
            opening = "opening new version" in low
            print(f"poll {i} opening={opening} has_run_preqc={'run client preqc' in low}")
            if not opening and "code-c227" in low and "drop a task here" not in low:
                # settled enough
                if i >= 1:
                    break
            await page.wait_for_timeout(5000)
            # soft refresh without losing hash
            await page.evaluate("window.location.reload()")
            await page.wait_for_timeout(4000)

        text = await dump(page, "settled2")

        preqc = await click_text_button(page, "Run client preQC", "PREQC")
        if not preqc:
            preqc = await click_text_button(page, "Re-run client preQC", "PREQC")
        await page.wait_for_timeout(4000)
        oracle = await click_text_button(page, "Run QC-Oracle-GLM", "ORACLE")
        if not oracle:
            oracle = await click_text_button(page, "Re-run QC-Oracle-GLM", "ORACLE")

        await page.wait_for_timeout(12000)
        text = await dump(page, "gates-fired")
        print("RESULT", {"preqc": preqc, "oracle": oracle})
        for pat in (
            r"Client [Pp]reQC[\s\S]{0,160}",
            r"QC-Oracle-GLM[\s\S]{0,200}",
            r"opening new version",
            r"running|queued|in progress|PreQC complete|Oracle",
        ):
            m = re.search(pat, text, re.I)
            if m:
                print("HIT", " ".join(m.group(0).split())[:220])
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
