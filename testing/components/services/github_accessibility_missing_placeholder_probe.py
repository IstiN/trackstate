from __future__ import annotations

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateError,
)
from testing.components.services.github_accessibility_semantics_failure_probe import (
    GitHubAccessibilitySemanticsFailureProbeService,
)


class GitHubAccessibilityMissingPlaceholderProbeService(
    GitHubAccessibilitySemanticsFailureProbeService
):
    simulation_require_statement = (
        "const {\n"
        "  installTs952MissingPlaceholderSimulation,\n"
        "} = require('./ts952_missing_placeholder_simulation');"
    )
    simulation_call = "  await installTs952MissingPlaceholderSimulation(page);"
    simulation_technique = (
        "Adds a disposable Playwright init script that removes and hides "
        "`flt-semantics-placeholder` queries so the live accessibility gate exercises "
        "the missing-placeholder pre-flight path without changing production app code."
    )

    @classmethod
    def _simulation_helper_source(cls) -> str:
        return """async function installTs952MissingPlaceholderSimulation(page) {
  await page.addInitScript(() => {
    const hiddenSelector = 'flt-semantics-placeholder';
    const fallbackSelector = 'flt-ts952-simulated-missing-placeholder';

    function matchesHiddenPlaceholderSelector(selectors) {
      if (typeof selectors !== 'string') {
        return false;
      }
      return selectors
        .split(',')
        .map((selector) => selector.trim())
        .some((selector) => selector === hiddenSelector);
    }

    const originalDocumentQuerySelector = Document.prototype.querySelector;
    const originalDocumentQuerySelectorAll = Document.prototype.querySelectorAll;
    const originalElementQuerySelector = Element.prototype.querySelector;
    const originalElementQuerySelectorAll = Element.prototype.querySelectorAll;

    function removePlaceholders() {
      const matches = Array.from(
        originalDocumentQuerySelectorAll.call(document, hiddenSelector),
      );
      for (const element of matches) {
        element.remove();
      }
    }

    Document.prototype.querySelector = function ts952DocumentQuerySelector(
        selectors,
    ) {
      if (matchesHiddenPlaceholderSelector(selectors)) {
        return null;
      }
      return originalDocumentQuerySelector.call(this, selectors);
    };

    Document.prototype.querySelectorAll = function ts952DocumentQuerySelectorAll(
        selectors,
    ) {
      if (matchesHiddenPlaceholderSelector(selectors)) {
        return originalDocumentQuerySelectorAll.call(this, fallbackSelector);
      }
      return originalDocumentQuerySelectorAll.call(this, selectors);
    };

    Element.prototype.querySelector = function ts952ElementQuerySelector(
        selectors,
    ) {
      if (matchesHiddenPlaceholderSelector(selectors)) {
        return null;
      }
      return originalElementQuerySelector.call(this, selectors);
    };

    Element.prototype.querySelectorAll = function ts952ElementQuerySelectorAll(
        selectors,
    ) {
      if (matchesHiddenPlaceholderSelector(selectors)) {
        return originalElementQuerySelectorAll.call(this, fallbackSelector);
      }
      return originalElementQuerySelectorAll.call(this, selectors);
    };

    const observer = new MutationObserver(() => {
      removePlaceholders();
    });

    function startHidingPlaceholders() {
      removePlaceholders();
      if (document.documentElement) {
        observer.observe(document.documentElement, {
          childList: true,
          subtree: true,
        });
      }
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', startHidingPlaceholders, {
        once: true,
      });
    } else {
      startHidingPlaceholders();
    }
  });
}

module.exports = {
  installTs952MissingPlaceholderSimulation,
};
"""

    @classmethod
    def _patch_spec_source(cls, source: str) -> str:
        if cls.simulation_require_statement not in source:
            import_anchor = "} = require('./accessibility_gate');"
            if import_anchor not in source:
                raise GitHubAccessibilityPullRequestGateError(
                    "TS-952 could not find the shared accessibility gate import block in "
                    "testing/accessibility/accessibility_gate.spec.js."
                )
            source = source.replace(
                import_anchor,
                import_anchor + "\n" + cls.simulation_require_statement,
                1,
            )

        if cls.simulation_call not in source:
            target = "  await captureFlutterStartupDiagnostics(page, {"
            if target not in source:
                raise GitHubAccessibilityPullRequestGateError(
                    "TS-952 could not find the startup diagnostics call in "
                    "testing/accessibility/accessibility_gate.spec.js."
                )
            source = source.replace(
                target,
                f"{cls.simulation_call}\n{target}",
                1,
            )

        return source

    def _extract_log_excerpt(self, run_log_text: str, fallback_text: str) -> str:
        text = run_log_text or fallback_text
        if not text.strip():
            return ""

        for raw_line in text.splitlines():
            normalized_line = " ".join(raw_line.split()).strip()
            lowered_line = normalized_line.lower()
            if "flt-semantics-placeholder" not in lowered_line:
                continue
            if any(
                marker in lowered_line
                for marker in (
                    "missing",
                    "absent",
                    "not found",
                    "not present",
                    "did not render",
                    "never appeared",
                )
            ):
                return self._snippet(normalized_line, limit=1200)

        lowered = text.lower()
        prioritized_markers = [
            "missing flt-semantics-placeholder",
            "accessibility pre-flight failed because flt-semantics-placeholder",
            "pre-flight",
            "preflight",
            "flt-semantics-placeholder",
            "page.waitforselector",
            "page.waitforfunction",
            "testing/accessibility/accessibility_gate.spec.js",
            "test timeout",
            "timeout",
            "missing flt-semantics-placeholder",
            "pre-flight",
            "preflight",
            "flt-semantics-placeholder",
            "waiting for nodes",
        ]
        for marker in prioritized_markers:
            index = lowered.find(marker)
            if index >= 0:
                start = max(index - 200, 0)
                end = min(index + 1000, len(text))
                return self._snippet(text[start:end], limit=1200)

        return super()._extract_log_excerpt(run_log_text, fallback_text)
