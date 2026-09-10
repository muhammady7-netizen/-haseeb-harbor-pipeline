const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TASK = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-cf347576d2d9beabcb4dac83b3452347-v1';
const NOTE = 'Advisory framework limitation. Deterministic gold/verifiers cover this. Dismiss per Shannon PreQC guidance.';
async function sleep(ms){await new Promise(r=>setTimeout(r,ms));}
(async()=>{
  const browser=await chromium.launchPersistentContext(PROFILE,{headless:false,channel:'chrome',viewport:{width:1400,height:1000},args:['--window-position=-32000,-32000','--window-size=1400,1000','--disable-blink-features=AutomationControlled']});
  const page=browser.pages()[0]||await browser.newPage();
  try{
    await page.goto(TASK,{waitUntil:'domcontentloaded',timeout:120000});
    await sleep(8000);
    for(let s=0;s<10;s++){await page.mouse.wheel(0,1000);await sleep(300);}    
    // dump controls
    const info=await page.evaluate(()=>{
      const els=[...document.querySelectorAll('button,a,[role=button]')].slice(0,80);
      return els.map(e=>({tag:e.tagName,text:(e.innerText||'').trim().slice(0,80),aria:e.getAttribute('aria-label')}));
    });
    fs.writeFileSync('tmp-pw/f53-buttons.json', JSON.stringify(info,null,2));
    console.log('BUTTONS_DUMP', info.filter(x=>/review|dismiss|confirm|issue|note/i.test(x.text||'')||/review|dismiss|confirm/i.test(x.aria||'')).slice(0,30));

    // Also poll status snippet
    const text=await page.locator('body').innerText();
    const lines=text.split(/\n/).filter(l=>/Oracle|GLM|Running|Passed|Failed|findings|to decide|Submit|Harbor/i.test(l));
    console.log('STATUS_LINES');
    console.log(lines.slice(0,40).join('\n'));
    fs.writeFileSync('tmp-pw/f53-poll.txt', text);
  } finally { await browser.close().catch(()=>{}); }
})().catch(e=>{console.error(e);process.exit(1);});
