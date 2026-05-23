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

  final triggerIndex = focusStops.indexWhere(
    (stop) => stop.isFocusable && stop.isWorkspaceSwitcherTrigger,
  );
  final selectedRowIndex = focusStops.indexWhere(
    (stop) => stop.isFocusable && stop.isSelectedWorkspaceRow,
  );
  if (selectedRowIndex == -1) {
    return null;
  }

  if (!backwards && triggerIndex != -1 && currentIndex == triggerIndex) {
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

  final firstPostRowControlIndex = _firstPostRowControlIndex(
    focusStops,
    startIndex: lastWorkspaceRowIndex + 1,
  );
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
    return currentIndex == lastPostRowControlIndex ? selectedRowIndex : null;
  }

  return currentIndex == firstPostRowControlIndex ? selectedRowIndex : null;
}

int _lastInPanelControlIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops,
) {
  return _lastMatchingIndex(
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
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops, {
  required int startIndex,
}) {
  for (var index = startIndex; index < stops.length; index += 1) {
    final stop = stops[index];
    if (stop.isFocusable &&
        stop.isWithinWorkspaceSwitcher &&
        !stop.isWithinWorkspaceRow) {
      return index;
    }
  }
  return -1;
}

int _lastPostRowControlIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops, {
  required int startIndex,
}) {
  return _lastMatchingIndex(
    stops,
    startIndex: startIndex,
    matches: (stop) =>
        stop.isFocusable &&
        stop.isWithinWorkspaceSwitcher &&
        !stop.isWithinWorkspaceRow,
  );
}

int _lastMatchingIndex(
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
