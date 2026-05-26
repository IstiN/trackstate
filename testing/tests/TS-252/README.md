# TS-252 test automation

This test verifies the live release-management behavior for
`IstiN/trackstate-setup` when a pull request is merged into a disposable
non-default branch:

1. creates a disposable target branch from `main`
2. creates a separate disposable source branch with a minor `README.md` update
3. opens a pull request from the source branch into the non-default branch
4. merges that pull request
5. waits through the same asynchronous observation window used for release checks
6. verifies that no new GitHub release and no new semantic version tag (`vX.Y.Z`)
   are tied to the merged non-default-branch commit

It also performs a human-style verification by checking the public GitHub
Releases and Tags pages still render normally and do not visibly surface an
unexpected new semantic version for that merge.

## Run this test

```bash
TS252_RESULT_PATH=outputs/ts252_observation.json \
python -m unittest discover -s testing/tests/TS-252 -p 'test_*.py' -v
```

## Required configuration

- GitHub CLI authenticated (`gh auth status`) with push, branch-delete, and merge
  permissions for `IstiN/trackstate-setup`
- `GH_TOKEN`/`GITHUB_TOKEN` available to `gh api` and `gh pr`
- network access to `api.github.com` and `github.com`

## Expected output when the test passes

```text
test_merge_to_non_default_branch_does_not_generate_release_or_semantic_tag ... ok
```
