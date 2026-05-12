# TrackState Test Automation Hardening Rules

These rules are TrackState-specific and are injected from `.dmtools/config.js`.
The shared `agents/` submodule must remain project-independent.

## Mandatory rules

1. Create `testing/tests/{TICKET-KEY}/README.md` before writing test code. Include dependency setup, the exact run command, required environment/config, and expected output.
2. Keep raw Flutter widget/finder logic out of ticket tests. Put `WidgetTester`, `Finder`, `find.*`, `tester.tap()`, and similar details behind Robot classes in `testing/components/screens/`.
3. Do not import or instantiate `testing/components/services/` from `testing/frameworks/`. Define contracts in `testing/core/interfaces/` and inject concrete clients through constructors/factories.
4. Do not inherit from an unrelated framework only to reuse helper methods. Extract shared CLI/file/git helpers into a neutral base/helper class.
5. Run TrackState Dart CLI tests from the repository root with `dart run trackstate <command>`. Pass target repositories through `--path`; never rely on `cwd` for package resolution.
6. Validate every fixture precondition before opening a browser or launching a UI flow. Fixture-data failures must be distinguishable from product defects.
7. When testing error cases, assert the full machine-readable error contract, including nested `error.exitCode`/`error.code` fields, not only the process exit code.
8. Do not hardcode example text from Jira tickets as exact assertions unless the product spec explicitly requires that exact copy. Assert behavior, accessibility, contrast, or visible placeholder presence instead.
9. Teardown must restore every path or artifact the test can create, including paths that should not exist if the product behaves correctly.
10. If a ticket specifies a CLI command, execute that command verbatim. Seed files or adjust setup so command arguments match the ticket exactly.

## Review patterns to avoid

- Missing `README.md` beside `config.yaml`
- Ticket test directly using Flutter locators instead of a Robot
- Framework code depending upward on component services
- Ambiguous product failures caused by missing live fixture data
- Tests passing after only the process exit code is fixed while JSON error fields stay wrong
- Cleanup that leaves attachments/comments/files behind after an unexpected product success
