import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

const String _ticketKey = 'TS-665';
const String _activeRepository = 'trackstate/trackstate';
const String _unrelatedRepository = 'other/repository';
const String _defaultBranch = 'main';
const String _activeLegacyToken = 'ts665-active-legacy-token';
const String _unrelatedLegacyToken = 'ts665-unrelated-legacy-token';
const String _workspaceStateKey = 'trackstate.workspaceProfiles.state';
const String _workspaceTokenPrefix = 'trackstate.githubToken.workspace.';
const String _activeLegacyTokenKey =
    'trackstate.githubToken.trackstate.trackstate';
const String _unrelatedLegacyTokenKey =
    'trackstate.githubToken.other.repository';
const String _expectedWorkspaceId = 'hosted:trackstate/trackstate@main';
const String _expectedWorkspaceDisplayName = 'trackstate/trackstate';
const String _expectedLogin = 'demo-user';
const String _expectedDisplayName = 'Demo User';
const String _expectedInitials = 'DU';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-665 first-run migration converts the active legacy hosted context into one scoped workspace',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final failures = <String>[];
      final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 13, 22, 0, 40),
      );
      const authStore = SharedPreferencesTrackStateAuthStore();

      SharedPreferences.setMockInitialValues(const <String, Object>{
        _activeLegacyTokenKey: _activeLegacyToken,
        _unrelatedLegacyTokenKey: _unrelatedLegacyToken,
      });

      final migratedWorkspace = await workspaceProfileService
          .ensureLegacyContextMigrated(
            const WorkspaceProfileInput(
              targetType: WorkspaceProfileTargetType.hosted,
              target: _activeRepository,
              defaultBranch: _defaultBranch,
            ),
          );

      final workspaceState = await workspaceProfileService.loadState();
      final preferences = await SharedPreferences.getInstance();
      final migratedWorkspaceToken = await authStore.readToken(
        workspaceId: _expectedWorkspaceId,
      );
      final leftoverActiveLegacyToken = await authStore.readToken(
        repository: _activeRepository,
      );
      final unrelatedLegacyTokenAfterMigration = await authStore.readToken(
        repository: _unrelatedRepository,
      );
      final workspaceScopedKeys = preferences.getKeys().where((key) {
        return key.startsWith(_workspaceTokenPrefix);
      }).toList()..sort();
      final expectedWorkspaceTokenKey =
          '$_workspaceTokenPrefix${Uri.encodeComponent(_expectedWorkspaceId)}';
      final rawWorkspaceState = preferences.getString(_workspaceStateKey);
      final decodedWorkspaceState = rawWorkspaceState == null
          ? null
          : jsonDecode(rawWorkspaceState) as Map<String, Object?>;

      if (migratedWorkspace == null) {
        failures.add(
          'Step 2 failed: WorkspaceMigrationCoordinator did not return a seeded workspace for the valid hosted legacy context.',
        );
      } else {
        if (migratedWorkspace.id != _expectedWorkspaceId) {
          failures.add(
            'Step 2 failed: the seeded workspace id was "${migratedWorkspace.id}" instead of "$_expectedWorkspaceId".',
          );
        }
        if (migratedWorkspace.displayName != _expectedWorkspaceDisplayName) {
          failures.add(
            'Step 2 failed: the seeded workspace display name was "${migratedWorkspace.displayName}" instead of "$_expectedWorkspaceDisplayName".',
          );
        }
      }

      if (workspaceState.profiles.length != 1) {
        failures.add(
          'Step 3 failed: WorkspaceProfileStore persisted ${workspaceState.profiles.length} workspaces instead of exactly one.\n'
          'Observed profiles: ${workspaceState.profiles.map((profile) => profile.toJson()).toList()}',
        );
      }
      if (workspaceState.activeWorkspaceId != _expectedWorkspaceId) {
        failures.add(
          'Step 3 failed: WorkspaceProfileStore activeWorkspaceId was "${workspaceState.activeWorkspaceId}" instead of "$_expectedWorkspaceId".',
        );
      }
      if (!workspaceState.migrationComplete) {
        failures.add(
          'Step 3 failed: WorkspaceProfileStore did not mark migrationComplete=true after first-run migration.',
        );
      }
      if (workspaceState.activeWorkspace?.displayName !=
          _expectedWorkspaceDisplayName) {
        failures.add(
          'Step 3 failed: the active workspace display name was "${workspaceState.activeWorkspace?.displayName}" instead of "$_expectedWorkspaceDisplayName".',
        );
      }

      final decodedProfiles =
          decodedWorkspaceState?['profiles'] as List<Object?>? ??
          const <Object?>[];
      if (decodedProfiles.length != 1) {
        failures.add(
          'Step 3 failed: the raw WorkspaceProfileStore JSON kept ${decodedProfiles.length} profiles instead of one.\n'
          'Raw state: ${rawWorkspaceState ?? '<missing>'}',
        );
      }
      if (decodedWorkspaceState?['activeWorkspaceId'] != _expectedWorkspaceId) {
        failures.add(
          'Step 3 failed: the raw WorkspaceProfileStore JSON did not preserve "$_expectedWorkspaceId" as activeWorkspaceId.\n'
          'Raw state: ${rawWorkspaceState ?? '<missing>'}',
        );
      }
      if (decodedWorkspaceState?['migrationComplete'] != true) {
        failures.add(
          'Step 3 failed: the raw WorkspaceProfileStore JSON did not persist migrationComplete=true.\n'
          'Raw state: ${rawWorkspaceState ?? '<missing>'}',
        );
      }

      if (migratedWorkspaceToken != _activeLegacyToken) {
        failures.add(
          'Step 4 failed: WorkspaceCredentialStore saved "${migratedWorkspaceToken ?? '<missing>'}" under the workspace-scoped key instead of "$_activeLegacyToken".',
        );
      }
      if (leftoverActiveLegacyToken != null) {
        failures.add(
          'Step 4 failed: the active legacy repository token still remained under "$_activeLegacyTokenKey" after migration.\n'
          'Observed token: $leftoverActiveLegacyToken',
        );
      }
      if (unrelatedLegacyTokenAfterMigration != _unrelatedLegacyToken) {
        failures.add(
          'Expected result failed: the unrelated legacy token was "${unrelatedLegacyTokenAfterMigration ?? '<missing>'}" instead of staying "$_unrelatedLegacyToken".',
        );
      }
      if (workspaceScopedKeys.length != 1 ||
          workspaceScopedKeys.single != expectedWorkspaceTokenKey) {
        failures.add(
          'Expected result failed: credential migration created the wrong workspace-scoped keys.\n'
          'Expected only: $expectedWorkspaceTokenKey\n'
          'Observed: $workspaceScopedKeys',
        );
      }
      if (preferences.getString(expectedWorkspaceTokenKey) !=
          _activeLegacyToken) {
        failures.add(
          'Step 4 failed: SharedPreferences did not persist "$_activeLegacyToken" at "$expectedWorkspaceTokenKey".',
        );
      }
      if (preferences.getString(_unrelatedLegacyTokenKey) !=
          _unrelatedLegacyToken) {
        failures.add(
          'Expected result failed: the unrelated legacy SharedPreferences token changed unexpectedly.\n'
          'Observed value: ${preferences.getString(_unrelatedLegacyTokenKey) ?? '<missing>'}',
        );
      }

      await tester.pumpWidget(
        TrackStateApp(
          repository: const DemoTrackStateRepository(),
          workspaceProfileService: workspaceProfileService,
        ),
      );
      await tester.pumpAndSettle();

      final connectedStateVisible =
          find.text('Connected').evaluate().isNotEmpty ||
          find.bySemanticsLabel(RegExp('^Connected\$')).evaluate().isNotEmpty;
      final visibleTexts = _visibleTexts(tester);
      if (!connectedStateVisible) {
        failures.add(
          'Human-style verification failed: after migration, the app chrome did not show the visible Connected state a hosted user should see.\n'
          'Visible texts: ${_formatSnapshot(visibleTexts)}',
        );
      }
      if (find.text(_expectedDisplayName).evaluate().isEmpty) {
        failures.add(
          'Human-style verification failed: the top bar did not show the migrated user display name "$_expectedDisplayName".\n'
          'Visible texts: ${_formatSnapshot(visibleTexts)}',
        );
      }
      if (!_containsTextFragment(visibleTexts, _expectedLogin)) {
        failures.add(
          'Human-style verification failed: the top bar did not show the migrated user login "$_expectedLogin".\n'
          'Visible texts: ${_formatSnapshot(visibleTexts)}',
        );
      }
      if (find.text(_expectedInitials).evaluate().isEmpty) {
        failures.add(
          'Human-style verification failed: the top bar did not show the migrated user initials "$_expectedInitials".\n'
          'Visible texts: ${_formatSnapshot(visibleTexts)}',
        );
      }

      if (failures.isNotEmpty) {
        fail(failures.join('\n'));
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

List<String> _visibleTexts(WidgetTester tester) {
  final snapshot = <String>[];
  for (final widget in tester.widgetList<Text>(find.byType(Text))) {
    final value = widget.data?.trim();
    if (value == null || value.isEmpty || snapshot.contains(value)) {
      continue;
    }
    snapshot.add(value);
  }
  return snapshot;
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
  if (values.isEmpty) {
    return '<none>';
  }
  if (values.length <= limit) {
    return values.join(' | ');
  }
  return values.take(limit).join(' | ');
}

bool _containsTextFragment(List<String> values, String fragment) {
  for (final value in values) {
    if (value.contains(fragment)) {
      return true;
    }
  }
  return false;
}
