# TS-501 test automation

Validates that the first attachment uploaded to an attachment-free live issue
creates a machine-managed draft GitHub Release container on the active write
branch.

## Probe runtime

The Python wrapper runs a Dart probe in `testing/tests/TS-501/dart_probe/` that
uses the production `ProviderBackedTrackStateRepository` and
`GitHubTrackStateProvider` against the live setup repository.

## Required environment and config

- Python 3.12+
- Dart runtime is bootstrapped automatically by `PythonDartProbeRuntime`
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Scenario notes

- The test reuses the live `attachmentStorage.mode = github-releases`
  configuration already present in `DEMO/project.json`, uses the stable
  attachment-free live issue `DEMO-4`, and uploads the first attachment through
  the production provider-backed repository path.
- A passing result means the upload updates `attachments.json` with one
  `github-releases` entry and the created release is a draft with the expected
  `target_commitish` and standardized machine-generated body text.
- A failing result is valid evidence when the hosted product creates the release
  on the wrong branch, publishes it instead of keeping it draft, or writes the
  wrong release body.
