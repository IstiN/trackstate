# TS-887

Reproduces the deployed hosted **Edit issue** Summary validation accessibility
scenario from the user's perspective.

The automation:
1. opens the live hosted TrackState app
2. connects the session with the configured GitHub token
3. opens the live **Edit issue** surface for `DEMO-2`
4. attempts to clear the visible `Summary` field
5. fails immediately if the production UI does not allow the user to perform
   that first required action
6. when the field is editable, clicks **Save** and verifies visible
   feedback containing `Summary is required`
7. checks that the visible validation text meets WCAG AA contrast
8. checks that the validation state exposes an accessibility announcement path

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-887/test_ts_887.py
```

## Expected result

```text
Pass: the Summary field is editable, the user can clear it, and the hosted Edit
issue dialog exposes the required validation, contrast, and accessibility
feedback after Save.

Fail: the deployed Edit issue surface renders Summary as non-editable/disabled,
so the user cannot trigger the required validation feedback scenario, or the
later validation/contrast/accessibility checks fail once Save is clicked.
```
