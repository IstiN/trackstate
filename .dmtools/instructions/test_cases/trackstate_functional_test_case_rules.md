# TrackState Functional Test Case Rules

Use these rules when generating test cases for TrackState.

## Goal

Generate test cases that validate repository behavior users and maintainers depend on, not just that files changed.

## Prefer functional evidence

Each test case should cite at least one concrete source of truth:

- a repository command and expected output;
- an implementation file or config that defines behavior;
- a GitHub workflow or automation step users rely on;
- a generated artifact or document consumed by maintainers;
- an issue tracker or pull request side effect visible to collaborators.

Avoid cases that only say "inspect the file" unless they name exact files and exact expected results.

## Step quality

Steps should be executable by a human or automation:

- include exact command, workflow, or file path;
- include precise expected text, state transition, or artifact;
- define failure conditions clearly;
- avoid vague words like "correct" or "updated" without measurable criteria.

## Coverage balance

For small repository changes, prefer 3-5 high-signal cases that cover:

1. source-of-truth implementation or config consistency;
2. user-facing workflow behavior;
3. documentation or setup guidance when it affects execution;
4. repository automation outputs when generation is part of the change.

## Accessibility testing

Every UI test case for a screen, component, or workflow must include accessibility verification:

- verify that all interactive elements (buttons, inputs, cards, links, navigation items, status badges) have non-empty Semantics labels;
- verify that screen readers can traverse the screen in a logical order;
- use Semantics labels as the primary element finder in widget and integration tests — if an element cannot be found by its accessibility label, the test should fail;
- verify WCAG AA contrast ratios (4.5:1 for normal text, 3:1 for large text) where the test framework supports it;
- verify keyboard/focus navigation works for web and desktop targets;
- include at least one test case per screen that validates the full accessibility tree is present and correctly ordered.
