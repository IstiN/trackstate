# TS-909

Validates that the live `IstiN/trackstate` GitHub pull-request compose flow
opens on GitHub and that the actual PR description field exposed on GitHub's
compose page includes the exact manual accessibility item:

`Manual verification: DOM order matches visual hierarchy for keyboard-accessible elements.`

The automation checks the live implementation in three ways:

1. GitHub CLI reads repository metadata, the GitHub community profile, the
   default-branch tree, conventional PR template file paths, and GitHub's
   `pullRequestTemplates` GraphQL field.
2. The test opens the live GitHub compare/compose surface for a branch that does
   not already have an open PR, verifies that GitHub reaches `Open a pull
   request`, and reads the compose page's PR description field value.
3. The checklist assertions use the actual compose-page description value, while
   the repository file probes and `pullRequestTemplates` query remain diagnostics
   for template-path selection.
4. The test requires a Playwright browser runtime; the unauthenticated `urllib`
   fallback is intentionally disallowed because it cannot prove the live GitHub
   compose form body.

## Run

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-909/test_ts_909.py
```
