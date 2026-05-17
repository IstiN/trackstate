import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/core/trackstate_icons.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

import '../../core/models/issue_edit_text_contrast_observation.dart';
import '../../core/utils/color_contrast.dart';

class IssueEditAccessibilityRobot {
  IssueEditAccessibilityRobot(this.tester);

  final WidgetTester tester;

  Finder get editIssueSurface {
    final candidates = find.byWidgetPredicate((widget) {
      return widget is Semantics && widget.properties.label == 'Edit issue';
    }, description: 'Edit issue semantics surface');

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

  Finder textWithinEditIssueSurface(String text) => find.descendant(
    of: editIssueSurface.first,
    matching: find.text(text, findRichText: true),
  );

  Finder labeledTextFieldWithinEditIssueSurface(String label) {
    final decorationMatch = find.descendant(
      of: editIssueSurface.first,
      matching: find.byWidgetPredicate((widget) {
        return widget is TextField && widget.decoration?.labelText == label;
      }, description: 'text field labeled $label'),
    );
    if (decorationMatch.evaluate().isNotEmpty) {
      return decorationMatch;
    }

    final semanticsMatch = find.descendant(
      of: editIssueSurface.first,
      matching: find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$')),
    );
    if (semanticsMatch.evaluate().isEmpty) {
      return semanticsMatch;
    }
    return find.descendant(
      of: semanticsMatch.first,
      matching: find.byWidgetPredicate(
        (widget) => widget is EditableText || widget is TextField,
        description: 'editable control labeled $label',
      ),
    );
  }

  Finder dropdownFieldWithinEditIssueSurface(String label) => find.descendant(
    of: editIssueSurface.first,
    matching: find.byWidgetPredicate((widget) {
      return widget is DropdownButtonFormField<String> &&
          widget.decoration.labelText == label;
    }, description: 'dropdown field labeled $label'),
  );

  Finder controlWithinEditIssueSurface(String label) {
    final semanticsMatch = find.descendant(
      of: editIssueSurface.first,
      matching: find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$')),
    );
    if (semanticsMatch.evaluate().isNotEmpty) {
      return semanticsMatch;
    }
    return find.descendant(
      of: editIssueSurface.first,
      matching: find.text(label, findRichText: true),
    );
  }

  void expectEditIssueSurfaceVisible() {
    if (editIssueSurface.evaluate().isEmpty) {
      throw StateError('The Edit issue surface is not visible.');
    }
  }

  bool showsText(String text) =>
      textWithinEditIssueSurface(text).evaluate().isNotEmpty;

  List<String> visibleTexts() {
    expectEditIssueSurfaceVisible();
    return tester
        .widgetList<Text>(
          find.descendant(
            of: editIssueSurface.first,
            matching: find.byType(Text),
          ),
        )
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList(growable: false);
  }

  List<String> visibleSemanticsLabels() {
    expectEditIssueSurfaceVisible();
    return _screenReaderTargets().map((target) => target.label).toList();
  }

  List<String> accessibilityFeedbackTexts() {
    expectEditIssueSurfaceVisible();
    final rootNode = tester.getSemantics(editIssueSurface.first);
    final values = <String>[];

    void collect(String? value) {
      final normalized = _normalizedLabel(value);
      if (normalized.isNotEmpty) {
        values.add(normalized);
      }
    }

    void visit(SemanticsNode node) {
      if (node.isInvisible) {
        return;
      }

      final data = node.getSemanticsData();
      collect(data.label);
      collect(data.value);
      collect(data.hint);
      collect(data.tooltip);
      for (final child in node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      )) {
        visit(child);
      }
    }

    visit(rootNode);
    return _dedupeConsecutive(values).toList(growable: false);
  }

  List<String> semanticsTraversal() {
    expectEditIssueSurfaceVisible();
    return _dedupeConsecutive(
      _screenReaderTargets().map((target) => target.label),
    ).toList(growable: false);
  }

  Future<List<String>> collectForwardFocusOrder() async {
    expectEditIssueSurfaceVisible();
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump();

    final candidates = _focusCandidates();
    final order = <String>[];
    final maxTabs = candidates.length + 32;
    for (var index = 0; index < maxTabs; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      final label = _focusedLabel(candidates);
      if (label != null && (order.isEmpty || order.last != label)) {
        order.add(label);
      }
      if (order.length == candidates.length) {
        break;
      }
    }
    return order;
  }

