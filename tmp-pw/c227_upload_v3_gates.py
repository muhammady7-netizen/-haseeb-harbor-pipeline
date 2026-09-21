"""Upload fixed zip as new version on c227 v2 task lineage; run PreQC + Oracle-GLM."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
ZIP = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip"
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
V2 = "shannon-continue-38a6f7358d4da27c27af3b2a-v2"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:40000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag} url={page.url}")
    print("SNIP", " ".join(text.split())[:900])
    return text


async def js_click(page, label: str) -> bool:
    r = await page.evaluate(
        """(label) => {
          const btns = [...document.querySelectorAll('button,a,[role=button]')]
            .filter(b => (b.innerText||'').trim().replace(/\\s+/g,' ') === label);
          if (!btns.length) return false;
          btns[0].click();
          return true;
        }""",
        label,
    )
    print("click", label, r)
    return bool(r)


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
        await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(2000)
        await page.evaluate(f"window.location.hash = 'task={V2}'")
        await page.wait_for_timeout(5000)
        # ensure select on v2
        sel = page.locator("select")
        if await sel.count():
            try:
                await sel.first.select_option(value=V2)
            except Exception:
                pass
        await dump(page, "pre-v3-upload")

        # Upload new version
        btn = page.get_by_role("button", name=re.compile(r"Upload new version", re.I))
        if await btn.count():
            async with page.expect_file_chooser(timeout=15000) as fc:
                await btn.first.click()
            chooser = await fc.value
            await chooser.set_files(str(ZIP))
            print("FILE_SET")
            await page.wait_for_timeout(3000)
            await js_click(page, "Upload")
            await page.wait_for_timeout(8000)

        # Wait for opening / new version
        for i in range(24):
            text = await page.inner_text("body")
            low = text.lower()
            opening = "opening new version" in low
            print(f"wait {i} opening={opening}")
            if not opening and i >= 1:
                # detect newest version id in hash/select
                break
            await page.wait_for_timeout(5000)

        # Prefer latest option in select
        if await sel.count():
            options = await sel.first.locator("option").all()
            vals = []
            for opt in options:
                vals.append(await opt.get_attribute("value"))
            print("versions", vals)
            if vals:
                latest = vals[0] if "latest" in (await sel.first.inner_text()).lower() else vals[0]
                # pick option whose label contains latest
                try:
                    await sel.first.select_option(index=0)
                    print("selected index 0")
                except Exception as e:
                    print("select idx fail", e)
                await page.wait_for_timeout(3000)

        text = await dump(page, "after-v3-upload")

        # Run PreQC then Oracle
        await js_click(page, "Run client preQC") or await js_click(page, "Re-run client preQC")
        await page.wait_for_timeout(3000)
        await js_click(page, "Run QC-Oracle-GLM") or await js_click(page, "Re-run QC-Oracle-GLM")

        for i in range(18):
            await page.wait_for_timeout(10000)
            text = await page.inner_text("body")
            low = text.lower()
            print(
                f"poll {i}: preqc_run={'running' in low and 'preqc' in low} "
                f"preqc_done={'preqc complete' in low or 'trainer changes' in low or '0 trainer' in low} "
                f"oracle_run={'oracle' in low and 'running' in low}"
            )
            if i in (0, 5, 11, 17):
                await dump(page, f"v3poll{i}")
            if ("preqc complete" in low or "0 trainer finding" in low) and (
                "oracle" in low and ("running" in low or "complete" in low or "queued" in low)
            ):
                break

        await dump(page, "v3-final")
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
