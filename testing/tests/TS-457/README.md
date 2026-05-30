# TS-457

Verifies that the CLI create flow accepts the native hierarchy flags from the
ticket command and returns the canonical TrackState success envelope while
creating the issue beneath the selected epic folder in a disposable Local Git
repository.

The automation:

1. seeds a Local Git repository with a `TS` project, required config defaults,
   and an existing `EPIC-101` issue,
2. runs the live `trackstate create --summary "New Story" --issueType Story
   --epic EPIC-101 --target local` command through this repository checkout,
3. verifies the JSON response exposes the canonical TrackState envelope with
   `ok`, `schemaVersion`, and an `issue` object inside `data`,
4. checks the created issue metadata reports the epic relationship and canonical
   `TS/EPIC-101/TS-1/main.md` storage path, and
5. confirms the visible repository content under `TS/EPIC-101/` shows the new
   issue markdown file with the expected summary and hierarchy fields.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-457 -p 'test_*.py' -v
```
