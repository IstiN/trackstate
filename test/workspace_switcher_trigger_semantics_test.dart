import 'dart:ui' show Tristate;
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_matcher.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('desktop workspace switcher exports focusable button semantics', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      final triggerNode = tester.getSemantics(
        find.bySemanticsLabel(RegExp('^Workspace switcher:')).last,
      );
      final triggerSemantics = triggerNode.getSemanticsData();

      expect(triggerSemantics.flagsCollection.isButton, isTrue);
      expect(
        triggerSemantics.flagsCollection.isFocused != Tristate.none,
        isTrue,
        reason:
            'The exported workspace switcher semantics node must be keyboard focusable '
            'so Flutter web can map it to a tabbable browser control.',
      );
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      semantics.dispose();
    }
  });

  testWidgets(
    'desktop workspace switcher trigger keeps a stable controls relationship while collapsed',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;

        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        final trigger = find.byKey(
          const ValueKey('workspace-switcher-trigger'),
        );
        final triggerSemantics = tester
            .getSemantics(trigger)
            .getSemanticsData();

        expect(
          triggerSemantics.controlsNodes,
          contains(browserWorkspaceSwitcherSemanticsIdentifier),
        );
        expect(
          find.byWidgetPredicate(
            (widget) =>
                widget is Semantics &&
                widget.properties.identifier ==
                    browserWorkspaceSwitcherSemanticsIdentifier,
            description:
                'workspace switcher sheet semantics anchor with a stable identifier',
          ),
          findsOneWidget,
        );
        expect(
          find.byKey(const ValueKey('workspace-switcher-sheet')),
          findsNothing,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop workspace switcher trigger exposes expandable semantics as visibility changes',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        final layouts = <({String name, Size size})>[
          (name: 'wide', size: const Size(1600, 960)),
          (name: 'condensed', size: const Size(1280, 960)),
        ];

        for (final layout in layouts) {
          tester.view.physicalSize = layout.size;
          tester.view.devicePixelRatio = 1;

          await tester.pumpWidget(
            const TrackStateApp(repository: DemoTrackStateRepository()),
          );
          await tester.pumpAndSettle();

          final trigger = find.byKey(
            const ValueKey('workspace-switcher-trigger'),
          );
          expect(trigger, findsOneWidget);

          await _focusByTabUntil(
            tester,
            isFocused: () => _focusWithinFinder(tester, trigger),
            reason:
                'Failed to focus the ${layout.name} workspace switcher trigger.',
          );

          _expectExpandedState(
            tester,
            trigger: trigger,
            context: '${layout.name} collapsed',
            hasExpandedState: true,
            isExpanded: false,
          );

          await tester.sendKeyEvent(LogicalKeyboardKey.space);
          await tester.pumpAndSettle();

          expect(
            find.byKey(const ValueKey('workspace-switcher-sheet')),
            findsOneWidget,
          );
          _expectExpandedState(
            tester,
            trigger: trigger,
            context: '${layout.name} opened',
            hasExpandedState: true,
            isExpanded: true,
          );

          await tester.sendKeyEvent(LogicalKeyboardKey.escape);
          await tester.pumpAndSettle();

          expect(
            find.byKey(const ValueKey('workspace-switcher-sheet')),
            findsNothing,
          );
          _expectExpandedState(
            tester,
            trigger: trigger,
            context: '${layout.name} closed',
            hasExpandedState: true,
            isExpanded: false,
          );
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop workspace switcher trigger closes the expanded surface on a second Space key press',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;

        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        final trigger = find.byKey(
          const ValueKey('workspace-switcher-trigger'),
        );
        expect(trigger, findsOneWidget);

        await _focusByTabUntil(
          tester,
          isFocused: () => _focusWithinFinder(tester, trigger),
          reason: 'Failed to focus the workspace switcher trigger.',
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.space);
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('workspace-switcher-sheet')),
          findsOneWidget,
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.space);
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('workspace-switcher-sheet')),
          findsNothing,
        );
        expect(_focusWithinFinder(tester, trigger), isTrue);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop workspace switcher trigger closes the expanded surface on a second Enter key press',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;

        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        final trigger = find.byKey(
          const ValueKey('workspace-switcher-trigger'),
        );
        expect(trigger, findsOneWidget);

        await _focusByTabUntil(
          tester,
          isFocused: () => _focusWithinFinder(tester, trigger),
          reason: 'Failed to focus the workspace switcher trigger.',
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.enter);
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('workspace-switcher-sheet')),
          findsOneWidget,
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.enter);
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('workspace-switcher-sheet')),
          findsNothing,
        );
        expect(_focusWithinFinder(tester, trigger), isTrue);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop workspace switcher keeps focus on the trigger when opened',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;

        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        final trigger = find.byKey(
          const ValueKey('workspace-switcher-trigger'),
        );
        final searchField = find.byType(TextField).first;

        await tester.tap(trigger);
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('workspace-switcher-sheet')),
          findsOneWidget,
        );
        expect(
          _focusWithinFinder(tester, trigger),
          isTrue,
          reason:
              'Opening the desktop workspace switcher should keep focus on the '
              'trigger so the next Tab can leave the component.',
        );

        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();

        expect(_focusWithinFinder(tester, searchField), isTrue);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

Future<void> _focusByTabUntil(
  WidgetTester tester, {
  required bool Function() isFocused,
  required String reason,
  int maxTabs = 24,
}) async {
  for (var index = 0; index < maxTabs; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    if (isFocused()) {
      return;
    }
  }

  throw TestFailure(reason);
}

bool _focusWithinFinder(WidgetTester tester, Finder ancestorFinder) {
  final focusContext = FocusManager.instance.primaryFocus?.context;
  if (focusContext == null) {
    return false;
  }
  final targetElements = ancestorFinder.evaluate().toSet();
  if (targetElements.contains(focusContext)) {
    return true;
  }
  var found = false;
  focusContext.visitAncestorElements((element) {
    if (targetElements.contains(element)) {
      found = true;
      return false;
    }
    return true;
  });
  return found;
}

void _expectExpandedState(
  WidgetTester tester, {
  required Finder trigger,
  required String context,
  required bool hasExpandedState,
  required bool isExpanded,
}) {
  final semantics = tester.getSemantics(trigger).getSemanticsData();

  expect(
    semantics.flagsCollection.isExpanded != Tristate.none,
    hasExpandedState,
    reason:
        '$context should expose hasExpandedState=$hasExpandedState, '
        'but was ${semantics.flagsCollection.isExpanded != Tristate.none}.',
  );
  expect(
    semantics.flagsCollection.isExpanded == Tristate.isTrue,
    isExpanded,
    reason:
        '$context should expose isExpanded=$isExpanded, '
        'but was ${semantics.flagsCollection.isExpanded == Tristate.isTrue}.',
  );
}