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

class BrowserDesktopPrimaryNavigationTabOrderSubscription {
  BrowserDesktopPrimaryNavigationTabOrderSubscription(
    this._timer,
    this._keydownListener,
  );

  final Timer _timer;
  final JSFunction _keydownListener;

  void cancel() {
    _timer.cancel();
    web.window.removeEventListener('keydown', _keydownListener, true.toJS);
    _restoreManagedDesktopPrimaryNavigationTabOrder();
  }
}

enum BrowserDesktopPrimaryNavigationTabOrderTargetType {
  semanticsIdentifier,
  inputLabel,
  accessibleLabel,
  accessibleLabelPrefix,
}

class BrowserDesktopPrimaryNavigationTabOrderTarget {
  const BrowserDesktopPrimaryNavigationTabOrderTarget.semanticsIdentifier(
    this.value,
  ) : type =
          BrowserDesktopPrimaryNavigationTabOrderTargetType.semanticsIdentifier;

  const BrowserDesktopPrimaryNavigationTabOrderTarget.inputLabel(this.value)
    : type = BrowserDesktopPrimaryNavigationTabOrderTargetType.inputLabel;

  const BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabel(
    this.value,
  ) : type = BrowserDesktopPrimaryNavigationTabOrderTargetType.accessibleLabel;

  const BrowserDesktopPrimaryNavigationTabOrderTarget.accessibleLabelPrefix(
    this.value,
  ) : type = BrowserDesktopPrimaryNavigationTabOrderTargetType
          .accessibleLabelPrefix;

  final BrowserDesktopPrimaryNavigationTabOrderTargetType type;
  final String value;

  @override
  bool operator ==(Object other) {
    return other is BrowserDesktopPrimaryNavigationTabOrderTarget &&
        other.type == type &&
        other.value == value;
  }