  Future<void> clearSummary() async {
    final field = labeledTextFieldWithinEditIssueSurface('Summary');
    if (field.evaluate().isEmpty) {
      throw StateError('No visible Summary field was rendered in Edit issue.');
    }
    await tester.ensureVisible(field.first);
    await tester.tap(field.first, warnIfMissed: false);
    await tester.pump();
    await tester.enterText(field.first, '');
    await tester.pumpAndSettle();
  }

  Future<void> focusField(String label) async {
    final candidates = <Finder>[
      labeledTextFieldWithinEditIssueSurface(label),
      dropdownFieldWithinEditIssueSurface(label),
      controlWithinEditIssueSurface(label),
    ];
    for (final candidate in candidates) {
      if (candidate.evaluate().isEmpty) {
        continue;
      }
      await tester.ensureVisible(candidate.first);
      await tester.tap(candidate.first, warnIfMissed: false);
      await tester.pumpAndSettle();
      return;
    }
    throw StateError(
      'No visible field or control labeled "$label" was rendered.',
    );
  }

  String? readLabeledTextFieldValue(String label) {
    final field = labeledTextFieldWithinEditIssueSurface(label);
    if (field.evaluate().isEmpty) {
      return null;
    }

    final widget = tester.widget(field.first);
    if (widget is EditableText) {
      return widget.controller.text;
    }
    if (widget is TextField) {
      return widget.controller?.text;
    }

    final editableText = find.descendant(
      of: field.first,
      matching: find.byType(EditableText),
    );
    if (editableText.evaluate().isNotEmpty) {
      return tester.widget<EditableText>(editableText.first).controller.text;
    }

    return null;
  }

  IssueEditTextContrastObservation observeSummaryPlaceholderContrast() {
    final foreground = _decoratedFieldTextColor('Summary');
    final background = _surfaceBackgroundColor();
    return IssueEditTextContrastObservation(
      text: 'Summary',
      foregroundHex: _rgbHex(foreground),
      backgroundHex: _rgbHex(background),
      contrastRatio: contrastRatio(foreground, background),
    );
  }

  Finder pendingInfoBanner(String message) {
    final bannerText = textWithinEditIssueSurface(message);
    if (bannerText.evaluate().isEmpty) {
      return bannerText;
    }

    return _smallestByArea(
      find.ancestor(
        of: bannerText.first,
        matching: find.byWidgetPredicate((widget) {
          if (widget is! Container) {
            return false;
          }
          final decoration = widget.decoration;
          return decoration is BoxDecoration &&
              decoration.color != null &&
              decoration.border is Border;
        }, description: 'pending info banner container'),
      ),
    );
  }

  String? pendingInfoBannerSemanticsLabel(String message) {
    final semantics = _pendingInfoBannerSemantics(message);
    if (semantics.evaluate().isEmpty) {
      return null;
    }
    return tester.widget<Semantics>(semantics.first).properties.label;
  }

  List<String> pendingInfoBannerSemanticsLabels(String message) {
    final semantics = _pendingInfoBannerSemantics(message);
    if (semantics.evaluate().isEmpty) {
      return const <String>[];
    }

    return tester
        .widgetList<Semantics>(
          find.descendant(
            of: semantics.first,
            matching: find.byType(Semantics),
          ),
        )
        .map((widget) => _normalizedLabel(widget.properties.label))
        .where((value) => value.isNotEmpty)
        .toList(growable: false);
  }

  int pendingInfoBannerIconCount(String message) => find
      .descendant(
        of: pendingInfoBanner(message),
        matching: find.byType(TrackStateIcon),
      )
      .evaluate()
      .length;

  List<String> pendingInfoBannerIconSemanticsLabels(String message) {
    final icons = find.descendant(
      of: pendingInfoBanner(message),
      matching: find.byType(TrackStateIcon),
    );
    final labels = <String>[];
    final count = icons.evaluate().length;
    for (var index = 0; index < count; index += 1) {
      final label = _normalizedLabel(
        tester.getSemantics(icons.at(index)).label,
      );
      if (label.isNotEmpty) {
        labels.add(label);
      }
    }
    return labels;
  }

