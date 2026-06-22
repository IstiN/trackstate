# TS-1395 — Documentation Synchronization

Verifies the repository README mirrors the install scripts and links to the setup repository documentation.

## Run this test

```bash
python -m unittest testing.tests.TS-1395.test_ts_1395 -v
```

## What is tested

- README contains the Linux/macOS, PowerShell, and Command Prompt install commands.
- README references the assistant install surface and the `trackstate assistant github` / `trackstate assistant claude` command paths.
- README links to the `IstiN/trackstate-setup` fork-and-run setup repository.
- README install snippets match the commands documented in the install scripts.
