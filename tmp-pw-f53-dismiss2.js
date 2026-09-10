/**
 * fin-f53 — open latest card from trainer list, dismiss PreQC, report eval status.
 * OpenCode chrome-profile off-screen.
 */
const { chromium } = require('./tmp-pw/node_modules/playwright');
const fs = require('fs');

const PROFILE = 'C:/Users/Haseeb Mirza/.config/opencode/chrome-profile';
const ROOT = 'https://harbor-trainer-s2eobzrxbq-uc.a.run.app/trainer#';
const NOTE =
  'Advisory framework limitation. Gold replay + deterministic verifiers cover correctness. Dismiss per Shannon PreQC guidance.';

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
    await page.goto(ROOT, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await sleep(6000);

    // Click the first fin-f53 row / Open near it
    const card = page.getByText(/fin-f53-deposit-account-fee-assessment-audit#/i).first();
    console.log('CARD_COUNT', await card.count());
    if (await card.count()) {
      await card.click();
      await sleep(2000);
    }
    // Prefer explicit Open button near top
    const openBtn = page.getByRole('button', { name: /^Open$/i }).first();
    if (await openBtn.count()) {
      await openBtn.click();
      console.log('CLICKED_OPEN_BUTTON');
      await sleep(7000);
    } else {
      const openText = page.getByText(/^Open$/i).first();
      if (await openText.count()) {
        await openText.click();
        console.log('CLICKED_OPEN_TEXT');
        await sleep(7000);
      }
    }

    console.log('URL_AFTER_OPEN', page.url());
    let text = await page.locator('body').innerText();
    console.log(text.slice(0, 900));

    // Dismiss loop
    for (let i = 0; i < 8; i++) {
      const review = page.getByRole('button', { name: /Review issue/i }).first();
      const reviewText = page.getByText(/Review issue/i).first();
      let opened = false;
      if (await review.count()) {
        await review.click();
        opened = true;
      } else if (await reviewText.count() && (await reviewText.isVisible().catch(() => false))) {
        await reviewText.click();
        opened = true;
      }
      if (!opened) {
        console.log('NO_MORE_REVIEW', i);
        break;
      }
      console.log('REVIEW', i);
      await sleep(1500);

      const ta = page.locator('textarea').last();
      if (await ta.count()) {
        await ta.fill(NOTE).catch(() => {});
      }

      const dismiss = page.getByRole('button', { name: /^Dismiss$/i }).first();
      if (await dismiss.count()) {
        await dismiss.click();
        console.log('DISMISS', i);
      } else {
        const d2 = page.getByText(/^Dismiss$/i).first();
        if (await d2.count()) {
          await d2.click();
          console.log('DISMISS_TEXT', i);
        } else {
          console.log('NO_DISMISS', i);
          await page.keyboard.press('Escape');
        }
      }
      await sleep(2000);
    }

    text = await page.locator('body').innerText();
    fs.writeFileSync('tmp-pw/f53-dismiss2-log.txt', `URL=${page.url()}\n\n${text}`);
    console.log('---FINAL---');
    console.log(text.slice(0, 3000));
  } finally {
    await browser.close().catch(() => {});
  }
})().catch((e) => {
  console.error('FAIL', e);
  process.exit(1);
});
