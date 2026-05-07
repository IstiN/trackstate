import 'dart:ui' show PointerDeviceKind, SemanticsFlag;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/core/trackstate_icons.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/local_git_repository_factory.dart';

class SettingsScreenRobot {
  SettingsScreenRobot(
    this.tester, {
    LocalGitRepositoryFactory? localGitRepositoryFactory,
  }) : _localGitRepositoryFactory = localGitRepositoryFactory;

  final WidgetTester tester;
  final LocalGitRepositoryFactory? _localGitRepositoryFactory;
  static const jqlPlaceholderText =
      'project = TRACK AND status != Done ORDER BY priority DESC';

  Finder get settingsNavigation => find.text('Settings').first;
  Finder get projectSettingsHeading => find.text('Project Settings');
  Finder get issueTypesCard => find.text('Issue Types');
  Finder get workflowCard => find.text('Workflow');
  Finder get fieldsCard => find.text('Fields');
  Finder get languageCard => find.text('Language');
  Finder get repositoryAccessSection =>
      find.bySemanticsLabel(RegExp('Repository access'));
  Finder get localGitTopBarControl => topBarProviderControl('Local Git');
  Finder get localGitSettingsControl => settingsProviderControl('Local Git');
  Finder get connectGitHubTopBarControl =>
      topBarProviderControl('Connect GitHub');
  Finder get connectGitHubSettingsControl =>
      settingsProviderControl('Connect GitHub');
  Finder get connectedTopBarControl => topBarProviderControl('Connected');
  Finder get connectedSettingsControl => settingsProviderControl('Connected');
  Finder get localGitControl => providerControl('Local Git');
  Finder get connectGitHubControl => providerControl('Connect GitHub');
  Finder get connectedControl => providerControl('Connected');
  Finder get selectedConnectedControl =>
      _filledSettingsProviderButton('Connected');
  Finder get settingsConnectedControl => find.descendant(
    of: repositoryAccessSection,
    matching: find.widgetWithText(FilledButton, 'Connected'),
  );
  Finder get searchIssuesField => find.byWidgetPredicate(
    (widget) =>
        widget is TextField &&
        widget.decoration?.hintText == jqlPlaceholderText,
    description: 'Settings top-bar search field',
  );
  Finder get darkThemeControl => find.bySemanticsLabel('Dark theme').first;
  Finder get placeholderText => find.text(jqlPlaceholderText);

  Future<void> pumpApp({
    required TrackStateRepository repository,
    Map<String, Object> sharedPreferences = const {},
    Widget Function(Widget child)? appWrapper,
  }) async {
    SharedPreferences.setMockInitialValues(sharedPreferences);
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    final app = TrackStateApp(key: UniqueKey(), repository: repository);
    await tester.pumpWidget(appWrapper == null ? app : appWrapper(app));
    await tester.pumpAndSettle();
  }

  Future<void> pumpLocalGitApp({
    required String repositoryPath,
    Map<String, Object> sharedPreferences = const {},
    Widget Function(Widget child)? appWrapper,
  }) async {
    final localGitRepositoryFactory = _localGitRepositoryFactory;
    if (localGitRepositoryFactory == null) {
      throw StateError('Local Git repository factory is not configured.');
    }
    await pumpApp(
      repository: await localGitRepositoryFactory.create(
        repositoryPath: repositoryPath,
      ),
      sharedPreferences: sharedPreferences,
      appWrapper: appWrapper,
    );
  }

  Future<void> openSettings() async {
    await tester.tap(settingsNavigation);
    await tester.pumpAndSettle();
  }

  Finder providerControl(String label) => find.descendant(
    of: repositoryAccessSection,
    matching: find.ancestor(
      of: find.text(label),
      matching: find.bySubtype<ButtonStyleButton>(),
    ),
  );

  Finder configCard(String title) => _smallestByArea(
    find.ancestor(of: find.text(title), matching: find.byType(Column)),
  );

  Finder configCardItem(String title, String item) =>
      find.descendant(of: configCard(title), matching: find.text(item));

