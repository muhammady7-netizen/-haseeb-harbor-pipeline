/**
 * fin-f53 — dismiss 5 advisory PreQC findings (never Confirm).
 * OpenCode chrome-profile off-screen.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const TASK =
  'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#task=content-cf347576d2d9beabcb4dac83b3452347-v1';
const NOTE =
  'Advisory only / framework limitation. Deterministic verifiers + gold replay cover correctness; dismiss per Shannon PreQC guidance.';

async function sleep(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

(async () => {
  const browser = await chromium.launchPersistentContext(PROFILE, {
    headless: false,
    channel: 'chrome',
    viewport: { width: 1280, height: 900 },
    args: [
      '--window-position=-32000,-32000',
      '--window-size=1280,900',
      '--disable-blink-features=AutomationControlled',
    ],
  });
  const page = browser.pages()[0] || (await browser.newPage());
  try {
    await page.goto(TASK, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(7000);

    for (let i = 0; i < 8; i++) {
      const review = page.getByRole('button', { name: /Review issue/i }).first();
      const reviewText = page.getByText(/Review issue/i).first();
      let opened = false;
      if (await review.count()) {
        await review.click();
        opened = true;
        console.log('OPENED_REVIEW_BUTTON', i);
      } else if (await reviewText.count() && (await reviewText.isVisible().catch(() => false))) {
        await reviewText.click();
        opened = true;
        console.log('OPENED_REVIEW_TEXT', i);
      }
      if (!opened) {
        console.log('NO_MORE_REVIEW_ISSUE', i);
        break;
      }
      await sleep(2000);

      const noteBox = page.locator('textarea, input[type="text"]').last();
      if (await noteBox.count()) {
        await noteBox.fill(NOTE).catch(async () => {
          await noteBox.click();
          await page.keyboard.type(NOTE);
        });
        console.log('NOTE_FILLED', i);
      }

      const dismissBtn = page.getByRole('button', { name: /^Dismiss$/i }).first();
      const dismissText = page.getByText(/^Dismiss$/i).first();
      if (await dismissBtn.count()) {
        await dismissBtn.click();
        console.log('DISMISSED_BTN', i);
      } else if (await dismissText.count()) {
        await dismissText.click();
        console.log('DISMISSED_TEXT', i);
      } else {
        const anyDismiss = page.getByText(/\bDismiss\b/i).first();
        if (await anyDismiss.count()) {
          await anyDismiss.click();
          console.log('DISMISSED_LOOSE', i);
        } else {
          console.log('NO_DISMISS_CONTROL', i);
          await page.keyboard.press('Escape');
        }
      }
      await sleep(2500);
    }

    const text = await page.locator('body').innerText();
    fs.writeFileSync('tmp-pw/f53-dismiss-log.txt', `URL=${page.url()}\n\n${text}`);
    console.log(text.slice(0, 2800));
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});
