# TS-1004

Verifies that the production workspace sync pill keeps its visible label concise
while exposing the fuller accessibility context through semantics when the app is
in the hosted `Attention needed` sync-error state.

The automation only passes when the same top-bar pill simultaneously shows:
1. visible text exactly `Attention needed`, and
2. semantics exactly `Sync error, attention needed`.

## Install dependencies

No additional dependencies are required beyond the repository Flutter toolchain.

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-1004/test_ts_1004.dart --reporter expanded
```

## Expected behavior

The test should reproduce the real production-visible sync error state and either:
1. pass when the visible pill text stays concise and the semantics label keeps the
   required sync-error context, or
2. fail with recorded evidence of the product regression.
