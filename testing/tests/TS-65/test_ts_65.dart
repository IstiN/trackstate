import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/ts65_issue_metadata_fixture.dart';

void main() {
  testWidgets('TS-65 resolves stable issue status IDs into localized UI labels', (
    tester,
  ) async {
    final fixture = Ts65IssueMetadataFixture.create();
    final snapshot = await fixture.repository.loadSnapshot();
    final issue = snapshot.issues.singleWhere((entry) => entry.key == 'TRACK-65');

    expect(
      snapshot.project.statusDefinitions.map((entry) => entry.id),
      contains('wip'),
      reason:
          'The fixture must define a non-semantic catalog ID so this test depends on config/statuses.json for read-time resolution.',
    );
    expect(
      snapshot.project.statusDefinitions.map((entry) => entry.id),
      isNot(contains('in-progress')),
      reason:
          'The catalog should not reuse the built-in semantic ID, otherwise fallback parsing could satisfy the test without catalog participation.',
    );
    expect(
      snapshot.project.statusLabel('wip'),
      'In Progress',
      reason:
          'The config catalog should provide the user-facing label for the stored custom status ID.',
    );

    expect(
      issue.statusId,
      'wip',
      reason:
          'The repository snapshot should preserve the canonical machine ID stored in frontmatter.',
    );
    expect(
      issue.status,
      IssueStatus.inProgress,
      reason:
          'The stored machine ID should resolve to the in-progress semantic status before the UI renders it.',
    );

    final viewModel = TrackerViewModel(repository: fixture.repository);
    await viewModel.load();

    expect(
      viewModel.selectedIssue?.key,
      'TRACK-65',
      reason:
          'The loaded issue should be selected so the presentation layer can render it without rewriting the stored metadata.',
    );
    expect(
      viewModel.selectedIssue?.statusId,
      'wip',
      reason:
          'TrackerViewModel should keep the canonical stable ID when it receives the issue aggregate.',
    );
    expect(
      viewModel.selectedIssue?.status,
      IssueStatus.inProgress,
      reason:
          'TrackerViewModel should expose the resolved semantic status that drives the localized UI badge.',
    );

    final TrackStateAppComponent screen = TrackStateAppScreen(tester);
    await screen.pump(fixture.repository);
    await screen.expectTextVisible('JQL Search');
    await screen.openSection('JQL Search');
    await screen.openIssue(
      'TRACK-65',
      'Resolve issue metadata from stable status IDs',
    );
    await screen.expectIssueDetailText(
      'TRACK-65',
      'Resolve issue metadata from stable status IDs',
    );
    await screen.expectIssueDetailText('TRACK-65', 'In Progress');

    final issueDetail = find.bySemanticsLabel(RegExp('Issue detail TRACK-65'));

    expect(
      find.descendant(of: issueDetail, matching: find.text('In Progress')),
      findsAtLeastNWidgets(1),
      reason:
          'A user should see the localized status label in the issue detail view, not just somewhere else in the widget tree.',
    );
    expect(
      find.descendant(of: issueDetail, matching: find.text('in-progress')),
      findsNothing,
      reason:
          'The raw stable ID should remain internal data and must not leak into the rendered issue detail text.',
    );
    expect(
      find.descendant(of: issueDetail, matching: find.text('wip')),
      findsNothing,
      reason:
          'The custom catalog ID should remain internal data and must not leak into the rendered issue detail text.',
    );
  });
}
