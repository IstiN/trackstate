import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../core/models/create_issue_layout_observation.dart';
import '../../core/models/create_issue_text_contrast_observation.dart';
import '../../core/utils/color_contrast.dart';

class CreateIssueAccessibilityRobot {
  CreateIssueAccessibilityRobot(this.tester);

  final WidgetTester tester;

  Finder get createIssueSurface {
    final candidates = find.byWidgetPredicate((widget) {
      return widget is Semantics && widget.properties.label == 'Create issue';
    }, description: 'Create issue semantics surface');

    Finder? bestMatch;
    double? largestArea;
    final count = candidates.evaluate().length;
    for (var index = 0; index < count; index++) {
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

  Finder textWithinCreateIssueSurface(String text) => find.descendant(
    of: createIssueSurface.first,
    matching: find.text(text, findRichText: true),
  );

  Finder labeledTextFieldWithinCreateIssueSurface(String label) {
    final decorationMatch = find.descendant(
      of: createIssueSurface.first,
      matching: find.byWidgetPredicate((widget) {
        return widget is TextField && widget.decoration?.labelText == label;
      }, description: 'text field labeled $label'),
    );
    if (decorationMatch.evaluate().isNotEmpty) {
      return decorationMatch;
    }

    final semanticsMatch = find.descendant(
      of: createIssueSurface.first,
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

  Finder controlWithinCreateIssueSurface(String label) {
    final semanticsMatch = find.descendant(
      of: createIssueSurface.first,
      matching: find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$')),
    );
    if (semanticsMatch.evaluate().isNotEmpty) {
      return semanticsMatch;
    }
    return find.descendant(
      of: createIssueSurface.first,
      matching: find.text(label, findRichText: true),
    );
  }

  void expectCreateIssueSurfaceVisible() {
    if (createIssueSurface.evaluate().isEmpty) {
      throw StateError('The Create issue surface is not visible.');
    }
  }

  Future<void> resizeToViewport({
    required double width,
    required double height,
  }) async {
    tester.view.physicalSize = Size(width, height);
    tester.view.devicePixelRatio = 1;
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
  }

  CreateIssueLayoutObservation observeLayout() {
    expectCreateIssueSurfaceVisible();
    final rect = tester.getRect(createIssueSurface.first);
    final viewportWidth =
        tester.view.physicalSize.width / tester.view.devicePixelRatio;
    final viewportHeight =
        tester.view.physicalSize.height / tester.view.devicePixelRatio;
    return CreateIssueLayoutObservation(
      viewportWidth: viewportWidth,
      viewportHeight: viewportHeight,
      surfaceLeft: rect.left,
      surfaceTop: rect.top,
      surfaceWidth: rect.width,
      surfaceHeight: rect.height,
    );
  }

  bool showsText(String text) =>
      textWithinCreateIssueSurface(text).evaluate().isNotEmpty;

  List<String> visibleTexts() {
    return tester
        .widgetList<Text>(
          find.descendant(
            of: createIssueSurface.first,
            matching: find.byType(Text),
          ),
        )
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList(growable: false);
  }

  Rect? observeLabeledTextFieldRect(String label) {
    final field = labeledTextFieldWithinCreateIssueSurface(label);
    if (field.evaluate().isEmpty) {
      return null;
    }
    return tester.getRect(field.first);
  }

  String? readLabeledTextFieldValue(String label) {
    final field = labeledTextFieldWithinCreateIssueSurface(label);
    if (field.evaluate().isEmpty) {
      return null;
    }

    String? emptyCandidate;
    final count = field.evaluate().length;
    for (var index = 0; index < count; index++) {
      final value = _readTextFieldValue(field.at(index));
      if (value == null) {
        continue;
      }
      if (value.isNotEmpty) {
        return value;
      }
      emptyCandidate ??= value;
    }
    return emptyCandidate;
  }

  Rect? observeControlRect(String label) {
    final control = controlWithinCreateIssueSurface(label);
    if (control.evaluate().isEmpty) {
      return null;
    }
    return tester.getRect(control.first);
  }

  List<String> semanticsTraversal() {
    expectCreateIssueSurfaceVisible();
    final rootNode = tester.getSemantics(createIssueSurface.first);
    final labels = <String>[];

    void visit(SemanticsNode node) {
      final children = node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      );
      final label = _normalizedLabel(node.label);
      if (label.isNotEmpty &&
          label != 'Create issue' &&
          !node.isInvisible &&
          !node.isMergedIntoParent &&
          !_isMergedContainerLabel(label, children) &&
          (_isScreenReaderTarget(node) || children.isEmpty)) {
        labels.add(label);
      }
      for (final child in children) {
        visit(child);
      }
    }

    visit(rootNode);
    return _dedupeConsecutive(labels);
  }

  CreateIssueTextContrastObservation observeTextContrast(String text) {
    final foreground = _renderedTextColor(text);
    final background = _surfaceBackgroundColor();
    return CreateIssueTextContrastObservation(
      text: text,
      foregroundHex: _rgbHex(foreground),
      backgroundHex: _rgbHex(background),
      contrastRatio: contrastRatio(foreground, background),
    );
  }

  bool _isScreenReaderTarget(SemanticsNode node) {
    return node.flagsCollection.isButton ||
        node.flagsCollection.isTextField ||
        node.flagsCollection.isReadOnly;
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

  Color _renderedTextColor(String text) {
    expectCreateIssueSurfaceVisible();
    final surfaceRect = tester.getRect(createIssueSurface.first);

    final richTextFinder = find.byType(RichText);
    final richTextCount = richTextFinder.evaluate().length;
    for (var index = 0; index < richTextCount; index++) {
      final candidate = richTextFinder.at(index);
      final widget = tester.widget<RichText>(candidate);
      if (!_matchesRequestedText(widget.text.toPlainText(), text)) {
        continue;
      }
      if (!_isWithinSurface(surfaceRect, tester.getRect(candidate))) {
        continue;
      }
      final element = candidate.evaluate().single;
      final color =
          widget.text.style?.color ?? DefaultTextStyle.of(element).style.color;
      if (color != null) {
        return color;
      }
    }

    final textFinder = find.byType(Text);
    final textCount = textFinder.evaluate().length;
    for (var index = 0; index < textCount; index++) {
      final candidate = textFinder.at(index);
      final widget = tester.widget<Text>(candidate);
      if (!_matchesRequestedText(widget.data, text)) {
        continue;
      }
      if (!_isWithinSurface(surfaceRect, tester.getRect(candidate))) {
        continue;
      }
      final element = candidate.evaluate().single;
      final color =
          widget.style?.color ?? DefaultTextStyle.of(element).style.color;
      if (color != null) {
        return color;
      }
    }

    final decorationColor = _decoratedFieldTextColor(text);
    if (decorationColor != null) {
      return decorationColor;
    }

    final themedColor = _surfaceThemeTextColor(text);
    if (themedColor != null) {
      return themedColor;
    }

    throw StateError('No rendered text color found for "$text".');
  }

  bool _isWithinSurface(Rect surfaceRect, Rect candidateRect) {
    return surfaceRect.overlaps(candidateRect) ||
        surfaceRect.contains(candidateRect.center);
  }

  bool _matchesRequestedText(String? candidate, String expected) {
    final normalizedCandidate = _normalizedLabel(candidate);
    return normalizedCandidate == expected ||
        normalizedCandidate.startsWith(expected);
  }

  Color? _decoratedFieldTextColor(String text) {
    expectCreateIssueSurfaceVisible();
    final surfaceRect = tester.getRect(createIssueSurface.first);
    final decoratedFieldFinder = find.byWidgetPredicate((widget) {
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
    }, description: 'decorated create issue field for $text');

    final decoratedFieldCount = decoratedFieldFinder.evaluate().length;
    for (var index = 0; index < decoratedFieldCount; index++) {
      final candidate = decoratedFieldFinder.at(index);
      if (!_isWithinSurface(surfaceRect, tester.getRect(candidate))) {
        continue;
      }
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

    return null;
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

  Color? _surfaceThemeTextColor(String text) {
    final element = createIssueSurface.first.evaluate().single;
    final theme = Theme.of(element);
    final prefersHintStyle = text == 'Optional';
    final explicitStyle = prefersHintStyle
        ? theme.inputDecorationTheme.hintStyle
        : theme.inputDecorationTheme.labelStyle;
    return explicitStyle?.color ?? theme.textTheme.bodyMedium?.color;
  }

  Color _surfaceBackgroundColor() {
    final decoratedContainers = find.descendant(
      of: createIssueSurface.first,
      matching: find.byWidgetPredicate((widget) {
        if (widget is! Container) {
          return false;
        }
        final decoration = widget.decoration;
        return decoration is BoxDecoration &&
            decoration.color != null &&
            decoration.borderRadius != null;
      }, description: 'decorated create issue container'),
    );

    Finder? bestMatch;
    double? largestArea;
    final count = decoratedContainers.evaluate().length;
    for (var index = 0; index < count; index++) {
      final candidate = decoratedContainers.at(index);
      final rect = tester.getRect(candidate);
      final area = rect.width * rect.height;
      if (largestArea == null || area > largestArea) {
        largestArea = area;
        bestMatch = candidate;
      }
    }

    if (bestMatch == null) {
      final element = createIssueSurface.first.evaluate().single;
      final theme = Theme.of(element);
      return theme.colorScheme.surface;
    }

    for (final element in bestMatch.evaluate()) {
      final widget = element.widget;
      if (widget is! Container) {
        continue;
      }
      final decoration = widget.decoration;
      if (decoration is BoxDecoration && decoration.color != null) {
        return decoration.color!;
      }
    }

    final element = createIssueSurface.first.evaluate().single;
    final theme = Theme.of(element);
    return theme.colorScheme.surface;
  }

  String _rgbHex(Color color) {
    final rgb = color.toARGB32() & 0x00FFFFFF;
    return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
  }

  String? _readTextFieldValue(Finder field) {
    final widget = tester.widget(field);
    if (widget is EditableText) {
      return widget.controller.text;
    }
    if (widget is TextField) {
      return widget.controller?.text;
    }

    final editableText = find.descendant(
      of: field,
      matching: find.byType(EditableText),
    );
    if (editableText.evaluate().isNotEmpty) {
      return tester.widget<EditableText>(editableText.first).controller.text;
    }

    return null;
  }
}
