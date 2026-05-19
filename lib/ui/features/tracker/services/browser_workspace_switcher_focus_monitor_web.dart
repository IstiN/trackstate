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

BrowserWorkspaceSwitcherFocusMonitorSubscription
createBrowserWorkspaceSwitcherFocusMonitorSubscription({
  required VoidCallback onBrowserTab,
  required VoidCallback onBrowserArrowDown,
  required VoidCallback onBrowserArrowUp,
}) {
  final subscription = web.window.onKeyDown.listen((event) {
    if (event.key != 'Tab') {
      if (event.key == 'ArrowDown' && isBrowserFocusWithinWorkspaceSwitcher()) {
        event.preventDefault();
        onBrowserArrowDown();
      } else if (event.key == 'ArrowUp' &&
          isBrowserFocusWithinWorkspaceSwitcher()) {
        event.preventDefault();
        onBrowserArrowUp();
      }
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
