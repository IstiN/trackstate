# TS-710 test automation

This test verifies the live GitHub Release page for the latest published
stable `v*` release in `IstiN/trackstate`.

The automation:
1. discovers the latest stable release through the public GitHub Releases API
2. opens the live release page in Chromium through Playwright
3. verifies the visible **Assets** section exposes focusable download links with
   non-empty accessible labels
4. verifies the checksum clipboard control has a descriptive ARIA label
5. tabs through the Assets section to confirm a logical keyboard traversal order
6. activates every visible asset link with the keyboard and verifies each one
   triggers a browser download
7. measures the rendered release-note text contrast against its effective
   background and checks it meets WCAG AA (4.5:1)
8. conditionally verifies any visible **Quick Start** heading uses a logical
   heading level and exposes labeled focusable controls inside that section

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
TS710_SCREENSHOT_PATH=outputs/ts710_release_page.png \
TS710_RESULT_PATH=outputs/ts710_observation.json \
python3 -m unittest discover -s testing/tests/TS-710 -p 'test_*.py' -v
```

## Optional environment variables

- `TRACKSTATE_RELEASE_ACCESSIBILITY_REPOSITORY` (default: `IstiN/trackstate`)
- `TRACKSTATE_RELEASE_ACCESSIBILITY_TAG` (optional; defaults to the latest stable
  published `v*` release)