  Future<void> clearFocus() async {
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump();
  }

  void expectVisibleSettingsContent() {
    expect(projectSettingsHeading, findsOneWidget);
    expect(issueTypesCard, findsOneWidget);
    expect(workflowCard, findsOneWidget);
    expect(fieldsCard, findsOneWidget);
    expect(languageCard, findsOneWidget);
  }

  TrackStateColors colors() {
    final context = tester.element(find.byType(Scaffold).first);
    return context.ts;
  }

  Offset centerOf(Finder finder) => tester.getCenter(finder);

  Future<TestGesture> hover(Finder finder) async {
    final gesture = await tester.createGesture(kind: PointerDeviceKind.mouse);
    await gesture.addPointer(location: const Offset(-1, -1));
    await gesture.moveTo(centerOf(finder));
    await tester.pump();
    return gesture;
  }

  Future<TestGesture> pressAndHold(Finder finder) async {
    final gesture = await tester.startGesture(centerOf(finder));
    await tester.pump();
    return gesture;
  }

  Future<List<String>> collectFocusOrder({
    required Map<String, Finder> candidates,
    int tabs = 8,
  }) async {
    final order = <String>[];
    for (var i = 0; i < tabs; i++) {
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.pump();
      final label = focusedLabel(candidates);
      if (label != null) {
        order.add(label);
      }
    }
    return order;
  }

