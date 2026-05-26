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
      'Choose a local folder or hosted repository to get started.';
  static const _legacyFirstRunDescription =
      'Choose a local folder to open an existing workspace or initialize '
      'TrackState in a new one.';
  static const _localFolder = 'Local folder';
  static const _hostedRepository = 'Hosted repository';
  static const _repositoryPath = 'Repository Path';
  static const _repository = 'Repository';
  static const _branch = 'Branch';
  static const _open = 'Open';
  static const _localHelper = 'Enter the local Git folder path.';
  static const _hostedHelper = 'Enter the repository as owner/repo.';
  static const _browseUnavailableHint =
      'Connect GitHub in an existing hosted workspace to browse accessible '
      'repositories. You can still enter owner/repo manually here.';
  static const _manualFallbackHint =
      'Select a repository from the current GitHub session or enter owner/repo manually.';
  static const _legacyOpenExistingFolder = 'Open existing folder';
  static const _legacyInitializeFolder = 'Initialize folder';

  Finder get _titleText => find.text(_title);

  Finder get _subtitleText =>
      find.text(_firstRunDescription, skipOffstage: false);

  Finder get _legacySubtitleText =>
      find.text(_legacyFirstRunDescription, skipOffstage: false);

  Finder get _onboardingSurface => find.byType(Scaffold);

  Finder get _modernOpenButton =>
      find.byKey(const ValueKey('workspace-onboarding-open'));

  Finder get _localPathField =>
      find.byKey(const ValueKey('workspace-onboarding-local-path'));

  Finder get _localBranchField =>
      find.byKey(const ValueKey('workspace-onboarding-local-branch'));

  Finder get _hostedRepositoryField =>
      find.byKey(const ValueKey('workspace-onboarding-hosted-repository'));

  Finder get _hostedBranchField =>
      find.byKey(const ValueKey('workspace-onboarding-hosted-branch'));

  Finder get _legacyOpenExistingFolderButton =>
      find.byKey(const ValueKey('local-workspace-onboarding-open-existing'));

  Finder get _legacyInitializeFolderButton => find.byKey(
    const ValueKey('local-workspace-onboarding-initialize-folder'),
  );

  @override
  Future<List<String>> visibleTexts({required bool hosted}) async {
    await _selectTargetIfVisible(hosted: hosted);
    _expectOnboardingVisible();
    final texts = <String>[];
    for (final widget in tester.widgetList<Text>(
      find.descendant(
        of: _onboardingSurface.first,
        matching: find.byType(Text),
      ),
    )) {
      final value = widget.data?.trim();
      if (value == null || value.isEmpty || texts.contains(value)) {
        continue;
      }
      texts.add(value);
    }
    return texts;
  }

  @override
  Future<List<String>> interactiveSemanticsLabels({
    required bool hosted,
  }) async {
    await _selectTargetIfVisible(hosted: hosted);
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
  Future<List<String>> collectForwardFocusOrder({required bool hosted}) async {
    await _selectTargetIfVisible(hosted: hosted);
    return _collectForwardFocusOrder(_focusCandidates(hosted: hosted));
  }

  @override
  Future<List<String>> collectBackwardFocusOrder({required bool hosted}) async {
    await _selectTargetIfVisible(hosted: hosted);
    return _collectBackwardFocusOrder(_focusCandidates(hosted: hosted));
  }

  @override
  Future<List<WorkspaceOnboardingContrastObservation>> observeContrastSet({
    required bool hosted,
  }) async {
    await _selectTargetIfVisible(hosted: hosted);
    _expectOnboardingVisible();
    final colors = this.colors();

    if (_hasModernOnboardingToggle) {
      final observations = <WorkspaceOnboardingContrastObservation>[
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
          label: hosted
              ? 'Hosted repository segmented choice'
              : 'Local folder segmented choice',
          buttonFinder: _buttonForText(
            hosted ? _hostedRepository : _localFolder,
          ),
          text: hosted ? _hostedRepository : _localFolder,
          backgroundFallback: colors.primary,
          minimumContrast: 4.5,
        ),
      ];

      if (hosted) {
        observations.add(
          _observeTextContrast(
            label: 'Repository helper',
            textFinder: find.text(_hostedHelper),
            background: colors.surface,
            minimumContrast: 4.5,
          ),
        );
        final hostedHintFinder = _visibleHostedHintFinder();
        if (hostedHintFinder != null) {
          observations.add(
            _observeTextContrast(
              label: _finderText(hostedHintFinder) == _browseUnavailableHint
                  ? 'Browse unavailable hint'
                  : 'Manual fallback hint',
              textFinder: hostedHintFinder,
              background: colors.surface,
              minimumContrast: 4.5,
            ),
          );
        }
      } else {
        observations.add(
          _observeTextContrast(
            label: 'Local path helper',
            textFinder: find.text(_localHelper),
            background: colors.surface,
            minimumContrast: 4.5,
          ),
        );
      }

      observations.add(
        _observeButtonTextContrast(
          label: 'Open action',
          buttonFinder: _modernOpenButton,
          text: _open,
          backgroundFallback: colors.primary,
          minimumContrast: 4.5,
        ),
      );
      return observations;
    }

    return <WorkspaceOnboardingContrastObservation>[
      _observeTextContrast(
        label: 'Heading',
        textFinder: _titleText,
        background: colors.page,
        minimumContrast: 3.0,
      ),
      _observeTextContrast(
        label: 'Subtitle',
        textFinder: _legacySubtitleText,
        background: colors.page,
        minimumContrast: 4.5,
      ),
      _observeButtonTextContrast(
        label: 'Open existing folder action',
        buttonFinder: _legacyOpenExistingFolderButton,
        text: _legacyOpenExistingFolder,
        backgroundFallback: colors.primary,
        minimumContrast: 4.5,
      ),
      _observeButtonIconContrast(
        label: 'Open existing folder icon',
        buttonFinder: _legacyOpenExistingFolderButton,
        iconLabel: 'folder',
        backgroundFallback: colors.primary,
        minimumContrast: 3.0,
      ),
      _observeButtonTextContrast(
        label: 'Initialize folder action',
        buttonFinder: _legacyInitializeFolderButton,
        text: _legacyInitializeFolder,
        backgroundFallback: colors.surface,
        minimumContrast: 4.5,
      ),
      _observeButtonIconContrast(
        label: 'Initialize folder icon',
        buttonFinder: _legacyInitializeFolderButton,
        iconLabel: 'plus',
        backgroundFallback: colors.surface,
        minimumContrast: 3.0,
      ),
    ];
  }

  @override
  Future<bool> hasVisiblePlaceholderText({required bool hosted}) async {
    await _selectTargetIfVisible(hosted: hosted);
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
  Future<bool> hasVisibleIcons({required bool hosted}) async {
    await _selectTargetIfVisible(hosted: hosted);
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

  bool get _hasModernOnboardingToggle =>
      _buttonForTextOrNull(_localFolder) != null &&
      _buttonForTextOrNull(_hostedRepository) != null &&
      _modernOpenButton.evaluate().isNotEmpty;

  void _expectOnboardingVisible() {
    if (_titleText.evaluate().isEmpty ||
        _onboardingSurface.evaluate().isEmpty) {
      throw StateError('The workspace onboarding screen is not visible.');
    }
  }

  Future<void> _selectTargetIfVisible({required bool hosted}) async {
    _expectOnboardingVisible();
    if (!_hasModernOnboardingToggle) {
      return;
    }
    final targetButton = hosted
        ? _buttonForText(_hostedRepository)
        : _buttonForText(_localFolder);
    await tester.ensureVisible(targetButton);
    await tester.tap(targetButton, warnIfMissed: false);
    await tester.pumpAndSettle();
  }

  Map<String, Finder> _focusCandidates({required bool hosted}) {
    if (_hasModernOnboardingToggle) {
      return <String, Finder>{
        _localFolder: _buttonForText(_localFolder),
        _hostedRepository: _buttonForText(_hostedRepository),
        (hosted ? _repository : _repositoryPath): hosted
            ? _hostedRepositoryField
            : _localPathField,
        _branch: hosted ? _hostedBranchField : _localBranchField,
        _open: _modernOpenButton,
      };
    }
    return <String, Finder>{
      _legacyOpenExistingFolder: _legacyOpenExistingFolderButton,
      _legacyInitializeFolder: _legacyInitializeFolderButton,
    };
  }

  Finder? _visibleHostedHintFinder() {
    for (final candidate in <String>[
      _browseUnavailableHint,
      _manualFallbackHint,
    ]) {
      final finder = find.text(candidate);
      if (finder.evaluate().isNotEmpty) {
        return finder;
      }
    }
    return null;
  }

  Finder _buttonForText(String text) {
    final finder = _buttonForTextOrNull(text);
    if (finder == null) {
      throw StateError('No button found for "$text".');
    }
    return finder;
  }

  Finder? _buttonForTextOrNull(String text) {
    final label = find.text(text);
    if (label.evaluate().isEmpty) {
      return null;
    }
    final button = find.ancestor(
      of: label.first,
      matching: find.bySubtype<ButtonStyleButton>(),
    );
    if (button.evaluate().isEmpty) {
      return null;
    }
    return button.first;
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
