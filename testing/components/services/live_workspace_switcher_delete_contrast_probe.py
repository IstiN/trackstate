from __future__ import annotations

from dataclasses import asdict, dataclass

from testing.components.pages.live_workspace_switcher_page import (
    WorkspaceSwitcherIconObservation,
    WorkspaceSwitcherInteractiveTextObservation,
    WorkspaceSwitcherSurfaceObservation,
)


@dataclass(frozen=True)
class WorkspaceSwitcherDeleteContrastObservation:
    workspace_name: str
    control_label: str
    visible_text: str
    text_foreground_color: str | None
    text_background_color: str | None
    text_contrast_ratio: float | None
    icon_label: str | None
    icon_foreground_color: str | None
    icon_background_color: str | None
    icon_contrast_ratio: float | None
    available_delete_controls: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def describe(self) -> str:
        icon_summary = (
            "icon=<not exposed>"
            if self.icon_label is None
            else (
                f"icon_label={self.icon_label!r}, "
                f"icon_foreground={self.icon_foreground_color!r}, "
                f"icon_background={self.icon_background_color!r}, "
                f"icon_contrast_ratio={self.icon_contrast_ratio!r}"
            )
        )
        return (
            f"workspace_name={self.workspace_name!r}, "
            f"control_label={self.control_label!r}, "
            f"visible_text={self.visible_text!r}, "
            f"text_foreground={self.text_foreground_color!r}, "
            f"text_background={self.text_background_color!r}, "
            f"text_contrast_ratio={self.text_contrast_ratio!r}, "
            f"{icon_summary}, "
            f"available_delete_controls={list(self.available_delete_controls)!r}"
        )


class LiveWorkspaceSwitcherDeleteContrastProbe:
    def observe(
        self,
        *,
        surface: WorkspaceSwitcherSurfaceObservation,
        preferred_workspace: str | None = None,
    ) -> WorkspaceSwitcherDeleteContrastObservation:
        delete_text_controls = tuple(
            control
            for control in surface.interactive_texts
            if self._is_delete_control(control.label, control.visible_text)
        )
        if not delete_text_controls:
            raise AssertionError(
                "The open workspace switcher did not expose any visible Delete action "
                "text controls.\n"
                f"Observed interactive text controls: "
                f"{[control.visible_text or control.label for control in surface.interactive_texts]!r}\n"
                f"Observed body text:\n{surface.body_text}",
            )

        selected = self._select_control(
            delete_text_controls=delete_text_controls,
            preferred_workspace=preferred_workspace,
        )
        workspace_name = self._workspace_name(selected.visible_text or selected.label)
        matching_icon = self._matching_icon(
            icons=surface.interactive_icons,
            workspace_name=workspace_name,
        )

        return WorkspaceSwitcherDeleteContrastObservation(
            workspace_name=workspace_name,
            control_label=selected.label,
            visible_text=selected.visible_text,
            text_foreground_color=selected.foreground_color,
            text_background_color=selected.background_color,
            text_contrast_ratio=selected.contrast_ratio,
            icon_label=matching_icon.label if matching_icon is not None else None,
            icon_foreground_color=(
                matching_icon.foreground_color if matching_icon is not None else None
            ),
            icon_background_color=(
                matching_icon.background_color if matching_icon is not None else None
            ),
            icon_contrast_ratio=(
                matching_icon.contrast_ratio if matching_icon is not None else None
            ),
            available_delete_controls=tuple(
                control.visible_text or control.label for control in delete_text_controls
            ),
        )

    @staticmethod
    def _is_delete_control(label: str, visible_text: str) -> bool:
        normalized = " ".join(f"{label} {visible_text}".split()).strip().lower()
        return normalized.startswith("delete")

    def _select_control(
        self,
        *,
        delete_text_controls: tuple[WorkspaceSwitcherInteractiveTextObservation, ...],
        preferred_workspace: str | None,
    ) -> WorkspaceSwitcherInteractiveTextObservation:
        if preferred_workspace:
            preferred = preferred_workspace.strip().lower()
            for control in delete_text_controls:
                candidate_text = " ".join(
                    f"{control.label} {control.visible_text}".split(),
                ).lower()
                if preferred in candidate_text:
                    return control
        return delete_text_controls[0]

    def _matching_icon(
        self,
        *,
        icons: tuple[WorkspaceSwitcherIconObservation, ...],
        workspace_name: str,
    ) -> WorkspaceSwitcherIconObservation | None:
        delete_icons = tuple(icon for icon in icons if self._is_delete_icon(icon.label))
        if not delete_icons:
            return None
        workspace_name_lower = workspace_name.lower()
        for icon in delete_icons:
            if workspace_name_lower and workspace_name_lower in icon.label.lower():
                return icon
        return delete_icons[0]

    @staticmethod
    def _is_delete_icon(label: str) -> bool:
        return " ".join(label.split()).strip().lower().startswith("delete")

    @staticmethod
    def _workspace_name(label: str) -> str:
        normalized = " ".join(label.split()).strip()
        if ":" in normalized:
            return normalized.split(":", 1)[1].strip()
        return normalized.removeprefix("Delete").strip()
