const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const zipG857 = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g857.zip';
  const zipC251 = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-code-c251.zip';
  const browser = await chromium.launchPersistentContext(profile, { headless: false, channel: 'chrome' });
  const page = browser.pages()[0] || await browser.newPage();

  async function uploadAtRoot(zip, label) {
    await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForTimeout(5000);
    // visible dropzone file input - usually the first in the upload card
    const input = page.locator('input[type="file"]').first();
    await input.setInputFiles(zip);
    console.log('uploaded', label);
    // wait for navigation / new task banner
    await page.waitForTimeout(15000);
    const text = await page.locator('body').innerText();
    fs.writeFileSync('tmp-pw/upload-' + label + '.txt', text);
    console.log(label, 'url', page.url());
    console.log(label, 'head', text.slice(0, 1200));
    return text;
  }

  async function openTaskContains(substr) {
    await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    for (let i=0;i<6;i++){ await page.mouse.wheel(0,1600); await page.waitForTimeout(400); }
    const link = page.locator(`text=${substr}`).first();
    console.log('open', substr, 'count', await link.count());
    if (await link.count()) {
      await link.click();
      await page.waitForTimeout(7000);
      return await page.locator('body').innerText();
    }
    return '';
  }

  async function clickTextButton(re) {
    // buttons may be role=button or plain clickable text
    const loc = page.getByText(re).first();
    const n = await loc.count();
    console.log('clickText', String(re), n, 'visible', n? await loc.isVisible().catch(()=>false): false);
    if (n && await loc.isVisible().catch(()=>false)) {
      await loc.click();
      await page.waitForTimeout(4000);
      return true;
    }
    return false;
  }

  // 1) Upload hardened g857 as NEW task version via root dropzone
  await uploadAtRoot(zipG857, 'g857');

  // 2) Open newest g857 (# should appear near top) and run gates
  let t = await openTaskContains('gen-g857-department-directory-categorization-audit');
  fs.writeFileSync('tmp-pw/g857-opened.txt', t);
  console.log('g857 opened head', t.slice(0,1000));
  await clickTextButton(/Re-run client preQC|Run client preQC/i);
  await clickTextButton(/Run QC-Oracle-GLM/i);
  t = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/g857-after-gates.txt', t);
  console.log('g857 after gates', t.slice(0,1500));

  // 3) Open c251 latest and run gates
  t = await openTaskContains('code-c251-pdf-form-field-conversion-audit#1ddef3');
  if (!t) t = await openTaskContains('code-c251-pdf-form-field-conversion-audit');
  fs.writeFileSync('tmp-pw/c251-opened.txt', t);
  console.log('c251 opened head', t.slice(0,1000));
  await clickTextButton(/Run client preQC/i);
  await clickTextButton(/Run QC-Oracle-GLM/i);
  t = await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/c251-after-gates.txt', t);
  console.log('c251 after gates', t.slice(0,1500));

  await browser.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
