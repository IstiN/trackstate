# TS-909

Validates that a live `IstiN/trackstate` GitHub PR for a UI layout change
automatically pre-fills the PR description with the exact manual accessibility
item:

`Manual verification: DOM order matches visual hierarchy for keyboard-accessible elements.`

The automation checks the live implementation in three ways:

1. GitHub CLI reads repository metadata, the GitHub community profile, the
   default-branch tree, conventional PR template file paths, and GitHub's
   `pullRequestTemplates` GraphQL field.
2. If GitHub exposes no usable PR template body at all, the test fails as a
   product defect immediately because a new PR cannot be auto-populated with the
   required checklist item.
3. When a template body exists, the test opens a live GitHub compare/compose
   surface for a branch without an open PR and verifies the actual PR
   description field value on the `Open a pull request` page.
4. When repository evidence already proves the template is missing, the test can
   also open the canonical PR-template file path to capture reviewer-visible 404
   evidence.
5. The test requires a Playwright browser runtime for live browser proof.

## Run

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-909/test_ts_909.py
```
