import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  test(
    'reactive hosted repository sync stays disconnected until authentication succeeds',
    () async {
      const readOnlyPermission = RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
        canManageAttachments: false,
        canCheckCollaborators: false,
      );
      final repository = ReactiveIssueDetailTrackStateRepository(
        permission: readOnlyPermission,
      );

      final initialSession =
          repository.session ??
          (throw StateError('Expected an initial provider session.'));
      expect(initialSession.connectionState, ProviderConnectionState.disconnected);

      await repository.checkSync();

      final syncedSession =
          repository.session ??
          (throw StateError('Expected a provider session after sync.'));
      expect(syncedSession.connectionState, ProviderConnectionState.disconnected);
      expect(syncedSession.canRead, isTrue);
      expect(syncedSession.canWrite, isFalse);
    },
  );
}
