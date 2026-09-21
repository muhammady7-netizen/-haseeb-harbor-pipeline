"""Open c227 v6 via All-tasks/Open-task, fire QC-Oracle-GLM, poll."""
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
    print(f"DUMP {tag} url={page.url}", " ".join(text.split())[:500], flush=True)
    return text


def on_task_page(text: str) -> bool:
    low = text.lower()
    return (
        "harbor package" in low
        and "upload new version" in low
        and "code-c227-table-bloat-maintenance-audit" in low
    )


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


async def open_c227_v6(page) -> str:
    await page.goto(f"{HOME}#task={V6}", wait_until="domcontentloaded", timeout=120000)
    await page.wait_for_timeout(5000)
    text = await dump(page, "nav-hash")
    if on_task_page(text):
        return text

    await page.goto(HOME, wait_until="domcontentloaded", timeout=120000)
    await page.wait_for_timeout(3000)
    await page.evaluate(f"window.location.hash = 'task={V6}'")
    await page.wait_for_timeout(5000)
    text = await dump(page, "nav-hash2")
    if on_task_page(text):
        return text

    # Open from recent list / All tasks
    await js_click(page, "All tasks")
    await page.wait_for_timeout(3000)
    opened = await page.evaluate(
        """() => {
          const nodes = [...document.querySelectorAll('a,button,[role=button],div,span')];
          // Prefer an Open task near c227
          for (let i = 0; i < nodes.length; i++) {
            const t = (nodes[i].innerText||'').trim();
            if (!/code-c227-table-bloat-maintenance-audit/i.test(t)) continue;
            for (let j = i; j < Math.min(i + 12, nodes.length); j++) {
              const u = (nodes[j].innerText||'').trim().replace(/\\s+/g,' ');
              if (/^Open task$/i.test(u) || /^Open$/i.test(u)) {
                nodes[j].click();
                return 'open-near-c227';
              }
            }
          }
          // fallback: click the task name itself
          const name = nodes.find(n => /code-c227-table-bloat-maintenance-audit/i.test(n.innerText||''));
          if (name) { name.click(); return 'click-name'; }
          return '';
        }"""
    )
    print("open_strategy", opened, flush=True)
    await page.wait_for_timeout(5000)
    await page.evaluate(f"window.location.hash = 'task={V6}'")
    await page.wait_for_timeout(4000)
    text = await dump(page, "nav-open")
    if on_task_page(text):
        return text

    # last resort: select version dropdown if present
    sel = page.locator("select")
    if await sel.count():
        try:
            await sel.first.select_option(value=V6)
            await page.wait_for_timeout(3000)
        except Exception as e:
            print("select fail", e, flush=True)
    text = await dump(page, "nav-final")
    return text


async def main() -> None:
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            channel="chrome",
            headless=True,
            accept_downloads=True,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        text = await open_c227_v6(page)
        if not on_task_page(text):
            print("OPEN_FAIL", flush=True)
            await ctx.close()
            raise SystemExit(2)
        print("OPEN_OK", flush=True)

        # Ensure v6 selected
        if "v6 · latest" not in text.lower() and "v6 (latest)" not in text.lower():
            sel = page.locator("select")
            if await sel.count():
                try:
                    await sel.first.select_option(value=V6)
                    await page.wait_for_timeout(3000)
                    text = await dump(page, "nav-v6sel")
                except Exception as e:
                    print("v6 select fail", e, flush=True)

        clicked = await js_click(page, "Run QC-Oracle-GLM")
        if not clicked:
            clicked = await js_click(page, "Re-run QC-Oracle-GLM")
        await page.wait_for_timeout(8000)
        text = await dump(page, "v6-oracle-fired")
        print("oracle_click", clicked, flush=True)

        for i in range(160):
            await page.wait_for_timeout(45000)
            text = await page.inner_text("body")
            m_or = re.search(r"QC-Oracle-GLM[\s\S]{0,500}", text, re.I)
            ora = " ".join((m_or.group(0) if m_or else "").split())[:320]
            print(f"poll{i} {ora}", flush=True)
            if i % 5 == 0:
                await dump(page, f"v6orapoll{i}")
            ora_low = ora.lower()
            page_low = text.lower()
            finished = False
            if m_or and "not run yet" not in ora_low and all(
                x not in ora_low for x in ("running now", "starting", "queued")
            ):
                if any(
                    k in ora_low
                    for k in (
                        "complete",
                        "passed",
                        "failed",
                        "too_easy",
                        "too_hard",
                        "changes required",
                        "ready",
                        "oracle 1",
                        "glm ",
                    )
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
                )
            ) and "running now" not in page_low:
                finished = True
            if finished:
                await dump(page, "v6-oracle-done")
                print("DONE_SIGNAL", flush=True)
                print("FINAL", " ".join(text.split())[:3000], flush=True)
                break
        else:
            await dump(page, "v6-oracle-timeout")
            print("TIMEOUT", flush=True)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
