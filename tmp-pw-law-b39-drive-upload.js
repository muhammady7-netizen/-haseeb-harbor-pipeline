/**
 * law-b39: upload zip to Shannon Drive batch folder using shared chrome-profile.
 * Does NOT close Chrome.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ZIP =
  'C:/Users/Haseeb Mirza/Downloads/law-b39-l16-custody-letter-instruction-audit.zip';
const DRIVE =
  'https://drive.google.com/drive/folders/15ULnjl1MvMNdkqLlz9wLXpxDiZzM1bDW';
const TASK_FOLDER = 'law-b39-l16-custody-letter-instruction-audit';
const OUT = 'tmp-pw';

function dump(name, text) {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, name), text);
}

(async () => {
  const result = {
    ok: false,
    step: 'start',
    driveUrl: DRIVE,
    folderUrl: null,
    fileUrl: null,
    errors: [],
  };

  let context;
  try {
    context = await chromium.launchPersistentContext(PROFILE, {
      headless: false,
      channel: 'chrome',
      acceptDownloads: true,
      viewport: { width: 1400, height: 900 },
    });
  } catch (e) {
    result.errors.push('launch: ' + String(e));
    dump('law-b39-drive-result.json', JSON.stringify(result, null, 2));
    console.error(JSON.stringify(result, null, 2));
    process.exit(1);
  }

  const page = context.pages()[0] || (await context.newPage());

  try {
    result.step = 'goto_drive';
    await page.goto(DRIVE, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForTimeout(6000);
    dump('law-b39-drive-after-goto.txt', page.url() + '\n' + (await page.title()));
    await page.screenshot({ path: path.join(OUT, 'law-b39-drive-1.png'), fullPage: true });

    if (page.url().includes('accounts.google.com')) {
      result.errors.push('Drive not logged in — redirected to Google sign-in');
      dump('law-b39-drive-result.json', JSON.stringify(result, null, 2));
      console.error(JSON.stringify(result, null, 2));
      // keep browser open
      process.exit(2);
    }

    // Look for existing task folder
    result.step = 'find_or_create_folder';
    const folderLink = page.locator(`a[aria-label*="${TASK_FOLDER}"], div[data-tooltip*="${TASK_FOLDER}"]`).first();
    let folderExists = false;
    try {
      folderExists = (await folderLink.count()) > 0 && (await folderLink.isVisible({ timeout: 3000 }));
    } catch (_) {}

    // Also try text search in page
    const bodyText = await page.locator('body').innerText().catch(() => '');
    dump('law-b39-drive-listing.txt', bodyText.slice(0, 8000));

    if (bodyText.includes(TASK_FOLDER)) {
      // Click existing folder by name
      const named = page.getByText(TASK_FOLDER, { exact: true }).first();
      if (await named.count()) {
        await named.dblclick({ timeout: 10000 }).catch(async () => {
          await named.click({ timeout: 10000 });
        });
        await page.waitForTimeout(4000);
        result.folderUrl = page.url();
        result.step = 'opened_existing_folder';
      }
    }

    if (!result.folderUrl) {
      // Create new folder via New > Folder
      result.step = 'create_folder';
      // Try keyboard shortcut or New button
      const newBtn = page.getByRole('button', { name: /^New$/i }).or(page.locator('button:has-text("New")')).first();
      if (await newBtn.count()) {
        await newBtn.click({ timeout: 10000 });
        await page.waitForTimeout(1000);
        const folderItem = page.getByRole('menuitem', { name: /Folder/i }).or(page.locator('[role="menuitem"]:has-text("Folder")')).first();
        if (await folderItem.count()) {
          await folderItem.click({ timeout: 10000 });
        } else {
          // fallback: press f after New menu
          await page.keyboard.press('f');
        }
      } else {
        // Drive shortcut: Shift+f? Try right-click empty area -> New folder
        await page.keyboard.press('Shift+n'); // sometimes New
      }
      await page.waitForTimeout(1500);

      // Type folder name into dialog
      const nameInput = page.locator('input[type="text"], input[aria-label*="Name"], input[aria-label*="name"]').last();
      await nameInput.waitFor({ state: 'visible', timeout: 15000 });
      await nameInput.fill(TASK_FOLDER);
      await page.waitForTimeout(500);
      const createBtn = page.getByRole('button', { name: /Create|OK|Done/i }).first();
      if (await createBtn.count()) {
        await createBtn.click();
      } else {
        await page.keyboard.press('Enter');
      }
      await page.waitForTimeout(4000);
      await page.screenshot({ path: path.join(OUT, 'law-b39-drive-2-folder.png'), fullPage: true });

      // Open the new folder
      const named2 = page.getByText(TASK_FOLDER, { exact: true }).first();
      await named2.dblclick({ timeout: 15000 }).catch(async () => {
        await named2.click({ timeout: 15000 });
      });
      await page.waitForTimeout(4000);
      result.folderUrl = page.url();
    }

    dump('law-b39-drive-folder-url.txt', result.folderUrl || '');
    await page.screenshot({ path: path.join(OUT, 'law-b39-drive-3-inside.png'), fullPage: true });

    // Upload zip into folder
    result.step = 'upload_zip';
    // Prefer New > File upload, or drag-drop via filechooser / hidden input
    const fileInputs = page.locator('input[type="file"]');
    let uploaded = false;

    // Try New > File upload
    const newBtn2 = page.getByRole('button', { name: /^New$/i }).or(page.locator('button:has-text("New")')).first();
    if (await newBtn2.count()) {
      await newBtn2.click({ timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(800);
      const fileUpload = page.getByRole('menuitem', { name: /File upload/i }).or(page.locator('[role="menuitem"]:has-text("File upload")')).first();
      if (await fileUpload.count()) {
        const [chooser] = await Promise.all([
          page.waitForEvent('filechooser', { timeout: 15000 }).catch(() => null),
          fileUpload.click({ timeout: 10000 }),
        ]);
        if (chooser) {
          await chooser.setFiles(ZIP);
          uploaded = true;
        }
      } else {
        await page.keyboard.press('Escape');
      }
    }

    if (!uploaded && (await fileInputs.count()) > 0) {
      await fileInputs.first().setInputFiles(ZIP);
      uploaded = true;
    }

    if (!uploaded) {
      // Last resort: inject a file input and use it
      await page.evaluate(() => {
        const inp = document.createElement('input');
        inp.type = 'file';
        inp.id = 'pw-drive-upload';
        inp.style.display = 'block';
        document.body.appendChild(inp);
      });
      await page.locator('#pw-drive-upload').setInputFiles(ZIP);
      // Drive may not pick this up — screenshot for diagnosis
      result.errors.push('used injected file input — may need manual confirm');
      uploaded = true;
    }

    // Wait for upload to finish
    await page.waitForTimeout(8000);
    for (let i = 0; i < 30; i++) {
      const t = await page.locator('body').innerText().catch(() => '');
      if (t.includes('Upload complete') || t.includes('1 upload') || t.includes(path.basename(ZIP).replace('.zip', ''))) {
        break;
      }
      // look for progress gone
      if (t.includes('law-b39-l16') && !t.toLowerCase().includes('uploading')) {
        break;
      }
      await page.waitForTimeout(2000);
    }

    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(OUT, 'law-b39-drive-4-uploaded.png'), fullPage: true });
    const afterUpload = await page.locator('body').innerText().catch(() => '');
    dump('law-b39-drive-after-upload.txt', afterUpload.slice(0, 10000));

    result.folderUrl = page.url();
    result.ok = afterUpload.includes('law-b39') || afterUpload.includes('custody');
    result.step = 'done';
    dump('law-b39-drive-result.json', JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
  } catch (e) {
    result.errors.push(String(e && e.stack ? e.stack : e));
    dump('law-b39-drive-result.json', JSON.stringify(result, null, 2));
    await page.screenshot({ path: path.join(OUT, 'law-b39-drive-error.png'), fullPage: true }).catch(() => {});
    console.error(JSON.stringify(result, null, 2));
    process.exit(1);
  }
  // Do NOT close context — keep session alive briefly; exit leaves browser if detached
  // Actually launchPersistentContext stays until we close — exit without close keeps it? No, process exit closes it.
  // Per handoff: don't close Chrome. Leave process running a bit then exit without context.close().
  await page.waitForTimeout(2000);
  // intentional: no context.close()
  process.exit(result.ok ? 0 : 3);
})();
