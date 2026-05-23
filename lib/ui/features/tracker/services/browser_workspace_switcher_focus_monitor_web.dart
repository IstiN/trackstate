import 'dart:async';
import 'dart:js_interop';
import 'dart:math' as math;

import 'package:flutter/foundation.dart' show VoidCallback;
import 'package:web/web.dart' as web;

import 'browser_workspace_switcher_focus_matcher.dart';
import 'browser_workspace_switcher_scroll_logic.dart';
import 'browser_workspace_switcher_tab_handoff.dart';

class BrowserViewportScrollSnapshot {
  const BrowserViewportScrollSnapshot(this._targets);

  final List<_BrowserViewportTrackedScrollTarget> _targets;

  bool get isEmpty => _targets.isEmpty;
}

class _BrowserViewportTrackedScrollTarget {
  const _BrowserViewportTrackedScrollTarget({
    required this.target,
    this.element,
  });

  final BrowserWorkspaceSwitcherTrackedScrollTarget target;
  final web.HTMLElement? element;
}

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
  required VoidCallback onBrowserFocusOutside,
  required void Function(String key) onBrowserBoundaryKey,
}) {
  final keydownListener = ((web.Event event) {
    final keyboardEvent = event as web.KeyboardEvent;
    final ancestors = _activeBrowserFocusAncestors();
    if (keyboardEvent.key == 'Tab') {
      final tabMoveResult = _moveBrowserWorkspaceSwitcherTabFocus(
        backwards: keyboardEvent.shiftKey,
      );
      if (tabMoveResult != _BrowserWorkspaceSwitcherTabMoveResult.none) {
        keyboardEvent.preventDefault();
      }
      if (tabMoveResult ==
          _BrowserWorkspaceSwitcherTabMoveResult.outsideWorkspaceSwitcher) {
        onBrowserFocusOutside();
      }
      onBrowserTab();
      return;
    }

    if (!browserWorkspaceSwitcherShouldPreventDefaultKey(
      key: keyboardEvent.key,
      ancestors: ancestors,
    )) {
      return;
    }

    keyboardEvent.preventDefault();
    if (keyboardEvent.key != 'Home' && keyboardEvent.key != 'End') {
      return;
    }

    onBrowserBoundaryKey(keyboardEvent.key);
  }).toJS;
  final focusinListener = ((web.Event _) {
    if (isBrowserFocusWithinWorkspaceSwitcher()) {
      return;
    }
    onBrowserFocusOutside();
  }).toJS;

  web.window.addEventListener('keydown', keydownListener, true.toJS);
  web.window.addEventListener('focusin', focusinListener, true.toJS);
  return BrowserWorkspaceSwitcherFocusMonitorSubscription(() {
    web.window.removeEventListener('keydown', keydownListener, true.toJS);
    web.window.removeEventListener('focusin', focusinListener, true.toJS);
  });
}

bool isBrowserFocusWithinWorkspaceSwitcher() {
  return browserFocusWithinWorkspaceSwitcher(
    ancestors: _activeBrowserFocusAncestors(),
  );
}

BrowserViewportScrollSnapshot captureBrowserViewportScrollSnapshot() {
  final elementCandidates = _backgroundScrollElementCandidates();
  final targets = captureBrowserWorkspaceSwitcherScrollTargets(
    windowCandidate: _windowBackgroundScrollCandidate(),
    elementCandidates: [
      for (final candidate in elementCandidates) candidate.candidate,
    ],
  );
  if (targets.isEmpty) {
    return const BrowserViewportScrollSnapshot([]);
  }
  final elementsByKey = <String, web.HTMLElement>{
    for (final candidate in elementCandidates)
      candidate.candidate.key: candidate.element,
  };
  return BrowserViewportScrollSnapshot([
    for (final target in targets)
      _BrowserViewportTrackedScrollTarget(
        target: target,
        element: target.isWindow ? null : elementsByKey[target.key],
      ),
  ]);
}

