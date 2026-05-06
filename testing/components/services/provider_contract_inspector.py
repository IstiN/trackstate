from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class ProviderContractObservation:
    repository_exposes_session: bool
    repository_session_symbol: str | None
    provider_session_file: str | None
    provider_session_fields: tuple[str, ...]
    capability_contract_file: str | None
    capability_flags: tuple[str, ...]
    repository_specific_types: tuple[str, ...]


class ProviderContractInspector:
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = repository_root

    def inspect(self) -> ProviderContractObservation:
        repository_file = self._repository_root / "lib/data/repositories/trackstate_repository.dart"
        repository_source = repository_file.read_text(encoding="utf-8")
        repository_session_symbol = self._find_repository_session_symbol(repository_source)
        provider_session_file, provider_session_fields = self._find_class_fields("ProviderSession")
        capability_contract_file, capability_flags = self._find_capability_flags()

        return ProviderContractObservation(
            repository_exposes_session=repository_session_symbol is not None,
            repository_session_symbol=repository_session_symbol,
            provider_session_file=provider_session_file,
            provider_session_fields=provider_session_fields,
            capability_contract_file=capability_contract_file,
            capability_flags=capability_flags,
            repository_specific_types=self._find_provider_specific_types(repository_source),
        )

    def _find_repository_session_symbol(self, source: str) -> str | None:
        patterns = (
            r"\bProviderSession\s+get\s+session\b",
            r"\bfinal\s+ProviderSession\s+session\b",
            r"\bProviderSession\?\s+get\s+session\b",
            r"\bProviderSession\?\s+session\b",
        )
        for pattern in patterns:
            match = re.search(pattern, source)
            if match:
                return match.group(0)
        return None

    def _find_class_fields(self, class_name: str) -> tuple[str | None, tuple[str, ...]]:
        class_pattern = re.compile(rf"class\s+{class_name}\b[\s\S]*?\{{([\s\S]*?)\n\}}", re.MULTILINE)
        for dart_file in sorted(self._repository_root.glob("lib/**/*.dart")):
            source = dart_file.read_text(encoding="utf-8")
            match = class_pattern.search(source)
            if not match:
                continue
            fields = tuple(
                dict.fromkeys(
                    field_match.group(1)
                    for field_match in re.finditer(
                        r"\bfinal\s+[A-Za-z0-9_<>,?. ]+\s+([A-Za-z0-9_]+)\s*;",
                        match.group(1),
                    )
                )
            )
            return str(dart_file.relative_to(self._repository_root)), fields
        return None, ()

    def _find_capability_flags(self) -> tuple[str | None, tuple[str, ...]]:
        requested_flags = (
            "canRead",
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        )
        for dart_file in sorted(self._repository_root.glob("lib/**/*.dart")):
            source = dart_file.read_text(encoding="utf-8")
            if all(re.search(rf"\b{flag}\b", source) for flag in requested_flags):
                return str(dart_file.relative_to(self._repository_root)), requested_flags
        observed_flags: list[str] = []
        for dart_file in sorted(self._repository_root.glob("lib/**/*.dart")):
            source = dart_file.read_text(encoding="utf-8")
            for flag in requested_flags:
                if flag not in observed_flags and re.search(rf"\b{flag}\b", source):
                    observed_flags.append(flag)
        return None, tuple(observed_flags)

    def _find_provider_specific_types(self, source: str) -> tuple[str, ...]:
        leaked_types = []
        for leaked_type in ("GitHubConnection", "GitHubUser"):
            if re.search(rf"\b{leaked_type}\b", source):
                leaked_types.append(leaked_type)
        return tuple(leaked_types)

