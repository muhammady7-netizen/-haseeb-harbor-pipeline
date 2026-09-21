"""Click newest c227 Open task, then Run client preQC + Run QC-Oracle-GLM."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
HOME = "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"


async def dump(page, tag: str) -> str:
    text = await page.inner_text("body")
    (OUT / f"portal-c227-{tag}.txt").write_text(text[:35000], encoding="utf-8")
    await page.screenshot(path=str(OUT / f"portal-c227-{tag}.png"), full_page=True)
    print(f"DUMP {tag} url={page.url}")
    print("SNIP", " ".join(text.split())[:800])
    return text


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
        await page.wait_for_timeout(6000)
        text = await dump(page, "home2")

        # Find Open task near the newest c227 card (#af3b2a preferred)
        opened = False
        for marker in ("#af3b2a", "#bcfd6e", "code-c227-table-bloat-maintenance-audit"):
            # Prefer an Open task link after the marker
            handle = await page.evaluate(
                """(marker) => {
                  const body = document.body.innerText || '';
                  if (!body.includes(marker) && !body.toLowerCase().includes(marker.toLowerCase())) {
                    return {found:false};
                  }
                  const links = Array.from(document.querySelectorAll('a,button,[role=button]'));
                  const hits = [];
                  for (const el of links) {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (/open task/i.test(t)) {
                      const rect = el.getBoundingClientRect();
                      hits.push({text:t, y:rect.y, href: el.href || null});
                    }
                  }
                  return {found:true, hits};
                }""",
                marker,
            )
            print("marker", marker, handle)

        # Click first visible "Open task" that is associated with c227 by scanning cards
        cards = page.locator("text=code-c227-table-bloat-maintenance-audit")
        n = await cards.count()
        print("c227 text nodes", n)
        # Click the Open task → that appears soon after the first c227 mention in recent tasks
        open_links = page.get_by_text(re.compile(r"Open task", re.I))
        on = await open_links.count()
        print("open task links", on)
        # Heuristic: recent tasks lists newest first; first Open task after page load in recent
        # section is often wrong (law). Find open task whose preceding text contains c227.
        for i in range(on):
            el = open_links.nth(i)
            try:
                # Walk up a few parents for context text
                ctx = await el.evaluate(
                    """(el) => {
                      let n = el;
                      for (let i=0;i<6 && n;i++) n = n.parentElement;
                      return (n && n.innerText || el.parentElement?.innerText || '').slice(0,500);
                    }"""
                )
            except Exception as e:
                print("ctx fail", i, e)
                continue
            print(f"open[{i}] ctx", " ".join(ctx.split())[:180])
            if "c227" in ctx.lower() or "bloat" in ctx.lower() or "af3b2a" in ctx.lower():
                await el.click(timeout=8000)
                opened = True
                print("OPENED via", i)
                await page.wait_for_timeout(6000)
                break

        if not opened:
            # fallback: go directly to known hashes
            for h in (
                "shannon-continue-38a6f7358d4da27c27af3b2a-v1",
                "content-a6f663b04ba9599d834b0d6495bcfd6e-v1",
            ):
                await page.goto(f"{HOME}#task={h}", wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)
                t = await page.inner_text("body")
                if "drop a task here" not in t.lower() and "code-c227" in t.lower():
                    opened = True
                    print("OPENED via hash", h)
                    break

        text = await dump(page, "taskpage")
        if "drop a task here" in text.lower():
            print("STILL_ON_HOME")
            await context.close()
            return

        # Wait out opening
        for i in range(20):
            t = await page.inner_text("body")
            if "opening new version" not in t.lower():
                print("settled", i)
                break
            print("opening...", i)
            await page.wait_for_timeout(4000)

        await dump(page, "ready3")

        # Click gates — use JS click on exact text nodes
        for label, tag in (
            ("Run client preQC", "PREQC"),
            ("Re-run client preQC", "PREQC"),
            ("Run QC-Oracle-GLM", "ORACLE"),
            ("Re-run QC-Oracle-GLM", "ORACLE"),
        ):
            clicked = await page.evaluate(
                """(label) => {
                  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                  const nodes = [];
                  while (walk.nextNode()) {
                    const el = walk.currentNode;
                    const t = (el.innerText || '').trim();
                    if (t === label || t.replace(/\\s+/g,' ') === label) {
                      const r = el.getBoundingClientRect();
                      if (r.width > 0 && r.height > 0) nodes.push(el);
                    }
                  }
                  if (!nodes.length) return {ok:false, n:0};
                  nodes[0].click();
                  return {ok:true, n:nodes.length, tag: nodes[0].tagName};
                }""",
                label,
            )
            print("jsclick", tag, label, clicked)
            if clicked and clicked.get("ok"):
                await page.wait_for_timeout(3000)
                # confirm dialogs
                await page.evaluate(
                    """() => {
                      for (const label of ['Confirm','Run','Yes','Start','OK']) {
                        const els = Array.from(document.querySelectorAll('button'));
                        const hit = els.find(b => (b.innerText||'').trim() === label);
                        if (hit) { hit.click(); return label; }
                      }
                      return null;
                    }"""
                )
                await page.wait_for_timeout(2000)

        await page.wait_for_timeout(10000)
        text = await dump(page, "after-gates")
        print("DONE")
        for pat in (
            r"Client [Pp]reQC[\s\S]{0,180}",
            r"QC-Oracle-GLM[\s\S]{0,220}",
            r"opening new version",
            r"running|queued|in progress|complete|not run yet",
            r"v\d+ · latest",
        ):
            m = re.search(pat, text, re.I)
            if m:
                print("HIT", " ".join(m.group(0).split())[:240])
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