void restoreBrowserViewportScrollSnapshot({
  required BrowserViewportScrollSnapshot snapshot,
}) {
  if (snapshot.isEmpty) {
    return;
  }
  Timer? timer;
  var attemptCount = 0;

  void restore() {
    attemptCount += 1;
    final currentElementScrollYByKey = <String, double>{};
    for (final target in snapshot._targets) {
      final element = target.element;
      if (element == null || !element.isConnected) {
        continue;
      }
      currentElementScrollYByKey[target.target.key] = element.scrollTop
          .toDouble();
    }
    final targetsToRestore =
        browserWorkspaceSwitcherScrollTargetsNeedingRestore(
          capturedTargets: [
            for (final target in snapshot._targets) target.target,
          ],
          currentWindowScrollY: web.window.scrollY,
          currentElementScrollYByKey: currentElementScrollYByKey,
        );
    for (final target in targetsToRestore) {
      if (target.isWindow) {
        web.window.scrollTo(web.window.scrollX.toJS, target.scrollY);
        continue;
      }
      final element = _snapshotElementForKey(
        snapshot: snapshot,
        key: target.key,
      );
      if (element == null || !element.isConnected) {
        continue;
      }
      element.scrollTop = target.scrollY.round();
    }
    if (targetsToRestore.isEmpty || attemptCount >= 12) {
      timer?.cancel();
      timer = null;
    }
  }

  timer = Timer.periodic(const Duration(milliseconds: 16), (_) => restore());
  Timer.run(restore);
}

BrowserWorkspaceSwitcherScrollCandidate _windowBackgroundScrollCandidate() {
  final scrollingElement =
      web.document.scrollingElement ??
      web.document.documentElement ??
      web.document.body;
  final windowScrollHeight = math.max(
    math.max(
      scrollingElement?.scrollHeight.toDouble() ?? 0,
      web.document.documentElement?.scrollHeight.toDouble() ?? 0,
    ),
    web.document.body?.scrollHeight.toDouble() ?? 0,
  );
  final windowViewportHeight = web.window.innerHeight.toDouble();
  final windowMaxScrollY = math.max(
    0.0,
    windowScrollHeight - windowViewportHeight,
  );
  return BrowserWorkspaceSwitcherScrollCandidate(
    key: 'window',
    scrollY: web.window.scrollY,
    maxScrollY: windowMaxScrollY,
    width: web.window.innerWidth.toDouble(),
    height: windowViewportHeight,
    explicitlyScrollable: true,
    isWindow: true,
  );
}

class _BrowserBackgroundScrollElementCandidate {
  const _BrowserBackgroundScrollElementCandidate({
    required this.candidate,
    required this.element,
  });

  final BrowserWorkspaceSwitcherScrollCandidate candidate;
  final web.HTMLElement element;
}

List<_BrowserBackgroundScrollElementCandidate>
_backgroundScrollElementCandidates() {
  final minimumWidth = math.min(web.window.innerWidth * 0.35, 280);
  final minimumHeight = math.min(web.window.innerHeight * 0.35, 200);
  final candidates = <_BrowserBackgroundScrollElementCandidate>[];
  final seenKeys = <String>{};
  final nodes = web.document.querySelectorAll(
    [
      'flt-semantics-host',
      'flt-semantics',
      'main',
      'section',
      '[role="main"]',
      '[style*="overflow"]',
      '[class*="scroll"]',
      '[class*="viewport"]',
    ].join(','),
  );
  for (var index = 0; index < nodes.length; index += 1) {
    final node = nodes.item(index);
    if (node == null) {
      continue;
    }
    final element = node as web.HTMLElement;
    if (!_isVisible(element)) {
      continue;
    }
    final rect = element.getBoundingClientRect();
    final style = web.window.getComputedStyle(element);
    if (rect.width < minimumWidth || rect.height < minimumHeight) {
      continue;
    }
    final key = _browserBackgroundScrollCandidateKey(
      element: element,
      index: index,
    );
    if (!seenKeys.add(key)) {
      continue;
    }
    final candidate = BrowserWorkspaceSwitcherScrollCandidate(
      key: key,
      scrollY: element.scrollTop.toDouble(),
      maxScrollY: math.max(
        0,
        element.scrollHeight.toDouble() - element.clientHeight.toDouble(),
      ),
      width: rect.width,
      height: rect.height,
      explicitlyScrollable:
          style.overflowY == 'scroll' || style.overflowY == 'auto',
      textSummary: _normalizeText(element.innerText),
    );
    candidates.add(
      _BrowserBackgroundScrollElementCandidate(
        candidate: candidate,
        element: element,
      ),
    );
  }
  return candidates;
}

web.HTMLElement? _snapshotElementForKey({
  required BrowserViewportScrollSnapshot snapshot,
  required String key,
}) {
  for (final candidate in snapshot._targets) {
    if (candidate.target.key == key) {
      return candidate.element;
    }
  }
  return null;
}

String _browserBackgroundScrollCandidateKey({
  required web.HTMLElement element,
  required int index,
}) {
  final semanticsIdentifier = element.getAttribute('flt-semantics-identifier');
  if (semanticsIdentifier case final value? when value.trim().isNotEmpty) {
    return 'semantics:$value';
  }
  if (element.id case final value when value.trim().isNotEmpty) {
    return 'id:${element.localName}:$value';
  }
  return 'element:${element.localName}:$index';
}

