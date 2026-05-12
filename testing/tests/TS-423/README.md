# TS-423

Verifies that the production Flutter tracker app exposes accessible loading and
partial-state feedback for dashboard, board, and issue detail content during the
bootstrap window.

The automation:
1. launches a hosted bootstrap snapshot with delayed initial search hydration
2. enables Flutter semantics and checks the visible dashboard loading state
3. verifies meaningful loading semantics labels and WCAG AA loading-banner
   contrast in the dashboard and board sections
4. opens a seeded issue while detail hydration is still partial and verifies the
   summary remains visible while the detail body exposes a loading placeholder
   with accessible semantics and readable contrast

## Run this test

```bash
flutter test testing/tests/TS-423/test_ts_423.dart -r expanded
```
