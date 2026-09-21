const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const zip = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g806.zip';
  const taskUrl = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-d181a0518c9e07d970b4149e69bb9ba2-v1';
  const outDir = 'tmp-pw';
  fs.mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
  });
  const page = browser.pages()[0] || await browser.newPage();

  await page.goto(taskUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(8000);
  let body = await page.locator('body').innerText();
  fs.writeFileSync(`${outDir}/g806-before.txt`, body);
  console.log('BEFORE head:\n', body.slice(0, 1500));

  if (/Sign in|accounts\.google/i.test(page.url()) || /Enter your email/i.test(body)) {
    console.log('NEED_LOGIN', page.url());
    fs.writeFileSync(`${outDir}/g806-need-login.txt`, page.url() + '\n' + body.slice(0, 2000));
    await browser.close();
    process.exit(2);
  }

  // Prefer Upload new version
  const uploadNew = page.getByText(/Upload new version/i).first();
  if (await uploadNew.count()) {
    await uploadNew.click();
    console.log('clicked Upload new version');
    await page.waitForTimeout(2500);
  }

  const inputs = page.locator('input[type="file"]');
  console.log('file inputs', await inputs.count());
  if (await inputs.count()) {
    await inputs.first().setInputFiles(zip);
    console.log('setInputFiles g806');
    await page.waitForTimeout(12000);
  } else {
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 8000 }).catch(() => null),
      page.getByText(/Drop a task|browse|Upload/i).first().click().catch(() => null),
    ]);
    if (chooser && chooser.setFiles) {
      await chooser.setFiles(zip);
      console.log('chooser setFiles g806');
      await page.waitForTimeout(12000);
    } else {
      // Root upload fallback
      await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(6000);
      const rootInputs = page.locator('input[type="file"]');
      console.log('root file inputs', await rootInputs.count());
      if (!(await rootInputs.count())) {
        console.log('NO_FILE_INPUT');
        fs.writeFileSync(`${outDir}/g806-no-input.txt`, await page.locator('body').innerText());
        await browser.close();
        process.exit(3);
      }
      await rootInputs.first().setInputFiles(zip);
      console.log('root uploaded g806');
      await page.waitForTimeout(12000);
    }
  }

  body = await page.locator('body').innerText();
  fs.writeFileSync(`${outDir}/g806-after-upload.txt`, body);
  console.log('AFTER head:\n', body.slice(0, 2000));
  console.log('URL', page.url());

  // Dismiss / leave PreQC findings unconfirmed if present, then start Oracle+GLM
  for (const label of [
    'Dismiss',
    'Leave unconfirmed',
    'Run client preQC',
    'Run QC-Oracle-GLM',
    'Run Oracle',
    'Start evaluation',
  ]) {
    const btn = page.getByRole('button', { name: new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') });
    const n = await btn.count();
    console.log('btn', label, n);
    if (n) {
      try {
        await btn.first().click({ timeout: 5000 });
        console.log('clicked', label);
        await page.waitForTimeout(4000);
      } catch (e) {
        console.log('click fail', label, String(e).slice(0, 120));
      }
    }
  }

  body = await page.locator('body').innerText();
  fs.writeFileSync(`${outDir}/g806-after-actions.txt`, body);
  console.log('ACTIONS head:\n', body.slice(0, 2000));
  console.log('FINAL URL', page.url());

  await browser.close();
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});
