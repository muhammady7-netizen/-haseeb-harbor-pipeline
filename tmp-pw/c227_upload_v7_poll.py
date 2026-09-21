"""Upload c227 v7 (hard densify), run PreQC + Oracle-GLM, hard-poll."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
ZIP = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip"
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
BASE = "shannon-continue-38a6f7358d4da27c27af3b2a-v6"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:60000], encoding="utf-8")
    try:
        await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    except Exception:
        pass
    print(f"DUMP {tag}", " ".join(text.split())[:650], flush=True)
    return text


def on_task(text: str) -> bool:
    low = text.lower()
    return "harbor package" in low and "code-c227-table-bloat" in low


async def js_click(page, label: str) -> bool:
    ok = await page.evaluate(
        """(label) => {
          const nodes = [...document.querySelectorAll('button,a,[role=button]')];
          for (const n of nodes) {
            const t = (n.innerText||n.textContent||'').trim().replace(/\\s+/g,' ');
            if (t === label) { n.click(); return true; }
          }
          for (const n of nodes) {
            const t = (n.innerText||n.textContent||'').trim().replace(/\\s+/g,' ');
            if (t.toLowerCase().includes(label.toLowerCase())) { n.click(); return true; }
          }
          return false;
        }""",
        label,
    )
    print("click", label, ok, flush=True)
    return bool(ok)


async def open_base(page) -> str:
    await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
    await asyncio.sleep(3)
    await page.evaluate(f"window.location.hash = 'task={BASE}'")
    await asyncio.sleep(5)
    text = await dump(page, "v7-nav")
    if on_task(text):
        return text
    await page.goto(f"{HOME}#task={BASE}", wait_until="domcontentloaded", timeout=120000)
    await asyncio.sleep(6)
    return await dump(page, "v7-nav2")


async def main() -> None:
    assert ZIP.is_file(), ZIP
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            channel="chrome",
            headless=True,
            accept_downloads=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        text = await open_base(page)
        if not on_task(text):
            print("OPEN_FAIL", flush=True)
            await ctx.close()
            raise SystemExit(2)

        btn = page.get_by_role("button", name=re.compile(r"Upload new version", re.I))
        if await btn.count():
            async with page.expect_file_chooser(timeout=20000) as fc:
                await btn.first.click()
            chooser = await fc.value
            await chooser.set_files(str(ZIP))
            print("FILE_SET", ZIP.stat().st_size, flush=True)
            await asyncio.sleep(2)
            await js_click(page, "Upload")
            await asyncio.sleep(8)

        for i in range(30):
            text = await page.inner_text("body")
            if "v7" in text.lower() and "opening new version" not in text.lower():
                break
            print("waiting v7", i, flush=True)
            await asyncio.sleep(4)

        sel = page.locator("select")
        if await sel.count():
            try:
                await sel.first.select_option(index=0)
            except Exception:
                pass
        await asyncio.sleep(3)
        text = await dump(page, "on-v7")
        if "v7" not in text.lower():
            print("WARN_NOT_V7", flush=True)

        await js_click(page, "Run client preQC") or await js_click(page, "Re-run client preQC")
        for i in range(40):
            await asyncio.sleep(12)
            text = await page.inner_text("body")
            low = text.lower()
            print(f"preqc{i}", "0 findings" if "0 trainer finding" in low else "…", flush=True)
            if "0 trainer finding" in low and "preqc complete" in low and "running" not in low:
                break
            if i % 5 == 0:
                await dump(page, f"v7-preqc{i}")

        await dump(page, "v7-preqc-done")
        await js_click(page, "Run QC-Oracle-GLM") or await js_click(page, "Re-run QC-Oracle-GLM")
        await asyncio.sleep(8)
        await dump(page, "v7-oracle-fired")

        for i in range(200):
            await asyncio.sleep(45)
            try:
                text = await page.inner_text("body")
            except Exception as e:
                print("read_fail", e, flush=True)
                text = await open_base(page)
            m = re.search(r"QC-Oracle-GLM[\s\S]{0,500}", text, re.I)
            ora = " ".join((m.group(0) if m else "").split())[:300]
            m2 = re.search(r"GLM-5\.2[\s\S]{0,220}", text, re.I)
            glm = " ".join((m2.group(0) if m2 else "").split())[:200]
            print(f"poll{i} {ora}", flush=True)
            print(f"       {glm}", flush=True)
            if i % 5 == 0:
                await dump(page, f"v7poll{i}")
            low = text.lower()
            running = "running now" in low or "runs are in progress" in low
            done = any(
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
            )
            if done and not running:
                await dump(page, "v7-done")
                print("DONE_SIGNAL", flush=True)
                print("FINAL", " ".join(text.split())[:3500], flush=True)
                break
        else:
            await dump(page, "v7-timeout")
            print("TIMEOUT", flush=True)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
