# TrackState Product Domain Knowledge

## Project context

TrackState is being bootstrapped with DMTools-style agent automation. The repository may start small, so agents should derive decisions from the current codebase, README, workflows, and issue context instead of assuming a fixed stack too early.

## Working model

1. The shared `agents/` submodule provides reusable agent configs and scripts.
2. `.dmtools/config.js` contains repository-specific overrides, prompt wiring, and extra instructions.
3. GitHub Actions workflows are the execution surface for teammate automation and validation.

## Guidance

- Favor repository-native patterns over speculative architecture.
- Keep stories and implementation slices testable, explicit, and easy to review.
- Preserve compatibility with shared agent configs and workflow inputs.
- When requirements are ambiguous, prefer concrete outputs that reference actual files, commands, workflows, or acceptance criteria visible in this repository.
- Keep credentials, generated artifacts, and machine-local state out of source control.
