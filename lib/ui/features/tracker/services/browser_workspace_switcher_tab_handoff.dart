class BrowserWorkspaceSwitcherTabStopSnapshot {
  const BrowserWorkspaceSwitcherTabStopSnapshot({
    required this.isFocusable,
    required this.isWithinWorkspaceSwitcher,
    required this.isWithinWorkspaceRow,
    required this.isSelectedWorkspaceRow,
    required this.isWorkspaceSwitcherTrigger,
  });

  final bool isFocusable;
  final bool isWithinWorkspaceSwitcher;
  final bool isWithinWorkspaceRow;
  final bool isSelectedWorkspaceRow;
  final bool isWorkspaceSwitcherTrigger;
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
  final firstExternalControlIndex = triggerIndex == -1
      ? -1
      : _firstExternalControlIndex(focusStops, startIndex: triggerIndex + 1);
  if (!backwards &&
      triggerIndex != -1 &&
      firstExternalControlIndex != -1 &&
      currentIndex == triggerIndex) {
    return firstExternalControlIndex;
  }
  if (backwards &&
      triggerIndex != -1 &&
      firstExternalControlIndex != -1 &&
      currentIndex == firstExternalControlIndex) {
    return triggerIndex;
  }

  final selectedRowIndex = focusStops.indexWhere(
    (stop) => stop.isFocusable && stop.isSelectedWorkspaceRow,
  );
  if (selectedRowIndex == -1) {
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

  if (!backwards) {
    return currentIndex == selectedRowIndex ? firstPostRowControlIndex : null;
  }

  return currentIndex == firstPostRowControlIndex ? selectedRowIndex : null;
}

int _lastWorkspaceRowIndex(List<BrowserWorkspaceSwitcherTabStopSnapshot> stops) {
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

int _firstExternalControlIndex(
  List<BrowserWorkspaceSwitcherTabStopSnapshot> stops, {
  required int startIndex,
}) {
  for (var index = startIndex; index < stops.length; index += 1) {
    final stop = stops[index];
    if (stop.isFocusable && !stop.isWithinWorkspaceSwitcher) {
      return index;
    }
  }
  return -1;
}
