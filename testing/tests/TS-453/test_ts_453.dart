import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/utils/color_contrast.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-453 loading state visual quality keeps loading affordances readable and interactive',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = _Ts453LoadingStateHarness(tester);

      try {
        final failures = <String>[];

        await screen.pumpApp(repository: const _Ts453BootstrapLoadingRepository());

        final initialVisibleTexts = screen.visibleTexts();
        final initialVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();
        for (final requiredText in const [
          'Dashboard',
          'Loading...',
          'Create issue',
          'Connect GitHub',
        ]) {
          if (!initialVisibleTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: the loading shell did not render the visible "$requiredText" text. '
              'Visible texts: ${_formatSnapshot(initialVisibleTexts)}.',
            );
          }
        }
        for (final requiredLabel in const [
          'Dashboard',
          'Dashboard Loading...',
        ]) {
          if (!initialVisibleSemantics.contains(requiredLabel)) {
            failures.add(
              'Step 1 failed: the loading dashboard shell did not expose the "$requiredLabel" semantics label. '
              'Visible semantics: ${_formatSnapshot(initialVisibleSemantics)}.',
            );
          }
        }

        await screen.openSection('JQL Search');

        final searchVisibleTexts = screen.visibleTexts();
        final searchVisibleSemantics = screen.visibleSemanticsLabelsSnapshot();
        for (final requiredText in const [
          'JQL Search',
          'Search issues',
          'Loading...',
        ]) {
          if (!searchVisibleTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: the JQL Search loading presenter did not render the visible "$requiredText" text. '
              'Visible texts: ${_formatSnapshot(searchVisibleTexts)}.',
            );
          }
        }
        if (screen.loadingRows().isEmpty) {
          failures.add(
            'Step 1 failed: the JQL Search loading presenter did not keep any visible result rows interactive while bootstrap loading was still in progress. '
            'Visible semantics: ${_formatSnapshot(searchVisibleSemantics)}.',
          );
        }

        final focusVisits = await screen.collectFocusVisits(
          <String, Finder>{
            'Create issue': screen.createIssueButton,
            'Connect GitHub': screen.connectGitHubButton,
            'JQL Search navigation': screen.navigationItem('JQL Search'),
            'Search issues field': screen.jqlSearchField,
            'First loading result': screen.loadingRows().firstOrNull ?? find.byType(SizedBox),
          },
          tabs: 40,
        );
        for (final requiredTarget in const [
          'Create issue',
          'Connect GitHub',
          'JQL Search navigation',
          'Search issues field',
          'First loading result',
        ]) {
          if (!focusVisits.contains(requiredTarget)) {
            failures.add(
              'Step 1 failed: keyboard Tab traversal during loading never reached "$requiredTarget". '
              'Observed focus visits: ${_formatSnapshot(focusVisits)}.',
            );
          }
        }

        final colors = screen.colors();
        final createIssueIdleBackground = screen.resolvedButtonBackground(
          screen.createIssueButton,
          const <WidgetState>{},
        );
        final createIssueHoverBackground = screen.resolvedButtonBackground(
          screen.createIssueButton,
          const <WidgetState>{WidgetState.hovered},
        );
        if (createIssueHoverBackground == createIssueIdleBackground) {
          failures.add(
            'Step 2 failed: the Create issue shell button did not expose a distinct hovered state. '
            'Idle background: ${_rgbHex(createIssueIdleBackground)}. Hovered background: ${_rgbHex(createIssueHoverBackground)}.',
          );
        }
        final createIssueFocusBackground = screen.resolvedButtonBackground(
          screen.createIssueButton,
          const <WidgetState>{WidgetState.focused},
        );
        if (createIssueFocusBackground == createIssueIdleBackground) {
          failures.add(
            'Step 2 failed: the Create issue shell button did not expose a distinct focused state. '
            'Idle background: ${_rgbHex(createIssueIdleBackground)}. Focused background: ${_rgbHex(createIssueFocusBackground)}.',
          );
        }

        final connectGitHubIdleBackground = screen.resolvedButtonBackground(
          screen.connectGitHubButton,
          const <WidgetState>{},
        );
        final connectGitHubHoverBackground = screen.resolvedButtonBackground(
          screen.connectGitHubButton,
          const <WidgetState>{WidgetState.hovered},
        );
        if (connectGitHubHoverBackground == connectGitHubIdleBackground) {
          failures.add(
            'Step 2 failed: the Connect GitHub shell button did not expose a distinct hovered state. '
            'Idle background: ${_rgbHex(connectGitHubIdleBackground)}. Hovered background: ${_rgbHex(connectGitHubHoverBackground)}.',
          );
        }

        final selectedJqlNavigationBackground = screen.navigationBackgroundColor(
          'JQL Search',
        );
        final selectedJqlNavigationText = screen.renderedTextColorWithin(
          screen.navigationItem('JQL Search'),
          'JQL Search',
        );
        if (!screen.isSelected(screen.navigationItem('JQL Search'))) {
          failures.add(
            'Step 2 failed: the JQL Search navigation item was not marked as the selected shell destination while its loading presenter was visible.',
          );
        }
        if (selectedJqlNavigationBackground == null) {
          failures.add(
            'Step 2 failed: the JQL Search navigation item did not render a detectable background treatment while selected during loading.',
          );
        } else if (contrastRatio(
              selectedJqlNavigationText,
              selectedJqlNavigationBackground,
            ) <
            4.5) {
          failures.add(
            'Step 2 failed: the selected JQL Search navigation item contrast was '
            '${contrastRatio(selectedJqlNavigationText, selectedJqlNavigationBackground).toStringAsFixed(2)}:1 '
            '(${_rgbHex(selectedJqlNavigationText)} on ${_rgbHex(selectedJqlNavigationBackground)}), below the required 4.5:1 threshold.',
          );
        }

        final loadingBannerContrast = contrastRatio(
          screen.renderedTextColorWithin(
            screen.jqlSearchLoadingBanner,
            'Loading...',
          ),
          colors.surfaceAlt,
        );
        if (loadingBannerContrast < 4.5) {
          failures.add(
            'Step 3 failed: the JQL Search loading banner text contrast was ${loadingBannerContrast.toStringAsFixed(2)}:1 '
            'on ${_rgbHex(colors.surfaceAlt)}, below the required WCAG AA 4.5:1 threshold for normal text.',
          );
        }

        final loadingPillContrast = contrastRatio(
          screen.renderedTextColorWithin(
            screen.firstLoadingPill,
            'Loading...',
          ),
          colors.surfaceAlt,
        );
        if (loadingPillContrast < 4.5) {
          failures.add(
            'Step 3 failed: the visible loading-pill text contrast was ${loadingPillContrast.toStringAsFixed(2)}:1 '
            'on ${_rgbHex(colors.surfaceAlt)}, below the required WCAG AA 4.5:1 threshold for normal text.',
          );
        }

        final loadingIndicatorContrast = contrastRatio(
          colors.primary,
          colors.surfaceAlt,
        );
        if (loadingIndicatorContrast < 3.0) {
          failures.add(
            'Step 3 failed: the loading indicator stroke/border contrast was ${loadingIndicatorContrast.toStringAsFixed(2)}:1 '
            '(${_rgbHex(colors.primary)} on ${_rgbHex(colors.surfaceAlt)}), below the required WCAG AA 3.0:1 threshold for non-text icons.',
          );
        }

        final placeholderContrast = contrastRatio(
          screen.renderedTextColorWithin(
            screen.topBarSearchField,
            _Ts453LoadingStateHarness.jqlPlaceholderText,
          ),
          colors.surface,
        );
        if (placeholderContrast < 3.0) {
          failures.add(
            'Step 4 failed: the top-bar Search issues placeholder contrast was ${placeholderContrast.toStringAsFixed(2)}:1 '
            '(${_rgbHex(screen.renderedTextColorWithin(screen.topBarSearchField, _Ts453LoadingStateHarness.jqlPlaceholderText))} on ${_rgbHex(colors.surface)}), '
            'below the required 3.0:1 threshold for placeholder text.',
          );
        }

        final enteredTextColor = screen.editableTextColor(screen.topBarSearchField);
        final placeholderColor = screen.renderedTextColorWithin(
          screen.topBarSearchField,
          _Ts453LoadingStateHarness.jqlPlaceholderText,
        );
        if (enteredTextColor == placeholderColor) {
          failures.add(
            'Step 4 failed: the Search issues placeholder text rendered with the same color ${_rgbHex(placeholderColor)} as entered text, '
            'so the placeholder was not visually distinct from typed content.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 45)),
  );
}

