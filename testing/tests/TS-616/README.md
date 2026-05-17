# TS-616 test automation

Verifies the deployed TrackState desktop header keeps the ticket-required 32px
standardized control height and alignment across hover, focus, theme-toggle,
and desktop-resize interactions.

The automation:
1. opens the hosted TrackState app in Chromium with the stored GitHub token
2. verifies the visible desktop header shows the sync pill, `Search issues`,
   `Create issue`, `Attachments limited`, the theme toggle, and the signed-in
   profile label
3. asserts the audited header controls render at the required 32px height in
   the baseline desktop state
4. repeats the height/alignment audit after hovering and clicking `Create
   issue`, focusing `Search issues`, toggling the theme twice, and resizing the
   browser within the desktop breakpoint range

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install --with-deps chromium
```

## Run this test

```bash
mkdir -p outputs && python testing/tests/TS-616/test_ts_616.py
```

## Required environment / config

- `GH_TOKEN` or `GITHUB_TOKEN` must be set so the hosted app can authenticate
  to the live setup repository.
- The test targets the deployed TrackState app configured by
  `testing/core/config/live_setup_test_config.py`.

## Expected pass / fail behavior

- **Pass:** the visible desktop header controls stay at the required 32px
  standardized height, preserve vertical alignment through the audited
  interactions, and remain in one non-overlapping row after the desktop resize.
- **Fail:** any audited control renders above or below the 32px target,
  interactive states shift the header vertically, the desktop row overlaps after
  resize, or the hosted app cannot expose the required controls.
