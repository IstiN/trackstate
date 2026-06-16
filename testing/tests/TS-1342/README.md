# TS-1342 test automation

Verifies that `tool/resolve_semantic_version.sh` correctly resolves the next
semantic release tag by patch-bumping the latest tag, or by reusing an existing
tag that already points at the current commit.

## What is tested

1. A disposable git repository is initialized with commits and tags `v1.0.0`, `v1.0.5`.
2. The script is run in `auto` mode on a new commit after `v1.0.5`.
3. Expected output: `release_tag=v1.0.6`.
4. A semantic version tag `v1.0.7` is created on the current commit.
5. The script is run again on the same commit.
6. Expected output: `release_tag=v1.0.7` (reuse, no conflict).

## Run this test

```bash
python -m unittest testing.tests.TS-1342.test_ts_1342
```
