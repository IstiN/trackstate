# TS-1027

Validates the shared stored-workspace runtime helpers that preload saved
workspace state for startup restoration tests.

The automation:
1. verifies the live stored-token factory builds a workspace-aware runtime for
   the hosted setup repository
2. confirms the workspace-profile preload script is injected into both the
   browser context and the already-open page
3. preserves the legacy default that seeds GitHub token storage for every saved
   workspace profile when no explicit workspace ids are supplied
4. seeds restorable local-workspace fixture data only when local handle restore
   is enabled
5. checks the delayed-auth runtime polling helpers and init-script injection for
   startup auth-probe scenarios

## Run this test

```bash
PYTHONPATH=. python3 -m unittest testing.tests.TS-1027.test_stored_workspace_profiles_runtime
```

## Required configuration

No external credentials are required. Run the test from the repository root so
the `testing.*` imports resolve through `PYTHONPATH=.`