class _Ts453LoadingStateHarness {
  _Ts453LoadingStateHarness(this.tester);

  static const String jqlPlaceholderText =
      'project = TRACK AND status != Done ORDER BY priority DESC';

  final WidgetTester tester;

  Future<void> pumpApp({required TrackStateRepository repository}) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    await tester.pumpWidget(
      TrackStateApp(key: UniqueKey(), repository: repository),
    );
    await _pumpFrames();
  }

  void resetView() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }

  TrackStateColors colors() {
    final context = tester.element(find.byType(Scaffold).first);
    return context.ts;
  }

  List<String> visibleTexts() {
    return tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList(growable: false);
  }

  List<String> visibleSemanticsLabelsSnapshot() {
    final root = tester.binding.pipelineOwner.semanticsOwner?.rootSemanticsNode;
    if (root == null) {
      return <String>[];
    }

    final labels = <String>[];
    void visit(SemanticsNode node) {
      final label = node.getSemanticsData().label.trim();
      if (label.isNotEmpty) {
        labels.add(label);
      }
      for (final child in node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      )) {
        visit(child);
      }
    }

    visit(root);
    return labels;
  }

  Finder get topBarSearchField => _topMost(
    find.byWidgetPredicate((widget) {
      return widget is TextField &&
          widget.decoration?.hintText == jqlPlaceholderText;
    }, description: 'top-bar Search issues field'),
  );

  Finder get createIssueButton => _topBarButton('Create issue');

  Finder get connectGitHubButton => _topBarButton('Connect GitHub');

  Finder navigationItem(String label) {
    final candidates = find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$'));
    return _filteredByGeometry(
      candidates,
      predicate: (rect) => rect.left < 280 && rect.width < 260 && rect.height >= 36,
      fallback: _topMost(candidates),
    );
  }

  Finder get jqlSearchSurface {
    final candidates = find.byWidgetPredicate((widget) {
      return widget is Semantics && widget.properties.label == 'JQL Search';
    }, description: 'JQL Search surface');
    return _largestByArea(candidates);
  }

  Finder get jqlSearchField =>
      find.descendant(of: jqlSearchSurface, matching: find.byType(TextField)).first;

  Finder get jqlSearchLoadingBanner => find.descendant(
    of: jqlSearchSurface,
    matching: find.bySemanticsLabel(RegExp(r'^JQL Search Loading\.\.\.$')),
  );

  List<Finder> loadingRows() {
    final rows = find.descendant(
      of: jqlSearchSurface,
      matching: find.bySemanticsLabel(RegExp(r'^Open .+ Loading\.\.\.$')),
    );
    return List<Finder>.generate(
      rows.evaluate().length,
      (index) => rows.at(index),
      growable: false,
    );
  }

  Finder get firstLoadingPill {
    final row = loadingRows().first;
    final loadingText = find.descendant(of: row, matching: find.text('Loading...'));
    final container = find.ancestor(of: loadingText.first, matching: find.byType(Container));
    return _smallestByArea(container);
  }

  Future<void> openSection(String label) async {
    final target = navigationItem(label);
    await tester.ensureVisible(target);
    await tester.tap(target, warnIfMissed: false);
    await _pumpFrames();
  }

  Future<List<String>> collectFocusVisits(
    Map<String, Finder> candidates, {
    required int tabs,
  }) async {
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump();

    final visits = <String>[];
    for (var index = 0; index < tabs; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump(const Duration(milliseconds: 60));
      final label = _focusedCandidate(candidates);
      if (label != null && (visits.isEmpty || visits.last != label)) {
        visits.add(label);
      }
    }
    return visits;
  }

  Color renderedTextColorWithin(Finder scope, String text) {
    final richTextFinder = find.descendant(of: scope, matching: find.byType(RichText));
    for (final element in richTextFinder.evaluate()) {
      final widget = element.widget as RichText;
      if (widget.text.toPlainText().trim() != text) {
        continue;
      }
      final color =
          widget.text.style?.color ?? DefaultTextStyle.of(element).style.color;
      if (color != null) {
        return color;
      }
    }

    final textFinder = find.descendant(of: scope, matching: find.text(text));
    for (final element in textFinder.evaluate()) {
      final widget = element.widget;
      if (widget is! Text) {
        continue;
      }
      final color =
          widget.style?.color ?? DefaultTextStyle.of(element).style.color;
      if (color != null) {
        return color;
      }
    }

    throw StateError('No rendered text "$text" found within $scope.');
  }

  Color editableTextColor(Finder textField) {
    final editable = find.descendant(of: textField, matching: find.byType(EditableText));
    if (editable.evaluate().isEmpty) {
      throw StateError('No EditableText found within $textField.');
    }
    return tester.widget<EditableText>(editable.first).style.color ??
        colors().text;
  }

  String? _focusedCandidate(Map<String, Finder> candidates) {
    for (final entry in candidates.entries) {
      if (_ownsFocusedNode(entry.value)) {
        return entry.key;
      }
    }
    return null;
  }

  bool isSelected(Finder finder) {
    final semantics = tester.getSemantics(finder);
    return semantics.hasFlag(SemanticsFlag.isSelected);
  }

  Color resolvedButtonBackground(Finder scope, Set<WidgetState> states) {
    final style = _effectiveButtonStyle(scope);
    final background =
        style.backgroundColor?.resolve(states) ?? Colors.transparent;
    final overlay = style.overlayColor?.resolve(states) ?? Colors.transparent;
    return Color.alphaBlend(overlay, background);
  }

  Color? navigationBackgroundColor(String label) {
    final containers = find.descendant(
      of: navigationItem(label),
      matching: find.byType(Container),
    );
    final matches = containers.evaluate().length;
    for (var index = 0; index < matches; index += 1) {
      final widget = tester.widget<Container>(containers.at(index));
      final decoration = widget.decoration;
      if (decoration is BoxDecoration && decoration.color != null) {
        return decoration.color;
      }
    }
    return null;
  }

  ButtonStyle _effectiveButtonStyle(Finder scope) {
    final element = scope.evaluate().first;
    final widget = element.widget;
    return switch (widget) {
      FilledButton button => _mergedButtonStyle(
        style: button.style,
        theme: button.themeStyleOf(element),
        defaults: button.defaultStyleOf(element),
      ),
      OutlinedButton button => _mergedButtonStyle(
        style: button.style,
        theme: button.themeStyleOf(element),
        defaults: button.defaultStyleOf(element),
      ),
      TextButton button => _mergedButtonStyle(
        style: button.style,
        theme: button.themeStyleOf(element),
        defaults: button.defaultStyleOf(element),
      ),
      ElevatedButton button => _mergedButtonStyle(
        style: button.style,
        theme: button.themeStyleOf(element),
        defaults: button.defaultStyleOf(element),
      ),
      _ => throw StateError('No button style available for ${widget.runtimeType}.'),
    };
  }

  ButtonStyle _mergedButtonStyle({
    required ButtonStyle? style,
    required ButtonStyle? theme,
    required ButtonStyle? defaults,
  }) {
    return (style?.merge(theme) ?? theme ?? const ButtonStyle()).merge(defaults);
  }

  bool _ownsFocusedNode(Finder finder) {
    if (finder.evaluate().isEmpty) {
      return false;
    }
    final focusedSemantics = find.semantics.byPredicate(
      (node) => node.getSemanticsData().flagsCollection.isFocused,
      describeMatch: (_) => 'focused semantics node',
    );
    if (focusedSemantics.evaluate().isEmpty) {
      return false;
    }

    final candidateSemantics = _semanticsFinderFor(finder);
    return find.semantics.descendant(
      of: candidateSemantics,
      matching: focusedSemantics,
      matchRoot: true,
    ).evaluate().isNotEmpty;
  }

  FinderBase<SemanticsNode> _semanticsFinderFor(Finder finder) {
    final semanticsId = tester.getSemantics(finder).id;
    return find.semantics.byPredicate(
      (node) => node.id == semanticsId,
      describeMatch: (_) => 'semantics node for $finder',
    );
  }

  Finder _topBarButton(String label) {
    final buttonCandidates = find.ancestor(
      of: find.text(label),
      matching: find.bySubtype<ButtonStyleButton>(),
    );
    return _filteredByGeometry(
      buttonCandidates,
      predicate: (rect) => rect.top < 120 && rect.right > 900,
      fallback: _topMost(buttonCandidates),
    );
  }

  Finder _filteredByGeometry(
    Finder candidates, {
    required bool Function(Rect rect) predicate,
    required Finder fallback,
  }) {
    final matches = candidates.evaluate().length;
    for (var index = 0; index < matches; index += 1) {
      final candidate = candidates.at(index);
      final rect = tester.getRect(candidate);
      if (predicate(rect)) {
        return candidate;
      }
    }
    return fallback;
  }

  Finder _largestByArea(Finder candidates) {
    final matches = candidates.evaluate().length;
    if (matches == 0) {
      return candidates;
    }

    var bestIndex = 0;
    var bestArea = 0.0;
    for (var index = 0; index < matches; index += 1) {
      final rect = tester.getRect(candidates.at(index));
      final area = rect.width * rect.height;
      if (area > bestArea) {
        bestArea = area;
        bestIndex = index;
      }
    }
    return candidates.at(bestIndex);
  }

  Finder _smallestByArea(Finder candidates) {
    final matches = candidates.evaluate().length;
    if (matches == 0) {
      return candidates;
    }

    var bestIndex = 0;
    var bestArea = double.infinity;
    for (var index = 0; index < matches; index += 1) {
      final rect = tester.getRect(candidates.at(index));
      final area = rect.width * rect.height;
      if (area <= bestArea) {
        bestArea = area;
        bestIndex = index;
      }
    }
    return candidates.at(bestIndex);
  }

  Finder _topMost(Finder candidates) {
    final matches = candidates.evaluate().length;
    if (matches == 0) {
      return candidates;
    }

    var bestIndex = 0;
    var bestTop = double.infinity;
    for (var index = 0; index < matches; index += 1) {
      final top = tester.getRect(candidates.at(index)).top;
      if (top < bestTop) {
        bestTop = top;
        bestIndex = index;
      }
    }
    return candidates.at(bestIndex);
  }

  Future<void> _pumpFrames([int count = 12]) async {
    await tester.pump();
    for (var index = 0; index < count; index += 1) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }
}

