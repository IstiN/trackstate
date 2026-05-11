import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../core/utils/color_contrast.dart';

class CreateIssueAccessibilityRobot {
  CreateIssueAccessibilityRobot(this.tester);

  final WidgetTester tester;

  Finder get dialog => find.byType(Dialog);

  Finder get createIssueSurface => find.descendant(
    of: dialog.first,
    matching: find.byWidgetPredicate((widget) {
      return widget is Semantics && widget.properties.label == 'Create issue';
    }, description: 'Create issue semantics surface'),
  );

  Finder textWithinDialog(String text) => find.descendant(
    of: dialog.first,
    matching: find.text(text, findRichText: true),
  );

  Future<void> resizeTo(Size size) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
  }

  CreateIssueLayoutObservation observeLayout() {
    if (createIssueSurface.evaluate().isEmpty) {
      throw StateError('The Create issue surface is not visible.');
    }
    final rect = tester.getRect(createIssueSurface.first);
    final viewport = Size(
      tester.view.physicalSize.width / tester.view.devicePixelRatio,
      tester.view.physicalSize.height / tester.view.devicePixelRatio,
    );
    return CreateIssueLayoutObservation(viewport: viewport, surfaceRect: rect);
  }

  bool showsText(String text) => textWithinDialog(text).evaluate().isNotEmpty;

  List<String> visibleTexts() {
    return tester
        .widgetList<Text>(
          find.descendant(of: dialog.first, matching: find.byType(Text)),
        )
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList(growable: false);
  }

  List<String> semanticsTraversal() {
    if (createIssueSurface.evaluate().isEmpty) {
      throw StateError(
        'The Create issue surface semantics node is not visible.',
      );
    }

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

  TextContrastObservation observeTextContrast(String text) {
    final foreground = _renderedTextColor(text);
    final background = _surfaceBackgroundColor();
    return TextContrastObservation(
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
    final finder = textWithinDialog(text);
    for (final element in finder.evaluate()) {
      final widget = element.widget;
      if (widget is RichText) {
        final color =
            widget.text.style?.color ??
            DefaultTextStyle.of(element).style.color;
        if (color != null) {
          return color;
        }
      }
      if (widget is Text) {
        final color =
            widget.style?.color ?? DefaultTextStyle.of(element).style.color;
        if (color != null) {
          return color;
        }
      }
    }
    throw StateError('No rendered text color found for "$text".');
  }

  Color _surfaceBackgroundColor() {
    final decoratedContainers = find.descendant(
      of: dialog.first,
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
      throw StateError('No create issue surface background could be resolved.');
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

    throw StateError('No create issue surface background color was rendered.');
  }

  String _rgbHex(Color color) {
    final rgb = color.toARGB32() & 0x00FFFFFF;
    return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
  }
}

class CreateIssueLayoutObservation {
  const CreateIssueLayoutObservation({
    required this.viewport,
    required this.surfaceRect,
  });

  final Size viewport;
  final Rect surfaceRect;

  double get widthFraction => surfaceRect.width / viewport.width;

  double get heightFraction => surfaceRect.height / viewport.height;

  double get leftInset => surfaceRect.left;

  double get rightInset => viewport.width - surfaceRect.right;

  double get topInset => surfaceRect.top;

  double get bottomInset => viewport.height - surfaceRect.bottom;

  String describe() {
    return 'viewport=${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}, '
        'rect=(${surfaceRect.left.toStringAsFixed(1)}, ${surfaceRect.top.toStringAsFixed(1)}) '
        '${surfaceRect.width.toStringAsFixed(1)}x${surfaceRect.height.toStringAsFixed(1)}, '
        'width=${(widthFraction * 100).toStringAsFixed(1)}%, '
        'height=${(heightFraction * 100).toStringAsFixed(1)}%, '
        'insets=left ${leftInset.toStringAsFixed(1)}, right ${rightInset.toStringAsFixed(1)}, '
        'top ${topInset.toStringAsFixed(1)}, bottom ${bottomInset.toStringAsFixed(1)}';
  }
}

class TextContrastObservation {
  const TextContrastObservation({
    required this.text,
    required this.foregroundHex,
    required this.backgroundHex,
    required this.contrastRatio,
  });

  final String text;
  final String foregroundHex;
  final String backgroundHex;
  final double contrastRatio;

  String describe() {
    return '$text: $foregroundHex on $backgroundHex '
        '(${contrastRatio.toStringAsFixed(2)}:1)';
  }
}
