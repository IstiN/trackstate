import 'dart:async';
import 'dart:js_interop';

import 'package:flutter/foundation.dart' show VoidCallback;
import 'package:web/web.dart' as web;

import 'browser_workspace_switcher_focus_matcher.dart';
import 'browser_workspace_switcher_tab_handoff.dart';

class BrowserWorkspaceSwitcherFocusMonitorSubscription {
  BrowserWorkspaceSwitcherFocusMonitorSubscription(this._cancel);

  final void Function() _cancel;

  void cancel() {
    _cancel();
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

BrowserWorkspaceSwitcherFocusMonitorSubscription
createBrowserWorkspaceSwitcherFocusMonitorSubscription({
  required VoidCallback onBrowserTab,
  required void Function(String key) onBrowserBoundaryKey,
}) {
  final listener = ((web.Event event) {
    final keyboardEvent = event as web.KeyboardEvent;
    if (keyboardEvent.key == 'Tab') {
      if (_moveBrowserWorkspaceSwitcherTabFocus(backwards: keyboardEvent.shiftKey)) {
        keyboardEvent.preventDefault();
      }
      onBrowserTab();
      return;
    }

    if (keyboardEvent.key != 'Home' && keyboardEvent.key != 'End') {
      return;
    }

    if (!browserFocusWithinWorkspaceSwitcherRow(
      ancestors: _activeBrowserFocusAncestors(),
    )) {
      return;
    }

    keyboardEvent.preventDefault();
    onBrowserBoundaryKey(keyboardEvent.key);
  }).toJS;

  web.window.addEventListener('keydown', listener, true.toJS);
  return BrowserWorkspaceSwitcherFocusMonitorSubscription(
    () => web.window.removeEventListener('keydown', listener, true.toJS),
  );
}

bool isBrowserFocusWithinWorkspaceSwitcher() {
  return browserFocusWithinWorkspaceSwitcher(
    ancestors: _activeBrowserFocusAncestors(),
  );
}

bool _moveBrowserWorkspaceSwitcherTabFocus({required bool backwards}) {
  final activeElement = web.document.activeElement;
  if (activeElement is! web.Element) {
    return false;
  }

  final focusTargets = _visibleDocumentFocusTargets();
  final currentIndex = _focusTargetIndexForActiveElement(
    targets: focusTargets,
    activeElement: activeElement,
  );
  if (currentIndex == null) {
    return false;
  }

  final targetIndex = browserWorkspaceSwitcherTabHandoffIndex(
    focusStops: [
      for (final target in focusTargets)
        BrowserWorkspaceSwitcherTabStopSnapshot(
          isFocusable: true,
          isWithinWorkspaceRow: target.isWithinWorkspaceRow,
          isSelectedWorkspaceRow: target.isSelectedWorkspaceRow,
        ),
    ],
    currentIndex: currentIndex,
    backwards: backwards,
  );
  if (targetIndex == null) {
    return false;
  }

  return _focusElement(focusTargets[targetIndex].element);
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
    if (candidate case final web.HTMLElement htmlElement) {
      htmlElement.focus();
    }
    final activeElement = web.document.activeElement;
    if (activeElement == candidate || candidate.contains(activeElement)) {
      return true;
    }
  }
  return false;
}

List<BrowserWorkspaceSwitcherFocusAncestorSnapshot>
_activeBrowserFocusAncestors() {
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
  return ancestors;
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

class _WorkspaceSwitcherFocusTarget {
  const _WorkspaceSwitcherFocusTarget({
    required this.element,
    required this.isWithinWorkspaceRow,
    required this.isSelectedWorkspaceRow,
  });

  final web.Element element;
  final bool isWithinWorkspaceRow;
  final bool isSelectedWorkspaceRow;
}

List<_WorkspaceSwitcherFocusTarget> _visibleDocumentFocusTargets() {
  final selector = [
    'flt-semantics[role="button"]',
    'button',
    'input',
    'textarea',
    'select',
    '[role="button"]',
    '[role="textbox"]',
    '[tabindex]',
  ].join(',');
  final targets = <_WorkspaceSwitcherFocusTarget>[];
  final seen = <web.Element>{};
  final nodes = web.document.querySelectorAll(selector);
  for (var index = 0; index < nodes.length; index += 1) {
    final node = nodes.item(index);
    if (node == null) {
      continue;
    }
    final element = node as web.Element;
    if (seen.contains(element)) {
      continue;
    }
    if (!_isVisible(element) || !_isFocusable(element)) {
      continue;
    }
    seen.add(element);
    targets.add(
      _WorkspaceSwitcherFocusTarget(
        element: element,
        isWithinWorkspaceRow: _workspaceRowElementFor(element) != null,
        isSelectedWorkspaceRow: _isSelectedWorkspaceRowElement(element),
      ),
    );
  }
  return targets;
}

int? _focusTargetIndexForActiveElement({
  required List<_WorkspaceSwitcherFocusTarget> targets,
  required web.Element activeElement,
}) {
  for (var index = 0; index < targets.length; index += 1) {
    final candidate = targets[index].element;
    if (candidate == activeElement || candidate.contains(activeElement)) {
      return index;
    }
  }
  return null;
}

bool _focusElement(web.Element element) {
  final htmlElement = element as web.HTMLElement;
  htmlElement.focus();
  final activeElement = web.document.activeElement;
  return activeElement == htmlElement || htmlElement.contains(activeElement);
}

bool _isVisible(web.Element element) {
  final rect = element.getBoundingClientRect();
  final style = web.window.getComputedStyle(element);
  return rect.width > 0 &&
      rect.height > 0 &&
      style.visibility != 'hidden' &&
      style.display != 'none';
}

bool _isFocusable(web.Element element) {
  final htmlElement = element as web.HTMLElement;
  return htmlElement.tabIndex >= 0;
}

web.Element? _workspaceRowElementFor(web.Element element) {
  web.Element? current = element;
  while (current != null) {
    final semanticsIdentifier = current.getAttribute(
      'flt-semantics-identifier',
    );
    if (semanticsIdentifier?.startsWith(
          browserWorkspaceSwitcherRowSemanticsIdentifierPrefix,
        ) ==
        true) {
      return current;
    }
    current = current.parentElement;
  }
  return null;
}

bool _isSelectedWorkspaceRowElement(web.Element element) {
  final semanticsIdentifier = element.getAttribute('flt-semantics-identifier');
  if (semanticsIdentifier?.startsWith(
        browserWorkspaceSwitcherRowSemanticsIdentifierPrefix,
      ) !=
      true) {
    return false;
  }
  if (element.getAttribute('aria-current') == 'true') {
    return true;
  }
  final htmlElement = element as web.HTMLElement;
  return htmlElement.tabIndex == 0;
}
