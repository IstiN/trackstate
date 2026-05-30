from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from testing.tests.support.delayed_auth_workspace_profiles_runtime import (
    DelayedAuthWorkspaceProfilesRuntime,
)
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)
from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
    WorkspaceProfilesRuntime,
    _build_preload_script,
    _workspace_token_storage_keys,
)
from testing.core.config.live_setup_test_config import LiveSetupTestConfig


class _FakeScriptTarget:
    def __init__(self) -> None:
        self.scripts: list[str] = []
        self.events: list[tuple[str, object]] = []

    def add_init_script(self, *, script: str) -> None:
        self.scripts.append(script)

    def on(self, event: str, callback: object) -> None:
        self.events.append((event, callback))


class _FakeRuntimeSession:
    pass


class _FakePollingPage:
    def __init__(self, *, on_wait: callable | None = None) -> None:
        self.wait_calls: list[int] = []
        self._on_wait = on_wait

    def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_calls.append(timeout_ms)
        if self._on_wait is not None:
            self._on_wait()


class StoredWorkspaceProfilesRuntimeRegressionTest(unittest.TestCase):
    def test_live_tracker_factory_bootstraps_workspace_aware_stored_token_runtime(
        self,
    ) -> None:
        config = LiveSetupTestConfig(
            app_url="https://example.test/trackstate/",
            repository="IstiN/trackstate-setup",
            ref="main",
        )

        context = create_live_tracker_app_with_stored_token(config, token="token")
        runtime = context._runtime_factory()

        self.assertIsInstance(
            runtime,
            StoredWorkspaceProfilesRuntime,
            "Live stored-token flows must preload hosted workspace state so the app "
            "restores the correct repository session on first load.",
        )
        self.assertEqual(
            runtime._workspace_token_profile_ids,
            ("hosted:istin/trackstate-setup@main",),
        )
        self.assertEqual(
            runtime._workspace_state,
            {
                "activeWorkspaceId": "hosted:istin/trackstate-setup@main",
                "migrationComplete": True,
                "profiles": [
                    {
                        "id": "hosted:istin/trackstate-setup@main",
                        "displayName": "",
                        "targetType": "hosted",
                        "target": "IstiN/trackstate-setup",
                        "defaultBranch": "main",
                        "writeBranch": "main",
                    },
                ],
            },
        )

    def test_live_tracker_factory_preserves_custom_viewport_for_stored_token_runtime(
        self,
    ) -> None:
        config = LiveSetupTestConfig(
            app_url="https://example.test/trackstate/",
            repository="IstiN/trackstate-setup",
            ref="main",
        )

        context = create_live_tracker_app_with_stored_token(
            config,
            token="token",
            viewport_width=1024,
            viewport_height=768,
        )
        runtime = context._runtime_factory()

        self.assertIsInstance(runtime, StoredWorkspaceProfilesRuntime)
        self.assertEqual(runtime._viewport_width, 1024)
        self.assertEqual(runtime._viewport_height, 768)

    def test_workspace_profiles_runtime_applies_preload_script_to_existing_page(self) -> None:
        runtime = WorkspaceProfilesRuntime(
            workspace_state={"activeWorkspaceId": "hosted:repo@main", "profiles": []},
        )
        runtime._context = _FakeScriptTarget()
        runtime._page = _FakeScriptTarget()
        expected_script = _build_preload_script(runtime._workspace_state)

        with patch(
            "testing.tests.support.stored_workspace_profiles_runtime.PlaywrightWebAppRuntime.__enter__",
            return_value=_FakeRuntimeSession(),
        ):
            session = runtime.__enter__()

        self.assertIsInstance(session, _FakeRuntimeSession)
        self.assertEqual(runtime._context.scripts, [expected_script])
        self.assertEqual(
            runtime._page.scripts,
            [expected_script],
            "Workspace profile preload must be injected into the already-open page "
            "as well as the context so the current tab sees saved workspace state.",
        )

    def test_stored_workspace_profiles_runtime_applies_preload_script_to_existing_page(
        self,
    ) -> None:
        runtime = StoredWorkspaceProfilesRuntime(
            repository="IstiN/trackstate-setup",
            token="token",
            workspace_state={
                "activeWorkspaceId": "local:/tmp/demo@main",
                "profiles": [
                    {"id": "local:/tmp/demo@main"},
                    {"id": "hosted:istin/trackstate-setup@main"},
                ],
            },
            workspace_token_profile_ids=("local:/tmp/demo@main",),
        )
        runtime._context = _FakeScriptTarget()
        runtime._page = _FakeScriptTarget()
        expected_script = _build_preload_script(
            runtime._workspace_state,
            repository=runtime._repository,
            token=runtime._token,
            workspace_token_profile_ids=runtime._workspace_token_profile_ids,
        )

        with patch(
            "testing.tests.support.stored_workspace_profiles_runtime.PlaywrightStoredTokenWebAppRuntime.__enter__",
            return_value=_FakeRuntimeSession(),
        ):
            session = runtime.__enter__()

        self.assertIsInstance(session, _FakeRuntimeSession)
        self.assertEqual(runtime._context.scripts, [expected_script])
        self.assertEqual(
            runtime._page.scripts,
            [expected_script],
            "Stored workspace preload must be injected into the current page or "
            "browser tests miss saved workspace state during the first load.",
        )

    def test_workspace_token_storage_keys_default_to_all_workspace_profiles(self) -> None:
        keys = _workspace_token_storage_keys(
            {
                "activeWorkspaceId": "local:/tmp/demo@main",
                "profiles": [
                    {"id": "local:/tmp/demo@main"},
                    {"id": "hosted:istin/trackstate-setup@main"},
                ],
            },
        )

        self.assertEqual(
            keys,
            [
                "trackstate.githubToken.workspace.local%3A%2Ftmp%2Fdemo%40main",
                "flutter.trackstate.githubToken.workspace.local%3A%2Ftmp%2Fdemo%40main",
                "trackstate.githubToken.workspace.hosted%3Aistin%2Ftrackstate-setup%40main",
                "flutter.trackstate.githubToken.workspace.hosted%3Aistin%2Ftrackstate-setup%40main",
            ],
            "When callers omit workspace_token_profile_ids, the shared runtime "
            "must preserve the legacy default of seeding every saved workspace "
            "token key so startup restore tests still exercise the real auth path.",
        )

    def test_preload_script_seeds_restorable_local_workspace_fixture_for_existing_path(
        self,
    ) -> None:
        with TemporaryDirectory() as workspace_dir:
            workspace_path = Path(workspace_dir)
            project_dir = workspace_path / "DEMO" / "config"
            project_dir.mkdir(parents=True, exist_ok=True)
            (workspace_path / "project.json").write_text(
                '{"key":"DEMO","name":"Demo","repository":"local/demo","branch":"main"}\n',
                encoding="utf-8",
            )
            (project_dir / "statuses.json").write_text("[]\n", encoding="utf-8")

            script = _build_preload_script(
                {
                    "activeWorkspaceId": f"local:{workspace_dir}@main",
                    "profiles": [
                        {
                            "id": f"local:{workspace_dir}@main",
                            "targetType": "local",
                            "target": workspace_dir,
                            "defaultBranch": "main",
                            "writeBranch": "main",
                        },
                    ],
                },
            )

        self.assertIn("localWorkspaceFixtures", script)
        self.assertIn("__trackstateStoredWorkspaceRuntimeFixtureHandles", script)
        self.assertIn("IDBObjectStore.prototype.get", script)
        self.assertIn(workspace_dir, script)

    def test_preload_script_skips_local_workspace_fixture_when_restore_is_disabled(
        self,
    ) -> None:
        with TemporaryDirectory() as workspace_dir:
            script = _build_preload_script(
                {
                    "activeWorkspaceId": f"local:{workspace_dir}@main",
                    "profiles": [
                        {
                            "id": f"local:{workspace_dir}@main",
                            "targetType": "local",
                            "target": workspace_dir,
                            "defaultBranch": "main",
                            "writeBranch": "main",
                        },
                    ],
                },
                restore_local_workspace_handles=False,
            )

        self.assertNotIn("localWorkspaceFixtures", script)
        self.assertNotIn("__trackstateStoredWorkspaceRuntimeFixtureHandles", script)
        self.assertNotIn("IDBObjectStore.prototype.get", script)

    def test_delayed_auth_runtime_wait_polls_page_until_probe_event_arrives(self) -> None:
        runtime = DelayedAuthWorkspaceProfilesRuntime(
            repository="IstiN/trackstate-setup",
            token="token",
            workspace_state={"activeWorkspaceId": None, "profiles": []},
            auth_delay_seconds=5,
        )

        def release_wait() -> None:
            runtime._auth_request_started.set()

        runtime._page = _FakePollingPage(on_wait=release_wait)

        started = runtime.wait_for_auth_probe_start(timeout_seconds=0.25)

        self.assertTrue(started)
        self.assertGreaterEqual(len(runtime._page.wait_calls), 1)
        self.assertTrue(runtime._auth_request_started.is_set())

    def test_delayed_auth_runtime_applies_fetch_delay_script_to_existing_page(self) -> None:
        runtime = DelayedAuthWorkspaceProfilesRuntime(
            repository="IstiN/trackstate-setup",
            token="token",
            workspace_state={"activeWorkspaceId": None, "profiles": []},
            auth_delay_seconds=5,
            delayed_paths=("/user", "/viewer"),
        )
        runtime._context = _FakeScriptTarget()
        runtime._page = _FakeScriptTarget()

        with patch(
            "testing.tests.support.delayed_auth_workspace_profiles_runtime.StoredWorkspaceProfilesRuntime.__enter__",
            return_value=_FakeRuntimeSession(),
        ):
            session = runtime.__enter__()

        self.assertIsInstance(session, _FakeRuntimeSession)
        self.assertEqual(len(runtime._context.scripts), 1)
        self.assertEqual(runtime._context.scripts, runtime._page.scripts)
        delayed_script = runtime._context.scripts[0]
        self.assertIn("__trackstateDelayedAuthStart__", delayed_script)
        self.assertIn("__trackstateDelayedAuthRelease__", delayed_script)
        self.assertIn("/user", delayed_script)
        self.assertIn("/viewer", delayed_script)
        self.assertEqual(
            runtime._page.events,
            [("console", runtime._handle_console_message)],
            "The delayed auth runtime must subscribe the live page to console "
            "events so delayed fetch start/release signals update the runtime state.",
        )


if __name__ == "__main__":
    unittest.main()
