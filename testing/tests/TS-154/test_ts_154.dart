import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts135_archived_issue_fixture.dart';
import '../../fixtures/repositories/ts154_repository_contract_fixture.dart';

void main() {
  test(
    'TS-154 LocalTrackStateRepository implements the lifecycle contract without missing methods',
    () async {
      final fixture = await Ts154RepositoryContractFixture.create();
      addTearDown(fixture.dispose);

      final contract = await fixture.observeContract();

      expect(
        contract.repositoryType,
        'LocalTrackStateRepository',
        reason:
            'Step 1 failed: the test must instantiate the LocalTrackStateRepository implementation under the real repository contract.',
      );
      expect(
        contract.usesLocalPersistence,
        isTrue,
        reason:
            'Step 1 failed: LocalTrackStateRepository must report local persistence so the contract test is exercising the expected implementation.',
      );
      expect(
        contract.supportsGitHubAuth,
        isFalse,
        reason:
            'Step 1 failed: LocalTrackStateRepository should remain a local-only repository implementation.',
      );
      expect(
        contract.validatedMethodNames,
        Ts154RepositoryContractFixture.validatedMethodNames,
        reason:
            'Step 2 failed: LocalTrackStateRepository must expose every required TrackStateRepository method as a callable runtime member.',
      );

      expect(
        contract.beforeArchival.issue.key,
        Ts135ArchivedIssueFixture.archivedIssueKey,
        reason:
            'Step 3 failed: the seeded archive target must be present before the repository contract exercise runs.',
      );
      expect(
        contract.beforeArchival.issue.isArchived,
        isFalse,
        reason:
            'Step 3 failed: TRACK-555 must start active so the contract suite can observe the archive lifecycle transition.',
      );
      expect(
        contract.beforeArchival.indexEntry?.isArchived,
        isFalse,
        reason:
            'Step 3 failed: the repository index must not already mark TRACK-555 as archived before archiveIssue is invoked.',
      );
      expect(
        contract.beforeArchival.standardSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts135ArchivedIssueFixture.archivedIssueKey],
        reason:
            'Step 3 failed: a standard repository search must expose the active TRACK-555 issue before archiving.',
      );

      final archived = await fixture.archiveIssueThroughDynamicContract();

      expect(
        archived.archivedIssue.key,
        Ts135ArchivedIssueFixture.archivedIssueKey,
        reason:
            'Step 3 failed: archiveIssue should return the archived TRACK-555 issue when invoked through the runtime contract path.',
      );
      expect(
        archived.archivedIssue.isArchived,
        isTrue,
        reason:
            'Step 3 failed: archiveIssue should return an archived issue instead of throwing a missing-method runtime error.',
      );
      expect(
        archived.afterArchival.issue.isArchived,
        isTrue,
        reason:
            'Expected result mismatch: the resolved repository issue should report archived after the contract suite invokes archiveIssue.',
      );
      expect(
        archived.afterArchival.indexEntry?.isArchived,
        isTrue,
        reason:
            'Expected result mismatch: repository metadata should persist the archived lifecycle state after archiveIssue completes.',
      );
      expect(
        archived.afterArchival.mainMarkdown,
        contains('archived: true'),
        reason:
            'Expected result mismatch: the issue frontmatter should persist archived: true after archiveIssue completes.',
      );
      expect(
        archived.afterArchival.standardSearchResults
            .map((issue) => issue.key)
            .toList(),
        [Ts135ArchivedIssueFixture.archivedIssueKey],
        reason:
            'Expected result mismatch: a standard repository search should still return TRACK-555 after the archive lifecycle update.',
      );
      expect(
        archived.afterArchival.standardSearchResults.single.isArchived,
        isTrue,
        reason:
            'Expected result mismatch: the issue returned from standard repository search must expose the archived state to consuming clients.',
      );
    },
  );
}