String _normalizeText(String? value) {
  return (value ?? '').replaceAll(RegExp(r'\s+'), ' ').trim();
}

_BrowserWorkspaceSwitcherTabMoveResult _moveBrowserWorkspaceSwitcherTabFocus({
  required bool backwards,
}) {
  final activeElement = web.document.activeElement;
  if (activeElement is! web.Element) {
    return _BrowserWorkspaceSwitcherTabMoveResult.none;
  }

  final focusTargets = _visibleDocumentFocusTargets();
  final currentIndex = _focusTargetIndexForActiveElement(
    targets: focusTargets,
    activeElement: activeElement,
  );
  if (currentIndex == null) {
    return _BrowserWorkspaceSwitcherTabMoveResult.none;
  }

  final targetIndex = browserWorkspaceSwitcherTabHandoffIndex(
    focusStops: [
      for (final target in focusTargets)
        () {
          final rect = target.element.getBoundingClientRect();
          return BrowserWorkspaceSwitcherTabStopSnapshot(
            isFocusable: true,
            isWithinWorkspaceSwitcher: target.isWithinWorkspaceSwitcher,
            isWithinWorkspaceRow: target.isWithinWorkspaceRow,
            isSelectedWorkspaceRow: target.isSelectedWorkspaceRow,
            isWorkspaceSwitcherTrigger: target.isWorkspaceSwitcherTrigger,
            visualTop: rect.top,
            visualLeft: rect.left,
          );
        }(),
    ],
    currentIndex: currentIndex,
    backwards: backwards,
  );
  if (targetIndex == null) {
    return _BrowserWorkspaceSwitcherTabMoveResult.none;
  }

  if (!_focusElement(focusTargets[targetIndex].element)) {
    return _BrowserWorkspaceSwitcherTabMoveResult.none;
  }
  return focusTargets[targetIndex].isWithinWorkspaceSwitcher
      ? _BrowserWorkspaceSwitcherTabMoveResult.withinWorkspaceSwitcher
      : _BrowserWorkspaceSwitcherTabMoveResult.outsideWorkspaceSwitcher;
}

BrowserWorkspaceSwitcherFocusRequest requestBrowserWorkspaceSwitcherFocus({
  required String semanticsIdentifier,
}) {
  Timer? timer;
  var attemptCount = 0;
  var consecutiveFocusedFrames = 0;

  void tryFocus() {
    attemptCount += 1;
    if (_focusBrowserFocusableControl(semanticsIdentifier) ||
        _focusSemanticsElement(semanticsIdentifier)) {
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
      htmlElement.focus(web.FocusOptions(preventScroll: true));
    }
    final activeElement = web.document.activeElement;
    if (activeElement == candidate || candidate.contains(activeElement)) {
      return true;
    }
  }
  return false;
}

bool _focusBrowserFocusableControl(String focusTargetId) {
  final element = _firstVisibleFocusableBridgeElement(
    focusTargetId: focusTargetId,
    assignedElements: const <web.Element>[],
  );
  if (element == null) {
    return false;
  }
  return _focusElement(element);
}

List<BrowserWorkspaceSwitcherFocusAncestorSnapshot>
_activeBrowserFocusAncestors() {
  final ancestors = <BrowserWorkspaceSwitcherFocusAncestorSnapshot>[];
  web.Element? element = web.document.activeElement;
  while (element != null) {
    ancestors.add(
      BrowserWorkspaceSwitcherFocusAncestorSnapshot(
        semanticsIdentifier:
            element.getAttribute(_browserFocusIdAttribute) ??
            element.getAttribute(_browserFocusPanelIdAttribute) ??
            element.getAttribute(_browserFocusRowIdAttribute) ??
            element.getAttribute('flt-semantics-identifier'),
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
    '[flt-semantics-identifier^="$prefix"], '
    '[$_browserFocusRowIdAttribute]',
  );
  for (var index = 0; index < elements.length; index++) {
    final node = elements.item(index);
    if (node == null) {
      continue;
    }
    final element = node as web.HTMLElement;
    final identifier =
        element.getAttribute(_browserFocusRowIdAttribute) ??
        element.getAttribute('flt-semantics-identifier');
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
    required this.isWithinWorkspaceSwitcher,
    required this.isWithinWorkspaceRow,
    required this.isSelectedWorkspaceRow,
    required this.isWorkspaceSwitcherTrigger,
  });

  final web.Element element;
  final bool isWithinWorkspaceSwitcher;
  final bool isWithinWorkspaceRow;
  final bool isSelectedWorkspaceRow;
  final bool isWorkspaceSwitcherTrigger;
}

enum _BrowserWorkspaceSwitcherTabMoveResult {
  none,
  withinWorkspaceSwitcher,
  outsideWorkspaceSwitcher,
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
    if (!_isVisible(element) ||
        !_isFocusable(element) ||
        !_isMeaningfullyInteractiveFocusTarget(element)) {
      continue;
    }
    seen.add(element);
    targets.add(
      _WorkspaceSwitcherFocusTarget(
        element: element,
        isWithinWorkspaceSwitcher:
            _workspaceSwitcherElementFor(element) != null ||
            _workspaceSwitcherTriggerElementFor(element) != null,
        isWithinWorkspaceRow: _workspaceRowElementFor(element) != null,
        isSelectedWorkspaceRow: _isSelectedWorkspaceRowElement(element),
        isWorkspaceSwitcherTrigger:
            _workspaceSwitcherTriggerElementFor(element) != null,
      ),
    );
  }
  return targets;
}

