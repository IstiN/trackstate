import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

import '../../core/interfaces/jql_search_accessibility_screen.dart';
import '../../core/models/jql_search_button_style_observation.dart';
import '../../core/utils/color_contrast.dart';

class JqlSearchAccessibilityRobot
    implements JqlSearchAccessibilityScreenHandle {
  JqlSearchAccessibilityRobot(this.tester);

  final WidgetTester tester;

  static const _searchLabel = 'Search issues';
  static const _loadMoreLabel = 'Load more issues';

  Finder get _searchNavigation => find.bySemanticsLabel(RegExp('JQL Search'));

  Finder get _searchSurface {
    final candidates = find.byWidgetPredicate((widget) {
      return widget is Semantics && widget.properties.label == 'JQL Search';
    }, description: 'JQL Search semantics surface');

    Finder? bestMatch;
    double? largestArea;
    final count = candidates.evaluate().length;
    for (var index = 0; index < count; index += 1) {
      final candidate = candidates.at(index);
      final rect = tester.getRect(candidate);
      final area = rect.width * rect.height;
      if (largestArea == null || area > largestArea) {
        largestArea = area;
        bestMatch = candidate;
      }
    }

    return bestMatch ?? candidates;
  }

  Finder get _searchTextField => find.descendant(
    of: _searchSurface.first,
    matching: find.byType(TextField),
  );

  Finder get _loadMoreButton => find.descendant(
    of: _searchSurface.first,
    matching: find.widgetWithText(OutlinedButton, 'Load more'),
  );

  @override
  Future<void> openSearch() async {
    await tester.tap(_searchNavigation.first);
    await tester.pumpAndSettle();
    _expectSearchSurfaceVisible();
  }

  @override
  List<String> visibleTexts() {
    _expectSearchSurfaceVisible();
    return tester
        .widgetList<Text>(
          find.descendant(
            of: _searchSurface.first,
            matching: find.byType(Text),
          ),
        )
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList(growable: false);
  }

  @override
  List<String> semanticsTraversal() {
    _expectSearchSurfaceVisible();
    final rootNode = tester.getSemantics(_searchSurface.first);
    final labels = <String>[];

    void visit(SemanticsNode node) {
      final children = node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      );
      final label = _normalizedLabel(node.label);
      if (label.isNotEmpty &&
          label != 'JQL Search' &&
          !node.isInvisible &&
          !node.isMergedIntoParent &&
          !_isMergedContainerLabel(label, children) &&
          _isInteractiveTarget(node)) {
        labels.add(label);
      }
      for (final child in children) {
        visit(child);
      }
    }

    visit(rootNode);
    return _dedupeConsecutive(labels);
  }

  @override
  int countExactSemanticsLabel(String label) {
    _expectSearchSurfaceVisible();
    return find
        .descendant(
          of: _searchSurface.first,
          matching: find.bySemanticsLabel(
            RegExp('^${RegExp.escape(label)}\$'),
          ),
        )
        .evaluate()
        .length;
  }

  @override
  Future<List<String>> collectForwardFocusOrder() async {
    final candidates = _focusCandidates();
    await _focusSearchField();
    final order = <String>[];

    final initialLabel = focusedLabel(candidates);
    if (initialLabel != null) {
      order.add(initialLabel);
    }

    for (var index = 0; index < 7; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      final label = focusedLabel(candidates);
      if (label != null) {
        order.add(label);
      }
    }

    return order;
  }

  @override
  Future<List<String>> collectBackwardFocusOrder() async {
    final candidates = _focusCandidates();
    await _focusSearchField();
    for (var index = 0; index < 7; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
    }

    final order = <String>[];
    final initialLabel = focusedLabel(candidates);
    if (initialLabel != null) {
      order.add(initialLabel);
    }

    for (var index = 0; index < 7; index += 1) {
      await tester.sendKeyDownEvent(LogicalKeyboardKey.shiftLeft);
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.sendKeyUpEvent(LogicalKeyboardKey.shiftLeft);
      await tester.pump();
      final label = focusedLabel(candidates);
      if (label != null) {
        order.add(label);
      }
    }

    return order;
  }

  @override
  JqlSearchButtonStyleObservation observeLoadMoreButtonIdle() {
    return _observeLoadMoreButton(
      state: 'idle',
      states: const <WidgetState>{},
      expectedOverlayRgbHex: 'transparent',
    );
  }

  @override
  JqlSearchButtonStyleObservation observeLoadMoreButtonHovered() {
    return _observeLoadMoreButton(
      state: 'hovered',
      states: const <WidgetState>{WidgetState.hovered},
      expectedOverlayRgbHex: _rgbHex(colors().primarySoft),
    );
  }

  @override
  JqlSearchButtonStyleObservation observeLoadMoreButtonFocused() {
    return _observeLoadMoreButton(
      state: 'focused',
      states: const <WidgetState>{WidgetState.focused},
      expectedOverlayRgbHex: _rgbHex(colors().primarySoft),
    );
  }

  String? focusedLabel(Map<String, Finder> candidates) {
    final focusedSemantics = find.semantics.byPredicate(
      (node) => node.getSemanticsData().flagsCollection.isFocused,
      describeMatch: (_) => 'focused semantics node',
    );
    if (focusedSemantics.evaluate().isEmpty) {
      return null;
    }

    for (final entry in candidates.entries) {
      final matches = entry.value.evaluate().length;
      if (matches == 0) {
        continue;
      }
      for (var index = 0; index < matches; index += 1) {
        final candidateSemantics = _semanticsFinderFor(entry.value.at(index));
        final ownsFocusedNode = find.semantics.descendant(
          of: candidateSemantics,
          matching: focusedSemantics,
          matchRoot: true,
        );
        if (ownsFocusedNode.evaluate().isNotEmpty) {
          return entry.key;
        }
      }
    }
    return null;
  }

  TrackStateColors colors() {
    final context = tester.element(find.byType(Scaffold).first);
    return context.ts;
  }

  void _expectSearchSurfaceVisible() {
    if (_searchSurface.evaluate().isEmpty) {
      throw StateError('The JQL Search surface is not visible.');
    }
  }

  Future<void> _focusSearchField() async {
    _expectSearchSurfaceVisible();
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump();
    await tester.tap(_searchTextField.first);
    await tester.pumpAndSettle();
  }

  Map<String, Finder> _focusCandidates() {
    return <String, Finder>{
      _searchLabel: _searchTextField,
      for (var index = 1; index <= 6; index += 1)
        'Open TRACK-$index Paged issue $index': find.descendant(
          of: _searchSurface.first,
          matching: find.bySemanticsLabel(
            RegExp(
              '^${RegExp.escape('Open TRACK-$index Paged issue $index')}\$',
            ),
          ),
        ),
      _loadMoreLabel: find.descendant(
        of: _searchSurface.first,
        matching: find.bySemanticsLabel(
          RegExp('^${RegExp.escape(_loadMoreLabel)}\$'),
        ),
      ),
    };
  }

  JqlSearchButtonStyleObservation _observeLoadMoreButton({
    required String state,
    required Set<WidgetState> states,
    required String expectedOverlayRgbHex,
  }) {
    final colors = this.colors();
    final style = _effectiveButtonStyle(_loadMoreButton.first);
    final foreground =
        style.foregroundColor?.resolve(states) ??
        _renderedTextColorWithin(_loadMoreButton.first, 'Load more');
    final background =
        style.backgroundColor?.resolve(states) ?? Colors.transparent;
    final overlay = style.overlayColor?.resolve(states) ?? Colors.transparent;
    final border =
        style.side?.resolve(states)?.color ??
        style.side?.resolve(const <WidgetState>{})?.color ??
        colors.border;

    return JqlSearchButtonStyleObservation(
      state: state,
      foregroundHex: _rgbHex(foreground),
      expectedForegroundHex: _rgbHex(colors.primary),
      backgroundHex: _rgbHex(background),
      expectedBackgroundHex: _rgbHex(colors.surface),
      borderHex: _rgbHex(border),
      expectedBorderHex: _rgbHex(colors.primary),
      overlayRgbHex: overlay.alpha == 0 ? 'transparent' : _rgbHex(overlay),
      expectedOverlayRgbHex: expectedOverlayRgbHex,
      overlayAlpha: overlay.a,
      contrastRatio: contrastRatio(
        foreground,
        Color.alphaBlend(overlay, background),
      ),
    );
  }

  Color _renderedTextColorWithin(Finder scope, String text) {
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

  bool _isInteractiveTarget(SemanticsNode node) {
    final flags = node.getSemanticsData().flagsCollection;
    return flags.isButton || flags.isTextField;
  }

  bool _isMergedContainerLabel(String label, List<SemanticsNode> children) {
    if (children.isEmpty) {
      return false;
    }

    var matchedChildLabels = 0;
    for (final child in children) {
      final childLabel = _normalizedLabel(child.label);
      if (childLabel.isEmpty ||
          childLabel == label ||
          !label.contains(childLabel)) {
        continue;
      }
      matchedChildLabels += 1;
    }
    return matchedChildLabels > 0;
  }

  List<String> _dedupeConsecutive(List<String> labels) {
    final deduped = <String>[];
    for (final label in labels) {
      if (deduped.isEmpty || deduped.last != label) {
        deduped.add(label);
      }
    }
    return deduped;
  }

  String _normalizedLabel(String? label) {
    return label?.replaceAll('\n', ' ').trim() ?? '';
  }

  FinderBase<SemanticsNode> _semanticsFinderFor(Finder finder) {
    final semanticsId = tester.getSemantics(finder).id;
    return find.semantics.byPredicate(
      (node) => node.id == semanticsId,
      describeMatch: (_) => 'semantics node for $finder',
    );
  }

  ButtonStyle _effectiveButtonStyle(Finder scope) {
    final element = scope.evaluate().first;
    final widget = element.widget;
    return switch (widget) {
      OutlinedButton button => _mergedButtonStyle(
        style: button.style,
        theme: button.themeStyleOf(element),
        defaults: button.defaultStyleOf(element),
      ),
      FilledButton button => _mergedButtonStyle(
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

  String _rgbHex(Color color) {
    final rgb = color.toARGB32() & 0x00FFFFFF;
    return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
  }
}
