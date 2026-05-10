import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts284_inverse_link_normalization_fixture.dart';

void main() {
  test(
    'TS-284 normalizes an inverse link label to one canonical stored link record',
    () async {
      final fixture = await Ts284InverseLinkNormalizationFixture.create();
      addTearDown(fixture.dispose);

      final observation = await fixture.observeInverseLinkNormalization();

      expect(
        observation.result.isSuccess,
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
        observation.result.value?.links,
        hasLength(1),
        reason:
            'The mutation result returned to the caller should expose exactly one normalized link.',
      );
      final resultLink = observation.result.value!.links.single;
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
        observation.refreshedIssue.links,
        hasLength(1),
        reason:
            'Reloading the issue aggregate should show one client-visible relationship after the write completes.',
      );
      final refreshedLink = observation.refreshedIssue.links.single;
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
  );
}
