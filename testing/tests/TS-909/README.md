# TS-909

Validates that the live `IstiN/trackstate` GitHub PR template configuration
exposes a PR template body containing the exact manual accessibility item:

`Manual verification: DOM order matches visual hierarchy for keyboard-accessible elements.`

The automation checks the live implementation in three ways:

1. GitHub CLI reads repository metadata, the GitHub community profile, the
   default-branch tree, conventional PR template file paths, and GitHub's
   `pullRequestTemplates` GraphQL field.
2. The checklist assertions use GitHub's recognized PR template body when
   available, otherwise they fall back to the live repository file contents for
   the selected template path.
3. The test opens the live GitHub file page for the selected PR-template path
   (or the canonical missing-template path) and captures a screenshot of the
   reviewer-visible page content for human-style verification.
4. The test requires a Playwright browser runtime for the visible-page proof.

## Run

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-909/test_ts_909.py
```
