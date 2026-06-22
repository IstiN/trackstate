# TS-1404 — CLI performance benchmark

Runs 10 concurrent TrackState CLI processes against the hosted setup repository
and verifies that the error rate is zero and the p95 latency stays within the
configured budget.