  @override
  int get hashCode => Object.hash(type, value);
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

BrowserDesktopPrimaryNavigationTabOrderSubscription
createBrowserDesktopPrimaryNavigationTabOrderSubscription({
  required List<BrowserDesktopPrimaryNavigationTabOrderTarget> orderedTargets,
}) {
  void refreshTabOrder() {
    _applyDesktopPrimaryNavigationTabOrder(orderedTargets);
  }

  refreshTabOrder();
  final timer = Timer.periodic(
    const Duration(milliseconds: 100),
    (_) => refreshTabOrder(),
  );
  final keydownListener = ((web.Event event) {
    final keyboardEvent = event as web.KeyboardEvent;
    if (keyboardEvent.key != 'Tab' ||
        keyboardEvent.altKey ||
        keyboardEvent.ctrlKey ||
        keyboardEvent.metaKey) {
      return;
    }
    final resolvedTargets = _resolveDesktopPrimaryNavigationTargets(
      orderedTargets,
    );
    if (resolvedTargets.isEmpty) {
      return;
    }
    final activeIndex = _activeDesktopPrimaryNavigationTargetIndex(
      navigationTargets: resolvedTargets,
      activeElement: web.document.activeElement,
    );
    if (activeIndex == null) {
      return;
    }
    final nextIndex = keyboardEvent.shiftKey
        ? activeIndex - 1
        : activeIndex + 1;
    if (nextIndex < 0 || nextIndex >= resolvedTargets.length) {
      return;
    }
    keyboardEvent.preventDefault();
    keyboardEvent.stopPropagation();
    resolvedTargets[nextIndex].focus();
  }).toJS;
  web.window.addEventListener('keydown', keydownListener, true.toJS);
  return BrowserDesktopPrimaryNavigationTabOrderSubscription(
    timer,
    keydownListener,
  );
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
  final activeIdentifier = browserWorkspaceSwitcherRowSemanticsIdentifier(
    activeWorkspaceId,
  );
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

void _applyDesktopPrimaryNavigationTabOrder(
  List<BrowserDesktopPrimaryNavigationTabOrderTarget> orderedTargets,
) {
  _restoreManagedDesktopPrimaryNavigationTabOrder();
  final resolvedTargets = _resolveDesktopPrimaryNavigationTargets(
    orderedTargets,
  );
  for (var index = 0; index < resolvedTargets.length; index += 1) {
    _setManagedTabIndex(resolvedTargets[index], index + 1);
  }
}

List<web.HTMLElement> _resolveDesktopPrimaryNavigationTargets(
  List<BrowserDesktopPrimaryNavigationTabOrderTarget> orderedTargets,
) {
  final assignedElements = <web.Element>[];
  final resolvedTargets = <web.HTMLElement>[];
  for (final target in orderedTargets) {
    final element = _resolveDesktopPrimaryNavigationTarget(
      target: target,
      assignedElements: assignedElements,
    );
    if (element == null) {
      continue;
    }
    assignedElements.add(element);
    resolvedTargets.add(element);
  }
  return resolvedTargets;
}

int? _activeDesktopPrimaryNavigationTargetIndex({
  required List<web.HTMLElement> navigationTargets,
  required web.Element? activeElement,
}) {
  if (activeElement == null) {
    return null;
  }
  for (var index = 0; index < navigationTargets.length; index += 1) {
    final candidate = navigationTargets[index];
    if (candidate == activeElement || candidate.contains(activeElement)) {
      return index;
    }
  }
  return null;
}

web.HTMLElement? _resolveDesktopPrimaryNavigationTarget({
  required BrowserDesktopPrimaryNavigationTabOrderTarget target,
  required List<web.Element> assignedElements,
}) {
  return switch (target.type) {
    BrowserDesktopPrimaryNavigationTabOrderTargetType.semanticsIdentifier =>
      _firstVisibleFocusableSemanticsElement(
        semanticsIdentifier: target.value,
        assignedElements: assignedElements,
      ),
    BrowserDesktopPrimaryNavigationTabOrderTargetType.inputLabel =>
      _firstVisibleInputElement(
        inputLabel: target.value,
        assignedElements: assignedElements,
      ),
    BrowserDesktopPrimaryNavigationTabOrderTargetType.accessibleLabel =>
      _firstVisibleFocusableElementWithAccessibleLabel(
        accessibleLabel: target.value,
        assignedElements: assignedElements,
      ),
    BrowserDesktopPrimaryNavigationTabOrderTargetType.accessibleLabelPrefix =>
      _firstVisibleFocusableElementWithAccessibleLabel(
        accessibleLabel: target.value,
        assignedElements: assignedElements,
        allowPrefixMatch: true,
      ),
  };
}

web.HTMLElement? _firstVisibleFocusableSemanticsElement({
  required String semanticsIdentifier,
  required List<web.Element> assignedElements,
}) {
  final candidates = web.document.querySelectorAll(
    '[flt-semantics-identifier="$semanticsIdentifier"]',
  );
  for (var index = 0; index < candidates.length; index += 1) {
    final candidateNode = candidates.item(index);
    if (candidateNode == null) {
      continue;
    }
    final candidate = candidateNode as web.HTMLElement;
    if (!_isVisible(candidate) || assignedElements.contains(candidate)) {
      continue;
    }
    final tabindex = candidate.getAttribute('tabindex');
    final allowMissingTabIndex =
        semanticsIdentifier == browserDesktopSearchInputSemanticsIdentifier ||
        semanticsIdentifier == browserDesktopSettingsSemanticsIdentifier;
    if ((tabindex == null && !allowMissingTabIndex) || tabindex == '-1') {
      continue;
    }
    return candidate;
  }
  return null;
}

web.HTMLElement? _firstVisibleInputElement({
  required String inputLabel,
  required List<web.Element> assignedElements,
}) {
  final normalizedInputLabel = _normalizeLabel(inputLabel);
  final candidates = web.document.querySelectorAll(
    'input[aria-label], textarea[aria-label]',
  );
  for (var index = 0; index < candidates.length; index += 1) {
    final candidateNode = candidates.item(index);
    if (candidateNode == null) {
      continue;
    }
    final candidate = candidateNode as web.HTMLElement;
    if (!_isVisible(candidate) || assignedElements.contains(candidate)) {
      continue;
    }
    if (_normalizeLabel(_elementAccessibleLabel(candidate)) !=
        normalizedInputLabel) {
      continue;
    }
    return candidate;
  }
  return null;
}

web.HTMLElement? _firstVisibleFocusableElementWithAccessibleLabel({
  required String accessibleLabel,
  required List<web.Element> assignedElements,
  bool allowPrefixMatch = false,
}) {
  final normalizedAccessibleLabel = _normalizeLabel(accessibleLabel);
  final candidates = web.document.querySelectorAll(
    'flt-semantics[role="button"], [role="button"], input[aria-label], textarea[aria-label]',
  );
  for (var index = 0; index < candidates.length; index += 1) {
    final candidateNode = candidates.item(index);
    if (candidateNode == null) {
      continue;
    }
    final candidate = candidateNode as web.HTMLElement;
    if (!_isVisible(candidate) || assignedElements.contains(candidate)) {
      continue;
    }
    final candidateLabel = _normalizeLabel(_elementAccessibleLabel(candidate));
    final labelMatches = allowPrefixMatch
        ? candidateLabel.startsWith(normalizedAccessibleLabel)
        : candidateLabel == normalizedAccessibleLabel;
    if (!labelMatches) {
      continue;
    }
    return candidate;
  }
  return null;
}

void _setManagedTabIndex(web.HTMLElement element, int tabIndex) {
  if (element.getAttribute(_managedTabOrderAttribute) == 'true') {
    element.setAttribute('tabindex', '$tabIndex');
    _applyManagedSearchBridgeSemantics(element);
    return;
  }
  element.setAttribute(
    _originalTabIndexAttribute,
    element.getAttribute('tabindex') ?? _missingTabIndexSentinel,
  );
  element.setAttribute(_managedTabOrderAttribute, 'true');
  element.setAttribute('tabindex', '$tabIndex');
  _applyManagedSearchBridgeSemantics(element);
}

void _restoreManagedDesktopPrimaryNavigationTabOrder() {
  final managedElements = web.document.querySelectorAll(
    '[$_managedTabOrderAttribute="true"]',
  );
  for (var index = 0; index < managedElements.length; index += 1) {
    final managedNode = managedElements.item(index);
    if (managedNode == null) {
      continue;
    }
    final managedElement = managedNode as web.Element;
    final originalTabIndex = managedElement.getAttribute(
      _originalTabIndexAttribute,
    );
    if (originalTabIndex == null ||
        originalTabIndex == _missingTabIndexSentinel) {
      managedElement.removeAttribute('tabindex');
    } else {
      managedElement.setAttribute('tabindex', originalTabIndex);
    }
    _restoreManagedAttribute(
      managedElement,
      attributeName: 'role',
      originalValueAttribute: _originalRoleAttribute,
    );
    _restoreManagedAttribute(
      managedElement,
      attributeName: 'aria-label',
      originalValueAttribute: _originalAriaLabelAttribute,
    );
    managedElement.removeAttribute(_managedTabOrderAttribute);
    managedElement.removeAttribute(_originalTabIndexAttribute);
  }
}

void _applyManagedSearchBridgeSemantics(web.HTMLElement element) {
  if (element.getAttribute('flt-semantics-identifier') !=
      browserDesktopSearchInputSemanticsIdentifier) {
    return;
  }
  final searchLabel = _searchBridgeLabel(element);
  if (searchLabel.isEmpty) {
    return;
  }
  _setManagedAttribute(
    element: element,
    attributeName: 'role',
    originalValueAttribute: _originalRoleAttribute,
    value: 'textbox',
  );
  _setManagedAttribute(
    element: element,
    attributeName: 'aria-label',
    originalValueAttribute: _originalAriaLabelAttribute,
    value: searchLabel,
  );
}

String _searchBridgeLabel(web.HTMLElement bridgeElement) {
  final bridgeRect = bridgeElement.getBoundingClientRect();
  final candidates = web.document.querySelectorAll(
    'input[aria-label], textarea[aria-label]',
  );
  for (var index = 0; index < candidates.length; index += 1) {
    final candidateNode = candidates.item(index);
    if (candidateNode == null) {
      continue;
    }
    final candidate = candidateNode as web.HTMLElement;
    if (!_isVisible(candidate)) {
      continue;
    }
    final candidateRect = candidate.getBoundingClientRect();
    final overlapsBridge =
        candidateRect.left < bridgeRect.right &&
        candidateRect.right > bridgeRect.left &&
        candidateRect.top < bridgeRect.bottom &&
        candidateRect.bottom > bridgeRect.top;
    if (!overlapsBridge) {
      continue;
    }
    return _elementAccessibleLabel(candidate);
  }
  return '';
}

void _setManagedAttribute({
  required web.Element element,
  required String attributeName,
  required String originalValueAttribute,
  required String value,
}) {
  if (!element.hasAttribute(originalValueAttribute)) {
    element.setAttribute(
      originalValueAttribute,
      element.getAttribute(attributeName) ?? _missingTabIndexSentinel,
    );
  }
  element.setAttribute(attributeName, value);
}

void _restoreManagedAttribute(
  web.Element element, {
  required String attributeName,
  required String originalValueAttribute,
}) {
  final originalValue = element.getAttribute(originalValueAttribute);
  if (originalValue == null) {
    return;
  }
  if (originalValue == _missingTabIndexSentinel) {
    element.removeAttribute(attributeName);
  } else {
    element.setAttribute(attributeName, originalValue);
  }
  element.removeAttribute(originalValueAttribute);
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

const String _managedTabOrderAttribute = 'data-trackstate-managed-tab-order';
const String _originalTabIndexAttribute =
    'data-trackstate-managed-original-tabindex';
const String _originalRoleAttribute = 'data-trackstate-managed-original-role';
const String _originalAriaLabelAttribute =
    'data-trackstate-managed-original-aria-label';
const String _missingTabIndexSentinel = '__trackstate_missing_tabindex__';
