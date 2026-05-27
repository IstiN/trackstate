# TS-230 test automation

This test verifies the live release-management behavior for
`IstiN/trackstate-setup`:

1. creates a disposable branch with a minor `README.md` update
2. opens a pull request into `main`
3. merges that pull request
4. waits for asynchronous release automation
5. verifies that GitHub exposes both:
   - a new release
   - a matching newly created semantic version tag (`vX.Y.Z`)

It also performs a human-style verification by checking the public GitHub
Releases and Tags pages for visible presence of the generated semantic tag.

## Install dependencies

```bash
python -m pip install -r testing/requirements.txt
```

## Run this test

```bash
TS230_RESULT_PATH=outputs/ts230_observation.json \
python -m unittest discover -s testing/tests/TS-230 -p 'test_*.py' -v
```

## Required configuration

- GitHub CLI authenticated (`gh auth status`) with push and merge permissions for
  `IstiN/trackstate-setup`
- `GH_TOKEN`/`GITHUB_TOKEN` available to `gh api` and `gh pr`
- network access to `api.github.com` and `github.com`

## Expected output when the test passes

```text
test_merge_to_default_branch_generates_release_and_semantic_tag ... ok
```
