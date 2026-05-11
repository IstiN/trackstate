# TS-398

Validates the visible workflow transition surface for an issue that starts in
**In Progress**.

The automation:
1. opens the issue from JQL Search and launches the visible **Transition** flow
2. verifies the **Current status** field stays at **In Progress**
3. confirms the **Status** dropdown exposes only **To Do** and **Done**
4. selects **Done** and verifies the **Resolution** dropdown appears
5. attempts to save without a resolution and verifies the exact required
   validation message
6. switches back to **To Do** and verifies the **Resolution** field disappears

## Run this test

```bash
flutter test testing/tests/TS-398/test_ts_398.dart
```

## Expected result

```text
Pass: The workflow transition surface shows only To Do and Done as targets,
Done reveals a required Resolution field, and To Do hides it again.

Fail: Additional targets appear, the Resolution field does not behave
conditionally, or the required validation message is missing.
```
