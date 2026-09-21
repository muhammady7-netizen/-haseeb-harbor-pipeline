const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const zipG857 = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g857.zip';
  const browser = await chromium.launchPersistentContext(profile, {
    headless: false,
    channel: 'chrome',
    acceptDownloads: true,
  });
  const page = browser.pages()[0] || await browser.newPage();

  // --- code-c251: start PreQC + Oracle ---
  const c251 = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-db0490a135ad1cc1e0d71549021ddef3-v1';
  await page.goto(c251, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(7000);
  for (const label of ['Run client preQC', 'Run QC-Oracle-GLM']) {
    const btn = page.getByRole('button', { name: new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'), 'i') });
    console.log('c251 btn', label, await btn.count());
    if (await btn.count()) {
      await btn.first().click();
      console.log('c251 clicked', label);
      await page.waitForTimeout(5000);
    }
  }
  fs.writeFileSync('tmp-pw/c251-live.txt', await page.locator('body').innerText());

  // --- gen-g857: upload new version ---
  const g857 = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-bc4890be9be34fc115b6db0a6ba41d17-v1';
  await page.goto(g857, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForTimeout(7000);
  // Prefer Upload new version
  const uploadNew = page.getByText(/Upload new version/i).first();
  if (await uploadNew.count()) {
    await uploadNew.click();
    await page.waitForTimeout(2000);
  }
  // file input
  const inputs = page.locator('input[type="file"]');
  console.log('file inputs', await inputs.count());
  if (await inputs.count()) {
    await inputs.first().setInputFiles(zipG857);
    console.log('setInputFiles g857');
    await page.waitForTimeout(8000);
  } else {
    // try drop zone click then set files via chooser
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 5000 }).catch(() => [null]),
      page.getByText(/Drop a task|browse|Upload/i).first().click().catch(() => null),
    ]);
    if (chooser && chooser.setFiles) {
      await chooser.setFiles(zipG857);
      console.log('chooser setFiles g857');
      await page.waitForTimeout(8000);
    } else {
      console.log('NO file chooser for g857 upload');
    }
  }
  const afterUp = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/g857-after-upload.txt', afterUp);
  console.log('g857 head', afterUp.slice(0, 1800));

  // If still on old page, go root and upload fresh
  if (/Upload new version/i.test(afterUp) && /6 to decide|Review required/i.test(afterUp)) {
    await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
    const rootInputs = page.locator('input[type="file"]');
    console.log('root file inputs', await rootInputs.count());
    if (await rootInputs.count()) {
      await rootInputs.first().setInputFiles(zipG857);
      console.log('root uploaded g857');
      await page.waitForTimeout(10000);
      fs.writeFileSync('tmp-pw/g857-root-upload.txt', await page.locator('body').innerText());
      console.log((await page.locator('body').innerText()).slice(0, 2000));
    }
  }

  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
