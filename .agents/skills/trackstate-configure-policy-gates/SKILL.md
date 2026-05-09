---
name: trackstate-configure-policy-gates
description: Add or update TrackState policy and quality gates so repository rules are enforced locally, in CI, and through agent feedback loops. Use when introducing repo-local policy checkers, wiring `policyGates`/`qualityGates` in `.dmtools/config.js`, or teaching agents to recover from gate failures.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Fri, 09 May 2026 06:49:00 GMT
---
# Configuring TrackState Policy Gates

## Contents
- [When to Use This Skill](#when-to-use-this-skill)
- [Core Gate Surfaces](#core-gate-surfaces)
- [Implementation Workflow](#implementation-workflow)
- [Agent Feedback Loop Integration](#agent-feedback-loop-integration)
- [CI and Command Requirements](#ci-and-command-requirements)
- [Example Configuration](#example-configuration)

## When to Use This Skill

Use this skill when TrackState needs a repository-enforced rule that should:

1. fail locally with a documented command,
2. run in GitHub Actions,
3. run inside agent post-actions before publish,
4. feed failures back into the same agent for automatic repair.

Typical cases:

* prevent hardcoded colors, strings, routes, or URLs,
* require structural checks that `flutter analyze` cannot reliably enforce,
* add project-specific policy commands without modifying the core Flutter toolchain.

## Core Gate Surfaces

TrackState gate wiring spans four surfaces and should stay consistent across all of them:

1. **Repository command** — e.g. `dart run tool/check_theme_tokens.dart`
2. **Policy config** — e.g. `.dmtools/policies/*.json`
3. **Project automation config** — `.dmtools/config.js`
4. **CI workflow** — usually `.github/workflows/unit-tests.yml`

If the rule should influence automated development/rework flows, also wire it through:

5. **Shared agent feedback logic** — `agents/js/common/feedbackLoop.js`

## Implementation Workflow

Follow this sequence when adding a new gate.

### Task Progress
- [ ] Define a single documented enforcement command that exits non-zero on violations.
- [ ] Implement the checker in-repo (`tool/` or `testing/tools/`) rather than relying on unsupported analyzer plugin behavior.
- [ ] Keep the checker output analyzer-style: `warning • message • file:line:column • code`.
- [ ] Add a policy config file if the rule needs include/exclude patterns or allowlists.
- [ ] Update `.dmtools/config.js` to register the command under `policyGates` or `qualityGates`.
- [ ] Add the same command to CI so pull requests fail before merge.
- [ ] Ensure the command is available in `CLI_ALLOWED_COMMANDS` and that the required runtime (`dart`, `flutter`, `python3`, etc.) is installed in `ai-teammate.yml`.
- [ ] Add or update targeted regression tests that exercise the supported enforcement command.
- [ ] Run local validation and confirm the same command works in both clean and violating cases.

## Agent Feedback Loop Integration

TrackState uses two gate families:

* **`qualityGates`** — broad validation like `flutter analyze` or `flutter test`
* **`policyGates`** — project-specific enforcement commands

When a gate should participate in agent retry/recovery:

1. Add it to `.dmtools/config.js` under `feedbackLoop`.
2. Prefer `policyGates` for custom repository rules.
3. Keep `maxAttempts` explicit.
4. Make the failure actionable so the agent can fix the exact violation.

The shared agents layer should call:

```js
feedbackLoop.runQualityGates(...)
feedbackLoop.runPolicyGates(...)
```

before commit/push or PR publish steps.

## CI and Command Requirements

Before enabling a gate for agents, confirm all required binaries are available in the runner.

Examples:

* **Dart checker:** install Flutter or Dart and allow `dart`
* **Flutter gate:** install Flutter and allow `flutter`
* **Python checker:** ensure `python3` is available and allowed

For TrackState specifically:

* `.github/workflows/ai-teammate.yml` must expose the runtime used by the gate.
* `CLI_ALLOWED_COMMANDS` must include the command family the checker uses.
* `unit-tests.yml` should run the same policy command on PRs.

Do not enable a gate in agent post-actions if the runner cannot execute it yet.

## Example Configuration

### `.dmtools/config.js`

```js
const FLUTTER_FEEDBACK = {
  postAction: {
    enabled: true,
    maxAttempts: 2,
  },
  qualityGates: {
    enabled: true,
    gates: [
      { name: 'flutter-analyze', command: 'flutter analyze', maxAttempts: 2 },
      { name: 'flutter-test', command: 'flutter test --coverage', maxAttempts: 2 },
    ],
  },
  policyGates: {
    enabled: true,
    gates: [
      {
        name: 'theme-token-lint',
        command: 'dart run tool/check_theme_tokens.dart',
        maxAttempts: 2,
      },
    ],
  },
};
```

### CI step

```yaml
- name: Enforce theme tokens
  run: dart run tool/check_theme_tokens.dart
```

### Good checker output

```text
warning • Use TrackState theme tokens instead of hardcoded colors. Color(0xFFFAF8F4) • lib/ts115_lint_probe.dart:8:14 • trackstate_theme_tokens
```

This keeps the rule understandable to humans, CI, and agent retry prompts.
