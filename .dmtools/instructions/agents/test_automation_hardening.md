# TrackState Test Automation Hardening Rules

Injected via `.dmtools/config.js → additionalInstructions`. The shared `agents/` submodule stays project-independent.

## Architecture — required layer order

```mermaid
graph TD
  T["tests/{TICKET-KEY}/\ntest_*.py / test_*.dart"] --> C["components/\npages · screens · services"]
  C --> F["frameworks/\nPlaywright · Appium · Python CLI"]
  F --> Core["core/\ninterfaces · models · config · utils"]
  T -. must not import .-> F
  C -. must not import .-> T
  F -. must not import .-> C
```

## Pre-submission checklist (verify ALL before opening PR)

```mermaid
flowchart TD
  A([Start]) --> R{README.md\nexists?}
  R -->|No| FAIL1[❌ Create it first]
  R -->|Yes| Cfg{config.yaml\nexists?}
  Cfg -->|No| FAIL2[❌ Add config.yaml]
  Cfg -->|Yes| Layer{Raw finder/\nwidget calls in\nticket test?}
  Layer -->|Yes| FAIL3[❌ Move to Robot/Page class]
  Layer -->|No| Import{Framework imports\ncomponent service?}
  Import -->|Yes| FAIL4[❌ Use interface + DI]
  Import -->|No| CLI{Dart CLI test\nrun from wrong dir?}
  CLI -->|Yes| FAIL5[❌ Run from repo root\nuse --path flag]
  CLI -->|No| Ctrl{UI upload controls\nvisible & enabled?}
  Ctrl -->|Not asserted| FAIL5B[❌ Assert controls before using them]
  Ctrl -->|Yes| Pre{Precondition guard\nbefore UI launch?}
  Pre -->|No| FAIL6[❌ Add assertion before browser.get]
  Pre -->|Yes| Err{Error contract\nfully asserted?}
  Err -->|No| FAIL7[❌ Assert all error fields\nnot just exit_code]
  Err -->|Yes| Copy{Exact ticket text\nas assertion?}
  Copy -->|Yes| FAIL8[❌ Assert behavior not copy]
  Copy -->|No| TD{Teardown restores\noriginal fixture state?}
  TD -->|No| FAIL9[❌ Restore deleted live fixtures;\ndon't leave orphaned assets]
  TD -->|Yes| Cmd{CLI command matches\nticket verbatim?}
  Cmd -->|No| FAIL10[❌ Seed files so exact command works]
  Cmd -->|Yes| OK([✅ Ready to open PR])
```

## Rule reference

| # | Rule | Common mistake |
|---|------|---------------|
| 1 | `README.md` before test code | Missing beside `config.yaml` |
| 2 | No raw Flutter/widget locators in ticket test | `find.widgetWithText` directly in `test_ts_XXX.dart` |
| 3 | Frameworks never import component services | `from testing.components.services.X import X` inside framework file |
| 4 | Shared helpers in neutral base class | Inheriting unrelated framework for its helpers |
| 5 | Dart CLI: run from repo root, `--path` for target | `cwd=/tmp/empty` breaks package resolution |
| 6 | Assert UI controls visible+enabled **before** using them | `choose_button_count` recorded but step passes when count=0 |
| 7 | Precondition guard before UI | No `assert len(attachments) >= 2` before `driver.get()` |
| 8 | Assert full error contract | Only `exit_code` checked, `error.exitCode` ignored |
| 9 | No exact ticket example strings | `find.text('Add a comment...')` verbatim |
| 10 | Teardown fully restores pre-existing fixtures | Original release deleted in setup, never recreated in teardown |
| 11 | Verbatim CLI command from ticket | Files seeded at `files/` subdir instead of repo root |

## Teardown & fixture isolation rules

```mermaid
flowchart TD
  Setup([Setup / _seed_fixture]) --> Exists{Pre-existing live\nfixture at same tag?}
  Exists -->|Yes| Capture[Capture full fixture:\nrelease + all assets]
  Exists -->|No| CreateIsolated[Create isolated fixture\nwith unique tag]
  Capture --> Run
  CreateIsolated --> Run([Run test])
  Run --> TD([Teardown])
  TD --> WasExisting{Was pre-existing\nfixture deleted?}
  WasExisting -->|Yes| Restore[Recreate original release\n+ restore all assets\nor raise error if impossible]
  WasExisting -->|No| Delete[Delete only test-created data]
  Restore --> Done([✅ Done])
  Delete --> Done
```

Key rules:
- **Never delete a live fixture** unless you capture it fully and can restore it exactly.
- Prefer an **isolated tag** (e.g. `test-ts-XXX-teardown`) that does not collide with seeded data.
- If teardown cannot restore original state, the test must fail loudly rather than leave the repo in a broken state.
- Teardown must cover ALL paths the test may create, including paths that "should not exist" on the success path.

When a test step records multiple matching elements, scope subsequent clicks to the **specific container** validated in the previous step — do not rely on a rightmost/last match across the whole page:

```python
# ❌ WRONG — clicks rightmost matching button on whole page
button = page.get_by_text("Open settings").last

# ✅ CORRECT — scoped to the gate callout validated in Step 3
button = gate_callout.get_by_role("button", name="Open settings")
```

## Review patterns to avoid

- Missing `README.md` beside `config.yaml`
- Ticket test directly using Flutter locators instead of a Robot
- Framework code depending upward on component services
- Ambiguous product failures caused by missing live fixture data
- Tests passing after only the process exit code is fixed while JSON error fields stay wrong
- Cleanup that leaves attachments/comments/files behind after unexpected product success
- Asserting exact UI copy that the ticket only uses as an example
