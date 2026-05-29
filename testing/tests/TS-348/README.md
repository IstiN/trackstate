# TS-348

Verifies that an empty CLI search result still returns flattened pagination
metadata and does not expose the legacy nested `data.page` object.

The automation:

1. compiles a temporary `trackstate` executable from this checkout
2. seeds a temporary Local Git repository with a valid `TRACK` project and two
   searchable issues
3. runs the exact ticket command from that repository:
   `trackstate search --jql "project = TRACK and status = 'Non-Existent-Status-XYZ'"`
4. checks that the JSON response under `data` contains `issues`, `startAt`,
   `maxResults`, `total`, and `isLastPage` as top-level fields
5. verifies `data.issues` is empty, `total` is `0`, and the visible CLI output
   shows an empty result set instead of any seeded issue rows
6. confirms the legacy nested `data.page` object is absent from both the parsed
   payload and the visible CLI output

## Command

```bash
python3 -m unittest discover -s testing/tests/TS-348 -p 'test_*.py' -v
```

## Environment

- Python 3 standard library
- Dart SDK
- git CLI
