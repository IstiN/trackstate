# GitHub App token for SM Agent

The SM Agent polls GitHub Actions for active workflow runs and dispatches new `ai-teammate.yml` runs. With a personal access token (PAT) this quickly exhausts the user-level 5 000 req/hour GitHub API rate limit, causing the long `Waiting 60000 ms before retry` pauses seen in the SM logs.

A GitHub App installation token has its own rate limit bucket (15 000 req/hour for most endpoints) and is short-lived, so it is a better fit for SM.

## What changed

`.github/workflows/sm.yml` now optionally generates a GitHub App token before checking out the repository. If the App credentials are not configured, it falls back to `secrets.PAT_TOKEN`, so existing runs keep working until you finish the setup.

## Required secrets / variables

| Name | Type | Value |
|---|---|---|
| `SM_GITHUB_APP_ID` | Repository variable (recommended) or secret | The numeric App ID from the GitHub App settings page. Not sensitive. |
| `SM_GITHUB_APP_PRIVATE_KEY` | Repository secret | The full contents of the generated `.pem` private key file. |

No installation-ID secret is required — `actions/create-github-app-token` derives it from the repository owner.

## Creating the GitHub App

1. Open GitHub → Settings → Developer settings → GitHub Apps → **New GitHub App**.
2. Fill in:
   * **GitHub App name**: `TrackState SM Bot` (or any unique name).
   * **Homepage URL**: `https://github.com/IstiN/trackstate`.
   * **Webhook**: **Disable** (uncheck "Active").
3. Set repository permissions:
   * **Actions**: `Read and write` — list workflow runs and dispatch workflows.
   * **Checks**: `Read-only` — read CI check runs before merging PRs.
   * **Commit statuses**: `Read-only` — read legacy CI statuses.
   * **Contents**: `Read and write` — checkout with submodules and merge PRs.
   * **Metadata**: `Read-only` (default).
   * **Pull requests**: `Read and write` — review/merge/label PRs via SM rules.
4. **Where can this GitHub App be installed?**: choose `Only on this account` (for `IstiN`) or `Any account`, whichever matches your org policy.
5. Click **Create GitHub App**.
6. On the app settings page:
   * note the **App ID**;
   * scroll to **Private keys** and click **Generate a private key**. A `.pem` file downloads — copy its entire contents.
7. Install the app:
   * click **Install App**;
   * select the `IstiN` organization / account;
   * choose only the `trackstate` repository.

## Adding the secrets

1. Go to `https://github.com/IstiN/trackstate/settings/secrets/actions`.
2. Create `SM_GITHUB_APP_ID` with the App ID.
3. Create `SM_GITHUB_APP_PRIVATE_KEY` with the full PEM text (including the `-----BEGIN`/`-----END` lines).

## Verification

Trigger SM manually or wait for the next `workflow_run` event. In the SM Agent run logs you should see:

```text
Run actions/create-github-app-token@v1
...
Run SM Agent
```

and the subsequent GitHub API calls should no longer show rate-limit errors for user ID `236856673`.

## Using the same app for AI Teammate

The AI Teammate workflow makes a large number of GitHub API calls on behalf of
the test probes (e.g. `gh api` against `ai-teammate/trackstate-setup`). With a
PAT this shares the same 5 000 req/hour user bucket and quickly exhausts it.

The same GitHub App can be used there:

1. Install the app on the `ai-teammate` account and grant it access to the
   `trackstate-setup` repository. It needs **Actions** `Read and write` and
   **Contents** `Read and write` so the probes can enable Actions, dispatch
   workflows, and read repository state.
2. In `https://github.com/IstiN/trackstate/settings/variables/actions`, create
   `AI_TEAMMATE_GITHUB_APP_ENABLED` and set it to `true`.
3. The workflow will now generate two short-lived App tokens:
   * one for `IstiN/trackstate` (for DMTools/source-repo operations), and
   * one for `ai-teammate/trackstate-setup` (for the test probes).

If the variable is missing or the app is not installed, the workflow falls back
to `secrets.PAT_TOKEN` automatically.

## Rolling back

If anything goes wrong, simply delete the two secrets (or set them to empty values) and/or remove the `AI_TEAMMATE_GITHUB_APP_ENABLED` variable. The workflows will then fall back to `secrets.PAT_TOKEN` automatically.
