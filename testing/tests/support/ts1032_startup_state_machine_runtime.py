from __future__ import annotations

from typing import Any

from testing.tests.support.ts984_delayed_auth_probe_runtime import (
    Ts984DelayedAuthProbeRuntime,
)


class Ts1032StartupStateMachineRuntime(Ts984DelayedAuthProbeRuntime):
    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "Ts1032StartupStateMachineRuntime expected a browser context and page.",
            )
        script = _pending_shell_probe_script()
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        return session

    def read_pending_shell_probe_state(self) -> dict[str, Any]:
        if self._page is None:
            raise RuntimeError(
                "Ts1032StartupStateMachineRuntime expected a browser page before reading state.",
            )
        payload = self._page.evaluate(
            """
            () => {
              const state = window.__ts1032PendingShellProbeState;
              if (!state) {
                return null;
              }
              return {
                firstNavigationVisibleAtMs: state.firstNavigationVisibleAtMs,
                firstTriggerVisibleAtMs: state.firstTriggerVisibleAtMs,
                firstBrandingVisibleAtMs: state.firstBrandingVisibleAtMs,
                firstAnyShellMarkerVisibleAtMs: state.firstAnyShellMarkerVisibleAtMs,
                firstTriggerLabel: state.firstTriggerLabel,
                firstNavigationLabels: state.firstNavigationLabels,
                samples: state.samples,
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            return {
                "first_navigation_visible_after_launch_seconds": None,
                "first_trigger_visible_after_launch_seconds": None,
                "first_branding_visible_after_launch_seconds": None,
                "first_any_shell_marker_visible_after_launch_seconds": None,
                "first_trigger_label": "",
                "first_navigation_labels": [],
                "sample_count": 0,
                "samples": [],
            }
        normalized_samples = _normalize_pending_probe_samples(payload.get("samples", []))
        return {
            "first_navigation_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstNavigationVisibleAtMs"),
            ),
            "first_trigger_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstTriggerVisibleAtMs"),
            ),
            "first_branding_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstBrandingVisibleAtMs"),
            ),
            "first_any_shell_marker_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstAnyShellMarkerVisibleAtMs"),
            ),
            "first_trigger_label": str(payload.get("firstTriggerLabel", "")),
            "first_navigation_labels": [
                str(label) for label in payload.get("firstNavigationLabels", [])
            ],
            "sample_count": len(normalized_samples),
            "samples": normalized_samples,
        }


def _ms_to_seconds(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(float(value) / 1000, 2)


def _normalize_pending_probe_samples(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    samples: list[dict[str, Any]] = []
    for sample in payload:
        if not isinstance(sample, dict):
            continue
        samples.append(
            {
                "observed_after_launch_seconds": _ms_to_seconds(sample.get("observedAtMs")),
                "visible_navigation_labels": [
                    str(label) for label in sample.get("visibleNavigationLabels", [])
                ],
                "trigger_visible": bool(sample.get("triggerVisible")),
                "trigger_label": str(sample.get("triggerLabel", "")),
                "branding_visible": bool(sample.get("brandingVisible")),
                "shell_ready": bool(sample.get("shellReady")),
                "body_excerpt": str(sample.get("bodyExcerpt", "")),
            },
        )
    return samples


def _pending_shell_probe_script() -> str:
    return """
(() => {
  const MAX_SAMPLES = 300;
  const SAMPLE_INTERVAL_MS = 100;
  const state = {
    firstNavigationVisibleAtMs: null,
    firstTriggerVisibleAtMs: null,
    firstBrandingVisibleAtMs: null,
    firstAnyShellMarkerVisibleAtMs: null,
    firstTriggerLabel: '',
    firstNavigationLabels: [],
    samples: [],
  };
  window.__ts1032PendingShellProbeState = state;

  const readyLabels = ['Dashboard', 'Board', 'JQL Search', 'Hierarchy', 'Settings'];
  const brandingLabels = ['Git-native. Jira-compatible. Team-proven.', 'TrackState.AI'];
  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();

  const semanticTexts = () => Array.from(
    document.querySelectorAll('flt-semantics, button, [role], nav, header, aside, a, [aria-label]'),
  )
    .filter((element) => !['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(element.tagName))
    .map((element) => normalize(
      element.getAttribute?.('aria-label')
      || element.innerText
      || element.textContent
      || '',
    ))
    .filter((text) => text.length > 0);

  const updateFirstAny = () => {
    if (state.firstAnyShellMarkerVisibleAtMs !== null) {
      return;
    }
    const candidates = [
      state.firstNavigationVisibleAtMs,
      state.firstTriggerVisibleAtMs,
      state.firstBrandingVisibleAtMs,
    ].filter((value) => value !== null);
    if (candidates.length > 0) {
      state.firstAnyShellMarkerVisibleAtMs = Math.min(...candidates);
    }
  };

  const observe = () => {
    const bodyText = normalize(document.body?.innerText ?? document.body?.textContent ?? '');
    const texts = semanticTexts();
    const visibleNavigation = readyLabels.filter(
      (label) => bodyText.includes(label) || texts.includes(label),
    );
    if (state.firstNavigationVisibleAtMs === null && visibleNavigation.length > 0) {
      state.firstNavigationVisibleAtMs = performance.now();
      state.firstNavigationLabels = visibleNavigation;
    }
    const triggerLabel = texts.find((text) => text.includes('Workspace switcher:'));
    if (state.firstTriggerVisibleAtMs === null && triggerLabel) {
      state.firstTriggerVisibleAtMs = performance.now();
      state.firstTriggerLabel = triggerLabel;
    }
    const brandingVisible = brandingLabels.some((label) =>
      bodyText.includes(label) || texts.some((text) => text.includes(label)),
    );
    if (state.firstBrandingVisibleAtMs === null && brandingVisible) {
      state.firstBrandingVisibleAtMs = performance.now();
    }
    updateFirstAny();
  };

  const captureSample = () => {
    const bodyText = normalize(document.body?.innerText ?? document.body?.textContent ?? '');
    const texts = semanticTexts();
    const visibleNavigationLabels = readyLabels.filter(
      (label) => bodyText.includes(label) || texts.includes(label),
    );
    const triggerLabel = texts.find((text) => text.includes('Workspace switcher:')) || '';
    const brandingVisible = brandingLabels.some((label) =>
      bodyText.includes(label) || texts.some((text) => text.includes(label)),
    );
    state.samples.push({
      observedAtMs: performance.now(),
      visibleNavigationLabels,
      triggerVisible: !!triggerLabel,
      triggerLabel,
      brandingVisible,
      shellReady: visibleNavigationLabels.length === readyLabels.length,
      bodyExcerpt: bodyText.slice(0, 240),
    });
    if (state.samples.length > MAX_SAMPLES) {
      state.samples.splice(0, state.samples.length - MAX_SAMPLES);
    }
  };

  const attachObserver = () => {
    observe();
    captureSample();
    if (!document.documentElement) {
      requestAnimationFrame(attachObserver);
      return;
    }
    new MutationObserver(() => observe()).observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
    });
  };

  attachObserver();
  window.setInterval(() => {
    observe();
    captureSample();
  }, SAMPLE_INTERVAL_MS);
  window.addEventListener('load', () => observe(), { once: false });
})();
"""
