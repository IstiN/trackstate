import '../components/services/dirty_local_issue_save_component.dart';
import '../core/utils/local_trackstate_fixture.dart';
import '../frameworks/providers/trackstate_provider_dirty_local_issue_write_client.dart';

DirtyLocalIssueSaveComponent createDirtyLocalIssueSaveComponentFixture(
  LocalTrackStateFixture fixture,
) {
  return DirtyLocalIssueSaveComponent(
    provider: TrackStateProviderDirtyLocalIssueWriteClient(
      provider: fixture.provider,
    ),
    issueKey: LocalTrackStateFixture.issueKey,
    issuePath: LocalTrackStateFixture.issuePath,
    originalDescription: LocalTrackStateFixture.originalDescription,
  );
}
