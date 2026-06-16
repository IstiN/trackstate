import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../../core/fakes/reactive_issue_detail_trackstate_repository.dart';

class Ts370RepositoryAccessBannerFixture {
  static const RepositoryPermission readOnlyPermission = RepositoryPermission(
    canRead: true,
    canWrite: false,
    isAdmin: false,
    canCreateBranch: false,
    canManageAttachments: false,
    canCheckCollaborators: false,
  );

  static const String readOnlyToken = 'ghp_ts370_read_only';
  static const String issueKey = 'TRACK-12';
  static const String issueSummary = 'Implement Git sync service';

  static const String disconnectedTitle =
      'GitHub write access is not connected';
  static const String disconnectedMessage =
      'Create, edit, comment, and status changes stay read-only until you connect GitHub with a fine-grained token that has repository Contents write access. PAT is the default browser path.';
  static const String disconnectedAction = 'Connect GitHub';

  static const String readOnlyLabel = 'Read-only';
  static const String readOnlyTitle = 'This repository session is read-only';
  static const String readOnlyMessage =
      'This account can read the repository but cannot push Git-backed changes. Reconnect with a token or account that has repository Contents write access, or switch to a repository where you have that access.';
  static const String readOnlyAction = 'Reconnect for write access';

  ReactiveIssueDetailTrackStateRepository createRepository() =>
      ReactiveIssueDetailTrackStateRepository(permission: readOnlyPermission);
}
