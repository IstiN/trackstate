from __future__ import annotations

import unittest

from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage


class HostedConnectedSessionDetectionTest(unittest.TestCase):
    def test_hosted_workspace_switcher_state_counts_as_authenticated(self) -> None:
        body_text = (
            "Workspace switcher: istin/trackstate-setup, Hosted, Connected\n"
            "TrackState.AI\n"
            "Git-native. Jira-compatible. Team-proven.\n"
            "Dashboard\n"
            "Board\n"
            "JQL Search\n"
            "Hierarchy\n"
            "Settings\n"
            "Synced with Git\n"
            "Repository Repository Repository istin/trackstate-setup Branch main\n"
            "Workspace switcher\n"
            "Create issue\n"
            "Synced with Git\n"
            "Dark theme\n"
            "ai-teammate\n"
        )

        self.assertTrue(
            TrackStateTrackerPage.body_has_authenticated_session(
                body_text,
                user_login="ai-teammate",
                repository="istin/trackstate-setup",
            ),
            "Hosted sessions that expose the current workspace switcher summary as "
            "`<repository>, Hosted, Connected` must count as authenticated so live "
            "tests can proceed to their actual user flow.\n"
            f"Observed body text:\n{body_text}",
        )


if __name__ == "__main__":
    unittest.main()
