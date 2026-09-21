"""Upload c227 v4 (Dockerfile fix), run PreQC + Oracle, poll to completion."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
ZIP = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip"
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
V3 = "shannon-continue-38a6f7358d4da27c27af3b2a-v4"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:60000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag}", " ".join(text.split())[:700], flush=True)
    return text


async def js_click(page, label: str) -> bool:
    ok = await page.evaluate(
        """(label) => {
          const b = [...document.querySelectorAll('button,a')]
            .find(x => (x.innerText||'').trim().replace(/\\s+/g,' ') === label);
          if (!b) return false; b.click(); return true;
        }""",
        label,
    )
    print("click", label, ok, flush=True)
    return bool(ok)


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
        await dump(page, "pre-v4")

        btn = page.get_by_role("button", name=re.compile(r"Upload new version", re.I))
        if await btn.count():
            async with page.expect_file_chooser(timeout=15000) as fc:
                await btn.first.click()
            chooser = await fc.value
            await chooser.set_files(str(ZIP))
            print("FILE_SET", flush=True)
            await page.wait_for_timeout(2000)
            await js_click(page, "Upload")
            await page.wait_for_timeout(5000)

        for i in range(20):
            text = await page.inner_text("body")
            if "opening new version" not in text.lower() and i >= 1:
                break
            print("waiting open", i, flush=True)
            await page.wait_for_timeout(4000)

        if await sel.count():
            try:
                await sel.first.select_option(index=0)
                print("selected latest", flush=True)
            except Exception as e:
                print("select fail", e, flush=True)
            await page.wait_for_timeout(3000)

        await dump(page, "on-v4")
        await js_click(page, "Run client preQC") or await js_click(page, "Re-run client preQC")
        await page.wait_for_timeout(3000)
        await js_click(page, "Run QC-Oracle-GLM") or await js_click(page, "Re-run QC-Oracle-GLM")

        for i in range(150):  # ~112 min at 45s
            await page.wait_for_timeout(45000)
            text = await page.inner_text("body")
            m_or = re.search(r"QC-Oracle-GLM[\s\S]{0,350}", text, re.I)
            ora = " ".join((m_or.group(0) if m_or else "").split())[:260]
            print(f"poll{i} {ora}", flush=True)
            if i % 5 == 0:
                await dump(page, f"v4poll{i}")
            ora_low = ora.lower()
            if m_or and "running" not in ora_low and "starting" not in ora_low and "not run yet" not in ora_low:
                await dump(page, "v4-done")
                print("DONE_SIGNAL", flush=True)
                print("FINAL", " ".join(text.split())[:2000], flush=True)
                break
        else:
            await dump(page, "v4-timeout")
            print("TIMEOUT", flush=True)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
