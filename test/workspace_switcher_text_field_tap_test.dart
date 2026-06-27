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
    'tapping repository and branch text fields keeps the workspace switcher open',
    (tester) async {
      const repository = 'IstiN/trackstate-setup';
      const defaultBranch = 'main';
      final service = SharedPreferencesWorkspaceProfileService(
        authStore: const SharedPreferencesTrackStateAuthStore(),
      );
      await service.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: repository,
          defaultBranch: defaultBranch,
          displayName: 'TrackState setup (main)',
        ),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        TrackStateApp(
          repository: const DemoTrackStateRepository(),
          workspaceProfileService: service,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => const DemoTrackStateRepository(),
        ),
      );
      await tester.pump();
      await tester.pumpAndSettle();

      final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
      expect(trigger, findsOneWidget);
      await tester.tap(trigger);
      await tester.pumpAndSettle();

      final sheet = find.byKey(const ValueKey('workspace-switcher-sheet'));
      expect(sheet, findsOneWidget);

      final repositoryField = find.ancestor(
        of: find.text('Repository'),
        matching: find.byType(TextField),
      );
      final branchField = find.ancestor(
        of: find.text('Branch'),
        matching: find.byType(TextField),
      );
      expect(repositoryField, findsOneWidget);
      expect(branchField, findsOneWidget);

      await tester.tap(repositoryField);
      await tester.pumpAndSettle();
      expect(sheet, findsOneWidget);

      await tester.tap(branchField);
      await tester.pumpAndSettle();
      expect(sheet, findsOneWidget);
    },
  );
}
