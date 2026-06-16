import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-303/support/ts303_issue_hierarchy_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-1139 blocks Sub-task creation without a parent and shows validation',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts303IssueHierarchyFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts303IssueHierarchyFixture.create);
        if (fixture == null) {
          throw StateError('TS-1139 fixture creation did not complete.');
        }

        final initialIssues =
            await tester.runAsync(fixture.describeIssues) ?? const <String>[];

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
        );

        expect(
          await screen.isDropdownFieldVisible('Issue Type'),
          isTrue,
          reason:
              'Step 1 failed: opening Create issue did not render the visible '
              '"Issue Type" selector. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.selectDropdownOption('Issue Type', optionText: 'Sub-task');

        expect(
          await screen.readDropdownFieldValue('Issue Type'),
          'Sub-task',
          reason:
              'Step 2 failed: after selecting "Sub-task", the Issue Type field '
              'did not show the selected value. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countDropdownFields('Parent'),
          1,
          reason:
              'Step 3 failed: selecting "Sub-task" should render one editable '
              'Parent field. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readDropdownFieldValue('Parent'),
          isNull,
          reason:
              'Step 3 failed: the Parent field should start empty for a new '
              'Sub-task. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countReadOnlyFields('Epic'),
          1,
          reason:
              'Step 3 failed: Sub-task mode should show the read-only Epic '
              'field derived from Parent. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.enterLabeledTextField(
          'Summary',
          text: 'TS-1139 missing parent regression draft',
        );

        await screen.submitCreateIssue(createIssueSection: createIssueSection);
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final validationVisible = await screen.isTextVisible(
          'Sub-tasks require a parent issue.',
        );
        final createFormStillVisible = await screen.isTextFieldVisible(
          'Summary',
        );
        final issuesAfterSubmit =
            await tester.runAsync(fixture.describeIssues) ?? const <String>[];
        final unexpectedCreatedIssue = issuesAfterSubmit.any(
          (issue) => issue.contains('TS-1139 missing parent regression draft'),
        );

        expect(
          validationVisible,
          isTrue,
          reason:
              'Step 4 failed: attempting to save a Sub-task without Parent '
              'should show the visible "Sub-tasks require a parent issue." '
              'validation message. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}. '
              'Repository issues: ${issuesAfterSubmit.join(' | ')}.',
        );
        expect(
          createFormStillVisible,
          isTrue,
          reason:
              'Step 5 failed: invalid Sub-task submission should keep the Create '
              'issue dialog open so the user can fix Parent. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          issuesAfterSubmit,
          equals(initialIssues),
          reason:
              'Expected result failed: the repository contents changed even '
              'though Parent was missing. Initial issues: '
              '${initialIssues.join(' | ')}. After submit: '
              '${issuesAfterSubmit.join(' | ')}.',
        );
        expect(
          unexpectedCreatedIssue,
          isFalse,
          reason:
              'Expected result failed: a new Sub-task draft was written even '
              'though Parent was missing. Repository issues: '
              '${issuesAfterSubmit.join(' | ')}.',
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
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }

  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
