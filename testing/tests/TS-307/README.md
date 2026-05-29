# TS-307

Validates the production-visible **Create issue** flow in the local Git runtime
across desktop and compact widget viewports.

The automation:
1. opens the real Create issue surface from the running app shell
2. verifies the visible form copy rendered inside that surface
3. checks the accessibility traversal order for the exposed form fields
4. measures rendered contrast for the visible labels and the `Optional`
   placeholder
5. resizes the same open surface to a compact viewport and verifies whether it
   becomes a full-screen presentation

## Run this test

```bash
flutter test testing/tests/TS-307/create_issue_responsive_accessibility_test.dart
```

## Expected result

```text
Pass: the Create issue surface appears as a right-docked side sheet on wide
layouts, switches to a full-screen surface on compact layouts, preserves a
logical accessibility traversal, and keeps visible text at WCAG AA contrast.

Fail: the surface stays modal/inset, overflows, loses the expected form
semantics order, or renders visible text below the required contrast threshold.
```
