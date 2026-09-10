const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');
(async()=>{
  const browser=await chromium.launchPersistentContext('C:/Users/Haseeb Mirza/.config/opencode/chrome-profile',{headless:true,channel:'chrome'});
  const page=browser.pages()[0]||await browser.newPage();
  await page.goto('https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#',{waitUntil:'domcontentloaded',timeout:120000});
  await page.waitForTimeout(6000);
  const card=page.getByRole('button',{name:/fin-f53-deposit-account-fee-assessment-audit#452347/i}).first();
  if(await card.count()){ await card.click(); } else {
    await page.locator('text=fin-f53-deposit-account-fee-assessment-audit#452347').first().click().catch(()=>{});
    await page.getByText(/^Open$/).first().click().catch(()=>{});
  }
  await page.waitForTimeout(9000);
  const text=await page.locator('body').innerText();
  fs.writeFileSync('tmp-pw/f53-gentle-poll.txt','URL='+page.url()+'\n\n'+text);
  console.log(text.split(/\n/).filter(l=>/Oracle|GLM|Running|Passed|Failed|findings|to decide|Submit|Waiting|Harbor|slots|NEEDS|Review required|Stop run/i.test(l)).slice(0,45).join('\n'));
  await browser.close();
})().catch(e=>{console.error('FAIL',e.message); process.exit(1);});