  bool pendingInfoBannerIsWithinEditIssueSurface(String message) {
    final banner = pendingInfoBanner(message);
    final bannerText = textWithinEditIssueSurface(message);
    if (banner.evaluate().isEmpty ||
        bannerText.evaluate().isEmpty ||
        editIssueSurface.evaluate().isEmpty) {
      return false;
    }
    return find
        .descendant(of: editIssueSurface.first, matching: banner)
        .evaluate()
        .isNotEmpty;
  }

  Color? pendingInfoBannerBackgroundColor(String message) {
    final banner = pendingInfoBanner(message);
    if (banner.evaluate().isEmpty) {
      return null;
    }
    final widget = tester.widget<Container>(banner.first);
    final decoration = widget.decoration;
    if (decoration is! BoxDecoration) {
      return null;
    }
    return decoration.color;
  }

  Color? pendingInfoBannerBorderColor(String message) {
    final banner = pendingInfoBanner(message);
    if (banner.evaluate().isEmpty) {
      return null;
    }
    final widget = tester.widget<Container>(banner.first);
    final decoration = widget.decoration;
    if (decoration is! BoxDecoration) {
      return null;
    }
    final border = decoration.border;
    if (border is Border) {
      return border.top.color;
    }
    return null;
  }

  Color pendingInfoBannerTextColor(String message) =>
      _renderedTextColorWithin(pendingInfoBanner(message), message);

  TextStyle pendingInfoBannerTextStyle(String message) {
    final texts = find.descendant(
      of: pendingInfoBanner(message),
      matching: find.text(message, findRichText: true),
    );
    for (final element in texts.evaluate()) {
      final widget = element.widget;
      if (widget is Text && widget.style != null) {
        return widget.style!;
      }
      if (widget is RichText && widget.text.style != null) {
        return widget.text.style!;
      }
    }
    throw StateError('No pending info banner text style was rendered.');
  }

  TrackStateColors trackStateColors() {
    final context = tester.element(editIssueSurface.first);
    return context.ts;
  }

  TextStyle? pendingInfoBannerExpectedTextStyle() {
    final context = tester.element(editIssueSurface.first);
    return Theme.of(
      context,
    ).textTheme.bodySmall?.copyWith(color: context.ts.text);
  }

