const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TASK = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-cf347576d2d9beabcb4dac83b3452347-v1';
async function sleep(ms){await new Promise(r=>setTimeout(r,ms));}
(async()=>{
  console.log('LAUNCH headless');
  const browser=await chromium.launchPersistentContext(PROFILE,{
    headless:true,
    channel:'chrome',
    viewport:{width:1400,height:1000},
    args:['--disable-blink-features=AutomationControlled','--noerrdialogs']
  });
  console.log('LAUNCHED pages', browser.pages().length);
  const page=browser.pages()[0]||await browser.newPage();
  page.setDefaultTimeout(60000);
  await page.goto(TASK,{waitUntil:'domcontentloaded',timeout:120000});
  await sleep(10000);
  const text=await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/f53-poll-headless.txt', 'URL='+page.url()+'\n\n'+text);
  const lines=text.split(/\n/).filter(l=>/Oracle|GLM|Running|Passed|Failed|findings|to decide|Submit|Harbor|Waiting|slots/i.test(l));
  console.log(lines.slice(0,50).join('\n'));
  const info=await page.evaluate(()=>[...document.querySelectorAll('button,[role=button]')].map(e=>(e.innerText||'').trim()).filter(Boolean).slice(0,60));
  console.log('BTNS', JSON.stringify(info));
  await browser.close();
  console.log('DONE');
})().catch(e=>{console.error('FAIL',e); process.exit(1);});
