# TS-893

Validates that startup retries active local workspace restoration after the local
repository becomes temporarily unavailable during initialization, then restores
the saved workspace as **Local Git** once access returns.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored signed-in
  GitHub session and a preloaded active local workspace profile
2. prepares the matching local git folder on disk, temporarily revokes access
  to it to simulate a transiently busy/unavailable file-system handle
3. runs the scenario at the default desktop viewport of `1440x900`
4. keeps the local workspace blocked until the header workspace trigger is
  already visible, then requires a public pre-release workspace state proving
  restore is still incomplete while the directory remains blocked before it
  restores access
5. records tracked File System Access activity on the saved local workspace
  lineage while it is still blocked, along with any TS-893 runtime failure
  probe, as diagnostic evidence only, then waits after the busy-state release
  for the workspace switcher trigger to restore the saved local workspace
  instead of asserting immediately
6. opens **Workspace switcher** and verifies the selected active row is the
  local workspace in the `Local Git` state rather than `Local Unavailable` or
  the hosted fallback
7. records the pre-release trigger state, any visible restore banner, the final
  row state, and a screenshot if the live startup flow still lands on the
  hosted fallback or keeps the local row unavailable

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-893/test_ts_893.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: while the local workspace is still blocked, startup exposes a public
pre-release workspace state showing restore is not yet complete, and after the
temporary busy state is released the prepared active local workspace is
restored as the selected Local Git row without leaving Hosted setup workspace
active or showing Local Unavailable.

Fail: startup never exposes a trustworthy public pre-release blocked-workspace
state while access is still revoked, or after the temporary busy state is
released it still keeps Hosted setup workspace active, leaves the local row
Unavailable, or otherwise does not restore the saved local workspace as Local
Git.
```
