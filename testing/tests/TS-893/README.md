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
  already visible, then restores access so the unblock cannot happen before
  startup has reached the visible recovery window
5. records any restore-specific blocked-window diagnostics while the workspace
  is still blocked, such as tracked File System Access activity on the saved
  local workspace lineage, a TS-893 runtime probe event, the visible restore
  skip banner, or another public pre-release non-restored state
6. after the busy-state release, waits for the workspace switcher trigger to
   restore the saved local workspace instead of asserting immediately
7. opens **Workspace switcher** and verifies the selected active row is the
   local workspace in the `Local Git` state rather than `Local Unavailable` or
   the hosted fallback
8. requires pre-release proof that startup actually overlapped the blocked
   saved-handle revalidation path before a passing result can be reported
9. records the pre-release trigger state, busy-gate activity, any visible
   restore banner, the final row state, and a screenshot if the live startup
   flow still lands on the hosted fallback, keeps the local row unavailable, or
   never proves the blocked-startup overlap required by TS-893

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
Pass: before release, the run captures a blocked-startup overlap signal for the
saved local workspace, and after the temporary busy state is released the
prepared active local workspace restores as the selected Local Git row without
keeping Hosted setup workspace active or showing Local Unavailable.

Fail: after the temporary busy state is released, startup keeps Hosted setup
workspace active or leaves the local row Unavailable; or the run never proves
that startup overlapped the blocked saved local handle before release, which
means TS-893 cannot pass from that execution.
```
