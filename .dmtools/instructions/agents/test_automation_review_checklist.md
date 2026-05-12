# TrackState Test Automation Review Checklist

For TrackState test automation PRs, verify every item in one review pass before deciding the recommendation.

| # | Check |
|---|-------|
| 1 | `testing/tests/{TICKET-KEY}/README.md` exists |
| 2 | `testing/tests/{TICKET-KEY}/config.yaml` exists |
| 3 | Ticket tests do not contain raw `find.*`, `WidgetTester`, `tester.tap()`, or framework locators |
| 4 | Framework files do not import `testing/components/services/` directly |
| 5 | Shared helpers are extracted into neutral helpers/base classes, not borrowed through unrelated inheritance |
| 6 | Dart CLI tests run from repo root and pass target path through `--path` |
| 7 | Precondition checks happen before browser/UI launch |
| 8 | Error assertions cover all expected contract fields, not only `exit_code` |
| 9 | Assertions do not hardcode example strings from tickets unless exact copy is required |
| 10 | Teardown restores all paths the test can create or mutate |
| 11 | CLI command invocation matches the ticket command verbatim |

If any item fails, request changes with an inline comment on the relevant diff line. Search the entire diff for all occurrences of the same pattern before posting the review.
