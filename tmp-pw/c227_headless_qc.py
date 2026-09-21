"""Headless: local-qc web judge + Drive upload + portal PreQC + QC-Oracle-GLM."""
from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path

import urllib.request

from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
ZIP = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip"
FIXED = Path.home() / "Downloads" / "UPLOAD-THIS-TO-QC-code-c227-fixed.zip"
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
TASK_URL = (
    "https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer"
    "#task=content-a6f663b04ba9599d834b0d6495bcfd6e-v1"
)
LOCAL_QC = "http://localhost:3000"


def local_qc_api() -> dict:
    zpath = FIXED if FIXED.exists() else ZIP
    boundary = "----c227boundary"
    data = zpath.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="zip"; filename="{zpath.name}"\r\n'
        f"Content-Type: application/zip\r\n\r\n"
    ).encode() + data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="model"\r\n\r\n'
        f"false\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        f"{LOCAL_QC}/api/judge",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=200) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


async def drive_upload(page) -> str:
    """Upload fixed zip via Drive search → parent folder (or search-page New)."""
    await page.goto(
        "https://drive.google.com/drive/search?q=UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip",
        wait_until="domcontentloaded",
        timeout=120000,
    )
    await page.wait_for_timeout(5000)
    folder_url = ""
    file = page.get_by_text(
        "UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip", exact=False
    ).first
    try:
        await file.click(button="right", timeout=8000)
        await page.wait_for_timeout(1000)
        show = page.locator("div[role='menuitem']").filter(
            has_text=re.compile(r"Show file location|Locate", re.I)
        )
        if await show.count():
            await show.first.click()
            await page.wait_for_timeout(5000)
            folder_url = page.url
    except Exception as e:
        print("locate folder fail", type(e).__name__, e)
        await page.keyboard.press("Escape")

    target = folder_url or page.url
    print("DRIVE_TARGET", target)
    if folder_url:
        await page.goto(folder_url, wait_until="domcontentloaded", timeout=120000)
        await page.wait_for_timeout(3000)

    uploaded = False
    for attempt in range(3):
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)
            await page.get_by_role("button", name="New").click(timeout=8000)
            await page.wait_for_timeout(1000)
            async with page.expect_file_chooser(timeout=12000) as fc:
                item = page.get_by_role("menuitem", name="File upload")
                if await item.count():
                    await item.click(force=True)
                else:
                    await page.get_by_text("File upload", exact=False).first.click()
            chooser = await fc.value
            await chooser.set_files(str(ZIP))
            uploaded = True
            print("DRIVE_UPLOAD_STARTED", ZIP.name)
            await page.wait_for_timeout(25000)
            break
        except Exception as e:
            print(f"upload attempt {attempt}", type(e).__name__, e)
            await page.wait_for_timeout(1500)
    (OUT / "drive-c227-folder-url.txt").write_text(target, encoding="utf-8")
    await page.screenshot(path=str(OUT / "drive-c227-upload.png"))
    print("DRIVE_UPLOADED", uploaded)
    return target


async def portal_preqc_and_oracle(page) -> None:
    await page.goto(TASK_URL, wait_until="domcontentloaded", timeout=120000)
    await page.wait_for_timeout(6000)
    await page.screenshot(path=str(OUT / "portal-c227-before.png"))
    text = await page.inner_text("body")
    (OUT / "portal-c227-before.txt").write_text(text[:12000], encoding="utf-8")
    print("PORTAL_TITLE", await page.title())
    print("PORTAL_SNIP", " ".join(text.split())[:400])

    # Prefer Upload new version if present
    for label in ("Upload new version", "Upload", "Re-upload"):
        btn = page.get_by_role("button", name=re.compile(label, re.I))
        if await btn.count():
            print("found", label, await btn.count())

    # Click Re-run client preQC
    clicked_preqc = False
    for name in (
        "Re-run client preQC",
        "Run client preQC",
        "Client preQC",
        "Re-run PreQC",
    ):
        loc = page.get_by_role("button", name=re.compile(re.escape(name), re.I))
        if await loc.count() == 0:
            loc = page.get_by_text(re.compile(name, re.I))
        if await loc.count():
            try:
                await loc.first.click(timeout=8000)
                clicked_preqc = True
                print("CLICKED_PREQC", name)
                await page.wait_for_timeout(4000)
                break
            except Exception as e:
                print("preqc click fail", name, type(e).__name__, e)

    # Confirm dialogs
    for conf in ("Confirm", "Run", "Yes", "Start"):
        c = page.get_by_role("button", name=re.compile(f"^{conf}$", re.I))
        if await c.count():
            try:
                await c.first.click(timeout=3000)
                print("CONFIRM", conf)
                await page.wait_for_timeout(2000)
            except Exception:
                pass

    # QC-Oracle-GLM
    clicked_oracle = False
    for name in (
        "Re-run QC-Oracle-GLM",
        "Run QC-Oracle-GLM",
        "QC-Oracle-GLM",
        "Start evaluation",
        "Run evaluation",
    ):
        loc = page.get_by_role("button", name=re.compile(re.escape(name), re.I))
        if await loc.count() == 0:
            loc = page.get_by_text(re.compile(name, re.I))
        if await loc.count():
            try:
                await loc.first.click(timeout=8000)
                clicked_oracle = True
                print("CLICKED_ORACLE", name)
                await page.wait_for_timeout(4000)
                break
            except Exception as e:
                print("oracle click fail", name, type(e).__name__, e)

    for conf in ("Confirm", "Run", "Yes", "Start"):
        c = page.get_by_role("button", name=re.compile(f"^{conf}$", re.I))
        if await c.count():
            try:
                await c.first.click(timeout=3000)
                print("CONFIRM2", conf)
                await page.wait_for_timeout(2000)
            except Exception:
                pass

    await page.wait_for_timeout(5000)
    text2 = await page.inner_text("body")
    (OUT / "portal-c227-after.txt").write_text(text2[:12000], encoding="utf-8")
    await page.screenshot(path=str(OUT / "portal-c227-after.png"))
    print("PREQC", clicked_preqc, "ORACLE", clicked_oracle)
    print("AFTER_SNIP", " ".join(text2.split())[:500])


async def main() -> None:
    assert ZIP.exists(), ZIP
    # 1) Local QC web API
    try:
        result = local_qc_api()
        (OUT / "c227-web-judge.json").write_text(
            json.dumps(result, indent=2)[:50000], encoding="utf-8"
        )
        print(
            "LOCAL_WEB_JUDGE",
            result.get("verdict"),
            result.get("counts"),
            "findings",
            len(result.get("findings") or []),
        )
    except Exception as e:
        print("LOCAL_WEB_JUDGE_FAIL", type(e).__name__, e)

    # 2) Portal headless (persistent chrome profile; headless=True for automation)
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            channel="chrome",
            headless=True,
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        try:
            await drive_upload(page)
        except Exception as e:
            print("DRIVE_FAIL", type(e).__name__, e)
            await page.screenshot(path=str(OUT / "drive-c227-fail.png"))
        try:
            await portal_preqc_and_oracle(page)
        except Exception as e:
            print("PORTAL_FAIL", type(e).__name__, e)
            await page.screenshot(path=str(OUT / "portal-c227-fail.png"))
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
