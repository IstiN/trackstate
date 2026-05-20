import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'desktop primary navigation tabs from Create issue through Settings, workspace switcher, and Search issues',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        final focusCandidates = <String, Finder>{
          'Search issues': find.byType(TextField),
          'Create issue': find.bySemanticsLabel(RegExp('^Create issue\$')).last,
          'Board': find.bySemanticsLabel(RegExp('^Board\$')).last,
          'JQL Search': find.bySemanticsLabel(RegExp('^JQL Search\$')).last,
          'Hierarchy': find.bySemanticsLabel(RegExp('^Hierarchy\$')).last,
          'Settings': find.bySemanticsLabel(RegExp('^Settings\$')).last,
          'Workspace switcher': find.byKey(
            const ValueKey('workspace-switcher-trigger'),
          ),
        };

        await tester.tap(focusCandidates['Search issues']!);
        await tester.pump();

        final focusOrder = await _collectFocusOrder(
          tester,
          focusedLabel: () => _focusedLabel(tester, focusCandidates),
          tabSteps: 10,
        );

        final primaryOrder = focusOrder
            .where((label) => label != '<outside candidates>')
            .take(8)
            .toList();

        expect(primaryOrder, const <String>[
          'Search issues',
          'Create issue',
          'Board',
          'JQL Search',
          'Hierarchy',
          'Settings',
          'Workspace switcher',
          'Search issues',
        ]);
      } finally {
        semantics.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'desktop primary navigation keeps reverse Tab order between Search issues, workspace switcher, and Settings',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        final focusCandidates = <String, Finder>{
          'Search issues': find.byType(TextField),
          'Settings': find.bySemanticsLabel(RegExp('^Settings\$')).last,
          'Workspace switcher': find.byKey(
            const ValueKey('workspace-switcher-trigger'),
          ),
        };

        await tester.tap(focusCandidates['Search issues']!);
        await tester.pump();

        final reverseOrder = <String>[_focusedLabel(tester, focusCandidates)!];
        await _sendShiftTab(tester);
        reverseOrder.add(_focusedLabel(tester, focusCandidates)!);
        await _sendShiftTab(tester);
        reverseOrder.add(_focusedLabel(tester, focusCandidates)!);

        expect(reverseOrder, const <String>[
          'Search issues',
          'Workspace switcher',
          'Settings',
        ]);
      } finally {
        semantics.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );

  testWidgets(
    'desktop tab order reaches secondary header controls and repository banner actions after search',
    (tester) async {
      const attachmentRestrictedPermission = RepositoryPermission(
        canRead: true,
        canWrite: true,
        isAdmin: false,
        canCreateBranch: true,
        canManageAttachments: false,
        attachmentUploadMode: AttachmentUploadMode.noLfs,
        canCheckCollaborators: false,
      );
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      SharedPreferences.setMockInitialValues(const <String, Object>{
        'trackstate.githubToken.trackstate.trackstate':
            'desktop-focus-order-token',
      });

      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: attachmentRestrictedPermission,
            ),
          ),
        );
        await tester.pumpAndSettle();

        final focusCandidates = <String, Finder>{
          'Search issues': find.byType(TextField),
          'Dark theme': find.bySemanticsLabel(RegExp('^Dark theme\$')).last,
          'Synced with Git': find.byKey(const ValueKey('workspace-sync-pill')),
          'Open settings': find.bySemanticsLabel(
            RegExp('^${RegExp.escape('Open settings')}\$'),
          ),
          'Create issue': find.bySemanticsLabel(RegExp('^Create issue\$')).last,
        };

        await tester.tap(focusCandidates['Search issues']!);
        await tester.pump();

        final focusOrder = await _collectFocusOrder(
          tester,
          focusedLabel: () => _focusedLabel(tester, focusCandidates),
          tabSteps: 8,
        );

        final reachableOrder = focusOrder
            .where((label) => label != '<outside candidates>')
            .take(4)
            .toList();

        expect(reachableOrder, const <String>[
          'Search issues',
          'Dark theme',
          'Synced with Git',
          'Open settings',
        ]);
      } finally {
        semantics.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}

Future<void> _sendShiftTab(WidgetTester tester) async {
  await tester.sendKeyDownEvent(LogicalKeyboardKey.shiftLeft);
  await tester.sendKeyEvent(LogicalKeyboardKey.tab);
  await tester.sendKeyUpEvent(LogicalKeyboardKey.shiftLeft);
  await tester.pump();
}

Future<List<String>> _collectFocusOrder(
  WidgetTester tester, {
  required String? Function() focusedLabel,
  required int tabSteps,
}) async {
  final order = <String>[focusedLabel() ?? '<outside candidates>'];
  for (var index = 0; index < tabSteps; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    order.add(focusedLabel() ?? '<outside candidates>');
  }
  return order;
}

String? _focusedLabel(
  WidgetTester tester,
  Map<String, Finder> focusCandidates,
) {
  final focusContext = FocusManager.instance.primaryFocus?.context;
  if (focusContext == null) {
    return null;
  }

  for (final entry in focusCandidates.entries) {
    final finder = entry.value;
    if (finder.evaluate().isEmpty) {
      continue;
    }

    final targetElements = finder.evaluate().toSet();
    if (targetElements.contains(focusContext)) {
      return entry.key;
    }

    var found = false;
    focusContext.visitAncestorElements((element) {
      if (targetElements.contains(element)) {
        found = true;
        return false;
      }
      return true;
    });
    if (found) {
      return entry.key;
    }
  }

  return null;
}
