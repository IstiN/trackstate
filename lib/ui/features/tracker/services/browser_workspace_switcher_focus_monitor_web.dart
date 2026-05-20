import 'dart:async';

import 'package:flutter/foundation.dart' show VoidCallback;
import 'package:web/web.dart' as web;

import 'browser_workspace_switcher_focus_matcher.dart';

class BrowserWorkspaceSwitcherFocusMonitorSubscription {
  BrowserWorkspaceSwitcherFocusMonitorSubscription(this._subscription);

  final StreamSubscription<web.KeyboardEvent> _subscription;

  void cancel() {
    unawaited(_subscription.cancel());
  }
}

class BrowserWorkspaceSwitcherFocusRequest {
  BrowserWorkspaceSwitcherFocusRequest(this._timer);

  Timer? _timer;

  void cancel() {
    _timer?.cancel();
    _timer = null;
  }
}

class BrowserDesktopPrimaryNavigationTabOrderSubscription {
  BrowserDesktopPrimaryNavigationTabOrderSubscription(this._subscription);

  final StreamSubscription<web.KeyboardEvent> _subscription;

  void cancel() {
    unawaited(_subscription.cancel());
  }
}

BrowserWorkspaceSwitcherFocusMonitorSubscription
createBrowserWorkspaceSwitcherFocusMonitorSubscription({
  required VoidCallback onBrowserTab,
}) {
  final subscription = web.window.onKeyDown.listen((event) {
    if (event.key != 'Tab') {
      return;
    }
    onBrowserTab();
  });
  return BrowserWorkspaceSwitcherFocusMonitorSubscription(subscription);
}

bool isBrowserFocusWithinWorkspaceSwitcher() {
  final ancestors = <BrowserWorkspaceSwitcherFocusAncestorSnapshot>[];
  web.Element? element = web.document.activeElement;
  while (element != null) {
    ancestors.add(
      BrowserWorkspaceSwitcherFocusAncestorSnapshot(
        semanticsIdentifier: element.getAttribute('flt-semantics-identifier'),
        textContent: element.textContent,
      ),
    );
    element = element.parentElement;
  }
  return browserFocusWithinWorkspaceSwitcher(ancestors: ancestors);
}

BrowserWorkspaceSwitcherFocusRequest requestBrowserWorkspaceSwitcherFocus({
  required String semanticsIdentifier,
}) {
  Timer? timer;
  var attemptCount = 0;
  var consecutiveFocusedFrames = 0;

  void tryFocus() {
    attemptCount += 1;
    if (_focusSemanticsElement(semanticsIdentifier)) {
      consecutiveFocusedFrames += 1;
    } else {
      consecutiveFocusedFrames = 0;
    }
    if (consecutiveFocusedFrames >= 2 || attemptCount >= 30) {
      timer?.cancel();
      timer = null;
    }
  }

  timer = Timer.periodic(const Duration(milliseconds: 16), (_) => tryFocus());
  Timer.run(tryFocus);
  return BrowserWorkspaceSwitcherFocusRequest(timer);
}

BrowserDesktopPrimaryNavigationTabOrderSubscription
createBrowserDesktopPrimaryNavigationTabOrderSubscription({
  required String settingsLabel,
  required String workspaceSwitcherLabelPrefix,
  required List<String> searchControlLabels,
}) {
  final normalizedSettingsLabel = _normalizeLabel(settingsLabel);
  final normalizedWorkspacePrefix = _normalizeLabel(
    workspaceSwitcherLabelPrefix,
  );
  final normalizedSearchLabels = searchControlLabels
      .map(_normalizeLabel)
      .where((label) => label.isNotEmpty)
      .toList(growable: false);
  final subscription = web.window.onKeyDown.listen((event) {
    if (event.key != 'Tab' || event.altKey || event.ctrlKey || event.metaKey) {
      return;
    }

    final activeElement = web.document.activeElement;
    if (activeElement is! web.Element) {
      return;
    }

    final activeLabel = _normalizeLabel(_elementAccessibleLabel(activeElement));
    if (activeLabel.isEmpty) {
      return;
    }

    final handled = event.shiftKey
        ? _handleReverseDesktopPrimaryNavigationTab(
            activeLabel: activeLabel,
            settingsLabel: normalizedSettingsLabel,
            workspacePrefix: normalizedWorkspacePrefix,
            searchLabels: normalizedSearchLabels,
          )
        : _handleForwardDesktopPrimaryNavigationTab(
            activeLabel: activeLabel,
            settingsLabel: normalizedSettingsLabel,
            workspacePrefix: normalizedWorkspacePrefix,
            searchLabels: normalizedSearchLabels,
          );
    if (!handled) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
  });
  return BrowserDesktopPrimaryNavigationTabOrderSubscription(subscription);
}

