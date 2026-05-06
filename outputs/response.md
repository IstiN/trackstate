## Issues/Notes

- Repository-root `instruction.md` was not present, so implementation followed the ticket inputs under `input/TS-23/` plus the existing repository/workflow conventions.
- The GitHub App path is documented as an **optional user-scoped broker flow** with `Metadata: Read-only` and `Contents: Read and write`, matching the answered PO clarifications instead of implying installation-token support.

## Approach

Refreshed the `trackstate-setup` template as a web-first fork-and-run package with explicit onboarding for auth, Pages deployment, editable tracker metadata, CLI handoff, and attachment/LFS expectations.

Expanded the setup template's machine-readable contract in `project-template.json`, enriched the demo project with a dedicated onboarding/configuration story plus links and attachment placeholders, and tightened the runtime integration by making `SetupTrackStateRepository` honor `project.json.configPath` instead of assuming `config/`.

Kept the setup workflow deployment-focused by removing the stale top-level `config/**` path trigger and continuing to deploy only from source-built Pages artifacts.

## Files Modified

- `.gitignore` - ignores task-generated `input/` and `cacheBasicJiraClient/` directories so automated staging does not pick them up.
- `lib/data/repositories/trackstate_repository.dart` - reads `configPath` from setup `project.json` and resolves config files from the declared location.
- `test/trackstate_repository_test.dart` - adds coverage for `configPath`-aware setup repository loading.
- `test/setup_template_contract_test.dart` - adds file-based contract tests for setup metadata, onboarding docs, and demo structure.
- `trackstate-setup/.github/workflows/install-update-trackstate.yml` - removes the stale `config/**` push trigger and keeps the workflow scoped to deploy-relevant changes.
- `trackstate-setup/README.md` - rewrites onboarding docs for PAT auth, optional GitHub App broker auth, required permissions, editable config locations, CLI handoff, Pages deployment, and Git LFS expectations.
- `trackstate-setup/project-template.json` - records source/data/config paths, editable config files, auth requirements, and Pages behavior in a machine-readable template contract.
- `trackstate-setup/DEMO/project.json` - adds a project description while keeping `configPath` explicit.
- `trackstate-setup/DEMO/config/fields.json` - expands sample fields to cover reporter, components, fix versions, hierarchy fields, and attachments.
- `trackstate-setup/DEMO/config/components.json` - adds setup-template and CLI/JSON compatibility sample components.
- `trackstate-setup/DEMO/config/versions.json` - expands sample release metadata.
- `trackstate-setup/DEMO/config/i18n/en.json` - broadens the example language pack to cover more issue types, fields, and priorities.
- `trackstate-setup/DEMO/DEMO-1/main.md` - updates the onboarding epic description to mention auth and Git-backed metadata.
- `trackstate-setup/DEMO/DEMO-1/DEMO-5/main.md` - new onboarding story for auth and metadata setup.
- `trackstate-setup/DEMO/DEMO-1/DEMO-5/acceptance_criteria.md` - sample acceptance criteria for setup onboarding.
- `trackstate-setup/DEMO/DEMO-1/DEMO-5/comments/0001.md` - sample comment history for the onboarding story.
- `trackstate-setup/DEMO/DEMO-1/DEMO-5/links.md` - sample non-hierarchy issue links.
- `trackstate-setup/DEMO/DEMO-1/DEMO-5/attachments/README.md` - attachment placeholder documenting Git LFS usage without adding sample binaries.

## Test Coverage

- Added a repository test that verifies setup loading honors `project.json.configPath`.
- Added setup-template contract tests that validate:
  - machine-readable auth/config metadata in `trackstate-setup/project-template.json`
  - required onboarding content in `trackstate-setup/README.md`
  - demo sample presence for comments, links, and attachment guidance
- Re-ran the existing Flutter analyze, widget/golden/unit test suite, and web build after the changes.
