# TS-458

Validates CLI field resolution precedence and ambiguity handling against a
disposable Local Git repository.

The automation:

1. seeds `TS/TS-1/main.md` with four custom fields,
2. runs the live `trackstate ticket update-field --target local --key TS-1
   --field customfield_10016 --value 8` command and verifies the exact canonical
   id updates only that field,
3. runs the live `trackstate ticket update-field --target local --key TS-1
   --field "Story Points" --value 5` command and verifies the configured
   display name resolves to `storyPoints`,
4. rewrites `TS/config/fields.json` so two fields share the display name
   `Points`, runs `trackstate ticket update-field --field "Points" --value 3`,
   and verifies the CLI returns a machine-readable `AMBIGUOUS_FIELD` error with
   the conflicting canonical ids, and
5. confirms the visible CLI output and final `TS/TS-1/main.md` content match the
   user-facing result after the two successful updates.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-458 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`.
