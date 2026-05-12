# TS-459

Verifies that the Jira-compatible hierarchy alias commands map a single
`--parent` input to the canonical `epic` or `parent` field based on the target
issue type.

The automation:
1. seeds a disposable Local Git TrackState repository with `EPIC-1`, `STORY-1`,
   `STORY-2`, and `SUB-1`
2. runs `trackstate jira_create_ticket_with_parent --target local --summary
   "Task" --parent EPIC-1`
3. verifies the returned JSON success envelope reports
   `command: jira-create-ticket-with-parent`, `epic: EPIC-1`, and `parent: null`
4. checks the created issue markdown is written under the canonical Epic
   hierarchy path and visibly shows the canonical hierarchy fields
5. runs `trackstate jira_update_ticket_parent --target local --issueKey SUB-1
   --parent STORY-1`
6. verifies the returned JSON success envelope reports
   `command: jira-update-ticket-parent`, `parent: STORY-1`, and `epic: EPIC-1`
7. confirms the sub-task moves from the original story directory into the
   target story directory and the repository ends with a clean worktree

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-459 -p 'test_ts_459.py' -v
```

## Required environment and config

- No Python packages are required beyond the standard library
- Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN` set to the Dart
  executable used to compile the temporary TrackState CLI
- `git` CLI available on `PATH`

## Expected result

```text
Pass: creating with `--parent EPIC-1` stores the relationship as `epic`,
updating `SUB-1` with `--parent STORY-1` stores the relationship as `parent`,
the returned storage paths match the canonical repository layout, and the old
sub-task path is removed after the move.

Fail: either command does not succeed, the JSON payload exposes the wrong
canonical hierarchy field, the repository files are written to the wrong
location, or the old sub-task path still exists after reassignment.
```
