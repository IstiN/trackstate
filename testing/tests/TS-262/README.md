# TS-262

Validates that a disposable pull request touching only `README.md` in
`IstiN/trackstate-setup` does not surface a failing `actionlint` gate. When
GitHub does not show an `actionlint` run or status check for the README-only
PR, the test also proves `actionlint` is not still declared as a required gate.
It only requires an enabled-looking merge surface when no unrelated required
checks are still gating the branch.
