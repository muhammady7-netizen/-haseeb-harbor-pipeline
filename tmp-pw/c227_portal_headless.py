"""Navigate to c227 task, upload new version, run PreQC + QC-Oracle-GLM headless."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
ZIP = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip"
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
TASK_HASH = "content-a6f663b04ba9599d834b0d6495bcfd6e-v1"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:20000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag} url={page.url} chars={len(text)}")
    return text


async def open_c227(page) -> bool:
    # Try hash route first
    await page.goto(f"{HOME}#task={TASK_HASH}", wait_until="domcontentloaded", timeout=120000)
    await page.wait_for_timeout(5000)
    text = await dump(page, "hash")
    if "code-c227" in text.lower() or "table-bloat" in text.lower():
        print("OPENED via hash")
        return True

    # SPA may need hash set after load
    await page.goto(HOME, wait_until="networkidle", timeout=120000)
    await page.wait_for_timeout(3000)
    await page.evaluate(f"window.location.hash = 'task={TASK_HASH}'")
    await page.wait_for_timeout(5000)
    text = await dump(page, "hash2")
    if "code-c227" in text.lower() or "table-bloat" in text.lower():
        print("OPENED via hash2")
        return True

    # Search recent / pipeline list
    await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
    await page.wait_for_timeout(4000)
    for probe in (
        "code-c227-table-bloat-maintenance-audit",
        "code-c227",
        "table-bloat",
        "bloat-maintenance",
    ):
        loc = page.get_by_text(re.compile(probe, re.I))
        n = await loc.count()
        print("probe", probe, n)
        if n:
            await loc.first.click(timeout=8000)
            await page.wait_for_timeout(4000)
            text = await dump(page, "click")
            if "preqc" in text.lower() or "oracle" in text.lower() or "upload new" in text.lower():
                print("OPENED via click", probe)
                return True

    # Try All tasks / search box
    for sel in ("All tasks", "Search", "Browse"):
        b = page.get_by_role("button", name=re.compile(sel, re.I))
        if await b.count():
            await b.first.click()
            await page.wait_for_timeout(2000)
    search = page.locator("input[type='search'], input[placeholder*='Search' i], input[placeholder*='task' i]")
    if await search.count():
        await search.first.fill("code-c227")
        await page.wait_for_timeout(2000)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)
        loc = page.get_by_text(re.compile("code-c227", re.I))
        if await loc.count():
            await loc.first.click()
            await page.wait_for_timeout(4000)
            await dump(page, "search")
            return True

    await dump(page, "notfound")
    return False


async def upload_new_version(page) -> bool:
    # Click Upload new version / upload zip into task
    for name in ("Upload new version", "Upload", "Replace package", "Choose file"):
        btn = page.get_by_role("button", name=re.compile(name, re.I))
        if await btn.count() == 0:
            btn = page.get_by_text(re.compile(name, re.I))
        if not await btn.count():
            continue
        print("try upload control", name)
        try:
            async with page.expect_file_chooser(timeout=8000) as fc:
                await btn.first.click(timeout=5000)
            chooser = await fc.value
            await chooser.set_files(str(ZIP))
            print("FILE_CHOSEN", ZIP.name)
            await page.wait_for_timeout(8000)
            # confirm upload
            for conf in ("Upload", "Confirm", "Submit", "Save"):
                c = page.get_by_role("button", name=re.compile(f"^{conf}$", re.I))
                if await c.count():
                    await c.first.click(timeout=4000)
                    print("UPLOAD_CONFIRM", conf)
                    await page.wait_for_timeout(5000)
            await dump(page, "after-upload")
            return True
        except Exception as e:
            print("upload control fail", name, type(e).__name__, e)
            # maybe need input[type=file]
            inp = page.locator("input[type='file']")
            if await inp.count():
                await inp.first.set_input_files(str(ZIP))
                print("SET_INPUT_FILES")
                await page.wait_for_timeout(8000)
                await dump(page, "after-upload-input")
                return True
    # Drop zone fallback
    inp = page.locator("input[type='file']")
    if await inp.count():
        await inp.first.set_input_files(str(ZIP))
        print("SET_INPUT_FILES_DIRECT")
        await page.wait_for_timeout(8000)
        await dump(page, "after-upload-direct")
        return True
    return False


async def click_named(page, names: tuple[str, ...], tag: str) -> bool:
    for name in names:
        loc = page.get_by_role("button", name=re.compile(re.escape(name), re.I))
        if await loc.count() == 0:
            loc = page.get_by_text(re.compile(rf"^{re.escape(name)}$", re.I))
        if await loc.count() == 0:
            loc = page.get_by_text(re.compile(name, re.I))
        if not await loc.count():
            continue
        try:
            await loc.first.scroll_into_view_if_needed()
            await loc.first.click(timeout=8000)
            print(f"CLICKED_{tag}", name)
            await page.wait_for_timeout(3000)
            for conf in ("Confirm", "Run", "Yes", "Start", "OK"):
                c = page.get_by_role("button", name=re.compile(f"^{conf}$", re.I))
                if await c.count():
                    try:
                        await c.first.click(timeout=2500)
                        print(f"CONFIRM_{tag}", conf)
                        await page.wait_for_timeout(2000)
                    except Exception:
                        pass
            return True
        except Exception as e:
            print(f"click fail {tag}", name, type(e).__name__, e)
    return False


async def main() -> None:
    assert ZIP.exists(), ZIP
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            channel="chrome",
            headless=True,
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        ok = await open_c227(page)
        print("TASK_OPEN", ok)
        if not ok:
            await context.close()
            return

        uploaded = await upload_new_version(page)
        print("UPLOADED", uploaded)

        preqc = await click_named(
            page,
            (
                "Re-run client preQC",
                "Run client preQC",
                "Client PreQC",
                "Re-run PreQC",
            ),
            "PREQC",
        )
        oracle = await click_named(
            page,
            (
                "Re-run QC-Oracle-GLM",
                "Run QC-Oracle-GLM",
                "QC-Oracle-GLM check",
                "QC-Oracle-GLM",
                "Start evaluation",
                "Run evaluation",
            ),
            "ORACLE",
        )
        await page.wait_for_timeout(5000)
        text = await dump(page, "final")
        print("RESULT", {"task_open": ok, "uploaded": uploaded, "preqc": preqc, "oracle": oracle})
        print("FINAL_SNIP", " ".join(text.split())[:700])
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
