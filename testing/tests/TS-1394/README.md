# TS-1394 — Assistant Subcommand Routing

Verifies ecosystem-specific assistant entry points route commands through the standard TrackState CLI.

## Run this test

```bash
python -m unittest testing.tests.TS-1394.test_ts_1394 -v
```

## What is tested

- `trackstate assistant github search --jql "project = TRACK"` routes to the search command and returns a JSON envelope.
- `trackstate assistant claude ticket create --summary "New story" --issue-type Story` routes to the ticket create command and returns a JSON envelope.
- The assistant namespace does not require a separate binary or runtime; it reuses the base CLI implementation.
