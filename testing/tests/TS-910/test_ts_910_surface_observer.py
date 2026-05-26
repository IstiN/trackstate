from __future__ import annotations

import unittest

from testing.components.pages.live_workspace_switcher_page import (
    _merge_surface_payload_items,
)


class WorkspaceSwitcherSurfaceObserverTest(unittest.TestCase):
    def test_merges_panel_owned_bridge_controls_into_surface_controls(self) -> None:
        primary_items = [
            {
                "label": "Repository",
                "accessibleLabel": "Repository",
                "role": None,
                "tagName": "input",
                "x": 0.0,
                "y": 0.0,
                "width": 100.0,
                "height": 24.0,
            },
            {
                "label": "Branch",
                "accessibleLabel": "Branch",
                "role": None,
                "tagName": "input",
                "x": 0.0,
                "y": 32.0,
                "width": 100.0,
                "height": 24.0,
            },
        ]
        panel_scoped_items = [
            {
                "label": "Save and switch",
                "accessibleLabel": "Save and switch",
                "role": None,
                "tagName": "button",
                "x": 0.0,
                "y": 64.0,
                "width": 140.0,
                "height": 36.0,
            },
        ]

        merged = _merge_surface_payload_items(primary_items, panel_scoped_items)

        self.assertEqual(
            [item["label"] for item in merged],
            ["Repository", "Branch", "Save and switch"],
        )


if __name__ == "__main__":
    unittest.main()
