# Development Focus

- Preserve existing repository, workflow, and agent configuration contracts.
- Prefer small, composable changes with explicit failure modes.
- Reuse existing scripts, workflows, and conventions before introducing new abstractions.
- For every Flutter UI asset, component, screen, or generated visual design implemented in the repo, add or update golden tests that verify the rendered UI output.
- Review each generated UI image/design asset before accepting it, and only keep assets that look visually correct, polished, and aligned with TrackState.AI design guidance.
- Keep all UI data mockable: screens and widgets must be able to render from fixtures/fakes without live Git, GitHub, Jira, network, or filesystem dependencies.
- Every interactive Flutter widget, button, input, card, navigation item, status badge, and screen landmark must have a meaningful Semantics label (or equivalent accessibility annotation) so screen readers, automated tests, and integration test finders can identify elements reliably.
- Accessibility labels must be descriptive and stable — use them as the canonical way to locate elements in widget tests and integration tests.
- Keep credentials, caches, and generated artifacts out of source control.
