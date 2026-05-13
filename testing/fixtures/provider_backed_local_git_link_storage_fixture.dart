import 'local_git_link_storage_fixture.dart';
import '../frameworks/providers/provider_backed_local_git_repository_factory.dart';
import '../frameworks/providers/trackstate_provider_dirty_local_issue_write_client.dart';

Future<LocalGitLinkStorageFixture>
createProviderBackedLocalGitLinkStorageFixture({
  required LocalGitLinkStorageFixtureConfig config,
}) {
  return LocalGitLinkStorageFixture.create(
    config: config,
    repositoryFactory: const ProviderBackedLocalGitRepositoryFactory(),
    writeClientBuilder: (repositoryPath) =>
        TrackStateProviderDirtyLocalIssueWriteClient.local(
          repositoryPath: repositoryPath,
        ),
  );
}
