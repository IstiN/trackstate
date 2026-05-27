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
  bool respectNativeDomOrder = true,
}) {
  if (currentIndex < 0 || currentIndex >= focusStops.length) {
    return null;
  }

  final triggerIndex = focusStops.indexWhere(
    (stop) => stop.isFocusable && stop.isWorkspaceSwitcherTrigger,
  );
  final inPanelIndices = _visuallyOrderedMatchingIndices(
    focusStops,
    matches: (stop) =>
        stop.isFocusable &&
        stop.isWithinWorkspaceSwitcher &&
        !stop.isWorkspaceSwitcherTrigger,
  );
  if (inPanelIndices.isEmpty) {
    return null;
  }

  final desiredIndex = switch (currentIndex) {
    final index when triggerIndex != -1 && index == triggerIndex => backwards
        ? inPanelIndices.last
        : inPanelIndices.first,
    final index when _isInPanelControl(focusStops[index]) =>
        _adjacentVisualInPanelIndex(
          inPanelIndices: inPanelIndices,
          currentIndex: index,
          backwards: backwards,
        ),
    _ => null,
  };
  if (desiredIndex == null) {
    return null;
  }
  final currentStop = focusStops[currentIndex];
  final shouldTrustNativeDomOrder =
      respectNativeDomOrder &&
      !currentStop.isWithinWorkspaceRow &&
      !currentStop.isWorkspaceSwitcherTrigger;
  if (shouldTrustNativeDomOrder) {
    final nativeIndex = _nextFocusableIndex(
      focusStops,
      currentIndex: currentIndex,
      backwards: backwards,
    );
    if (nativeIndex == desiredIndex) {
      return null;
    }
  }
  return desiredIndex;
}

bool _isInPanelControl(BrowserWorkspaceSwitcherTabStopSnapshot stop) {
  return stop.isFocusable &&
      stop.isWithinWorkspaceSwitcher &&
      !stop.isWorkspaceSwitcherTrigger;
}

int? _adjacentVisualInPanelIndex({
  required List<int> inPanelIndices,
  required int currentIndex,
  required bool backwards,
}) {
  final currentPosition = inPanelIndices.indexOf(currentIndex);
  if (currentPosition == -1) {
    return null;
  }
  final nextPosition = backwards
      ? (currentPosition == 0 ? inPanelIndices.length - 1 : currentPosition - 1)
      : (currentPosition == inPanelIndices.length - 1
            ? 0
            : currentPosition + 1);
  return inPanelIndices[nextPosition];
}

List<int> _visuallyOrderedMatchingIndices(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops, {
  required bool Function(BrowserWorkspaceSwitcherTabStopSnapshot stop) matches,
}) {
  final matchingIndices = <int>[];
  for (var index = 0; index < stops.length; index += 1) {
    final stop = stops[index];
    if (!matches(stop)) {
      continue;
    }
    matchingIndices.add(index);
  }
  matchingIndices.sort(
    (leftIndex, rightIndex) =>
        _compareVisualOrder(stops[leftIndex], stops[rightIndex]),
  );
  return matchingIndices;
}

int? _nextFocusableIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops, {
  required int currentIndex,
  required bool backwards,
}) {
  if (!backwards) {
    for (var index = currentIndex + 1; index < stops.length; index += 1) {
      if (stops[index].isFocusable) {
        return index;
      }
    }
    return null;
  }
  for (var index = currentIndex - 1; index >= 0; index -= 1) {
    if (stops[index].isFocusable) {
      return index;
    }
  }
  return null;
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
