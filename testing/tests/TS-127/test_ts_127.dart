import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../fixtures/repositories/ts127_varied_frontmatter_types_repository_fixture.dart';

void main() {
  test(
    'TS-127 preserves integer, boolean, and list values from top-level frontmatter inside customFields',
    () async {
      final fixture =
          await Ts127VariedFrontmatterTypesRepositoryFixture.create();
      addTearDown(fixture.dispose);

      final resolution = await fixture.resolveIssueByKey();
      final issue = resolution.issue;
      final observedState = _describeObservedIssue(
        issue: issue,
        project: resolution.project,
      );

      final customInt =
          issue.customFields[Ts127VariedFrontmatterTypesRepositoryFixture
              .myIntFieldKey];
      expect(
        customInt,
        isA<int>(),
        reason:
            'The arbitrary my_int frontmatter entry should stay an integer in '
            'customFields rather than being coerced to a string. '
            '$observedState',
      );
      expect(
        customInt,
        Ts127VariedFrontmatterTypesRepositoryFixture.myIntFieldValue,
        reason:
            'The parsed issue should preserve my_int as 100 inside '
            'customFields. $observedState',
      );

      final customBool =
          issue.customFields[Ts127VariedFrontmatterTypesRepositoryFixture
              .myBoolFieldKey];
      expect(
        customBool,
        isA<bool>(),
        reason:
            'The arbitrary my_bool frontmatter entry should stay a boolean in '
            'customFields rather than being coerced to text. $observedState',
      );
      expect(
        customBool,
        Ts127VariedFrontmatterTypesRepositoryFixture.myBoolFieldValue,
        reason:
            'The parsed issue should preserve my_bool as false inside '
            'customFields. $observedState',
      );

      final customList =
          issue.customFields[Ts127VariedFrontmatterTypesRepositoryFixture
              .myListFieldKey];
      expect(
        customList,
        isA<List<dynamic>>(),
        reason:
            'The arbitrary my_list frontmatter entry should stay a YAML list '
            'inside customFields rather than being flattened to a scalar. '
            '$observedState',
      );
      final typedList = (customList as List<dynamic>).cast<Object?>();
      expect(
        typedList,
        Ts127VariedFrontmatterTypesRepositoryFixture.myListFieldValue,
        reason:
            'The parsed issue should preserve my_list as ["a", "b"] inside '
            'customFields. $observedState',
      );
      expect(
        typedList,
        everyElement(isA<String>()),
        reason:
            'The my_list YAML entry should keep string list members after '
            'resolution. $observedState',
      );

      expect(
        issue.statusId,
        'closed',
        reason:
            'The canonical top-level status field should still resolve to the '
            'configured machine status id while customFields preserve typed '
            'arbitrary metadata. $observedState',
      );
      expect(
        resolution.project.statusLabel(issue.statusId),
        'Closed',
        reason:
            'Integrated clients should still resolve the configured user-facing '
            'status label after typed customFields are preserved. '
            '$observedState',
      );
      expect(
        issue.rawMarkdown,
        contains(
          '${Ts127VariedFrontmatterTypesRepositoryFixture.myListFieldKey}: '
          '["a", "b"]',
        ),
        reason:
            'The fixture should exercise the inline YAML list syntax from '
            'TS-127. $observedState',
      );
    },
  );

  testWidgets(
    'TS-127 keeps the real issue-detail flow usable when arbitrary frontmatter values use multiple YAML data types',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );
      Ts127VariedFrontmatterTypesRepositoryFixture? fixture;

      try {
        fixture = await tester.runAsync(
          Ts127VariedFrontmatterTypesRepositoryFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-127 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Launching the app against the varied frontmatter fixture should '
              'not surface a framework exception.',
        );

        await screen.openSection('JQL Search');
        await screen.openIssue(
          Ts127VariedFrontmatterTypesRepositoryFixture.issueKey,
          Ts127VariedFrontmatterTypesRepositoryFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          Ts127VariedFrontmatterTypesRepositoryFixture.issueKey,
          Ts127VariedFrontmatterTypesRepositoryFixture.issueSummary,
        );
        await screen.expectIssueDetailText(
          Ts127VariedFrontmatterTypesRepositoryFixture.issueKey,
          Ts127VariedFrontmatterTypesRepositoryFixture.issueDescription,
        );
        expect(
          tester.takeException(),
          isNull,
          reason:
              'Opening the issue through the real issue-detail flow should keep '
              'the visible issue content usable and free of framework '
              'exceptions even when customFields contain mixed YAML data '
              'types.',
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

String _describeObservedIssue({
  required TrackStateIssue issue,
  required ProjectConfig project,
}) {
  final normalizedMarkdown = issue.rawMarkdown.replaceAll('\n', r'\n');
  final intValue = issue
      .customFields[Ts127VariedFrontmatterTypesRepositoryFixture.myIntFieldKey];
  final boolValue =
      issue.customFields[Ts127VariedFrontmatterTypesRepositoryFixture
          .myBoolFieldKey];
  final listValue =
      issue.customFields[Ts127VariedFrontmatterTypesRepositoryFixture
          .myListFieldKey];
  return 'Observed customFields=${issue.customFields}, '
      'my_int_runtimeType=${intValue.runtimeType}, '
      'my_bool_runtimeType=${boolValue.runtimeType}, '
      'my_list_runtimeType=${listValue.runtimeType}, '
      'statusId=${issue.statusId}, statusLabel=${project.statusLabel(issue.statusId)}, '
      'rawMarkdown=$normalizedMarkdown';
}
