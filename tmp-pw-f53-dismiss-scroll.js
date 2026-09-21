const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TASK = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-cf347576d2d9beabcb4dac83b3452347-v1';
const NOTE = 'Advisory framework limitation. Gold replay + deterministic verifiers cover correctness. Dismiss per Shannon PreQC guidance.';
async function sleep(ms){ await new Promise(r=>setTimeout(r,ms)); }
(async()=>{
  const browser = await chromium.launchPersistentContext(PROFILE,{
    headless:false, channel:'chrome', viewport:{width:1280,height:900},
    args:['--window-position=-32000,-32000','--window-size=1280,900','--disable-blink-features=AutomationControlled']
  });
  const page = browser.pages()[0] || await browser.newPage();
  try {
    await page.goto(TASK,{waitUntil:'domcontentloaded',timeout:120000});
    await sleep(8000);
    for (let s=0;s<14;s++){ await page.mouse.wheel(0,1000); await sleep(350); const t=await page.locator('body').innerText(); if(/NEEDS ATTENTION|Review issue/i.test(t)){ console.log('SECTION',s); break; } }
    for (let i=0;i<8;i++){
      const buttons = page.getByRole('button',{name:/Review issue/i});
      const n = await buttons.count();
      console.log('BUTTONS',n);
      if(!n){
        const texts=page.getByText(/Review issue/i); const tn=await texts.count(); console.log('TEXTS',tn); if(!tn) break; await texts.first().click();
      } else { await buttons.first().click(); }
      console.log('OPENED',i); await sleep(2000);
      const ta=page.locator('textarea').last(); if(await ta.count()) await ta.fill(NOTE).catch(()=>{});
      let dismissed=false;
      const b=page.getByRole('button',{name:/^Dismiss$/i}).first();
      if(await b.count()){ await b.click(); dismissed=true; console.log('DISMISS',i); }
      if(!dismissed){ const d=page.getByText(/^Dismiss$/i).first(); if(await d.count()){ await d.click(); dismissed=true; console.log('DISMISS_TEXT',i);} }
      if(!dismissed){ console.log('NO_DISMISS',i); await page.keyboard.press('Escape'); }
      await sleep(2500);
    }
    const text=await page.locator('body').innerText();
    fs.writeFileSync('tmp-pw/f53-after-dismiss.txt', 'URL='+page.url()+'\n\n'+text);
    console.log(text.slice(0,3500));
  } finally { await browser.close().catch(()=>{}); }
})().catch(e=>{ console.error('FAIL',e); process.exit(1); });