  Future<void> submit() async {
    final save = controlWithinEditIssueSurface('Save');
    if (save.evaluate().isEmpty) {
      throw StateError('No visible Save control was rendered in Edit issue.');
    }
    await tester.ensureVisible(save.first);
    await tester.tap(save.first, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  String? focusedSemanticsLabel() {
    expectEditIssueSurfaceVisible();
    final rootNode = tester.getSemantics(editIssueSurface.first);
    String? focusedLabel;

    void visit(SemanticsNode node) {
      if (focusedLabel != null) {
        return;
      }
      final data = node.getSemanticsData();
      final label = _normalizedLabel(data.label);
      if (data.flagsCollection.isFocused && label.isNotEmpty) {
        focusedLabel = label;
        return;
      }
      for (final child in node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      )) {
        visit(child);
      }
    }

    visit(rootNode);
    return focusedLabel;
  }

  Finder _pendingInfoBannerSemantics(String message) {
    final bannerText = textWithinEditIssueSurface(message);
    if (bannerText.evaluate().isEmpty) {
      return bannerText;
    }
    final semantics = find.ancestor(
      of: bannerText.first,
      matching: find.byWidgetPredicate((widget) {
        return widget is Semantics &&
            _normalizedLabel(widget.properties.label) == message;
      }, description: 'pending info banner semantics'),
    );
    if (semantics.evaluate().isNotEmpty) {
      return semantics.first;
    }
    return semantics;
  }

  Map<String, Finder> _focusCandidates() {
    final orderedCandidates = <String, Finder>{
      'Status': dropdownFieldWithinEditIssueSurface('Status'),
      'Summary': labeledTextFieldWithinEditIssueSurface('Summary'),
      'Description': labeledTextFieldWithinEditIssueSurface('Description'),
      'Priority': dropdownFieldWithinEditIssueSurface('Priority'),
      'Assignee': labeledTextFieldWithinEditIssueSurface('Assignee'),
      'Labels': labeledTextFieldWithinEditIssueSurface('Labels'),
      'Components': controlWithinEditIssueSurface('Components'),
      'Fix versions': controlWithinEditIssueSurface('Fix versions'),
      'Epic': controlWithinEditIssueSurface('Epic'),
      'Save': controlWithinEditIssueSurface('Save'),
      'Cancel': controlWithinEditIssueSurface('Cancel'),
    };
    return {
      for (final entry in orderedCandidates.entries)
        if (entry.value.evaluate().isNotEmpty) entry.key: entry.value,
    };
  }

  String? _focusedLabel(Map<String, Finder> candidates) {
    final focusedSemantics = find.semantics.byPredicate(
      (node) => node.getSemanticsData().flagsCollection.isFocused,
      describeMatch: (_) => 'focused semantics node',
    );
    if (focusedSemantics.evaluate().isEmpty) {
      return null;
    }

    for (final entry in candidates.entries) {
      final exactFocusedMatch = find.semantics.byPredicate(
        (node) =>
            node.getSemanticsData().flagsCollection.isFocused &&
            _normalizedLabel(node.label) == entry.key,
        describeMatch: (_) => 'focused semantics labeled ${entry.key}',
      );
      if (exactFocusedMatch.evaluate().isNotEmpty) {
        return entry.key;
      }

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

  FinderBase<SemanticsNode> _semanticsFinderFor(Finder finder) {
    final semanticsId = tester.getSemantics(finder).id;
    return find.semantics.byPredicate(
      (node) => node.id == semanticsId,
      describeMatch: (_) => 'semantics node for $finder',
    );
  }

  List<_ScreenReaderTarget> _screenReaderTargets() {
    final rootNode = tester.getSemantics(editIssueSurface.first);
    final targets = <_ScreenReaderTarget>[];

    void visit(SemanticsNode node) {
      final children = node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      );
      final label = _normalizedLabel(node.label);
      if (label.isNotEmpty &&
          label != 'Edit issue' &&
          !node.isInvisible &&
          !node.isMergedIntoParent &&
          !_isMergedContainerLabel(label, children) &&
          (_isScreenReaderTarget(node) || children.isEmpty)) {
        targets.add(
          _ScreenReaderTarget(
            label: label,
            isButton: node.getSemanticsData().flagsCollection.isButton,
          ),
        );
      }
      for (final child in children) {
        visit(child);
      }
    }

    visit(rootNode);
    return targets;
  }

  bool _isScreenReaderTarget(SemanticsNode node) {
    final data = node.getSemanticsData();
    return data.flagsCollection.isButton ||
        data.flagsCollection.isTextField ||
        data.flagsCollection.isReadOnly;
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

  Iterable<String> _dedupeConsecutive(Iterable<String> labels) sync* {
    String? previous;
    for (final label in labels) {
      if (previous != label) {
        yield label;
      }
      previous = label;
    }
  }

  String _normalizedLabel(String? label) =>
      label?.replaceAll('\n', ' ').trim() ?? '';

  Color _decoratedFieldTextColor(String text) {
    expectEditIssueSurfaceVisible();
    final decoratedFieldFinder = find.descendant(
      of: editIssueSurface.first,
      matching: find.byWidgetPredicate((widget) {
        if (widget is TextField) {
          return widget.decoration?.labelText == text ||
              widget.decoration?.hintText == text;
        }
        if (widget is InputDecorator) {
          return widget.decoration.labelText == text ||
              widget.decoration.hintText == text;
        }
        if (widget is DropdownButtonFormField<String>) {
          return widget.decoration.labelText == text ||
              widget.decoration.hintText == text;
        }
        return false;
      }, description: 'decorated edit issue field for $text'),
    );

    final count = decoratedFieldFinder.evaluate().length;
    for (var index = 0; index < count; index += 1) {
      final candidate = decoratedFieldFinder.at(index);
      final element = candidate.evaluate().single;
      final decoration = _inputDecorationFor(element.widget);
      if (decoration == null) {
        continue;
      }
      final matchesHint = decoration.hintText == text;
      final theme = Theme.of(element);
      final explicitStyle = matchesHint
          ? decoration.hintStyle
          : decoration.labelStyle;
      final themedStyle = matchesHint
          ? theme.inputDecorationTheme.hintStyle
          : theme.inputDecorationTheme.labelStyle;
      final color =
          explicitStyle?.color ??
          themedStyle?.color ??
          theme.textTheme.bodyMedium?.color;
      if (color != null) {
        return color;
      }
    }

    throw StateError('No rendered field-label color found for "$text".');
  }

  InputDecoration? _inputDecorationFor(Widget widget) {
    if (widget is TextField) {
      return widget.decoration;
    }
    if (widget is InputDecorator) {
      return widget.decoration;
    }
    if (widget is DropdownButtonFormField<String>) {
      return widget.decoration;
    }
    return null;
  }

  Color _surfaceBackgroundColor() {
    final decoratedContainers = find.descendant(
      of: editIssueSurface.first,
      matching: find.byWidgetPredicate((widget) {
        if (widget is! Container) {
          return false;
        }
        final decoration = widget.decoration;
        return decoration is BoxDecoration &&
            decoration.color != null &&
            decoration.borderRadius != null;
      }, description: 'decorated edit issue container'),
    );

    Finder? bestMatch;
    double? largestArea;
    final count = decoratedContainers.evaluate().length;
    for (var index = 0; index < count; index += 1) {
      final candidate = decoratedContainers.at(index);
      final rect = tester.getRect(candidate);
      final area = rect.width * rect.height;
      if (largestArea == null || area > largestArea) {
        largestArea = area;
        bestMatch = candidate;
      }
    }

    if (bestMatch == null) {
      final element = editIssueSurface.first.evaluate().single;
      return Theme.of(element).colorScheme.surface;
    }

    final widget = bestMatch.evaluate().single.widget;
    if (widget is Container) {
      final decoration = widget.decoration;
      if (decoration is BoxDecoration && decoration.color != null) {
        return decoration.color!;
      }
    }

    final element = editIssueSurface.first.evaluate().single;
    return Theme.of(element).colorScheme.surface;
  }

  Finder _smallestByArea(Finder candidates) {
    Finder? bestMatch;
    double? smallestArea;
    final count = candidates.evaluate().length;
    for (var index = 0; index < count; index += 1) {
      final candidate = candidates.at(index);
      final rect = tester.getRect(candidate);
      final area = rect.width * rect.height;
      if (smallestArea == null || area < smallestArea) {
        smallestArea = area;
        bestMatch = candidate;
      }
    }
    return bestMatch ?? candidates;
  }

  Color _renderedTextColorWithin(Finder scope, String text) {
    final richTextFinder = find.descendant(
      of: scope,
      matching: find.byType(RichText),
    );
    for (final element in richTextFinder.evaluate()) {
      final widget = element.widget as RichText;
      if (widget.text.toPlainText().trim() == text) {
        final color =
            widget.text.style?.color ??
            DefaultTextStyle.of(element).style.color ??
            _fallbackTextColor(scope);
        if (color != null) {
          return color;
        }
      }
    }

    final textFinder = find.descendant(
      of: scope,
      matching: find.text(text, findRichText: true),
    );
    for (final element in textFinder.evaluate()) {
      final widget = element.widget;
      if (widget is Text) {
        final color =
            widget.style?.color ??
            DefaultTextStyle.of(element).style.color ??
            _fallbackTextColor(scope);
        if (color != null) {
          return color;
        }
      }
    }

    throw StateError('No rendered text "$text" found within $scope.');
  }

  Color? _fallbackTextColor(Finder scope) {
    final elements = scope.evaluate();
    if (elements.isEmpty) {
      return null;
    }
    final theme = Theme.of(elements.first);
    return theme.textTheme.bodyMedium?.color ?? theme.colorScheme.onSurface;
  }

  String _rgbHex(Color color) {
    final rgb = color.toARGB32() & 0x00FFFFFF;
    return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
  }
}

class _ScreenReaderTarget {
  const _ScreenReaderTarget({required this.label, required this.isButton});

  final String label;
  final bool isButton;
}
