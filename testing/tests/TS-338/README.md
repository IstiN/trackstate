# TS-338

Verifies the CLI search command rejects invalid pagination values while still
accepting the Jira-style `--startAt` and `--maxResults` flag aliases.

The automation:

1. compiles a temporary `trackstate` executable from this checkout
2. seeds a temporary Local Git repository with a valid `TRACK` project and two
   searchable issues
3. runs the exact ticket commands from that repository:
   `trackstate search --jql "project = TRACK" --startAt "first"` and
   `trackstate search --jql "project = TRACK" --maxResults -10`
4. checks that each command fails with exit code `2` and the expected JSON
   validation envelope
5. runs a supported control command from the same seeded repository to prove
   the fixture itself is valid

## Command

```bash
python3 -m unittest discover -s testing/tests/TS-338 -p 'test_*.py' -v
```
