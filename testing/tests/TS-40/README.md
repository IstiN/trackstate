# TS-40

Verifies the local Git mutation flow end-to-end through the Flutter UI.

## Coverage

- opens `DEMO-1` from **JQL Search**
- drags the issue to **Done** on the **Board**
- asserts the exact local Git confirmation banner
- verifies the same user action created exactly one new Git commit
- verifies the commit message, touched files, and saved markdown status
