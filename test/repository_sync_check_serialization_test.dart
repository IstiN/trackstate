import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'RepositorySyncCheck jsonEncode preserves explicit load_snapshot_delta=0',
    () {
      final controlPayload = _encode(
        RepositorySyncCheck(
          state: _state(),
          signals: const <WorkspaceSyncSignal>{
            WorkspaceSyncSignal.hostedRepository,
          },
        ),
      );
      final explicitPayload = _encode(
        RepositorySyncCheck(
          state: _state(),
          signals: const <WorkspaceSyncSignal>{
            WorkspaceSyncSignal.hostedRepository,
          },
          hostedSnapshotReloadDirective: HostedSnapshotReloadDirective.disabled,
        ),
      );

      expect(controlPayload['state'], <String, Object?>{
        'provider_type': 'github',
        'repository_revision': 'repo-sha',
        'session_revision': 'session-sha',
        'connection_state': 'connected',
        'working_tree_revision': null,
        'permission': <String, Object?>{
          'can_read': true,
          'can_write': true,
          'is_admin': false,
          'can_create_branch': true,
          'can_manage_attachments': true,
          'attachment_upload_mode': 'full',
          'supports_release_attachment_writes': false,
          'release_attachment_write_failure_reason': null,
          'can_check_collaborators': false,
        },
      });
      expect(controlPayload['signals'], <String>['hostedRepository']);
      expect(controlPayload['changed_paths'], isEmpty);
      expect(controlPayload.containsKey('load_snapshot_delta'), isFalse);

      expect(explicitPayload['load_snapshot_delta'], 0);
      expect(jsonEncode(explicitPayload), isNot(jsonEncode(controlPayload)));
    },
  );
}

Map<String, Object?> _encode(RepositorySyncCheck syncCheck) =>
    Map<String, Object?>.from(jsonDecode(jsonEncode(syncCheck)) as Map);

RepositorySyncState _state() => RepositorySyncState(
  providerType: ProviderType.github,
  repositoryRevision: 'repo-sha',
  sessionRevision: 'session-sha',
  connectionState: ProviderConnectionState.connected,
  permission: const RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
  ),
);
