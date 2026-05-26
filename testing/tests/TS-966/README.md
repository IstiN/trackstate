# TS-966

Live web regression for the deployed TrackState workspace switcher runtime-failure
scenario.

The test:

1. opens the hosted TrackState app at desktop viewport `1440x900`
2. verifies the interactive shell and workspace switcher are reachable
3. injects a workspace-switcher-scoped runtime fault in the browser
4. re-triggers the switcher fault path
5. confirms the global shell stays interactive and sidebar navigation still works

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-966/test_ts_966.py
```

## Expected result

Pass: the synthetic workspace switcher runtime error is exercised, but the page
does not collapse to a blank `Sync issue` surface and the sidebar still
navigates to another section.

Fail: the fault is not exercised, the shell stalls, the top bar/sidebar become
unusable, or navigation no longer works after the switcher fault.
