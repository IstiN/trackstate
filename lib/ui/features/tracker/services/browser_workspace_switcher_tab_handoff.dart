class BrowserWorkspaceSwitcherTabStopSnapshot {
  const BrowserWorkspaceSwitcherTabStopSnapshot({
    required this.isFocusable,
    required this.isWithinWorkspaceSwitcher,
    required this.isWithinWorkspaceRow,
    required this.isSelectedWorkspaceRow,
    required this.isWorkspaceSwitcherTrigger,
    this.visualTop,
    this.visualLeft,
  });

  final bool isFocusable;
  final bool isWithinWorkspaceSwitcher;
  final bool isWithinWorkspaceRow;
  final bool isSelectedWorkspaceRow;
  final bool isWorkspaceSwitcherTrigger;
  final double? visualTop;
  final double? visualLeft;
}

int? browserWorkspaceSwitcherTabHandoffIndex({
  required List<BrowserWorkspaceSwitcherTabStopSnapshot> focusStops,
  required int currentIndex,
  required bool backwards,
}) {
  if (currentIndex < 0 || currentIndex >= focusStops.length) {
    return null;
  }

  final selectedRowIndex = focusStops.indexWhere(
    (stop) => stop.isFocusable && stop.isSelectedWorkspaceRow,
  );
  if (selectedRowIndex == -1) {
    return null;
  }

  final triggerIndex = focusStops.indexWhere(
    (stop) => stop.isFocusable && stop.isWorkspaceSwitcherTrigger,
  );
  if (!backwards && triggerIndex != -1 && currentIndex == triggerIndex) {
    // Forward Tab from trigger wraps to the selected row inside the panel,
    // keeping focus trapped within the workspace switcher.
    return selectedRowIndex;
  }
  if (backwards && triggerIndex != -1 && currentIndex == triggerIndex) {
    // Reverse Tab from trigger wraps to the last in-panel control (or the
    // selected row when no post-row controls exist).
    final lastInPanel = _lastInPanelControlIndex(focusStops);
    if (lastInPanel != -1) {
      return lastInPanel;
    }
    return selectedRowIndex;
  }
  if (backwards && currentIndex == selectedRowIndex) {
    final lastInPanelControlIndex = _lastInPanelControlIndex(focusStops);
    if (lastInPanelControlIndex != -1) {
      return lastInPanelControlIndex;
    }
    if (triggerIndex != -1) {
      return triggerIndex;
    }
    return null;
  }

  final lastWorkspaceRowIndex = _lastWorkspaceRowIndex(focusStops);
  if (lastWorkspaceRowIndex == -1) {
    return null;
  }

  final firstPostRowControlIndex = _firstPostRowControlIndex(focusStops);
  if (firstPostRowControlIndex == -1) {
    return null;
  }
  final lastPostRowControlIndex = _lastPostRowControlIndex(
    focusStops,
    startIndex: firstPostRowControlIndex,
  );

  if (!backwards) {
    if (currentIndex == selectedRowIndex) {
      return firstPostRowControlIndex;
    }
    // Forward Tab from the last post-row control wraps to the trigger (or
    // back to the selected row when no trigger exists) to complete the
    // focus trap loop.
    return currentIndex == lastPostRowControlIndex
        ? (triggerIndex != -1 ? triggerIndex : selectedRowIndex)
        : null;
  }

  return currentIndex == firstPostRowControlIndex ? selectedRowIndex : null;
}

int _lastInPanelControlIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops,
) {
  return _lastVisuallyOrderedMatchingIndex(
    stops,
    matches: (stop) =>
        stop.isFocusable &&
        stop.isWithinWorkspaceSwitcher &&
        !stop.isWithinWorkspaceRow &&
        !stop.isWorkspaceSwitcherTrigger,
  );
}

int _lastWorkspaceRowIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops,
) {
  for (var index = stops.length - 1; index >= 0; index -= 1) {
    if (stops[index].isFocusable && stops[index].isWithinWorkspaceRow) {
      return index;
    }
  }
  return -1;
}

int _firstPostRowControlIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops,
) {
  return _firstVisuallyOrderedMatchingIndex(
    stops,
    matches: (stop) =>
        stop.isFocusable &&
        stop.isWithinWorkspaceSwitcher &&
        !stop.isWithinWorkspaceRow &&
        !stop.isWorkspaceSwitcherTrigger,
  );
}

int _lastPostRowControlIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops, {
  required int startIndex,
}) {
  for (var index = stops.length - 1; index >= startIndex; index -= 1) {
    final stop = stops[index];
    if (stop.isFocusable &&
        stop.isWithinWorkspaceSwitcher &&
        !stop.isWithinWorkspaceRow &&
        !stop.isWorkspaceSwitcherTrigger) {
      return index;
    }
  }
  return -1;
}

int _firstVisuallyOrderedMatchingIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops, {
  int startIndex = 0,
  required bool Function(BrowserWorkspaceSwitcherTabStopSnapshot stop) matches,
}) {
  var fallbackIndex = -1;
  var visuallyFirstIndex = -1;
  for (var index = startIndex; index < stops.length; index += 1) {
    final stop = stops[index];
    if (!matches(stop)) {
      continue;
    }
    fallbackIndex = fallbackIndex == -1 ? index : fallbackIndex;
    if (stop.visualTop == null || stop.visualLeft == null) {
      continue;
    }
    if (visuallyFirstIndex == -1 ||
        _compareVisualOrder(stops[visuallyFirstIndex], stop) > 0) {
      visuallyFirstIndex = index;
    }
  }
  return visuallyFirstIndex != -1 ? visuallyFirstIndex : fallbackIndex;
}

int _lastVisuallyOrderedMatchingIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops, {
  int startIndex = 0,
  required bool Function(BrowserWorkspaceSwitcherTabStopSnapshot stop) matches,
}) {
  var fallbackIndex = -1;
  var visuallyLastIndex = -1;
  for (var index = startIndex; index < stops.length; index += 1) {
    final stop = stops[index];
    if (!matches(stop)) {
      continue;
    }
    fallbackIndex = index;
    if (stop.visualTop == null || stop.visualLeft == null) {
      continue;
    }
    if (visuallyLastIndex == -1 ||
        _compareVisualOrder(stops[visuallyLastIndex], stop) < 0) {
      visuallyLastIndex = index;
    }
  }
  return visuallyLastIndex != -1 ? visuallyLastIndex : fallbackIndex;
}

int _compareVisualOrder(
  BrowserWorkspaceSwitcherTabStopSnapshot left,
  BrowserWorkspaceSwitcherTabStopSnapshot right,
) {
  final leftTop = left.visualTop;
  final rightTop = right.visualTop;
  if (leftTop != null && rightTop != null) {
    final topDelta = leftTop - rightTop;
    if (topDelta.abs() > 4) {
      return topDelta < 0 ? -1 : 1;
    }
  }

  final leftLeft = left.visualLeft;
  final rightLeft = right.visualLeft;
  if (leftLeft != null && rightLeft != null) {
    final leftDelta = leftLeft - rightLeft;
    if (leftDelta.abs() > 4) {
      return leftDelta < 0 ? -1 : 1;
    }
  }

  return 0;
}
