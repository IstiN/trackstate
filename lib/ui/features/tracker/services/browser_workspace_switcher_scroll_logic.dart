class BrowserWorkspaceSwitcherScrollCandidate {
  const BrowserWorkspaceSwitcherScrollCandidate({
    required this.key,
    required this.scrollY,
    required this.maxScrollY,
    required this.width,
    required this.height,
    required this.explicitlyScrollable,
    this.textSummary = '',
    this.isWindow = false,
  });

  final String key;
  final double scrollY;
  final double maxScrollY;
  final double width;
  final double height;
  final bool explicitlyScrollable;
  final String textSummary;
  final bool isWindow;
}

class BrowserWorkspaceSwitcherTrackedScrollTarget {
  const BrowserWorkspaceSwitcherTrackedScrollTarget({
    required this.key,
    required this.scrollY,
    required this.isWindow,
  });

  final String key;
  final double scrollY;
  final bool isWindow;
}

List<BrowserWorkspaceSwitcherTrackedScrollTarget>
captureBrowserWorkspaceSwitcherScrollTargets({
  required BrowserWorkspaceSwitcherScrollCandidate windowCandidate,
  required Iterable<BrowserWorkspaceSwitcherScrollCandidate> elementCandidates,
}) {
  final sortedCandidates =
      [
        for (final candidate in elementCandidates)
          if (_isViableBackgroundScrollCandidate(candidate)) candidate,
      ]..sort(
        (left, right) => _backgroundScrollCandidateScore(
          right,
        ).compareTo(_backgroundScrollCandidateScore(left)),
      );

  final targets = <BrowserWorkspaceSwitcherTrackedScrollTarget>[];
  if (sortedCandidates case [final strongestCandidate, ...]) {
    targets.add(
      BrowserWorkspaceSwitcherTrackedScrollTarget(
        key: strongestCandidate.key,
        scrollY: strongestCandidate.scrollY,
        isWindow: false,
      ),
    );
  }
  if (windowCandidate.maxScrollY > 0) {
    targets.add(
      BrowserWorkspaceSwitcherTrackedScrollTarget(
        key: windowCandidate.key,
        scrollY: windowCandidate.scrollY,
        isWindow: true,
      ),
    );
  }
  return targets;
}

List<BrowserWorkspaceSwitcherTrackedScrollTarget>
browserWorkspaceSwitcherScrollTargetsNeedingRestore({
  required Iterable<BrowserWorkspaceSwitcherTrackedScrollTarget>
  capturedTargets,
  required double currentWindowScrollY,
  required Map<String, double> currentElementScrollYByKey,
  double tolerance = 1,
}) {
  final targetsToRestore = <BrowserWorkspaceSwitcherTrackedScrollTarget>[];
  for (final target in capturedTargets) {
    final currentScrollY = target.isWindow
        ? currentWindowScrollY
        : currentElementScrollYByKey[target.key];
    if (currentScrollY == null) {
      continue;
    }
    if ((currentScrollY - target.scrollY).abs() > tolerance) {
      targetsToRestore.add(target);
    }
  }
  return targetsToRestore;
}

bool _isViableBackgroundScrollCandidate(
  BrowserWorkspaceSwitcherScrollCandidate candidate,
) {
  if (candidate.maxScrollY <= 40) {
    return false;
  }
  if (candidate.width <= 0 || candidate.height <= 0) {
    return false;
  }
  return !candidate.textSummary.startsWith('Workspace switcher');
}

double _backgroundScrollCandidateScore(
  BrowserWorkspaceSwitcherScrollCandidate candidate,
) {
  final area = candidate.width * candidate.height;
  final overflowBonus = candidate.explicitlyScrollable ? 1000000 : 0;
  return overflowBonus + area + candidate.maxScrollY;
}
