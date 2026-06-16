import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/issue_aggregate_loader.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/repositories/ts67_issue_artifacts_fixture.dart';

void main() {
  testWidgets('TS-67 loads issue comments and links into the issue aggregate model', (
    tester,
  ) async {
    final fixture = await Ts67IssueArtifactsFixture.create();
    addTearDown(fixture.dispose);

    const dependencies = defaultTestingDependencies;
    final LocalGitRepositoryPort repositoryPort = dependencies
        .createLocalGitRepositoryPort(tester);
    final repository = await repositoryPort.openRepository(
      repositoryPath: fixture.path,
    );
    final IssueAggregateLoader aggregateProbe = dependencies
        .createIssueAggregateLoader(repository);
    final TrackStateIssue issue = await aggregateProbe.loadIssue(
      Ts67IssueArtifactsFixture.issueKey,
    );

    expect(
      issue.summary,
      Ts67IssueArtifactsFixture.issueSummary,
      reason:
          'The loaded aggregate should identify the target issue before artifact assertions run.',
    );
    expect(
      issue.storagePath,
      'DEMO/DEMO-1/DEMO-2/main.md',
      reason:
          'The aggregate should resolve from the prepared issue folder that contains the side-car artifacts.',
    );
    expect(
      issue.comments,
      hasLength(fixture.expectedComments.length),
      reason:
          'The aggregate should load both markdown files from the comments directory.',
    );
    for (var index = 0; index < fixture.expectedComments.length; index++) {
      final actual = issue.comments[index];
      final expected = fixture.expectedComments[index];
      expect(
        actual.id,
        expected.id,
        reason:
            'Comment ${index + 1} should preserve the markdown file id in load order.',
      );
      expect(
        actual.author,
        expected.author,
        reason:
            'Comment ${expected.id} should preserve the author declared in its markdown front matter.',
      );
      expect(
        actual.body,
        expected.body,
        reason:
            'Comment ${expected.id} should preserve the markdown body loaded from disk.',
      );
      expect(
        actual.storagePath,
        expected.storagePath,
        reason:
            'Comment ${expected.id} should keep the source markdown path for traceability.',
      );
    }

    expect(
      issue.links,
      hasLength(fixture.expectedLinks.length),
      reason:
          'The aggregate should parse every non-hierarchical relationship from links.json.',
    );
    for (var index = 0; index < fixture.expectedLinks.length; index++) {
      final actual = issue.links[index];
      final expected = fixture.expectedLinks[index];
      expect(
        actual.type,
        expected.type,
        reason:
            'Link ${index + 1} should preserve its relationship type from links.json.',
      );
      expect(
        actual.targetKey,
        expected.targetKey,
        reason:
            'Link ${index + 1} should resolve its target key from either target or targetKey fields.',
      );
      expect(
        actual.direction,
        expected.direction,
        reason:
            'Link ${index + 1} should preserve its declared direction from links.json.',
      );
    }

    final TrackStateAppComponent screen = dependencies
        .createTrackStateAppScreen(tester);
    await screen.pump(repository);
    await screen.expectTextVisible('Local Git');
    await screen.openSection('JQL Search');
    await screen.openIssue(
      Ts67IssueArtifactsFixture.issueKey,
      Ts67IssueArtifactsFixture.issueSummary,
    );
    await screen.expectIssueDetailText(
      Ts67IssueArtifactsFixture.issueKey,
      'Comments',
    );

    for (final comment in fixture.expectedComments) {
      await screen.expectIssueDetailText(
        Ts67IssueArtifactsFixture.issueKey,
        comment.author,
      );
      await screen.expectIssueDetailText(
        Ts67IssueArtifactsFixture.issueKey,
        comment.body,
      );
    }
  });
}
