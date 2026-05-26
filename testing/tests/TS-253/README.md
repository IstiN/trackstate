# TS-253

Validates the live `trackstate-setup` README `CLI quick start` walkthrough by
copying each documented `gh api` snippet, expanding it for the authenticated
user's fork, and checking that the terminal-visible result matches the README:

1. the positive command prints the current `DEMO/project.json` payload from the
   forked setup repository
2. the negative command for `DEMO/project.missing.json` fails with HTTP
   `404 Not Found`

The test also performs human-style verification by asserting that the visible
CLI output matches what a README reader would observe in the terminal: project
JSON for the positive path and a 404 error with no JSON payload for the
negative path.

## Run this test

```bash
TS253_RESULT_PATH=outputs/ts253_observation.json \
python3 -m unittest discover -s testing/tests/TS-253 -p 'test_*.py' -v
```
