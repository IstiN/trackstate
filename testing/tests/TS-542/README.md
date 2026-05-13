# TS-542

Verifies that a local release-backed `trackstate attachment download --target local`
run resolves GitHub repository identity from a configured `upstream` remote even
when `origin` points to a non-GitHub host.

The ticket wording uses the older `--issue` / `--file` download syntax. The live
CLI now supports only `--attachment-id` and `--out`, so the automation executes
that supported equivalent while preserving the original scenario:

1. create a disposable local TrackState repository with `origin` on GitLab and
   `upstream` on GitHub;
2. seed `attachments.json` with `TS/TS-123/attachments/manual.pdf` backed by a
   public GitHub Release asset;
3. run `trackstate attachment download --attachment-id TS/TS-123/attachments/manual.pdf --out ./downloads/manual.pdf --target local`;
4. verify the command succeeds, the saved file matches the live release asset,
   and the caller-visible result shows the local download path instead of a
   provider-capability failure.
