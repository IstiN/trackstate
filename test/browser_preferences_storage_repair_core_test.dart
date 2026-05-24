import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/browser_preferences_storage_repair_core.dart';

void main() {
  test(
    'repairs raw preloaded workspace state and repository token values into shared_preferences web format',
    () {
      final rawWorkspaceState = jsonEncode({
        'activeWorkspaceId': 'hosted:istin/trackstate-setup@main',
        'migrationComplete': true,
        'profiles': [
          {
            'id': 'hosted:istin/trackstate-setup@main',
            'displayName': '',
            'targetType': 'hosted',
            'target': 'IstiN/trackstate-setup',
            'defaultBranch': 'main',
            'writeBranch': 'main',
          },
        ],
      });
      final storage = _FakeBrowserPreferencesStorage({
        'trackstate.workspaceProfiles.state': rawWorkspaceState,
        'flutter.trackstate.workspaceProfiles.state': rawWorkspaceState,
        'trackstate.githubToken.IstiN.trackstate-setup': 'test-token',
        'flutter.trackstate.githubToken.IstiN.trackstate-setup': 'test-token',
      });

      repairBrowserPreferencesStorageEntries(storage);

      expect(
        storage.values['flutter.trackstate.workspaceProfiles.state'],
        jsonEncode(rawWorkspaceState),
      );
      expect(
        storage.values['trackstate.workspaceProfiles.state'],
        rawWorkspaceState,
      );
      expect(
        storage.values['flutter.trackstate.githubToken.IstiN.trackstate-setup'],
        jsonEncode('test-token'),
      );
    },
  );

  test(
    'repairs a stale raw workspace state key from the newer shared_preferences web value',
    () {
      final staleRawWorkspaceState = jsonEncode({
        'activeWorkspaceId': 'hosted:istin/trackstate-setup@main',
        'migrationComplete': true,
        'profiles': [
          {
            'id': 'hosted:istin/trackstate-setup@main',
            'displayName': 'Hosted setup workspace',
            'targetType': 'hosted',
            'target': 'IstiN/trackstate-setup',
            'defaultBranch': 'main',
            'writeBranch': 'main',
          },
        ],
      });
      final updatedWorkspaceState = jsonEncode({
        'activeWorkspaceId': 'local:/tmp/trackstate-ts980-workspace@main',
        'migrationComplete': true,
        'profiles': [
          {
            'id': 'local:/tmp/trackstate-ts980-workspace@main',
            'displayName': 'Restorable local workspace',
            'targetType': 'local',
            'target': '/tmp/trackstate-ts980-workspace',
            'defaultBranch': 'main',
            'writeBranch': 'main',
          },
          {
            'id': 'hosted:istin/trackstate-setup@main',
            'displayName': 'Hosted setup workspace',
            'targetType': 'hosted',
            'target': 'IstiN/trackstate-setup',
            'defaultBranch': 'main',
            'writeBranch': 'main',
          },
        ],
      });
      final storage = _FakeBrowserPreferencesStorage({
        'trackstate.workspaceProfiles.state': staleRawWorkspaceState,
        'flutter.trackstate.workspaceProfiles.state': jsonEncode(
          updatedWorkspaceState,
        ),
      });

      repairBrowserPreferencesStorageEntries(storage);

      expect(
        storage.values['trackstate.workspaceProfiles.state'],
        updatedWorkspaceState,
      );
      expect(
        storage.values['flutter.trackstate.workspaceProfiles.state'],
        jsonEncode(updatedWorkspaceState),
      );
    },
  );

  test(
    'repairs raw preloaded workspace-scoped token values into shared_preferences web format',
    () {
      const workspaceId = 'hosted:istin/trackstate-setup@main';
      final encodedWorkspaceId = Uri.encodeComponent(workspaceId);
      final plainKey = 'trackstate.githubToken.workspace.$encodedWorkspaceId';
      final prefixedKey = 'flutter.$plainKey';
      final storage = _FakeBrowserPreferencesStorage({
        plainKey: 'workspace-token',
        prefixedKey: 'workspace-token',
      });

      repairBrowserPreferencesStorageEntries(storage);

      expect(storage.values[prefixedKey], jsonEncode('workspace-token'));
    },
  );

  test(
    'reports malformed preloaded browser storage repairs for startup diagnostics',
    () {
      final rawWorkspaceState = jsonEncode({
        'activeWorkspaceId': 'hosted:istin/trackstate-setup@main',
        'migrationComplete': true,
        'profiles': [
          {
            'id': 'hosted:istin/trackstate-setup@main',
            'displayName': '',
            'targetType': 'hosted',
            'target': 'IstiN/trackstate-setup',
            'defaultBranch': 'main',
            'writeBranch': 'main',
          },
        ],
      });
      final storage = _FakeBrowserPreferencesStorage({
        'flutter.trackstate.workspaceProfiles.state': rawWorkspaceState,
        'flutter.trackstate.githubToken.IstiN.trackstate-setup': 'test-token',
      });

      final dynamic repairReport =
          (repairBrowserPreferencesStorageEntries as dynamic)(storage);

      expect(repairReport, isNotNull);
      expect(repairReport.hasRepairs, isTrue);

      final diagnosticMessage =
          repairReport.toDiagnosticMessage(includePrefix: false) as String;

      expect(diagnosticMessage, contains('workspace'));
      expect(diagnosticMessage, contains('storage'));
      expect(diagnosticMessage, contains('schema'));
      expect(diagnosticMessage, contains('shared_preferences'));
      expect(diagnosticMessage, contains('malformed'));
      expect(diagnosticMessage, contains('repair'));
    },
  );
}

class _FakeBrowserPreferencesStorage implements BrowserPreferencesStorage {
  _FakeBrowserPreferencesStorage(this.values);

  final Map<String, String> values;

  @override
  Iterable<String> get keys => values.keys;

  @override
  void remove(String key) {
    values.remove(key);
  }

  @override
  String? read(String key) => values[key];

  @override
  void write(String key, String value) {
    values[key] = value;
  }
}
