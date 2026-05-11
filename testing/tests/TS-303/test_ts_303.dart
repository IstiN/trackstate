import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts303_issue_hierarchy_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-303 applies hierarchy field visibility and derivation rules in Create issue',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts303IssueHierarchyFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts303IssueHierarchyFixture.create);
        if (fixture == null) {
          throw StateError('TS-303 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
        final openedCreateFlow = await screen.tapTopBarControl('Create issue');
        if (!openedCreateFlow) {
          fail(
            'Step 1 failed: the visible top-bar "Create issue" control on '
            'Dashboard was not reachable. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.expectCreateIssueFormVisible(
          createIssueSection: 'Dashboard',
        );
        expect(
          await screen.isDropdownFieldVisible('Issue Type'),
          isTrue,
          reason:
              'Step 1 failed: opening Create issue from Dashboard did not render '
              'the visible "Issue Type" selector. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.selectDropdownOption('Issue Type', optionText: 'Epic');
        expect(
          await screen.readDropdownFieldValue('Issue Type'),
          'Epic',
          reason:
              'Step 2 failed: after selecting "Epic", the visible Issue Type '
              'field did not show Epic as the current value. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countDropdownFields('Parent'),
          0,
          reason:
              'Step 3 failed: selecting "Epic" should hide the editable Parent '
              'field. Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countDropdownFields('Epic'),
          0,
          reason:
              'Step 3 failed: selecting "Epic" should hide the editable Epic '
              'field. Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countReadOnlyFields('Epic'),
          0,
          reason:
              'Step 3 failed: selecting "Epic" should not leave a read-only Epic '
              'field behind. Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.selectDropdownOption('Issue Type', optionText: 'Sub-task');
        expect(
          await screen.readDropdownFieldValue('Issue Type'),
          'Sub-task',
          reason:
              'Step 4 failed: after selecting "Sub-task", the visible Issue Type '
              'field did not show Sub-task as the current value. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countDropdownFields('Parent'),
          1,
          reason:
              'Step 5 failed: selecting "Sub-task" should render exactly one '
              'editable Parent field. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countDropdownFields('Epic'),
          0,
          reason:
              'Step 5 failed: selecting "Sub-task" should not render an editable '
              'Epic dropdown because Epic must be derived from Parent. Visible '
              'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countReadOnlyFields('Epic'),
          1,
          reason:
              'Step 5 failed: selecting "Sub-task" should render one read-only '
              'Epic field derived from Parent. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readReadOnlyFieldValue('Epic'),
          'Derived from parent',
          reason:
              'Step 5 failed: before choosing a Parent, the read-only Epic field '
              'should show the "Derived from parent" placeholder. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible(
            'Epic is derived from the selected parent issue.',
          ),
          isTrue,
          reason:
              'Step 5 failed: Sub-task mode should explain that Epic is derived '
              'from the selected parent issue. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.enterLabeledTextField(
          'Summary',
          text: 'TS-303 hierarchy validation draft',
        );
        await screen.submitCreateIssue(createIssueSection: 'Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
        final parentValidationVisible = await screen.isTextVisible(
          'Sub-tasks require a parent issue.',
        );
        final createFormStillVisible = await screen.isTextFieldVisible(
          'Summary',
        );
        final repositoryIssues =
            await tester.runAsync(fixture.describeIssues) ?? const <String>[];
        expect(
          parentValidationVisible,
          isTrue,
          reason:
              'Step 5 failed: saving a Sub-task without Parent should surface the '
              'visible parent-required validation message. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}. '
              'Create form still visible: $createFormStillVisible. Repository '
              'issues: ${repositoryIssues.join(' | ')}.',
        );

        await screen.selectDropdownOption(
          'Parent',
          optionText: Ts303IssueHierarchyFixture.parentOptionLabel,
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        expect(
          await screen.readReadOnlyFieldValue('Epic'),
          Ts303IssueHierarchyFixture.derivedEpicLabel,
          reason:
              'Step 6 failed: selecting Parent should derive the matching Epic in '
              'the visible read-only field. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible('Sub-tasks require a parent issue.'),
          isFalse,
          reason:
              'Expected result failed: after selecting a valid Parent, the '
              'parent-required validation message should clear. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.countDropdownFields('Epic'),
          0,
          reason:
              'Expected result failed: the derived Epic field must remain '
              'non-editable after selecting Parent. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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
