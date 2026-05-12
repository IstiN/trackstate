import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

class LoadingStateVisualQualityRobot {
  LoadingStateVisualQualityRobot(this.tester);

  static const String jqlPlaceholderText =
      'project = TRACK AND status != Done ORDER BY priority DESC';

  final WidgetTester tester;

  Finder get topBarSearchField => _topMost(
    find.byWidgetPredicate((widget) {
      return widget is TextField &&
          widget.decoration?.hintText == jqlPlaceholderText;
    }, description: 'top-bar Search issues field'),
  );

  Finder topBarButton(String label) {
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

  Finder navigationItem(String label) {
    final candidates = find.bySemanticsLabel(
      RegExp('^${RegExp.escape(label)}\$'),
    );
    return _filteredByGeometry(
      candidates,
      predicate: (rect) =>
          rect.left < 280 && rect.width < 260 && rect.height >= 36,
      fallback: _topMost(candidates),
    );
  }

  Finder get jqlSearchSurface {
    final candidates = find.byWidgetPredicate((widget) {
      return widget is Semantics && widget.properties.label == 'JQL Search';
    }, description: 'JQL Search surface');
    return _largestByArea(candidates);
  }

  Finder get jqlSearchField => find
      .descendant(of: jqlSearchSurface, matching: find.byType(TextField))
      .first;

  Finder get jqlSearchLoadingBanner => find.descendant(
    of: jqlSearchSurface,
    matching: find.bySemanticsLabel(RegExp(r'^JQL Search Loading\.\.\.$')),
  );

  Future<void> waitForJqlSearchLoadingState({
    Duration timeout = const Duration(seconds: 5),
    Duration step = const Duration(milliseconds: 100),
  }) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      await tester.pump(step);
      if (jqlSearchSurface.evaluate().isNotEmpty &&
          jqlSearchField.evaluate().isNotEmpty &&
          jqlSearchLoadingBanner.evaluate().isNotEmpty) {
        return;
      }
    }
  }

  int loadingRowCount() => loadingRows().length;

  List<Finder> loadingRows() {
    final rows = find.descendant(
      of: jqlSearchSurface,
      matching: find.bySemanticsLabel(RegExp(r'^Open .+ Loading\.\.\.$')),
    );
    return List<Finder>.generate(
      rows.evaluate().length,
      rows.at,
      growable: false,
    );
  }

  Finder get firstLoadingPill {
    final row = loadingRows().first;
    final loadingText = find.descendant(
      of: row,
      matching: find.text('Loading...'),
    );
    final container = find.ancestor(
      of: loadingText.first,
      matching: find.byType(Container),
    );
    return _smallestByArea(container);
  }

  List<String> visibleSemanticsLabels() {
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

  Future<List<String>> collectLoadingFocusVisits({required int tabs}) async {
    final rows = loadingRows();
    final firstLoadingResult = rows.isNotEmpty
        ? rows.first
        : find.byWidgetPredicate(
            (_) => false,
            description: 'missing loading result row',
          );
    return collectFocusVisits(<String, Finder>{
      'Create issue': topBarButton('Create issue'),
      'Connect GitHub': topBarButton('Connect GitHub'),
      'JQL Search navigation': navigationItem('JQL Search'),
      'Search issues field': jqlSearchField,
      'First loading result': firstLoadingResult,
    }, tabs: tabs);
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

  TrackStateColors colors() {
    final context = tester.element(find.byType(Scaffold).first);
    return context.ts;
  }

  Color resolveTopBarButtonBackground(String label, Set<WidgetState> states) {
    final style = _effectiveButtonStyle(topBarButton(label));
    final background =
        style.backgroundColor?.resolve(states) ?? Colors.transparent;
    final overlay = style.overlayColor?.resolve(states) ?? Colors.transparent;
    return Color.alphaBlend(overlay, background);
  }

  bool isNavigationSelected(String label) {
    final semantics = tester.getSemantics(navigationItem(label));
    return semantics.hasFlag(SemanticsFlag.isSelected);
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

  Color navigationTextColor(String label) {
    return renderedTextColorWithin(navigationItem(label), label);
  }

  Color loadingBannerTextColor() {
    return renderedTextColorWithin(jqlSearchLoadingBanner, 'Loading...');
  }

  Color firstLoadingPillTextColor() {
    return renderedTextColorWithin(firstLoadingPill, 'Loading...');
  }

  Color topBarPlaceholderTextColor() {
    return renderedTextColorWithin(topBarSearchField, jqlPlaceholderText);
  }

  Color topBarEnteredTextColor() => editableTextColor(topBarSearchField);

  Color renderedTextColorWithin(Finder scope, String text) {
    final richTextFinder = find.descendant(
      of: scope,
      matching: find.byType(RichText),
    );
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
    final editable = find.descendant(
      of: textField,
      matching: find.byType(EditableText),
    );
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
    return find.semantics
        .descendant(
          of: candidateSemantics,
          matching: focusedSemantics,
          matchRoot: true,
        )
        .evaluate()
        .isNotEmpty;
  }

  FinderBase<SemanticsNode> _semanticsFinderFor(Finder finder) {
    final semanticsId = tester.getSemantics(finder).id;
    return find.semantics.byPredicate(
      (node) => node.id == semanticsId,
      describeMatch: (_) => 'semantics node for $finder',
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
      _ => throw StateError(
        'No button style available for ${widget.runtimeType}.',
      ),
    };
  }

  ButtonStyle _mergedButtonStyle({
    required ButtonStyle? style,
    required ButtonStyle? theme,
    required ButtonStyle? defaults,
  }) {
    return (style?.merge(theme) ?? theme ?? const ButtonStyle()).merge(
      defaults,
    );
  }
}
