# TS-1387

Verifies the `trackstate-setup/README.md` quick-start CLI command syntax.

The automation passes only when the `CLI quick start` section documents the
GitHub CLI validation command with:

1. the approved `<fork>` repository placeholder,
2. the short `-H` header flag (not the long `--header` form),
3. the `Accept: application/vnd.github.raw+json` header value,
4. the command presented as a single-line, copy-pasteable bash snippet.

## Install dependencies

No Python packages are required beyond the standard library.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-1387 -p 'test_*.py'
```

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
