"""Open c227 from Recent tasks, ensure latest version, run PreQC + Oracle-GLM."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
ZIP = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip"
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:30000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag} url={page.url}")
    print("SNIP", " ".join(text.split())[:600])
    return text


async def on_task_page(text: str) -> bool:
    low = text.lower()
    return (
        "code-c227-table-bloat-maintenance-audit" in low
        and ("review.csv" in low or "client preqc" in low or "harbor package" in low)
        and "drop a task here" not in low
    )


async def open_task(page) -> bool:
    await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
    await page.wait_for_timeout(5000)
    await dump(page, "home")

    # Click the recent-tasks card for c227 (prefer exact package name)
    for label in (
        "code-c227-table-bloat-maintenance-audit",
        "Table bloat maintenance audit",
    ):
        loc = page.get_by_text(label, exact=False)
        n = await loc.count()
        print("cards", label, n)
        if not n:
            continue
        # click the last/most specific visible match
        for i in range(n - 1, -1, -1):
            el = loc.nth(i)
            try:
                if not await el.is_visible():
                    continue
                await el.click(timeout=8000)
                await page.wait_for_timeout(5000)
                text = await dump(page, "opened")
                if await on_task_page(text):
                    return True
            except Exception as e:
                print("open click fail", i, type(e).__name__, e)
    return False


async def ensure_latest_and_upload(page) -> None:
    text = await page.inner_text("body")
    # If still opening, wait
    for i in range(20):
        low = text.lower()
        if "opening new version" in low:
            print("waiting open", i)
            await page.wait_for_timeout(5000)
            text = await page.inner_text("body")
            continue
        break
    await dump(page, "pre-upload-state")

    # Upload new version again to be sure latest zip is on this version
    for name in ("Upload new version",):
        btn = page.get_by_role("button", name=re.compile(name, re.I))
        if await btn.count():
            try:
                async with page.expect_file_chooser(timeout=10000) as fc:
                    await btn.first.click()
                chooser = await fc.value
                await chooser.set_files(str(ZIP))
                print("UPLOADED_ZIP")
                await page.wait_for_timeout(5000)
                conf = page.get_by_role("button", name=re.compile(r"^Upload$", re.I))
                if await conf.count():
                    await conf.first.click()
                    print("CONFIRMED_UPLOAD")
                await page.wait_for_timeout(10000)
            except Exception as e:
                print("upload fail", type(e).__name__, e)

    # Wait for opening to finish
    for i in range(30):
        text = await page.inner_text("body")
        if "opening new version" not in text.lower():
            print("version settled", i)
            break
        print("still opening", i)
        await page.wait_for_timeout(4000)
    await dump(page, "version-settled")


async def run_gate(page, names: tuple[str, ...], tag: str) -> bool:
    for name in names:
        btns = page.get_by_role("button", name=re.compile(re.escape(name), re.I))
        n = await btns.count()
        print(f"gate {tag} candidates for '{name}':", n)
        for i in range(n):
            el = btns.nth(i)
            try:
                txt = (await el.inner_text()).strip()
                print(f"  btn[{i}]={txt!r} visible={await el.is_visible()}")
                if not await el.is_visible():
                    continue
                await el.scroll_into_view_if_needed()
                await el.click(timeout=8000)
                print(f"CLICKED_{tag}", txt)
                await page.wait_for_timeout(2000)
                for conf in ("Confirm", "Run", "Yes", "Start"):
                    c = page.get_by_role("button", name=re.compile(f"^{conf}$", re.I))
                    if await c.count() and await c.first.is_visible():
                        await c.first.click(timeout=3000)
                        print(f"CONFIRM_{tag}", conf)
                        await page.wait_for_timeout(1500)
                return True
            except Exception as e:
                print("gate click err", type(e).__name__, e)
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
        ok = await open_task(page)
        print("OPEN", ok)
        if not ok:
            await context.close()
            return

        await ensure_latest_and_upload(page)

        preqc = await run_gate(
            page,
            ("Re-run client preQC", "Run client preQC"),
            "PREQC",
        )
        await page.wait_for_timeout(3000)
        oracle = await run_gate(
            page,
            ("Re-run QC-Oracle-GLM", "Run QC-Oracle-GLM"),
            "ORACLE",
        )
        await page.wait_for_timeout(10000)
        text = await dump(page, "done")
        print("FINAL", {"preqc": preqc, "oracle": oracle})
        for pat in (
            r"Client [Pp]reQC[\s\S]{0,120}",
            r"QC-Oracle-GLM[\s\S]{0,160}",
            r"Evaluation[\s\S]{0,100}",
            r"v\d+ · latest",
            r"opening new version",
            r"running|queued|in progress|complete",
        ):
            m = re.search(pat, text, re.I)
            if m:
                print("HIT", " ".join(m.group(0).split())[:200])
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
