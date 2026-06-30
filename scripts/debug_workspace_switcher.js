const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: false,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto('http://localhost:8080');
  await page.waitForTimeout(3000);

  const tags = await page.evaluate(() => {
    const counts = {};
    document.querySelectorAll('*').forEach(e => { counts[e.tagName] = (counts[e.tagName]||0)+1; });
    return counts;
  });
  console.log('Tag counts:', tags);

  const fltSemanticsHost = await page.$('flt-semantics-host');
  console.log('flt-semantics-host present:', !!fltSemanticsHost);
  if (fltSemanticsHost) {
    const children = await fltSemanticsHost.evaluate(el => Array.from(el.children).map(c => c.tagName));
    console.log('children:', children);
  }

  await browser.close();
})();
