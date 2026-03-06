# Playwright Browser Notes

## What worked here

The reliable path was not `playwright-cli open --browser chromium`.

That CLI only supports these browser/channel values:

- `chrome`
- `firefox`
- `webkit`
- `msedge`

On this Fedora machine, the installed browser is:

```bash
/usr/bin/chromium-browser
```

So the workable approach was:

1. Install Chromium on the machine.
2. Install Playwright locally in the frontend workspace.
3. Launch Playwright with an explicit `executablePath` pointing at system Chromium.

## Useful setup

Install Playwright in the repo:

```bash
cd /home/horsehead/Projects/StudySpace_Interim/frontend
npm install -D playwright
```

Confirm Chromium exists:

```bash
command -v chromium-browser
```

Expected path in this environment:

```bash
/usr/bin/chromium-browser
```

## Working example

Run a one-off browser script from the repo root:

```bash
node <<'EOF'
const { chromium } = require('./frontend/node_modules/playwright');

(async() => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/chromium-browser'
  });

  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle' });
  await page.screenshot({ path: '/tmp/playwright-shot.png', fullPage: true });
  await browser.close();
})();
EOF
```

## Dark mode check example

```bash
node <<'EOF'
const { chromium } = require('./frontend/node_modules/playwright');

(async() => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/chromium-browser'
  });

  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:8000/?v=' + Date.now(), { waitUntil: 'networkidle' });

  const bodyClass = await page.locator('body').evaluate((el) => el.className);
  if (!bodyClass.includes('dark-mode')) {
    await page.click('.theme-toggle');
    await page.waitForTimeout(300);
  }

  await page.screenshot({ path: '/tmp/playwright-dark.png', fullPage: true });
  await browser.close();
})();
EOF
```

## Why `playwright-cli` was not enough

`playwright-cli` worked as a command, but these issues came up:

- it did not accept `chromium` as a supported `--browser` value
- the `chrome` channel expected Google Chrome rather than Fedora Chromium
- using Playwright directly with `executablePath` was more reliable

## Practical rule

For this repo on this machine:

- use `playwright-cli` only if the target browser channel matches an installed supported browser
- otherwise use local Playwright with:

```js
executablePath: '/usr/bin/chromium-browser'
```
