# Bug Test Automation Scope Override

Applies to `bug_test_automation` and `bug_test_automation_rework` runs.

## Scope rule

A Bug ticket usually `Blocks` the failing Test Case that exposed the bug and also `Relates to` many other Test Cases. You must **NOT** run every related Test Case.

Only verify the Test Case(s) that the Bug **blocks** (the regression target). If the blocked Test Case is missing an automated test, create one that is narrowly focused on the bug reproduction and the fix.

## What to skip

- Do not run existing passing Test Cases that are only `Relates to` the Bug.
- Do not create new tests for `Relates to` Test Cases unless they are the actual failing scenario.
- Do not execute broad bulk suites for the Bug branch.

## Output

Write the usual `outputs/story_test_automation_result.json`, `outputs/tracker_comment.md`, and `outputs/failed_description_{TC_KEY}.md` only for the blocked Test Case(s) you verified.
