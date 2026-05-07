import '../../core/interfaces/trackstate_app_component.dart';

class DirtyLocalIssueAppFlowComponent {
  const DirtyLocalIssueAppFlowComponent({
    required TrackStateAppComponent app,
    required this.issueKey,
    required this.originalDescription,
  }) : _app = app;

  final TrackStateAppComponent _app;
  final String issueKey;
  final String originalDescription;

  Future<void> attemptDescriptionSave(String updatedDescription) async {
    await _app.expectIssueDetailText(issueKey, originalDescription);
    await _app.tapIssueDetailAction(key: issueKey, label: 'Edit');
    await _app.enterIssueDetailDescription(
      key: issueKey,
      text: updatedDescription,
    );
    await _app.tapIssueDetailAction(key: issueKey, label: 'Save');
  }
}
