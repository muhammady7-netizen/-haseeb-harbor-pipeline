const { chromium } = require('./tmp-pw/node_modules/playwright');
const PROFILE='C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const jobs=[
 ['fin-f39','https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-d09f3e79ded320c787b15498063ef758-v1'],
 ['the-thread','https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-5cc146d448ffc4f0a07bba4ad679dd1f-v1'],
];
(async()=>{
 const b=await chromium.launchPersistentContext(PROFILE,{headless:true,channel:'chrome',args:['--disable-blink-features=AutomationControlled']});
 const p=b.pages()[0]||await b.newPage();
 for(const [short,url] of jobs){
  await p.goto(url,{waitUntil:'domcontentloaded',timeout:90000});
  await sleep(9000);
  const t=await p.locator('body').innerText();
  require('fs').writeFileSync('tmp-pw/a-st-'+short+'.txt',t);
  console.log(JSON.stringify({short,url:p.url(),
   onTask:/Upload new version/i.test(t),
   lastRun:(t.match(/Last run:[^\n]+/i)||[])[0],
   oracle:(t.match(/Oracle (Passed|Failed|Waiting|Running)[^\n]{0,40}/i)||[])[0],
   glm:(t.match(/GLM-5\.2 ×4[^\n]{0,90}/)||[])[0],
   tooEasy:/TOO_EASY/i.test(t),
   findings:(t.match(/\d+ trainer finding/i)||[])[0],
   held:/Finalization held/i.test(t),
  }));
 }
})().catch(e=>{console.error(String(e).slice(0,200));process.exit(1);});
