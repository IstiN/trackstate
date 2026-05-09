from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.flutter_analyze_probe import FlutterAnalyzeProbe
from testing.frameworks.python.flutter_analyze_framework import (
    PythonFlutterAnalyzeFramework,
)


def create_flutter_analyze_probe(
    repository_root: Path,
    *,
    flutter_version: str,
) -> FlutterAnalyzeProbe:
    return PythonFlutterAnalyzeFramework(
        repository_root,
        flutter_version=flutter_version,
    )
