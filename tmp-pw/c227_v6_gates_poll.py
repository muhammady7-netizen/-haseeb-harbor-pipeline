"""On c227 v6: fire PreQC + QC-Oracle-GLM, then poll to completion."""
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
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:60000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag}", " ".join(text.split())[:700], flush=True)
    return text


async def js_click(page, label: str) -> bool:
    ok = await page.evaluate(
        """(label) => {
          const needles = [label, label.replace(/-/g,' '), label.replace(/ /g,'-')];
          const nodes = [...document.querySelectorAll('button,a,[role=button]')];
          for (const n of nodes) {
            const t = (n.innerText||n.textContent||'').trim().replace(/\\s+/g,' ');
            if (needles.some(x => t === x || t.toLowerCase() === x.toLowerCase())) {
              n.click(); return true;
            }
          }
          // partial match for Re-run variants
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
        await page.wait_for_timeout(2500)
        await page.evaluate(f"window.location.hash = 'task={V6}'")
        await page.wait_for_timeout(5000)
        sel = page.locator("select")
        if await sel.count():
            try:
                await sel.first.select_option(value=V6)
            except Exception:
                try:
                    await sel.first.select_option(index=0)
                except Exception as e:
                    print("select fail", e, flush=True)
        await page.wait_for_timeout(3000)
        text = await dump(page, "v6-gates-pre")
        assert "v6" in text.lower(), "not on v6"

        await js_click(page, "Run client preQC") or await js_click(page, "Re-run client preQC")
        await page.wait_for_timeout(5000)
        # Wait until PreQC finishes or unlocks Oracle
        for i in range(40):
            text = await page.inner_text("body")
            low = text.lower()
            pre = re.search(r"Client preQC[\s\S]{0,220}|preQC[\s\S]{0,220}", text, re.I)
            print(f"preqc{i}", " ".join((pre.group(0) if pre else "").split())[:200], flush=True)
            if i % 5 == 0:
                await dump(page, f"v6-preqc{i}")
            if any(
                k in low
                for k in (
                    "0 trainer finding",
                    "preqc complete",
                    "preqc passed",
                    "no blocking",
                    "unlocked",
                )
            ) and "running" not in low:
                break
            if "finding" in low and "preqc" in low and "running" not in low and i > 2:
                # may have findings — still try Oracle if button exists
                break
            await page.wait_for_timeout(15000)

        await dump(page, "v6-preqc-done")
        await js_click(page, "Run QC-Oracle-GLM") or await js_click(page, "Re-run QC-Oracle-GLM")
        await page.wait_for_timeout(5000)

        for i in range(160):
            await page.wait_for_timeout(45000)
            text = await page.inner_text("body")
            m_or = re.search(r"QC-Oracle-GLM[\s\S]{0,450}", text, re.I)
            ora = " ".join((m_or.group(0) if m_or else "").split())[:300]
            print(f"poll{i} {ora}", flush=True)
            if i % 5 == 0:
                await dump(page, f"v6poll{i}")
            ora_low = ora.lower()
            page_low = text.lower()
            finished = False
            if m_or and all(
                x not in ora_low for x in ("running", "starting", "not run yet", "queued")
            ):
                finished = True
            if any(
                k in page_low
                for k in (
                    "oracle 1.0",
                    "glm 0/4",
                    "glm 1/4",
                    "glm 2/4",
                    "glm 3/4",
                    "glm 4/4",
                    "too_easy",
                    "too_hard",
                    "delivery gate",
                )
            ) and "running now" not in page_low:
                finished = True
            if finished:
                await dump(page, "v6-oracle-done")
                print("DONE_SIGNAL", flush=True)
                print("FINAL", " ".join(text.split())[:2800], flush=True)
                break
        else:
            await dump(page, "v6-oracle-timeout")
            print("TIMEOUT", flush=True)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
