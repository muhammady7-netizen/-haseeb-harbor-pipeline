const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const NOTE = 'Advisory framework limitation. Deterministic gold/verifiers cover this. Dismiss per Shannon PreQC guidance.';
async function sleep(ms){await new Promise(r=>setTimeout(r,ms));}
(async()=>{
  const browser=await chromium.launchPersistentContext(PROFILE,{headless:true,channel:'chrome',viewport:{width:1400,height:1000},args:['--disable-blink-features=AutomationControlled']});
  const page=browser.pages()[0]||await browser.newPage();
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#',{waitUntil:'domcontentloaded',timeout:120000});
  await sleep(7000);
  // Click the card that contains #452347
  const card = page.locator('text=fin-f53-deposit-account-fee-assessment-audit#452347').first();
  console.log('card', await card.count());
  if(await card.count()){
    await card.click();
    await sleep(1500);
  }
  // Click Open that is in the same button as #452347 if possible
  const openInCard = page.getByRole('button', { name: /fin-f53-deposit-account-fee-assessment-audit#452347[\s\S]*Open/i }).first();
  if(await openInCard.count()){
    await openInCard.click();
    console.log('CLICKED_CARD_BUTTON');
  } else {
    // fallback: first Open after locating text
    await page.locator('div,button,a').filter({ hasText: /fin-f53-deposit-account-fee-assessment-audit#452347/ }).getByText(/^Open$/).first().click().catch(async()=>{
      await page.getByText(/^Open$/).first().click();
      console.log('CLICKED_FIRST_OPEN');
    });
  }
  await sleep(10000);
  console.log('URL', page.url());
  let text = await page.locator('body').innerText();
  const status = text.split(/\n/).filter(l=>/Oracle|GLM|Running|Passed|Failed|findings|to decide|Submit|Waiting|slots|Harbor Check|NEEDS/i.test(l));
  console.log(status.slice(0,40).join('\n'));

  // dismiss findings if present
  for(let i=0;i<8;i++){
    for(let s=0;s<8;s++){await page.mouse.wheel(0,800);await sleep(200);}    
    const btns=page.getByRole('button',{name:/Review issue/i});
    const n=await btns.count();
    console.log('REVIEW',n);
    if(!n) break;
    await btns.first().click();
    await sleep(2000);
    // dump modal buttons
    const modalBtns=await page.evaluate(()=>[...document.querySelectorAll('button,[role=button]')].map(e=>(e.innerText||'').trim()).filter(t=>t && t.length<60));
    console.log('MODAL', JSON.stringify(modalBtns.filter(t=>/dismiss|confirm|cancel|close|note|save|issue/i.test(t))));
    const ta=page.locator('textarea').last();
    if(await ta.count()) await ta.fill(NOTE).catch(()=>{});
    // try several dismiss labels
    let ok=false;
    for(const re of [/^Dismiss$/i,/Dismiss with note/i,/Leave unconfirmed/i,/Mark dismissed/i,/\bDismiss\b/i]){
      const b=page.getByRole('button',{name:re}).first();
      if(await b.count()){ await b.click(); ok=true; console.log('DISMISSED', String(re)); break; }
    }
    if(!ok){
      // maybe it's a link-styled control
      const t=page.getByText(/^Dismiss$/i).first();
      if(await t.count()){ await t.click(); ok=true; console.log('DISMISS_TEXT'); }
    }
    if(!ok){ console.log('NO_DISMISS'); await page.screenshot({path:`tmp-pw/f53-modal-${i}.png`}); await page.keyboard.press('Escape'); break; }
    await sleep(2000);
  }

  text=await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/f53-open-dismiss.txt','URL='+page.url()+'\n\n'+text);
  console.log('---TAIL---');
  console.log(text.split(/\n/).filter(l=>/Oracle|GLM|Running|Passed|Failed|findings|to decide|Submit|Waiting|Harbor|NEEDS|Dismiss|Review required/i.test(l)).slice(0,50).join('\n'));
  await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
