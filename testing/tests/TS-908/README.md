# TS-908

## Objective

Verify that the live pull-request CI pipeline exposes an accessibility gate capable of
blocking UI changes that violate WCAG AA contrast or ARIA semantic requirements.

## Automation approach

This ticket must remain read-only, so the automation does not create a disposable pull
request. Instead it verifies the live GitHub repository contract that a contributor would
depend on before opening such a PR:

1. reads the active pull-request workflow definitions from the GitHub API;
2. checks whether any PR workflow declares accessibility-oriented markers such as
   `axe-core`, `accessibility`, `contrast`, or `aria`;
3. checks whether branch rules / required checks would enforce such a workflow on PRs;
4. opens the live workflow file page in GitHub and records the visible step list as
   human-style evidence.

If the workflow contract and required checks do not expose an accessibility gate, the
test fails and writes a product bug report because the requested CI capability is missing.
