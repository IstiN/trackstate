# TS-614 test automation

Verifies the deployed TrackState desktop header renders the ticket-listed
interactive controls at a consistent 32px height and keeps them vertically
aligned in the shared header container.

The automation:
1. opens the hosted TrackState app in Chromium with the stored GitHub token
2. verifies the visible desktop header shows the sync pill, `Search issues`,
   `Create issue`, `Attachments limited`, the theme toggle, and the signed-in
   profile label
3. measures the rendered heights of each visible header control and checks that
   they match the required 32px target
4. derives the shared public header ancestor for those controls when the live
   DOM exposes one and, if present, checks that it uses a flex layout with
   `align-items: center`
5. writes failure evidence and a bug description when the hosted product still
   exposes the desktop header sizing defect

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install --with-deps chromium
```

## Run this test

```bash
mkdir -p outputs && python testing/tests/TS-614/test_ts_614.py
```

## Required environment / config

- `GH_TOKEN` or `GITHUB_TOKEN` must be set so the hosted app can authenticate
  to the live setup repository.
- The test targets the deployed TrackState app configured by
  `testing/core/config/live_setup_test_config.py`.

## Expected pass / fail behavior

- **Pass:** every audited desktop header control renders at 32px height, the
  controls stay vertically centered within tolerance, and any publicly exposed
  shared header container uses a flex layout with `align-items: center`.
- **Fail:** any audited header control renders above or below 32px, the
  visible controls drift off a shared vertical centerline, an exposed shared
  header container is not a centered flex layout, or the hosted app cannot
  expose the required desktop header controls.
