# TS-1401 — Runtime variables validation

Validates that the setup-repo smoke pre-flight check detects missing or
malformed runtime configuration. The test confirms that at least one of the
configured auth-token variables is present and that the absence of all tokens
is reported as a failure.
