# TrackState Test Automation Review Checklist

For TrackState test automation PRs, verify every item in one review pass before deciding the recommendation.

## Quick decision flow

```mermaid
flowchart TD
  PR([Incoming test PR]) --> README{README.md\nIN pr_files.txt?}
  README -->|No| RC1[REQUEST_CHANGES\nMissing README]
  README -->|Yes| YAML{config.yaml\nIN pr_files.txt?}
  YAML -->|No| RC2[REQUEST_CHANGES\nMissing config.yaml]
  YAML -->|Yes| Locator{Raw finder/widget\nin test file diff?}
  Locator -->|Yes| RC3[REQUEST_CHANGES\nMove to Robot/Page]
  Locator -->|No| FwImport{Framework imports\ncomponent services?}
  FwImport -->|Yes| RC4[REQUEST_CHANGES\nUse interface + DI]
  FwImport -->|No| DartCLI{dart run from\nnon-root dir?}
  DartCLI -->|Yes| RC5[REQUEST_CHANGES\nRun from repo root]
  DartCLI -->|No| Pre{Precondition guard\nbefore UI launch?}
  Pre -->|Missing| RC6[REQUEST_CHANGES\nAdd guard]
  Pre -->|Yes| Err{All error contract\nfields asserted?}
  Err -->|No| RC7[REQUEST_CHANGES\nAssert full contract]
  Err -->|Yes| Copy{Exact ticket copy\nin assertion?}
  Copy -->|Yes| RC8[REQUEST_CHANGES\nAssert behavior not text]
  Copy -->|No| Scope{Click scoped to\nvalidated container?}
  Scope -->|No| RC9[REQUEST_CHANGES\nScope to correct container]
  Scope -->|Yes| TD{Teardown covers\nall created paths?}
  TD -->|No| RC10[REQUEST_CHANGES\nInclude all paths]
  TD -->|Yes| Cmd{Verbatim ticket\nCLI command?}
  Cmd -->|No| RC11[REQUEST_CHANGES\nMatch ticket command exactly]
  Cmd -->|Yes| APPROVE([✅ APPROVE])
```

## Checklist table

| # | Check | File to inspect |
|---|-------|----------------|
| 1 | `testing/tests/{TICKET-KEY}/README.md` exists | `pr_files.txt` |
| 2 | `testing/tests/{TICKET-KEY}/config.yaml` exists | `pr_files.txt` |
| 3 | No raw `find.*`, `WidgetTester`, `tester.tap()` in ticket test file | `pr_diff.txt` under `testing/tests/` |
| 4 | No `testing/components/services/` import inside `testing/frameworks/` | `pr_diff.txt` imports |
| 5 | Shared helpers use neutral base class, not unrelated inheritance | `pr_diff.txt` class definitions |
| 6 | Dart CLI tests: `cwd` is repo root, target passed via `--path` | `pr_diff.txt` subprocess calls |
| 7 | Precondition assertion before `driver.get()` / browser launch | `pr_diff.txt` |
| 8 | Error assertions cover all contract fields (not only `exit_code`) | `pr_diff.txt` assert blocks |
| 9 | No exact ticket example strings as assertion values | `pr_diff.txt` `find.text()` / `assert x == '...'` |
| 10 | Click targets scoped to validated container (not rightmost page match) | `pr_diff.txt` page object methods |
| 11 | Teardown deletes ALL paths the test can create, including "should not exist" | `pr_diff.txt` teardown methods |
| 12 | CLI command matches ticket verbatim; files seeded at expected locations | `pr_diff.txt` subprocess args |

**If any item fails → REQUEST_CHANGES with an inline comment on the relevant diff line.**
**Search the entire diff for ALL occurrences of the same pattern before posting the review.**