bool _isMeaningfullyInteractiveFocusTarget(web.Element element) {
  final tagName = element.tagName.toLowerCase();
  if (tagName == 'button' ||
      tagName == 'input' ||
      tagName == 'textarea' ||
      tagName == 'select') {
    return true;
  }

  if (element.getAttribute(_browserFocusIdAttribute) case final String _?) {
    return true;
  }
  if (element.getAttribute(_browserFocusPanelIdAttribute)
      case final String _?) {
    return true;
  }
  if (element.getAttribute(_browserFocusRowIdAttribute) case final String _?) {
    return true;
  }

  final role = element.getAttribute('role')?.trim().toLowerCase();
  switch (role) {
    case 'button':
    case 'checkbox':
    case 'combobox':
    case 'link':
    case 'menuitem':
    case 'option':
    case 'radio':
    case 'searchbox':
    case 'switch':
    case 'tab':
    case 'textbox':
      return true;
  }

  return false;
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
    if (_matchesDesktopPrimaryNavigationTarget(
      candidate: candidate,
      activeElement: activeElement,
    )) {
      return index;
    }
  }
  return null;
}

bool _matchesDesktopPrimaryNavigationTarget({
  required web.HTMLElement candidate,
  required web.Element activeElement,
}) {
  if (candidate == activeElement || candidate.contains(activeElement)) {
    return true;
  }

  final semanticsIdentifier = candidate.getAttribute(
    'flt-semantics-identifier',
  );
  if (semanticsIdentifier != browserDesktopSearchInputSemanticsIdentifier) {
    return false;
  }

  final candidateLabel = _normalizeLabel(_elementAccessibleLabel(candidate));
  if (candidateLabel.isEmpty) {
    return false;
  }
  return candidateLabel ==
      _normalizeLabel(_elementAccessibleLabel(activeElement));
}

bool _focusElement(web.Element element) {
  final htmlElement = element as web.HTMLElement;
  htmlElement.focus(web.FocusOptions(preventScroll: true));
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
  final browserControlAncestor = _ancestorWithAttribute(
    element,
    attributeName: _browserFocusRowIdAttribute,
    matches: (value) =>
        value.startsWith(browserWorkspaceSwitcherRowSemanticsIdentifierPrefix),
  );
  if (browserControlAncestor != null) {
    return browserControlAncestor;
  }
  return _ancestorWithSemanticsIdentifier(
    element,
    (identifier) => identifier.startsWith(
      browserWorkspaceSwitcherRowSemanticsIdentifierPrefix,
    ),
  );
}

web.Element? _workspaceSwitcherElementFor(web.Element element) {
  final browserControlAncestor = _ancestorWithAttribute(
    element,
    attributeName: _browserFocusPanelIdAttribute,
    matches: (value) => value == browserWorkspaceSwitcherSemanticsIdentifier,
  );
  if (browserControlAncestor != null) {
    return browserControlAncestor;
  }
  final semanticsAncestor = _ancestorWithSemanticsIdentifier(
    element,
    (identifier) => identifier == browserWorkspaceSwitcherSemanticsIdentifier,
  );
  if (semanticsAncestor != null) {
    return semanticsAncestor;
  }
  return _overlappingWorkspaceSwitcherPanel(element);
}

web.Element? _workspaceSwitcherTriggerElementFor(web.Element element) {
  final browserControlAncestor = _ancestorWithAttribute(
    element,
    attributeName: _browserFocusIdAttribute,
    matches: (value) =>
        value == browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
  );
  if (browserControlAncestor != null) {
    return browserControlAncestor;
  }
  return _ancestorWithSemanticsIdentifier(
    element,
    (identifier) =>
        identifier == browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
  );
}

