@TestOn('browser')
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'browser Summary field uses a web-safe semantics wrapper in Edit issue',
    (tester) async {
      final semanticsHandle = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        const workspaceId = 'hosted:stable/repo@main';
        const authStore = SharedPreferencesTrackStateAuthStore();
        final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
          authStore: authStore,
        );
        await workspaceProfiles.createProfile(
          const WorkspaceProfileInput(
            targetType: WorkspaceProfileTargetType.hosted,
            target: 'stable/repo',
            defaultBranch: 'main',
            displayName: 'Hosted setup workspace',
          ),
        );
        await authStore.saveToken('github-token', workspaceId: workspaceId);

        await tester.pumpWidget(
          TrackStateApp(
            workspaceProfileService: workspaceProfiles,
            authStore: authStore,
            openHostedRepository:
                ({
                  required String repository,
                  required String defaultBranch,
                  required String writeBranch,
                }) async => const DemoTrackStateRepository(),
          ),
        );
        await _pumpUntilFound(tester, find.text('Board'));

        await tester.tap(find.text('Board').first);
        await _pumpUntilFound(
          tester,
          find.bySemanticsLabel(RegExp('Open TRACK-12 Implement Git sync service')),
        );

        await tester.tap(
          find.bySemanticsLabel(RegExp('Open TRACK-12 Implement Git sync service'))
              .first,
        );
        await _pumpUntilFound(tester, find.text('Edit'));

        await tester.tap(find.text('Edit').first);
        final summaryField = find.byWidgetPredicate(
          (widget) =>
              widget is TextField && widget.decoration?.labelText == 'Summary',
          description: 'Summary text field',
        );
        await _pumpUntilFound(tester, summaryField);

        final excludedInnerSemantics = find.ancestor(
          of: summaryField,
          matching: find.byType(ExcludeSemantics),
        );

        expect(
          excludedInnerSemantics,
          findsOneWidget,
          reason:
              'The browser Edit issue Summary field must exclude inner '
              'TextField semantics so web accessibility uses the synchronized '
              'wrapper instead of a stale duplicate browser input.',
        );
      } finally {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pump(const Duration(seconds: 1));
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semanticsHandle.dispose();
      }
    },
  );
}

Future<void> _pumpUntilFound(WidgetTester tester, Finder finder) async {
  await tester.pump();
  for (var index = 0; index < 200; index += 1) {
    if (finder.evaluate().isNotEmpty) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 50));
  }
  expect(finder, findsWidgets);
}
