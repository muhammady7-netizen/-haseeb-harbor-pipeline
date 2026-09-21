"""Select c227 v2 via <select>, then run PreQC + QC-Oracle-GLM."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
V1 = "shannon-continue-38a6f7358d4da27c27af3b2a-v1"
V2 = "shannon-continue-38a6f7358d4da27c27af3b2a-v2"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:35000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag} url={page.url}")
    print("SNIP", " ".join(text.split())[:900])
    return text


async def js_click_exact(page, label: str) -> dict:
    return await page.evaluate(
        """(label) => {
          const all = Array.from(document.querySelectorAll('button,a,[role=button]'));
          const nodes = all.filter(el => {
            const t = (el.innerText || '').trim().replace(/\\s+/g,' ');
            const r = el.getBoundingClientRect();
            return t === label && r.width > 0 && r.height > 0;
          });
          if (!nodes.length) return {ok:false,n:0};
          nodes[0].click();
          return {ok:true,n:nodes.length,tag:nodes[0].tagName};
        }""",
        label,
    )


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
        await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(2000)
        await page.evaluate(f"window.location.hash = 'task={V1}'")
        await page.wait_for_timeout(5000)

        # Prefer navigating directly to v2 hash if SPA supports it
        await page.evaluate(f"window.location.hash = 'task={V2}'")
        await page.wait_for_timeout(4000)
        text = await dump(page, "v2-hash")

        # Also set select if present
        selects = page.locator("select")
        sc = await selects.count()
        print("selects", sc)
        for i in range(sc):
            sel = selects.nth(i)
            html = await sel.inner_html()
            if "shannon-continue" in html or "v2" in html.lower():
                try:
                    await sel.select_option(value=V2)
                    print("selected V2 via select")
                    await page.wait_for_timeout(4000)
                except Exception as e:
                    print("select fail", e)
                    try:
                        await sel.select_option(label=re.compile(r"v2 \(latest\)", re.I))
                        print("selected V2 via label")
                        await page.wait_for_timeout(4000)
                    except Exception as e2:
                        print("select label fail", e2)

        text = await dump(page, "on-v2")

        for label in ("Run client preQC", "Re-run client preQC"):
            r = await js_click_exact(page, label)
            print("preqc", label, r)
            if r.get("ok"):
                await page.wait_for_timeout(2000)
                break
        for label in ("Run QC-Oracle-GLM", "Re-run QC-Oracle-GLM"):
            r = await js_click_exact(page, label)
            print("oracle", label, r)
            if r.get("ok"):
                await page.wait_for_timeout(2000)
                break

        for i in range(8):
            await page.wait_for_timeout(8000)
            text = await page.inner_text("body")
            low = text.lower()
            print(
                f"poll {i}: running_preqc={'client preqc' in low and 'running' in low} "
                f"oracle={'qc-oracle' in low and ('running' in low or 'queued' in low)} "
                f"v2_latest={'v2 · latest' in low}"
            )
            if i in (0, 3, 7):
                await dump(page, f"v2poll{i}")

        await dump(page, "v2-final")
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
