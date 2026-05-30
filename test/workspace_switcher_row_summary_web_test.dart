@TestOn('browser')
library;

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/services/browser_workspace_switcher_focus_matcher.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'web inactive workspace row summaries stay visible after a row-summary click',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService();
      final activeWorkspace = await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'alpha/repo',
          defaultBranch: 'main',
          displayName: 'alpha/repo',
        ),
      );
      final inactiveWorkspace = await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'beta/repo',
          defaultBranch: 'main',
          displayName: 'beta/repo',
        ),
        select: false,
      );
      await workspaceProfiles.saveHostedAccessMode(
        inactiveWorkspace.id,
        HostedWorkspaceAccessMode.readOnly,
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
        await tester.pumpWidget(
          TrackStateApp(
            repository: const DemoTrackStateRepository(),
            workspaceProfileService: workspaceProfiles,
            openHostedRepository:
                ({
                  required String repository,
                  required String defaultBranch,
                  required String writeBranch,
                }) async => const DemoTrackStateRepository(),
          ),
        );
        await tester.pumpAndSettle();
        await _pumpUntilVisible(
          tester,
          find.byKey(const ValueKey('workspace-switcher-trigger')),
        );

        final triggerSemantics = _semanticsNodeFinder(
          browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier,
        );
        tester.semantics.tap(triggerSemantics);
        await tester.pump();
        await _pumpUntilVisible(
          tester,
          find.byKey(const ValueKey('workspace-switcher-sheet')),
        );

        final switcherSheet = find.byKey(
          const ValueKey('workspace-switcher-sheet'),
        );
        final activeRow = find.byKey(
          ValueKey('workspace-${activeWorkspace.id}'),
        );
        final inactiveRow = find.byKey(
          ValueKey('workspace-${inactiveWorkspace.id}'),
        );

        expect(switcherSheet, findsOneWidget);
        expect(find.text('Saved workspaces'), findsOneWidget);
        expect(activeRow, findsOneWidget);
        expect(inactiveRow, findsOneWidget);

        final inactiveRowSemantics = _semanticsFinderFor(
          tester: tester,
          finder: inactiveRow,
        );
        final inactiveRowData = inactiveRowSemantics
            .evaluate()
            .single
            .getSemanticsData();
        expect(inactiveRowData.hasAction(SemanticsAction.tap), isFalse);

        tester.semantics.performAction(
          inactiveRowSemantics,
          SemanticsAction.tap,
          checkForAction: false,
        );
        await tester.pump();
        await tester.pump(const Duration(seconds: 1));

        expect(switcherSheet, findsOneWidget);
        expect(find.text('Saved workspaces'), findsOneWidget);
        expect(activeRow, findsOneWidget);
        expect(inactiveRow, findsOneWidget);
        expect(
          (await workspaceProfiles.loadState()).activeWorkspaceId,
          activeWorkspace.id,
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

Future<void> _pumpUntilVisible(
  WidgetTester tester,
  Finder finder, {
  int maxPumps = 60,
  Duration step = const Duration(milliseconds: 100),
}) async {
  for (var index = 0; index < maxPumps; index += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  throw TestFailure('Expected $finder to become visible.');
}

FinderBase<SemanticsNode> _semanticsNodeFinder(String identifier) =>
    find.semantics.byPredicate(
      (node) => node.getSemanticsData().identifier == identifier,
      describeMatch: (_) => 'semantics node for $identifier',
    );

FinderBase<SemanticsNode> _semanticsFinderFor({
  required WidgetTester tester,
  required Finder finder,
}) {
  final semanticsId = tester.getSemantics(finder).id;
  return find.semantics.byPredicate(
    (node) => node.id == semanticsId,
    describeMatch: (_) => 'semantics node for $finder',
  );
}
