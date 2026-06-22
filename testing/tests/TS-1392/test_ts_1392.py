from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GITHUB_SKILL_PATH = REPO_ROOT / "assets" / "assistant" / "trackstate-github.skill"
CLAUDE_SKILL_PATH = REPO_ROOT / "assets" / "assistant" / "trackstate-claude.skill"
MANIFEST_DART_PATH = REPO_ROOT / "lib" / "cli" / "assistant_manifests.dart"

REQUIRED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "name",
    "id",
    "assistant",
    "description",
    "install",
    "invocation",
    "runtime",
}
REQUIRED_INSTALL_KEYS = {"command", "commandWindows", "shell", "docs"}
REQUIRED_INVOCATION_KEYS = {"commandPath", "description", "examples"}
REQUIRED_RUNTIME_KEYS = {"authSource", "target", "provider", "repository"}


def _load_skill(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _extract_manifest_constant(dart_source: str, constant_name: str) -> str:
    pattern = rf"const String {constant_name} = r'''(.*?)''';"
    match = re.search(pattern, dart_source, re.DOTALL)
    if not match:
        raise AssertionError(
            f"Could not find manifest constant {constant_name} in {MANIFEST_DART_PATH}"
        )
    return match.group(1)


class AssistantSkillManifestAssetsTest(unittest.TestCase):
    def test_github_skill_file_exists_and_is_valid_json(self) -> None:
        self.assertTrue(
            GITHUB_SKILL_PATH.exists(),
            f"GitHub skill manifest not found at {GITHUB_SKILL_PATH}",
        )
        manifest = _load_skill(GITHUB_SKILL_PATH)
        self.assertIsInstance(manifest, dict)
        missing = REQUIRED_TOP_LEVEL_KEYS - manifest.keys()
        self.assertFalse(
            missing,
            f"GitHub skill manifest missing top-level keys: {missing}",
        )
        self.assertEqual(manifest["id"], "trackstate-github")
        self.assertEqual(manifest["assistant"], "github")
        self._assert_install_block(manifest["install"], "github")
        self._assert_invocation_block(manifest["invocation"], "github")
        self._assert_runtime_block(manifest["runtime"])

    def test_claude_skill_file_exists_and_is_valid_json(self) -> None:
        self.assertTrue(
            CLAUDE_SKILL_PATH.exists(),
            f"Claude skill manifest not found at {CLAUDE_SKILL_PATH}",
        )
        manifest = _load_skill(CLAUDE_SKILL_PATH)
        self.assertIsInstance(manifest, dict)
        missing = REQUIRED_TOP_LEVEL_KEYS - manifest.keys()
        self.assertFalse(
            missing,
            f"Claude skill manifest missing top-level keys: {missing}",
        )
        self.assertEqual(manifest["id"], "trackstate-claude")
        self.assertEqual(manifest["assistant"], "claude")
        self._assert_install_block(manifest["install"], "claude")
        self._assert_invocation_block(manifest["invocation"], "claude")
        self._assert_runtime_block(manifest["runtime"])

    def test_skill_files_match_in_code_manifest_constants(self) -> None:
        self.assertTrue(
            MANIFEST_DART_PATH.exists(),
            f"Dart manifest source not found at {MANIFEST_DART_PATH}",
        )
        dart_source = MANIFEST_DART_PATH.read_text(encoding="utf-8")

        github_from_code = json.loads(
            _extract_manifest_constant(dart_source, "trackStateGitHubAssistantManifest")
        )
        claude_from_code = json.loads(
            _extract_manifest_constant(dart_source, "trackStateClaudeAssistantManifest")
        )

        self.assertEqual(
            _load_skill(GITHUB_SKILL_PATH),
            github_from_code,
            "The published GitHub skill file does not match the in-code manifest constant.",
        )
        self.assertEqual(
            _load_skill(CLAUDE_SKILL_PATH),
            claude_from_code,
            "The published Claude skill file does not match the in-code manifest constant.",
        )

    def _assert_install_block(
        self, install: object, assistant: str
    ) -> None:
        self.assertIsInstance(install, dict)
        assert isinstance(install, dict)
        missing = REQUIRED_INSTALL_KEYS - install.keys()
        self.assertFalse(
            missing,
            f"{assistant} install block missing keys: {missing}",
        )
        self.assertIn("curl -fsSL", install["command"])
        self.assertIn("install.sh", install["command"])
        self.assertIn("irm", install["commandWindows"])
        self.assertIn("install.ps1", install["commandWindows"])
        self.assertIn("releases/latest", install["docs"])

    def _assert_invocation_block(
        self, invocation: object, assistant: str
    ) -> None:
        self.assertIsInstance(invocation, dict)
        assert isinstance(invocation, dict)
        missing = REQUIRED_INVOCATION_KEYS - invocation.keys()
        self.assertFalse(
            missing,
            f"{assistant} invocation block missing keys: {missing}",
        )
        self.assertEqual(
            invocation["commandPath"],
            f"trackstate assistant {assistant}",
        )
        self.assertIsInstance(invocation["examples"], list)
        assert isinstance(invocation["examples"], list)
        self.assertTrue(
            invocation["examples"],
            f"{assistant} invocation examples should not be empty.",
        )

    def _assert_runtime_block(self, runtime: object) -> None:
        self.assertIsInstance(runtime, dict)
        assert isinstance(runtime, dict)
        missing = REQUIRED_RUNTIME_KEYS - runtime.keys()
        self.assertFalse(
            missing,
            f"runtime block missing keys: {missing}",
        )
        self.assertEqual(runtime["target"], "hosted")
        self.assertEqual(runtime["provider"], "github")
        self.assertIn("__REPO_PLACEHOLDER__", runtime["repository"])


if __name__ == "__main__":
    unittest.main()
