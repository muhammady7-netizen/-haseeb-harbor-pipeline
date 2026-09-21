"""Switch c227 to v2 latest, ensure PreQC+Oracle run on that version."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
HASH = "shannon-continue-38a6f7358d4da27c27af3b2a-v1"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:35000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag}")
    print("SNIP", " ".join(text.split())[:900])
    return text


async def js_click_exact(page, label: str) -> dict:
    return await page.evaluate(
        """(label) => {
          const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
          const nodes = [];
          while (walk.nextNode()) {
            const el = walk.currentNode;
            const t = (el.innerText || '').trim().replace(/\\s+/g,' ');
            if (t === label) {
              const r = el.getBoundingClientRect();
              if (r.width > 0 && r.height > 0) nodes.push(el);
            }
          }
          // also try includes for version rows
          if (!nodes.length) {
            const all = Array.from(document.querySelectorAll('button,a,[role=button],div,span'));
            for (const el of all) {
              const t = (el.innerText || '').trim().replace(/\\s+/g,' ');
              if (t === label || t.startsWith(label)) {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0 && t.length < 80) nodes.push(el);
              }
            }
          }
          if (!nodes.length) return {ok:false,n:0};
          nodes[0].click();
          return {ok:true,n:nodes.length,text:nodes[0].innerText.trim().slice(0,80),tag:nodes[0].tagName};
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
        await page.evaluate(f"window.location.hash = 'task={HASH}'")
        await page.wait_for_timeout(5000)
        await dump(page, "before-switch")

        # Open version switcher / click v2 latest
        for label in (
            "SWITCH VERSION",
            "Switch version",
            "v2 (latest) — not run · Sep 21, 12:47 PM",
            "v2 (latest)",
            "V2",
        ):
            r = await js_click_exact(page, label)
            print("click", label, r)
            if r.get("ok"):
                await page.wait_for_timeout(3000)

        # Also try regex click on version row
        loc = page.get_by_text(re.compile(r"v2 \(latest\)", re.I))
        if await loc.count():
            await loc.first.click(force=True)
            print("clicked v2 latest text")
            await page.wait_for_timeout(4000)

        text = await dump(page, "after-switch")

        # Fire PreQC + Oracle on whatever version is active
        for label in ("Run client preQC", "Re-run client preQC", "Run QC-Oracle-GLM", "Re-run QC-Oracle-GLM"):
            r = await js_click_exact(page, label)
            print("gate", label, r)
            if r.get("ok"):
                await page.wait_for_timeout(2500)
                await page.evaluate(
                    """() => {
                      for (const label of ['Confirm','Run','Yes','Start','OK']) {
                        const hit = Array.from(document.querySelectorAll('button'))
                          .find(b => (b.innerText||'').trim() === label);
                        if (hit) { hit.click(); return label; }
                      }
                      return null;
                    }"""
                )
                await page.wait_for_timeout(2000)

        # Poll a bit for status change
        for i in range(12):
            await page.wait_for_timeout(10000)
            text = await page.inner_text("body")
            low = text.lower()
            print(
                f"status {i}: preqc_running={'preqc' in low and 'running' in low} "
                f"oracle_running={'oracle' in low and 'running' in low} "
                f"v2={'v2 · latest' in low or 'v2 (latest)' in low}"
            )
            if i in (0, 5, 11):
                await dump(page, f"poll{i}")
            if "preqc complete" in low or ("oracle" in low and "running" in low):
                break

        await dump(page, "final-status")
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
