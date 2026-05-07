import '../../../components/services/dirty_local_issue_app_flow_component.dart';
import '../../../core/interfaces/trackstate_app_component.dart';
import '../../../core/utils/local_trackstate_fixture.dart';

DirtyLocalIssueAppFlowComponent createTs41DirtyLocalIssueAppFlowComponent(
  TrackStateAppComponent app,
) {
  return DirtyLocalIssueAppFlowComponent(
    app: app,
    issueKey: LocalTrackStateFixture.issueKey,
    originalDescription: LocalTrackStateFixture.originalDescription,
  );
}
