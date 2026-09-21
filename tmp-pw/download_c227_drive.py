import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

PROFILE = str(Path.home() / ".config" / "opencode" / "chrome-profile")
DL = Path.home() / "Downloads"
OUT = Path(r"C:\Users\Haseeb Mirza\Documents\Codex\haseeb-pipeline\tmp-pw")
DEST = DL / "ACCEPTED-code-c227-table-bloat-maintenance-audit.zip"
REPORT = DL / "ACCEPTED-c227-REPORT-code-c227-table-bloat-maintenance-audit-qc-report.zip"


async def main() -> None:
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE,
            channel="chrome",
            headless=False,
            accept_downloads=True,
        )
        page = context.pages[0] if context.pages else await context.new_page()

        await page.goto(
            "https://drive.google.com/drive/search?q=UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip",
            wait_until="domcontentloaded",
            timeout=120000,
        )
        await page.wait_for_timeout(6000)
        file = page.get_by_text(
            "UPLOAD-THIS-TO-QC-code-c227-table-bloat-maintenance-audit.zip", exact=False
        ).first
        await file.click()
        await page.wait_for_timeout(500)
        await file.click(button="right")
        await page.wait_for_timeout(1500)

        # Visible Drive context-menu Download entry
        item = page.locator("div[role='menuitem']").filter(has_text=re.compile(r"^Download$"))
        print("menuitem", await item.count())
        async with page.expect_download(timeout=180000) as di:
            if await item.count():
                await item.first.click()
            else:
                await page.locator("[data-target='clientDownload']").last.click(force=True)
        download = await di.value
        await download.save_as(str(DEST))
        print("SAVED_ZIP", DEST, DEST.stat().st_size)

        # Locate parent folder URL
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)
        await file.click(button="right")
        await page.wait_for_timeout(1000)
        show = page.locator("div[role='menuitem']").filter(
            has_text=re.compile(r"Show file location|Locate", re.I)
        )
        print("show loc", await show.count())
        folder_url = ""
        if await show.count():
            await show.first.click()
            await page.wait_for_timeout(5000)
            folder_url = page.url
            print("FOLDER_URL", folder_url)
            (OUT / "drive-c227-folder-url.txt").write_text(folder_url, encoding="utf-8")

        # Upload report into that folder if we have it
        if folder_url and REPORT.exists():
            await page.goto(folder_url, wait_until="domcontentloaded", timeout=120000)
            await page.wait_for_timeout(4000)
            try:
                await page.get_by_role("button", name="New").click(timeout=8000)
                await page.wait_for_timeout(1000)
                async with page.expect_file_chooser(timeout=10000) as fc:
                    await page.get_by_text("File upload", exact=False).first.click()
                chooser = await fc.value
                await chooser.set_files(str(REPORT))
                print("UPLOADED_REPORT", REPORT.name)
                await page.wait_for_timeout(20000)
            except Exception as e:
                print("upload report fail", type(e).__name__, e)
                # fallback: also try uploading the package zip if missing
                try:
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)
                    await page.get_by_role("button", name="New").click(timeout=5000)
                    await page.wait_for_timeout(800)
                    async with page.expect_file_chooser(timeout=10000) as fc:
                        await page.get_by_text("File upload", exact=False).first.click()
                    chooser = await fc.value
                    await chooser.set_files(str(DEST))
                    print("UPLOADED_ZIP_FALLBACK")
                    await page.wait_for_timeout(20000)
                except Exception as e2:
                    print("upload zip fail", type(e2).__name__, e2)

        await page.screenshot(path=str(OUT / "drive-c227-final.png"))
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
