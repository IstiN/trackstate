# TS-1317

Verifies that the JQL search flow applies the mandatory archived-issue filter
before results are rendered.

The test opens **JQL Search**, submits the active query `search`, and checks
both the captured repository JQL and the visible issue rows to ensure archived
issues do not leak into active search results.

## Run this test

```bash
flutter test testing/tests/TS-1317/test_ts_1317.dart --reporter expanded
```

## Expected result

```text
Pass: the active search request includes an explicit archived exclusion, the
search field preserves the typed query, and only the active issue row remains
visible.
```