web.Element? _ancestorWithSemanticsIdentifier(
  web.Element element,
  bool Function(String identifier) matches,
) {
  web.Element? current = element;
  while (current != null) {
    final semanticsIdentifier = current.getAttribute(
      'flt-semantics-identifier',
    );
    if (semanticsIdentifier case final value? when matches(value)) {
      return current;
    }
    current = current.parentElement;
  }
  return null;
}

web.Element? _ancestorWithAttribute(
  web.Element element, {
  required String attributeName,
  required bool Function(String value) matches,
}) {
  web.Element? current = element;
  while (current != null) {
    final attributeValue = current.getAttribute(attributeName);
    if (attributeValue case final value? when matches(value)) {
      return current;
    }
    current = current.parentElement;
  }
  return null;
}

web.Element? _overlappingWorkspaceSwitcherPanel(web.Element element) {
  final htmlElement = element as web.HTMLElement;
  if (!_isWorkspaceSwitcherPanelOverlapCandidate(htmlElement)) {
    return null;
  }
  final elementRect = htmlElement.getBoundingClientRect();
  if (elementRect.width <= 0 || elementRect.height <= 0) {
    return null;
  }
  final panelElements = web.document.querySelectorAll(
    '[flt-semantics-identifier="$browserWorkspaceSwitcherSemanticsIdentifier"]',
  );
  for (var index = 0; index < panelElements.length; index += 1) {
    final panelNode = panelElements.item(index);
    if (panelNode == null) {
      continue;
    }
    final panelElement = panelNode as web.Element;
    if (!_isVisible(panelElement)) {
      continue;
    }
    final panelRect = panelElement.getBoundingClientRect();
    if (_rectanglesOverlap(a: elementRect, b: panelRect)) {
      return panelElement;
    }
  }
  return null;
}

bool _isWorkspaceSwitcherPanelOverlapCandidate(web.HTMLElement element) {
  final tagName = element.tagName.toLowerCase();
  if (tagName == 'input' || tagName == 'textarea' || tagName == 'select') {
    return true;
  }
  final role = element.getAttribute('role')?.trim().toLowerCase();
  return role == 'textbox' || role == 'combobox';
}

bool _rectanglesOverlap({required web.DOMRect a, required web.DOMRect b}) {
  return a.left < b.right &&
      a.right > b.left &&
      a.top < b.bottom &&
      a.bottom > b.top;
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
  final bridgeElement = _firstVisibleFocusableBridgeElement(
    focusTargetId: semanticsIdentifier,
    assignedElements: assignedElements,
  );
  if (bridgeElement != null) {
    return bridgeElement;
  }
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

web.HTMLElement? _firstVisibleFocusableBridgeElement({
  required String focusTargetId,
  required List<web.Element> assignedElements,
}) {
  final candidates = web.document.querySelectorAll(
    '[$_browserFocusIdAttribute="$focusTargetId"]',
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
    if (candidate.tabIndex < 0 || candidate.getAttribute('disabled') != null) {
      continue;
    }
    return candidate;
  }
  return null;
}

bool _isSelectedWorkspaceRowElement(web.Element element) {
  if (element.getAttribute('aria-current') == 'true') {
    return true;
  }
  final semanticsIdentifier =
      element.getAttribute(_browserFocusRowIdAttribute) ??
      element.getAttribute('flt-semantics-identifier');
  if (semanticsIdentifier?.startsWith(
        browserWorkspaceSwitcherRowSemanticsIdentifierPrefix,
      ) !=
      true) {
    return false;
  }
  final htmlElement = element as web.HTMLElement;
  return htmlElement.tabIndex == 0;
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
    'button, flt-semantics[role="button"], [role="button"], input[aria-label], textarea[aria-label]',
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

const String _managedTabOrderAttribute = 'data-trackstate-managed-tab-order';
const String _originalTabIndexAttribute =
    'data-trackstate-managed-original-tabindex';
const String _originalRoleAttribute = 'data-trackstate-managed-original-role';
const String _originalAriaLabelAttribute =
    'data-trackstate-managed-original-aria-label';
const String _browserFocusIdAttribute = 'data-trackstate-browser-focus-id';
const String _browserFocusPanelIdAttribute =
    'data-trackstate-browser-focus-panel-id';
const String _browserFocusRowIdAttribute =
    'data-trackstate-browser-focus-row-id';
const String _missingTabIndexSentinel = '__trackstate_missing_tabindex__';
