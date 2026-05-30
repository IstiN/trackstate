# TS-319

Verifies the CLI search command against the ticketed Jira-compatible response
shape.

The automation:

1. compiles a temporary `trackstate` executable from this checkout
2. seeds a temporary Local Git repository with a valid `TRACK` project and two
   searchable issues
3. runs the exact ticket command from that repository:
   `trackstate search --jql "project = TRACK" --startAt 0 --maxResults 2`
4. checks that the JSON response under `data` contains `issues`, `startAt`,
   `maxResults`, `total`, and `isLastPage`
5. runs a supported control command from the same repository to prove the
   fixture itself is valid

## Command

```bash
python3 -m unittest discover -s testing/tests/TS-319 -p 'test_*.py' -v
```

## Environment

- Python 3 standard library
- Dart SDK
- git CLI
