# TS-445

Validates the Settings startup-recovery callout in the hosted runtime.

The automation pumps the production Flutter app into the GitHub startup
rate-limit recovery state, opens Settings, and verifies:
1. the recovery callout renders above the repository-access controls,
2. the visible recovery actions match the ticket,
3. the callout uses the amber warning token treatment,
4. the recovery copy remains readable at WCAG AA contrast,
5. keyboard focus and hover/focus visuals remain available on the recovery
   actions, and
6. a user can trigger Retry and open the Connect GitHub dialog from the
   callout itself.

## Run this test

```bash
flutter test testing/tests/TS-445/test_ts_445.dart -r expanded
```
