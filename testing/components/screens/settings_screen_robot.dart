import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

class SettingsScreenRobot {
  SettingsScreenRobot(this.tester);

  final WidgetTester tester;
  static const jqlPlaceholderText =
      'project = TRACK AND status != Done ORDER BY priority DESC';

  Finder get settingsNavigation => find.text('Settings').first;
  Finder get projectSettingsHeading => find.text('Project Settings');
  Finder get issueTypesCard => find.text('Issue Types');
  Finder get workflowCard => find.text('Workflow');
  Finder get fieldsCard => find.text('Fields');
  Finder get languageCard => find.text('Language');
  Finder get localGitControl => _providerControl('Local Git');
  Finder get connectGitHubControl => _providerControl('Connect GitHub');
  Finder get connectedControl => _providerControl('Connected');
  Finder get selectedConnectedControl =>
      find.widgetWithText(FilledButton, 'Connected');
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
  }) async {
    SharedPreferences.setMockInitialValues(sharedPreferences);
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    await tester.pumpWidget(
      TrackStateApp(key: UniqueKey(), repository: repository),
    );
    await tester.pumpAndSettle();
  }

  Future<void> openSettings() async {
    await tester.tap(settingsNavigation);
    await tester.pumpAndSettle();
  }

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
      (node) => node.flagsCollection.isFocused,
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

  Finder _providerControl(String label) => find
      .ancestor(
        of: find.text(label),
        matching: find.bySubtype<ButtonStyleButton>(),
      )
      .first;

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

  FinderBase<SemanticsNode> _semanticsFinderFor(Finder finder) {
    final semanticsId = tester.getSemantics(finder).id;
    return find.semantics.byPredicate(
      (node) => node.id == semanticsId,
      describeMatch: (_) => 'semantics node for $finder',
    );
  }

  List<String> visibleTexts() {
    return tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }
}
