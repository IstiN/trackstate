# TS-340

Verifies the CLI search command reports the flattened Jira-compatible
`isLastPage` flag as `true` on the final page of results.

The automation:

1. compiles a temporary `trackstate` executable from this checkout
2. seeds a temporary Local Git repository with a valid `TRACK` project and five
   searchable issues
3. runs the exact ticket command from that repository:
   `trackstate search --jql "project = TRACK" --startAt 4 --maxResults 1`
4. checks that the JSON response under `data` contains `issues`, `startAt`,
   `maxResults`, `total`, and `isLastPage`
5. confirms the final page returns only `TRACK-5` and flags `isLastPage: true`
6. runs a supported control command from the same repository to prove the
   fixture itself is valid

## Command

```bash
python3 -m unittest discover -s testing/tests/TS-340 -p 'test_*.py' -v
```

## Environment

- Python 3 standard library
- Dart SDK
- git CLI