class _Ts453BootstrapLoadingRepository implements TrackStateRepository {
  const _Ts453BootstrapLoadingRepository();

  static const DemoTrackStateRepository _delegate = DemoTrackStateRepository();
  static const JqlSearchService _searchService = JqlSearchService();

  @override
  bool get usesLocalPersistence => false;

  @override
  bool get supportsGitHubAuth => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _delegate.connect(connection);

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final snapshot = await _delegate.loadSnapshot();
    return TrackerSnapshot(
      project: snapshot.project,
      issues: snapshot.issues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
      readiness: const TrackerBootstrapReadiness(
        domainStates: {
          TrackerDataDomain.projectMeta: TrackerLoadState.ready,
          TrackerDataDomain.issueSummaries: TrackerLoadState.ready,
          TrackerDataDomain.repositoryIndex: TrackerLoadState.ready,
          TrackerDataDomain.issueDetails: TrackerLoadState.partial,
        },
        sectionStates: {
          TrackerSectionKey.dashboard: TrackerLoadState.ready,
          TrackerSectionKey.board: TrackerLoadState.ready,
          TrackerSectionKey.search: TrackerLoadState.partial,
          TrackerSectionKey.hierarchy: TrackerLoadState.ready,
          TrackerSectionKey.settings: TrackerLoadState.ready,
        },
      ),
      startupRecovery: snapshot.startupRecovery,
    );
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    final snapshot = await loadSnapshot();
    await Future<void>.delayed(const Duration(seconds: 8));
    return _searchService.search(
      issues: snapshot.issues,
      project: snapshot.project,
      jql: jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 2147483647)).issues;

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) =>
      _delegate.archiveIssue(issue);

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) =>
      _delegate.deleteIssue(issue);

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) => _delegate.createIssue(
    summary: summary,
    description: description,
    customFields: customFields,
  );

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) => _delegate.updateIssueDescription(issue, description);

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) => _delegate.updateIssueStatus(issue, status);

  @override
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body) =>
      _delegate.addIssueComment(issue, body);

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) => _delegate.uploadIssueAttachment(issue: issue, name: name, bytes: bytes);

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      _delegate.downloadAttachment(attachment);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      _delegate.loadIssueHistory(issue);
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}

String _rgbHex(Color color) {
  final value = color.toARGB32();
  return '#${value.toRadixString(16).padLeft(8, '0').substring(2).toUpperCase()}';
}

extension<T> on List<T> {
  T? get firstOrNull => length == 0 ? null : first;
}
