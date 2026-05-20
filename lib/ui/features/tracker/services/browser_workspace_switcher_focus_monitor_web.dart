import 'dart:async';
import 'dart:js_interop';

import 'package:flutter/foundation.dart' show VoidCallback;
import 'package:web/web.dart' as web;

import 'browser_workspace_switcher_focus_matcher.dart';

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