bool _focusSemanticsElement(String semanticsIdentifier) {
  final elements = web.document.querySelectorAll('[flt-semantics-identifier]');
  for (var index = 0; index < elements.length; index++) {
    final candidateNode = elements.item(index);
    if (candidateNode == null) {
      continue;
    }
    final candidate = candidateNode as web.Element;
    if (candidate.getAttribute('flt-semantics-identifier') !=
        semanticsIdentifier) {
      continue;
    }
    (candidate as web.HTMLElement).focus();
    final activeElement = web.document.activeElement;
    return activeElement == candidate || candidate.contains(activeElement);
  }
  return false;
}

void syncBrowserWorkspaceSwitcherRowTabIndices({
  required String activeWorkspaceId,
}) {
  final prefix = browserWorkspaceSwitcherRowSemanticsIdentifierPrefix;
  final activeIdentifier =
      browserWorkspaceSwitcherRowSemanticsIdentifier(activeWorkspaceId);
  final elements = web.document.querySelectorAll(
    '[flt-semantics-identifier^="$prefix"]',
  );
  for (var index = 0; index < elements.length; index++) {
    final node = elements.item(index);
    if (node == null) {
      continue;
    }
    final element = node as web.HTMLElement;
    final identifier = element.getAttribute('flt-semantics-identifier');
    if (identifier == activeIdentifier) {
      element.tabIndex = 0;
    } else {
      element.tabIndex = -1;
    }
  }
}

bool _handleForwardDesktopPrimaryNavigationTab({
  required String activeLabel,
  required String settingsLabel,
  required String workspacePrefix,
  required List<String> searchLabels,
}) {
  if (activeLabel == settingsLabel) {
    return _focusFirstFocusableElement(
      (label, tagName) =>
          tagName == 'FLT-SEMANTICS' && label.startsWith(workspacePrefix),
    );
  }
  if (activeLabel.startsWith(workspacePrefix)) {
    return _focusFirstFocusableElement(
      (label, tagName) => _isSearchControlLabel(
        label: label,
        tagName: tagName,
        searchLabels: searchLabels,
      ),
    );
  }
  return false;
}

bool _handleReverseDesktopPrimaryNavigationTab({
  required String activeLabel,
  required String settingsLabel,
  required String workspacePrefix,
  required List<String> searchLabels,
}) {
  if (_isSearchControlLabel(
    label: activeLabel,
    tagName: web.document.activeElement?.tagName ?? '',
    searchLabels: searchLabels,
  )) {
    return _focusFirstFocusableElement(
      (label, tagName) =>
          tagName == 'FLT-SEMANTICS' && label.startsWith(workspacePrefix),
    );
  }
  if (activeLabel.startsWith(workspacePrefix)) {
    return _focusFirstFocusableElement(
      (label, tagName) => tagName == 'FLT-SEMANTICS' && label == settingsLabel,
    );
  }
  return false;
}

bool _focusFirstFocusableElement(
  bool Function(String normalizedLabel, String tagName) predicate,
) {
  final selectors =
      'flt-semantics[role="button"], input[aria-label], textarea[aria-label]';
  final candidates = web.document.querySelectorAll(selectors);
  for (var index = 0; index < candidates.length; index++) {
    final candidateNode = candidates.item(index);
    if (candidateNode == null) {
      continue;
    }
    final candidateElement = candidateNode as web.HTMLElement;
    if (!_isVisible(candidateElement)) {
      continue;
    }
    final label = _normalizeLabel(_elementAccessibleLabel(candidateElement));
    if (!predicate(label, candidateElement.tagName)) {
      continue;
    }
    candidateElement.focus();
    final activeElement = web.document.activeElement;
    return activeElement == candidateElement ||
        candidateElement.contains(activeElement);
  }
  return false;
}

bool _isSearchControlLabel({
  required String label,
  required String tagName,
  required List<String> searchLabels,
}) {
  if (tagName == 'INPUT' || tagName == 'TEXTAREA') {
    return searchLabels.contains(label);
  }
  return searchLabels.contains(label) || label == 'search';
}

String _elementAccessibleLabel(web.Element element) {
  return element.getAttribute('aria-label') ?? element.textContent ?? '';
}

String _normalizeLabel(String label) {
  return label.replaceAll(RegExp(r'\s+'), ' ').trim().toLowerCase();
}

bool _isVisible(web.HTMLElement element) {
  final rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}
