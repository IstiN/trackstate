# TS-238

Validates the `trackstate-setup/README.md` quick-start formatting contract for
the fork connectivity validation command.

The automation passes only when the `CLI quick start` section:
1. exists,
2. explains the validation flow to the reader, and
3. presents the executable `gh api ...` validation command inside a fenced
   markdown code block so it remains copy-pasteable for manual users and
   automation such as TS-74.

## Install dependencies

No Python packages are required beyond the standard library.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-238 -p 'test_*.py'
```

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```
