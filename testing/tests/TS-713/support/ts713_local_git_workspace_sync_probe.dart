import '../../../components/services/local_git_workspace_sync_reason_validator.dart';
import '../../../core/interfaces/local_git_workspace_sync_reason_probe.dart';
import '../../../core/utils/local_git_repository_fixture.dart';

LocalGitWorkspaceSyncReasonProbe createTs713LocalGitWorkspaceSyncProbe() {
  return LocalGitWorkspaceSyncReasonValidator(
    createFixture: () => LocalGitRepositoryFixture.create(
      userName: 'TS-713 Tester',
      userEmail: 'ts713@example.com',
    ),
  );
}
