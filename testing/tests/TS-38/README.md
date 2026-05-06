# TS-38

This test verifies the repository abstraction boundary through a Dart probe that:

1. Instantiates `ProviderBackedTrackStateRepository` with a fake `TrackStateProviderAdapter`.
2. Connects the repository through its public API.
3. Reads the repository's `ProviderSession` contract from the repository instance.
4. Verifies the neutral session fields and capability flags through that contract.

The Python test remains the entrypoint for CI, but it delegates the product-facing assertion to the Dart probe via `testing/core/interfaces/provider_contract_probe.py`.
