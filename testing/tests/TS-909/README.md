# TS-909

Validates that the live `IstiN/trackstate` GitHub pull-request compose flow
opens on GitHub and that GitHub's recognized PR template body includes the
exact manual accessibility item:

`Manual verification: DOM order matches visual hierarchy for keyboard-accessible elements.`

The automation checks the live implementation in three ways:

1. GitHub CLI reads repository metadata, the GitHub community profile, the
   default-branch tree, conventional PR template file paths, and GitHub's
   `pullRequestTemplates` GraphQL field.
2. The test opens the live GitHub compare/compose surface for a branch that does
   not already have an open PR and verifies that GitHub reaches `Open a pull
   request`.
3. The checklist assertions use GitHub's recognized PR template body, while the
   repository file probes remain as diagnostics for template-path selection.

## Run

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-909/test_ts_909.py
```