  String? focusedLabel(Map<String, Finder> candidates) {
    final focusedSemantics = find.semantics.byPredicate(
      (node) => node.getSemanticsData().hasFlag(SemanticsFlag.isFocused),
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
      for (var index = 0; index < matches; index++) {
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

  Color renderedTextColor(Finder finder) {
    for (final element in finder.evaluate()) {
      final widget = element.widget;
      if (widget is RichText && widget.text.style?.color != null) {
        return widget.text.style!.color!;
      }
      if (widget is Text && widget.style?.color != null) {
        return widget.style!.color!;
      }
    }
    throw StateError('No rendered text color found for $finder');
  }

  Color renderedTextColorWithin(Finder scope, String text) {
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
    final textFinder = find.descendant(of: scope, matching: find.text(text));
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
    throw StateError('No rendered text "$text" found within $scope');
  }

  Color resolvedButtonForeground(
    Finder scope,
    Set<WidgetState> states, {
    String? text,
  }) {
    final style = _effectiveButtonStyle(scope);
    return style.foregroundColor?.resolve(states) ??
        (text == null
            ? renderedTextColor(scope)
            : renderedTextColorWithin(scope, text));
  }

  Color resolvedButtonBackground(Finder scope, Set<WidgetState> states) {
    final style = _effectiveButtonStyle(scope);
    final background =
        style.backgroundColor?.resolve(states) ?? Colors.transparent;
    final overlay = style.overlayColor?.resolve(states) ?? Colors.transparent;
    return Color.alphaBlend(overlay, background);
  }

  Color renderedButtonBackground(Finder scope) {
    for (final element in scope.evaluate()) {
      final widget = element.widget;
      if (widget is ButtonStyleButton) {
        final color = widget.style?.backgroundColor?.resolve(
          _buttonStates(widget),
        );
        if (color != null) {
          return color;
        }
      }
    }
    final materialFinder = find.descendant(
      of: scope,
      matching: find.byType(Material),
      matchRoot: true,
    );
    for (final element in materialFinder.evaluate()) {
      final widget = element.widget;
      if (widget is Material && widget.color != null) {
        return widget.color!;
      }
    }
    throw StateError('No rendered button background found for $scope');
  }

  Color? _fallbackTextColor(Finder scope) {
    for (final element in scope.evaluate()) {
      final widget = element.widget;
      if (widget is ButtonStyleButton) {
        return widget.style?.foregroundColor?.resolve(<WidgetState>{});
      }
    }
    return null;
  }

  Set<WidgetState> _buttonStates(ButtonStyleButton button) {
    final states = <WidgetState>{};
    final controller = button.statesController;
    if (controller != null) {
      states.addAll(controller.value);
    }
    if (!button.enabled) {
      states.add(WidgetState.disabled);
    }
    return states;
  }

  String semanticsLabelOf(Finder finder) {
    return tester.getSemantics(finder.first).label;
  }

  List<String> visibleProviderLabels(Iterable<String> candidateLabels) {
    final rows = <({String label, double top})>[];
    for (final label in candidateLabels) {
      final control = providerControl(label);
      if (control.evaluate().isEmpty) {
        continue;
      }
      rows.add((label: label, top: tester.getRect(control.first).top));
    }
    rows.sort((left, right) => left.top.compareTo(right.top));
    return rows.map((row) => row.label).toList();
  }

  Finder topBarProviderControl(String label) =>
      _buttonControlWithText(label, requiresTrackStateIcon: true);

  Finder settingsProviderControl(String label) =>
      _buttonControlWithText(label, requiresTrackStateIcon: false);

  FinderBase<SemanticsNode> _semanticsFinderFor(Finder finder) {
    final semanticsId = tester.getSemantics(finder).id;
    return find.semantics.byPredicate(
      (node) => node.id == semanticsId,
      describeMatch: (_) => 'semantics node for $finder',
    );
  }

  Finder _settingsProviderButton(String label) {
    return _lowestButton(
      find.ancestor(
        of: find.text(label),
        matching: find.bySubtype<ButtonStyleButton>(),
      ),
    );
  }

  Finder _filledSettingsProviderButton(String label) {
    return _lowestButton(find.widgetWithText(FilledButton, label));
  }

  Finder _lowestButton(Finder buttons) {
    final matches = buttons.evaluate().length;
    if (matches == 0) {
      return buttons;
    }

    var bestIndex = 0;
    var bestTop = double.negativeInfinity;
    for (var index = 0; index < matches; index++) {
      final top = tester.getRect(buttons.at(index)).top;
      if (top > bestTop) {
        bestTop = top;
        bestIndex = index;
      }
    }
    return buttons.at(bestIndex);
  }

  Finder _smallestByArea(Finder candidates) {
    final matches = candidates.evaluate().length;
    if (matches == 0) {
      return candidates;
    }

    var bestIndex = 0;
    var bestArea = double.infinity;
    for (var index = 0; index < matches; index++) {
      final rect = tester.getRect(candidates.at(index));
      final area = rect.width * rect.height;
      if (area <= bestArea) {
        bestArea = area;
        bestIndex = index;
      }
    }
    return candidates.at(bestIndex);
  }

  List<String> visibleTexts() {
    return tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }

  List<String> visibleConfigItems(String title) {
    final texts = find.descendant(
      of: configCard(title),
      matching: find.byType(Text),
    );
    final values = <String>[];
    for (final element in texts.evaluate()) {
      final widget = element.widget as Text;
      final value = widget.data?.trim();
      if (value == null || value.isEmpty || value == title) {
        continue;
      }
      values.add(value);
    }
    return values;
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
        'No button style available for ${widget.runtimeType}',
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

  Finder _buttonControlWithText(
    String label, {
    required bool requiresTrackStateIcon,
  }) {
    return find.byElementPredicate(
      (element) =>
          element.widget is ButtonStyleButton &&
          _subtreeContainsWidget(
            element,
            (widget) => widget is Text && widget.data?.trim() == label,
          ) &&
          _subtreeContainsWidget(
                element,
                (widget) => widget is TrackStateIcon,
              ) ==
              requiresTrackStateIcon,
      description:
          '${requiresTrackStateIcon ? 'top-bar' : 'settings'} '
          'button control "$label"',
    );
  }

  bool _subtreeContainsWidget(Element root, bool Function(Widget) matches) {
    if (matches(root.widget)) {
      return true;
    }

    var found = false;
    void visit(Element element) {
      if (found) {
        return;
      }
      if (matches(element.widget)) {
        found = true;
        return;
      }
      element.visitChildren(visit);
    }

    root.visitChildren(visit);
    return found;
  }
}
