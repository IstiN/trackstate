# TS-347

Verifies that the camelCase CLI search pagination flags return the flattened
Jira-compatible pagination fields without the legacy nested `data.page` object.

The automation:

1. compiles a temporary `trackstate` executable from this checkout
2. seeds a temporary Local Git repository with a valid `TRACK` project and two
   searchable issues
3. runs the exact ticket command from that repository:
   `trackstate search --jql "project = TRACK" --startAt 0 --maxResults 1`
4. checks that the JSON response under `data` contains `issues`, `startAt`,
   `maxResults`, `total`, and `isLastPage` as top-level fields
5. verifies the legacy nested `data.page` object is absent from the parsed
   payload and the visible CLI output
6. runs the equivalent kebab-case control command from the same repository to
   prove the fixture itself is valid and the aliases stay consistent

## Command

```bash
python3 -m unittest discover -s testing/tests/TS-347 -p 'test_*.py' -v
```

## Environment

- Python 3 standard library
- Dart SDK
- git CLI
