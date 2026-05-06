import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

class SettingsScreenRobot {
  SettingsScreenRobot(this.tester);

  final WidgetTester tester;

  Finder get settingsNavigation => find.text('Settings').first;
  Finder get projectSettingsHeading => find.text('Project Settings');
  Finder get issueTypesCard => find.text('Issue Types');
  Finder get workflowCard => find.text('Workflow');
  Finder get fieldsCard => find.text('Fields');
  Finder get languageCard => find.text('Language');
  Finder get localGitControl => find.text('Local Git');
  Finder get connectGitHubControl => find.text('Connect GitHub');
  Finder get connectedControl => find.text('Connected');
  Finder get searchIssuesField => find.bySemanticsLabel('Search issues').first;
  Finder get darkThemeControl => find.bySemanticsLabel('Dark theme').first;
  Finder get connectGitHubSemanticControl =>
      find.bySemanticsLabel('Connect GitHub');
  Finder get placeholderText =>
      find.text('project = TRACK AND status != Done ORDER BY priority DESC');
  Finder get connectedText => find.text('Connected');

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
    for (final entry in candidates.entries) {
      final matches = entry.value.evaluate().length;
      if (matches == 0) {
        continue;
      }
      for (var index = 0; index < matches; index++) {
        final semantics = tester.getSemantics(entry.value.at(index));
        if (semantics.flagsCollection.isFocused) {
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

  String semanticsLabelOf(Finder finder) {
    return tester.getSemantics(finder.first).label;
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
