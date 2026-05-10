# TS-254

Validates the live `trackstate-setup` README negative validation example so it
cannot collide with real repository assets.

The test:

1. reads the deployed `CLI quick start` section from `IstiN/trackstate-setup`
2. extracts the documented negative validation path example(s)
3. inspects the live default-branch repository tree
4. verifies each negative example path is unique and absent from the tree
5. runs each documented negative `gh api` command and expects a terminal-visible
   `404 Not Found` with empty stdout

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-254 -p 'test_*.py' -v
```
