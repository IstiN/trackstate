import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/issue_aggregate_loader.dart';
import '../../core/interfaces/issue_link_mutation_port.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../fixtures/repositories/ts284_inverse_link_normalization_fixture.dart';

void main() {
  testWidgets(
    'TS-284 normalizes an inverse link label to one canonical stored link record',
    (tester) async {
      final fixture = await tester.runAsync(
        Ts284InverseLinkNormalizationFixture.create,
      );
      if (fixture == null) {
        throw StateError('TS-284 fixture creation did not complete.');
      }
      addTearDown(() async {
        await tester.runAsync(fixture.dispose);
      });

      const dependencies = defaultTestingDependencies;
      final LocalGitRepositoryPort repositoryPort = dependencies
          .createLocalGitRepositoryPort(tester);
      final repository = await repositoryPort.openRepository(
        repositoryPath: fixture.repositoryPath,
      );
      final IssueAggregateLoader beforeIssueAggregateLoader = dependencies
          .createIssueAggregateLoader(repository);
      final beforeIssue = await tester.runAsync(
        () => beforeIssueAggregateLoader.loadIssue(
          Ts284InverseLinkNormalizationFixture.sourceIssueKey,
        ),
      );
      if (beforeIssue == null) {
        throw StateError('TS-284 pre-mutation issue load did not complete.');
      }
      final IssueLinkMutationPort linkMutationPort = dependencies
          .createIssueLinkMutationPort(tester);

      final mutationResult = await linkMutationPort.createLink(
        repositoryPath: fixture.repositoryPath,
        issueKey: Ts284InverseLinkNormalizationFixture.sourceIssueKey,
        targetKey: Ts284InverseLinkNormalizationFixture.targetIssueKey,
        type: Ts284InverseLinkNormalizationFixture.inverseLabel,
      );

      final observation = await tester.runAsync(
        fixture.observePersistedLinkState,
      );
      if (observation == null) {
        throw StateError(
          'TS-284 persisted state observation did not complete.',
        );
      }

      final LocalGitRepositoryPort reloadedRepositoryPort = dependencies
          .createLocalGitRepositoryPort(tester);
      final reloadedRepository = await reloadedRepositoryPort.openRepository(
        repositoryPath: fixture.repositoryPath,
      );
      final IssueAggregateLoader issueAggregateLoader = dependencies
          .createIssueAggregateLoader(reloadedRepository);
      final refreshedIssue = await tester.runAsync(
        () => issueAggregateLoader.loadIssue(
          Ts284InverseLinkNormalizationFixture.sourceIssueKey,
        ),
      );
      if (refreshedIssue == null) {
        throw StateError('TS-284 refreshed issue load did not complete.');
      }

      expect(
        beforeIssue.links,
        isEmpty,
        reason:
            'Precondition failed: ${Ts284InverseLinkNormalizationFixture.sourceIssueKey} should start without any stored links before TS-284 creates the inverse relationship.',
      );
      expect(
        mutationResult.isSuccess,
        isTrue,
        reason:
            'Submitting the inverse label "${Ts284InverseLinkNormalizationFixture.inverseLabel}" should succeed for two existing issues.',
      );
      expect(
        observation.sourceLinksExists,
        isTrue,
        reason:
            'Creating the relationship should persist ${observation.sourceLinksPath} for the source issue.',
      );
      expect(
        observation.persistedLinks,
        hasLength(1),
        reason:
            'TS-284 requires a single stored record for the business relationship after inverse-label normalization.',
      );
      expect(
        observation.linksJsonFiles,
        [Ts284InverseLinkNormalizationFixture.sourceLinksPath],
        reason:
            'The normalized relationship should be represented by exactly one links.json artifact in the repository.',
      );
      expect(
        observation.rawLinksFileContent,
        isNot(contains(Ts284InverseLinkNormalizationFixture.inverseLabel)),
        reason:
            'The persisted links.json payload must not keep the inverse label text after normalization.',
      );

      final persistedLink = observation.persistedLinks.single;
      expect(
        persistedLink['type'],
        Ts284InverseLinkNormalizationFixture.canonicalType,
        reason:
            'The stored link type should use the canonical outward form "blocks".',
      );
      expect(
        persistedLink['target'],
        Ts284InverseLinkNormalizationFixture.targetIssueKey,
        reason:
            'The normalized record should still point at the original target issue.',
      );
      expect(
        persistedLink['direction'],
        Ts284InverseLinkNormalizationFixture.canonicalDirection,
        reason:
            'The stored direction should be inward so the single record still expresses "${Ts284InverseLinkNormalizationFixture.targetIssueKey} blocks ${Ts284InverseLinkNormalizationFixture.sourceIssueKey}".',
      );

      expect(
        mutationResult.value?.links,
        hasLength(1),
        reason:
            'The mutation result returned to the caller should expose exactly one normalized link.',
      );
      final resultLink = mutationResult.value!.links.single;
      expect(
        resultLink.type,
        Ts284InverseLinkNormalizationFixture.canonicalType,
      );
      expect(
        resultLink.targetKey,
        Ts284InverseLinkNormalizationFixture.targetIssueKey,
      );
      expect(
        resultLink.direction,
        Ts284InverseLinkNormalizationFixture.canonicalDirection,
        reason:
            'The returned issue model should mirror the persisted canonical link semantics.',
      );

      expect(
        refreshedIssue.links,
        hasLength(1),
        reason:
            'Reloading the issue aggregate should show one client-visible relationship after the write completes.',
      );
      final refreshedLink = refreshedIssue.links.single;
      expect(
        refreshedLink.type,
        Ts284InverseLinkNormalizationFixture.canonicalType,
        reason:
            'Clients reading the refreshed issue should see the canonical "blocks" relationship.',
      );
      expect(
        refreshedLink.targetKey,
        Ts284InverseLinkNormalizationFixture.targetIssueKey,
        reason:
            'The refreshed issue should still point at the blocking issue key the user selected.',
      );
      expect(
        refreshedLink.direction,
        Ts284InverseLinkNormalizationFixture.canonicalDirection,
        reason:
            'The refreshed aggregate should expose the inward direction that tells the user ${Ts284InverseLinkNormalizationFixture.targetIssueKey} blocks ${Ts284InverseLinkNormalizationFixture.sourceIssueKey}.',
      );
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
