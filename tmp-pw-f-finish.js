const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const profile = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
  const zipG857 = 'C:/Users/Haseeb Mirza/Downloads/UPLOAD-THIS-TO-QC-gen-g857.zip';
  const browser = await chromium.launchPersistentContext(profile, {
    headless: true, channel: 'chrome', acceptDownloads: true,
  });
  const page = browser.pages()[0] || await browser.newPage();
  const out = [];

  async function text() { return page.locator('body').innerText().catch(()=>''); }

  // 1) Root: capture recent list for g857 / c251
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded', timeout: 90000 });
  await sleep(5000);
  let t = await text();
  fs.writeFileSync('tmp-pw/f-root.txt', t);
  const lines = t.split(/\n+/);
  const hits = [];
  for (let i=0;i<lines.length;i++) {
    if (/g857|c251|pdf-form|department-directory/i.test(lines[i])) {
      hits.push(lines.slice(i, i+6).join(' | '));
    }
  }
  out.push({ event: 'hits', hits: hits.slice(0, 25) });
  console.log(JSON.stringify({ event: 'hits', count: hits.length, sample: hits.slice(0, 12) }));

  // 2) Upload g857 again and WAIT until preparing disappears / new hash in list
  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(zipG857);
  console.log(JSON.stringify({ event: 'upload_started' }));
  let newHash = null;
  for (let i=0;i<90;i++) {
    await sleep(2000);
    t = await text();
    if (/preparing upload/i.test(t)) { console.log(JSON.stringify({event:'still_preparing', i})); continue; }
    // look for fresh g857 line near top with today's time
    const m = t.match(/gen-g857-department-directory-categorization-audit#([a-f0-9]{6})/i);
    if (m) {
      newHash = m[1];
      // Prefer first occurrence (newest)
      console.log(JSON.stringify({ event: 'saw_hash', hash: newHash, i }));
      // If URL already on task, break
      if (/#task=/.test(page.url())) break;
      // Click the newest Open near that hash if still on root
      if (!/#task=/.test(page.url())) {
        const loc = page.getByText('gen-g857-department-directory-categorization-audit#' + newHash, { exact: false }).first();
        if (await loc.count()) {
          await loc.click();
          await sleep(6000);
          break;
        }
      }
      break;
    }
    if (/#task=/.test(page.url()) && /gen-g857/i.test(t)) break;
  }
  t = await text();
  fs.writeFileSync('tmp-pw/f-g857-postupload.txt', t);
  console.log(JSON.stringify({ event: 'g857_page', url: page.url(), head: t.slice(0, 900) }));

  // Start gates on whatever g857 page we have
  async function gates(label) {
    const pre = page.getByText(/Run client preQC|Re-run client preQC/i).first();
    const ev = page.getByText(/Run QC-Oracle-GLM/i).first();
    let preOk=false, evOk=false;
    if (await pre.count() && await pre.isVisible().catch(()=>false)) { await pre.click(); preOk=true; await sleep(4000); }
    if (await ev.count() && await ev.isVisible().catch(()=>false)) { await ev.click(); evOk=true; await sleep(4000); }
    const body = await text();
    fs.writeFileSync('tmp-pw/f-' + label + '-gates.txt', body);
    console.log(JSON.stringify({ event: 'gates', label, preOk, evOk, head: body.slice(0, 700) }));
  }
  if (/gen-g857/i.test(await text())) await gates('g857');

  // 3) Open c251 #1ddef3 specifically
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#', { waitUntil: 'domcontentloaded' });
  await sleep(4000);
  t = await text();
  // try hash then name
  let opened = false;
  for (const key of ['code-c251-pdf-form-field-conversion-audit#1ddef3', 'code-c251-pdf-form-field-conversion-audit']) {
    const loc = page.getByText(key, { exact: false }).first();
    if (await loc.count()) {
      await loc.click();
      await sleep(7000);
      opened = true;
      console.log(JSON.stringify({ event: 'opened_c251', key, url: page.url() }));
      break;
    }
  }
  t = await text();
  fs.writeFileSync('tmp-pw/f-c251-page.txt', t);
  if (/code-c251/i.test(t)) {
    await gates('c251');
  } else {
    console.log(JSON.stringify({ event: 'c251_miss', url: page.url(), head: t.slice(0, 500) }));
  }

  await browser.close();
})().catch(e => { console.error(JSON.stringify({event:'fatal', error: String(e)})); process.exit(1); });
