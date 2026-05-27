import 'dart:async';

import 'package:web/web.dart' as web;

import 'browser_workspace_switcher_focus_matcher.dart';

const Duration _browserWorkspaceSwitcherTabIntentGrace = Duration(
  milliseconds: 250,
);
const String _browserFocusIdAttribute = 'data-trackstate-browser-focus-id';
const String _browserFocusPanelIdAttribute =
    'data-trackstate-browser-focus-panel-id';
const String _browserFocusRowIdAttribute =
    'data-trackstate-browser-focus-row-id';

class BrowserWorkspaceSwitcherTabIntent {
  const BrowserWorkspaceSwitcherTabIntent({
    required this.backwards,
    required this.focusTargetId,
    required this.rowId,
  });

  final bool backwards;
  final String? focusTargetId;
  final String? rowId;
}

BrowserWorkspaceSwitcherTabIntent? _recentBrowserWorkspaceSwitcherTabIntent;
Timer? _recentBrowserWorkspaceSwitcherTabIntentTimer;

void recordBrowserWorkspaceSwitcherTabIntent({
  required bool backwards,
  required String? panelId,
  String? focusTargetId,
  String? rowId,
}) {
  if (panelId != browserWorkspaceSwitcherSemanticsIdentifier) {
    return;
  }
  _recentBrowserWorkspaceSwitcherTabIntent = BrowserWorkspaceSwitcherTabIntent(
    backwards: backwards,
    focusTargetId: focusTargetId,
    rowId: rowId,
  );
  _recentBrowserWorkspaceSwitcherTabIntentTimer?.cancel();
  _recentBrowserWorkspaceSwitcherTabIntentTimer = Timer(
    _browserWorkspaceSwitcherTabIntentGrace,
    clearRecentBrowserWorkspaceSwitcherTabIntent,
  );
}

BrowserWorkspaceSwitcherTabIntent?
consumeRecentBrowserWorkspaceSwitcherTabIntentForElement(web.Element element) {
  final intent = _recentBrowserWorkspaceSwitcherTabIntent;
  if (intent == null ||
      !_browserWorkspaceSwitcherTabIntentMatchesElement(intent, element)) {
    return null;
  }
  clearRecentBrowserWorkspaceSwitcherTabIntent();
  return intent;
}

void clearRecentBrowserWorkspaceSwitcherTabIntent() {
  _recentBrowserWorkspaceSwitcherTabIntentTimer?.cancel();
  _recentBrowserWorkspaceSwitcherTabIntentTimer = null;
  _recentBrowserWorkspaceSwitcherTabIntent = null;
}

bool _browserWorkspaceSwitcherTabIntentMatchesElement(
  BrowserWorkspaceSwitcherTabIntent intent,
  web.Element element,
) {
  web.Element? current = element;
  while (current != null) {
    if (intent.focusTargetId case final focusTargetId?
        when current.getAttribute(_browserFocusIdAttribute) == focusTargetId) {
      return true;
    }
    if (intent.rowId case final rowId?
        when current.getAttribute(_browserFocusRowIdAttribute) == rowId) {
      return true;
    }
    if (current.getAttribute(_browserFocusPanelIdAttribute) ==
        browserWorkspaceSwitcherSemanticsIdentifier) {
      return intent.focusTargetId == null && intent.rowId == null;
    }
    current = current.parentElement;
  }
  return false;
}
