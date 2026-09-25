const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TASK = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-c2f5a173762313b980e93ef631303895-v14';
const OUT = 'tmp-pw/b50-v14-preqc.txt';

async function sleep(ms) { await new Promise(r => setTimeout(r, ms)); }

(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    args: ['--window-position=-32000,-32000', '--window-size=1280,900', '--disable-blink-features=AutomationControlled'],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  try {
    await page.goto(TASK, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(8000);

    // Run PreQC
    let clicked = false;
    const btn = page.getByRole('button', { name: /Run client preQC|Re-run client preQC/i }).first();
    if (await btn.count()) { await btn.click(); clicked = true; console.log('CLICKED_PREQC'); }
    if (!clicked) { const t = page.getByText(/Run client preQC/i).first(); if (await t.count()) { await t.click(); clicked = true; console.log('CLICKED_PREQC_TEXT'); } }
    
    await sleep(15000);
    
    // Wait for PreQC to complete (up to 5 min)
    for (let i = 0; i < 40; i++) {
      await sleep(8000);
      const text = await page.locator('body').innerText();
      if (/PreQC complete|0 trainer finding|Trainer changes required/i.test(text)) {
        console.log('PREQC_DONE', i);
        break;
      }
      if (i % 5 === 0) console.log('wait_preqc', i);
    }

    // Now run QC-Oracle-GLM
    const glmBtn = page.getByRole('button', { name: /Run QC-Oracle-GLM/i }).first();
    if (await glmBtn.count()) {
      await glmBtn.click();
      console.log('CLICKED_QC_ORACLE_GLM');
    } else {
      const glmText = page.getByText(/Run QC-Oracle-GLM/i).first();
      if (await glmText.count()) { await glmText.click(); console.log('CLICKED_GLM_TEXT'); }
      else console.log('NO_GLM_BUTTON');
    }
    
    await sleep(10000);
    const text = await page.locator('body').innerText();
    fs.writeFileSync(OUT, `URL=${page.url()}\n\n${text}`);
    console.log(text.slice(0, 2000));
    console.log('FINAL_URL', page.url());
  } finally {
    await browser.close().catch(() => {});
  }
})().catch(e => { console.error('FAIL', e); process.exit(1); });
