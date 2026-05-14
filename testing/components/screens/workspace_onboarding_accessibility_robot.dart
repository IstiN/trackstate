import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/core/trackstate_icons.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

import '../../core/interfaces/workspace_onboarding_accessibility_screen.dart';
import '../../core/models/workspace_onboarding_contrast_observation.dart';
import '../../core/utils/color_contrast.dart';

class WorkspaceOnboardingAccessibilityRobot
    implements WorkspaceOnboardingAccessibilityScreenHandle {
  WorkspaceOnboardingAccessibilityRobot(this.tester);

  final WidgetTester tester;

  static const _title = 'Add workspace';
  static const _firstRunDescription =
      'Choose a local folder to open an existing workspace or initialize '
      'TrackState in a new one.';
  static const _openExistingFolder = 'Open existing folder';
  static const _initializeFolder = 'Initialize folder';

  Finder get _openExistingFolderButton =>
      find.byKey(const ValueKey('local-workspace-onboarding-open-existing'));

  Finder get _initializeFolderButton => find.byKey(
    const ValueKey('local-workspace-onboarding-initialize-folder'),
  );

  Finder get _titleText => find.text(_title);

  Finder get _subtitleText => find.text(_firstRunDescription);

  Finder get _onboardingSurface => find.byType(Scaffold);

  @override
  List<String> visibleTexts() {
    _expectOnboardingVisible();
    final texts = <String>[];
    for (final widget in tester.widgetList<Text>(
      find.descendant(
        of: _onboardingSurface.first,
        matching: find.byType(Text),
      ),
    )) {
      final value = widget.data?.trim();
      if (value == null || value.isEmpty) {
        continue;
      }
      if (!texts.contains(value)) {
        texts.add(value);
      }
    }
    return texts;
  }

  @override
  List<String> interactiveSemanticsLabels() {
    _expectOnboardingVisible();
    final rootNode = tester.getSemantics(_onboardingSurface.first);
    final labels = <String>[];

    void visit(SemanticsNode node) {
      final children = node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      );
      final label = _normalizedLabel(node.label);
      if (label.isNotEmpty &&
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
  Future<List<String>> collectForwardFocusOrder() async {
    return _collectForwardFocusOrder(_focusCandidates());
  }

  @override
  Future<List<String>> collectBackwardFocusOrder() async {
    return _collectBackwardFocusOrder(_focusCandidates());
  }

  @override
  List<WorkspaceOnboardingContrastObservation> observeContrastSet() {
    _expectOnboardingVisible();
    final colors = this.colors();
    return <WorkspaceOnboardingContrastObservation>[
      _observeTextContrast(
        label: 'Heading',
        textFinder: _titleText,
        background: colors.page,
        minimumContrast: 3.0,
      ),
      _observeTextContrast(
        label: 'Subtitle',
        textFinder: _subtitleText,
        background: colors.page,
        minimumContrast: 4.5,
      ),
      _observeButtonTextContrast(
        label: 'Open existing folder action',
        buttonFinder: _openExistingFolderButton,
        text: _openExistingFolder,
        backgroundFallback: colors.primary,
        minimumContrast: 4.5,
      ),
      _observeButtonIconContrast(
        label: 'Open existing folder icon',
        buttonFinder: _openExistingFolderButton,
        iconLabel: 'folder',
        backgroundFallback: colors.primary,
        minimumContrast: 3.0,
      ),
      _observeButtonTextContrast(
        label: 'Initialize folder action',
        buttonFinder: _initializeFolderButton,
        text: _initializeFolder,
        backgroundFallback: colors.surface,
        minimumContrast: 4.5,
      ),
      _observeButtonIconContrast(
        label: 'Initialize folder icon',
        buttonFinder: _initializeFolderButton,
        iconLabel: 'plus',
        backgroundFallback: colors.surface,
        minimumContrast: 3.0,
      ),
    ];
  }

  @override
  bool hasVisiblePlaceholderText() {
    final textFields = find.descendant(
      of: _onboardingSurface.first,
      matching: find.byType(TextField),
    );
    for (final element in textFields.evaluate()) {
      final widget = element.widget;
      if (widget is! TextField) {
        continue;
      }
      final hintText = widget.decoration?.hintText?.trim() ?? '';
      if (hintText.isNotEmpty && find.text(hintText).evaluate().isNotEmpty) {
        return true;
      }
    }
    return false;
  }

  @override
  bool hasVisibleIcons() {
    return find
        .descendant(
          of: _onboardingSurface.first,
          matching: find.byType(TrackStateIcon),
        )
        .evaluate()
        .isNotEmpty;
  }

  TrackStateColors colors() {
    final context = tester.element(_onboardingSurface.first);
    return context.ts;
  }

  void _expectOnboardingVisible() {
    if (_titleText.evaluate().isEmpty ||
        _onboardingSurface.evaluate().isEmpty) {
      throw StateError('The workspace onboarding screen is not visible.');
    }
  }

  Map<String, Finder> _focusCandidates() {
    return <String, Finder>{
      _openExistingFolder: _openExistingFolderButton,
      _initializeFolder: _initializeFolderButton,
    };
  }

  Future<List<String>> _collectForwardFocusOrder(
    Map<String, Finder> candidates,
  ) async {
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump();

    final order = <String>[];
    for (var index = 0; index < candidates.length; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      final label = _focusedLabel(candidates);
      if (label != null) {
        order.add(label);
      }
    }
    return order;
  }

  Future<List<String>> _collectBackwardFocusOrder(
    Map<String, Finder> candidates,
  ) async {
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump();

    for (var index = 0; index < candidates.length; index += 1) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
    }

    final order = <String>[];
    final initialLabel = _focusedLabel(candidates);
    if (initialLabel != null) {
      order.add(initialLabel);
    }

    for (var index = 1; index < candidates.length; index += 1) {
      await tester.sendKeyDownEvent(LogicalKeyboardKey.shiftLeft);
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.sendKeyUpEvent(LogicalKeyboardKey.shiftLeft);
      await tester.pump();
      final label = _focusedLabel(candidates);
      if (label != null) {
        order.add(label);
      }
    }

    return order;
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

  WorkspaceOnboardingContrastObservation _observeTextContrast({
    required String label,
    required Finder textFinder,
    required Color background,
    required double minimumContrast,
  }) {
    final text = _finderText(textFinder);
    final foreground = _renderedTextColor(textFinder);
    return WorkspaceOnboardingContrastObservation(
      label: label,
      text: text,
      foregroundHex: _rgbHex(foreground),
      backgroundHex: _rgbHex(background),
      contrastRatio: contrastRatio(foreground, background),
      minimumContrast: minimumContrast,
    );
  }

  WorkspaceOnboardingContrastObservation _observeButtonTextContrast({
    required String label,
    required Finder buttonFinder,
    required String text,
    required Color backgroundFallback,
    required double minimumContrast,
  }) {
    final style = _effectiveButtonStyle(buttonFinder.first);
    final foreground =
        style.foregroundColor?.resolve(const <WidgetState>{}) ??
        _renderedTextColorWithin(buttonFinder.first, text);
    final resolvedBackground = style.backgroundColor?.resolve(
      const <WidgetState>{},
    );
    final background =
        resolvedBackground == null || resolvedBackground.alpha == 0
        ? backgroundFallback
        : resolvedBackground;
    return WorkspaceOnboardingContrastObservation(
      label: label,
      text: text,
      foregroundHex: _rgbHex(foreground),
      backgroundHex: _rgbHex(background),
      contrastRatio: contrastRatio(foreground, background),
      minimumContrast: minimumContrast,
    );
  }

  WorkspaceOnboardingContrastObservation _observeButtonIconContrast({
    required String label,
    required Finder buttonFinder,
    required String iconLabel,
    required Color backgroundFallback,
    required double minimumContrast,
  }) {
    final style = _effectiveButtonStyle(buttonFinder.first);
    final resolvedBackground = style.backgroundColor?.resolve(
      const <WidgetState>{},
    );
    final background =
        resolvedBackground == null || resolvedBackground.alpha == 0
        ? backgroundFallback
        : resolvedBackground;
    final foreground = _renderedIconColorWithin(buttonFinder.first);
    return WorkspaceOnboardingContrastObservation(
      label: label,
      text: iconLabel,
      foregroundHex: _rgbHex(foreground),
      backgroundHex: _rgbHex(background),
      contrastRatio: contrastRatio(foreground, background),
      minimumContrast: minimumContrast,
    );
  }

  String _finderText(Finder finder) {
    for (final element in finder.evaluate()) {
      final widget = element.widget;
      if (widget is Text) {
        final value = widget.data?.trim();
        if (value != null && value.isNotEmpty) {
          return value;
        }
      }
      if (widget is RichText) {
        final value = widget.text.toPlainText().trim();
        if (value.isNotEmpty) {
          return value;
        }
      }
    }
    throw StateError('No rendered text found for $finder.');
  }

  Color _renderedTextColor(Finder finder) {
    for (final element in finder.evaluate()) {
      final widget = element.widget;
      if (widget is Text) {
        final color =
            widget.style?.color ?? DefaultTextStyle.of(element).style.color;
        if (color != null) {
          return color;
        }
      }
      if (widget is RichText) {
        final color =
            widget.text.style?.color ??
            DefaultTextStyle.of(element).style.color;
        if (color != null) {
          return color;
        }
      }
    }
    throw StateError('No rendered text color found for $finder.');
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

  Color _renderedIconColorWithin(Finder scope) {
    final iconFinder = find.descendant(
      of: scope,
      matching: find.byType(TrackStateIcon),
    );
    for (final element in iconFinder.evaluate()) {
      final widget = element.widget;
      if (widget is TrackStateIcon && widget.color != null) {
        return widget.color!;
      }
    }
    throw StateError('No rendered icon color found within $scope.');
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

  String _rgbHex(Color color) {
    final rgb = color.toARGB32() & 0x00FFFFFF;
    return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
  }
}
