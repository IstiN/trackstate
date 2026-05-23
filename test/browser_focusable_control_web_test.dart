@TestOn('browser')
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'web startup keeps the shell visible when the saved active local workspace has no browser handle',
    (tester) async {
      const activeLocalWorkspaceId = 'local:/tmp/trackstate-demo@main';
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService();
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.local,
          target: '/tmp/trackstate-demo',
          defaultBranch: 'main',
        ),
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
        ),
        select: false,
      );

      var browserLocalRepositoryChecks = 0;
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repositoryFactory: DemoTrackStateRepository.new,
          workspaceProfileService: workspaceProfiles,
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async => const DemoTrackStateRepository(),
          openBrowserLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                browserLocalRepositoryChecks += 1;
                expect(repositoryPath, '/tmp/trackstate-demo');
                return null;
              },
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => const DemoTrackStateRepository(),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsOneWidget,
      );
      expect(browserLocalRepositoryChecks, greaterThanOrEqualTo(1));
      final savedState = await workspaceProfiles.loadState();
      expect(savedState.activeWorkspaceId, activeLocalWorkspaceId);
      expect(
        savedState.unavailableLocalWorkspaceIds,
        contains(activeLocalWorkspaceId),
      );
    },
  );
}
