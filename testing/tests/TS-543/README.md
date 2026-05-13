# TS-543

Automates the local CLI regression where a release-backed attachment download is
attempted from a repository with no Git remotes configured.

The scenario seeds a disposable Local Git repository whose `attachments.json`
points `TS/TS-123/attachments/manual.pdf` at `github-releases` storage, runs:

```bash
trackstate attachment download --attachment-id TS/TS-123/attachments/manual.pdf --out ./downloads/manual.pdf --target local
```

and verifies the CLI surfaces an explicit GitHub repository identity error
instead of the generic provider capability error, while leaving no downloaded
file or local manifest changes behind.
