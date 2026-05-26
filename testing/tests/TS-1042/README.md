# TS-1042 test automation

This test validates the live TrackState startup priority queue behavior for the
GitHub `/user` identity probe under secondary bootstrap latency.

1. Preloads the deployed app with local and hosted workspace profiles plus a
   stored GitHub token.
2. Delays the live repository tree bootstrap request (`git/trees/main`) by 10
   seconds to simulate the ticket's secondary repository-latency condition on
   the current deployment.
3. Records the exact monotonic timestamp when the GitHub `/user` request is
   initiated and asserts that it starts within 2000ms of application launch.
4. Captures the visible startup state and the later shell state for human-style
   verification.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1042/test_ts_1042.py
```

## Required configuration

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and
  `https://api.github.com/`
