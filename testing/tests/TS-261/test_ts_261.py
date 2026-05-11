from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.config.actionlint_ruleset_enforcement_config import (
    ActionlintRulesetEnforcementConfig,
)
from testing.core.interfaces.actionlint_ruleset_enforcement_probe import (
    ActionlintRulesetEnforcementObservation,
    ActionlintRulesetEnforcementProbe,
)
from testing.tests.support.actionlint_ruleset_enforcement_probe_factory import (
    create_actionlint_ruleset_enforcement_probe,
)


class ActionlintRulesetEnforcementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config_path = self.repository_root / "testing/tests/TS-261/config.yaml"
        self.config = ActionlintRulesetEnforcementConfig.from_file(self.config_path)
        self.probe: ActionlintRulesetEnforcementProbe = (
            create_actionlint_ruleset_enforcement_probe(
                self.repository_root,
                config_path=self.config_path,
            )
        )

    def test_actionlint_is_enforced_by_rulesets_on_all_protected_branches(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-261 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.base_branch,
            "Step 1 failed: TS-261 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.base_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )

        self.assertGreaterEqual(
            len(observation.protected_branches),
            self.config.minimum_protected_branch_count,
            "Step 2 failed: GitHub did not expose the expected number of protected "
            "branches for TS-261.\n"
            f"Expected at least: {self.config.minimum_protected_branch_count}\n"
            f"Observed protected branches: {observation.protected_branches}",
        )
        self.assertIn(
            self.config.base_branch,
            observation.protected_branches,
            "Step 2 failed: the default branch is not currently reported as protected.\n"
            f"Expected protected branch: {self.config.base_branch}\n"
            f"Observed protected branches: {observation.protected_branches}",
        )

        self.assertTrue(
            observation.active_ruleset_ids,
            "Step 3 failed: the repository does not expose any active branch rulesets.\n"
            f"Observed active ruleset names: {observation.active_ruleset_names}",
        )
        self.assertTrue(
            observation.matching_ruleset_ids,
            "Step 4 failed: no active branch ruleset explicitly requires the "
            f"{self.config.expected_actionlint_context} status check.\n"
            f"Observed active rulesets: {observation.active_ruleset_names}\n"
            f"Observed required checks by matching ruleset candidate: "
            f"{observation.matching_ruleset_required_status_checks}",
        )
        for ruleset_name, required_checks in (
            observation.matching_ruleset_required_status_checks.items()
        ):
            self.assertIn(
                self.config.expected_actionlint_context,
                required_checks,
                "Step 5 failed: the active ruleset does not list actionlint in its "
                "required status checks.\n"
                f"Ruleset: {ruleset_name}\n"
                f"Observed required checks: {required_checks}",
            )

        self.assertTrue(
            all(
                include_patterns
                for include_patterns in observation.matching_ruleset_include_patterns.values()
            ),
            "Step 6 failed: the actionlint ruleset did not expose any 'Applied to' "
            "branch patterns.\n"
            f"Observed include patterns: {observation.matching_ruleset_include_patterns}",
        )
        self.assertFalse(
            observation.protected_branches_missing_matching_ruleset_scope,
            "Step 6 failed: the matching ruleset 'Applied to' scope does not cover "
            "every protected branch required by TS-261.\n"
            f"Protected branches: {observation.protected_branches}\n"
            f"Branches missing ruleset scope coverage: "
            f"{observation.protected_branches_missing_matching_ruleset_scope}\n"
            f"Observed include patterns: {observation.matching_ruleset_include_patterns}\n"
            f"Observed exclude patterns: {observation.matching_ruleset_exclude_patterns}\n"
            f"Observed covered branches by ruleset: "
            f"{observation.matching_ruleset_scope_covered_branches}",
        )
        self.assertFalse(
            observation.branches_missing_actionlint_required,
            "Expected-result verification failed: not every protected branch "
            "resolves to an effective actionlint required-status-check rule from "
            "rulesets.\n"
            f"Protected branches: {observation.protected_branches}\n"
            f"Branches missing actionlint: {observation.branches_missing_actionlint_required}\n"
            f"Observed branch contexts: {observation.branch_required_check_contexts}\n"
            f"Observed branch rule descriptions: "
            f"{observation.branch_required_rule_descriptions}\n"
            f"Observed actionlint ruleset ids by branch: "
            f"{observation.branch_actionlint_ruleset_ids}",
        )

        self.assertTrue(
            all(
                ruleset_ids
                for branch_name, ruleset_ids in observation.branch_actionlint_ruleset_ids.items()
                if branch_name in observation.branches_with_actionlint_required
            ),
            "Human-style verification failed: GitHub did not identify a ruleset-backed "
            "source for every protected branch that shows actionlint as required.\n"
            f"Observed actionlint ruleset ids by branch: "
            f"{observation.branch_actionlint_ruleset_ids}",
        )
        self.assertTrue(
            all(url.startswith("https://github.com/") for url in observation.matching_ruleset_urls),
            "Human-style verification failed: the matching ruleset did not expose a "
            "human-viewable GitHub settings URL.\n"
            f"Observed ruleset URLs: {observation.matching_ruleset_urls}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS261_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
