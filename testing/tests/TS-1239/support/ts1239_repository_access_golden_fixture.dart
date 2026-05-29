import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../../core/fakes/reactive_issue_detail_trackstate_repository.dart';

class Ts1239RepositoryAccessGoldenFixture {
  static const RepositoryPermission readOnlyPermission = RepositoryPermission(
    canRead: true,
    canWrite: false,
    isAdmin: false,
    canCreateBranch: false,
    canManageAttachments: false,
    canCheckCollaborators: false,
  );

  static const RepositoryPermission writablePermission = RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: true,
    canCheckCollaborators: false,
  );

  static const String disconnectedLabel = 'Connect GitHub';
  static const String disconnectedTitle =
      'GitHub write access is not connected';
  static const String disconnectedMessage =
      'Create, edit, comment, and status changes stay read-only until you connect GitHub with a fine-grained token that has repository Contents write access. PAT is the default browser path.';
  static const String disconnectedAction = 'Connect GitHub';

  static const String readOnlyToken = 'ghp_ts1239_read_only';
  static const String readOnlyLabel = 'Read-only';
  static const String readOnlyTitle = 'This repository session is read-only';
  static const String readOnlyMessage =
      'This account can read the repository but cannot push Git-backed changes. Reconnect with a token or account that has repository Contents write access, or switch to a repository where you have that access.';
  static const String readOnlyAction = 'Reconnect for write access';

  static const String writableToken = 'ghp_ts1239_full_access';
  static const String writableLabel = 'Connected';
  static const String manageAccessDialogTitle = 'Manage GitHub access';

  ReactiveIssueDetailTrackStateRepository createRepository() =>
      ReactiveIssueDetailTrackStateRepository(
        permission: readOnlyPermission,
        tokenPermissions: const <String, RepositoryPermission>{
          readOnlyToken: readOnlyPermission,
          writableToken: writablePermission,
        },
      );
}
