import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts454_targeted_issue_refresh_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-454 mutation refreshes only the affected issue artifacts without reloading the hosted snapshot',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final fixture = await Ts454TargetedIssueRefreshFixture.create();

      try {
        await screen.pump(fixture.repository);
        await screen.openSection('JQL Search');
        await screen.searchIssues(
          'project = ${Ts454TargetedIssueRefreshFixture.projectKey}',
        );

        await screen.expectIssueSearchResultVisible(
          Ts454TargetedIssueRefreshFixture.issueAKey,
          Ts454TargetedIssueRefreshFixture.issueASummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts454TargetedIssueRefreshFixture.issueBKey,
          Ts454TargetedIssueRefreshFixture.issueBSummary,
        );

        expect(
          await screen.isIssueSearchResultTextVisible(
            Ts454TargetedIssueRefreshFixture.issueAKey,
            Ts454TargetedIssueRefreshFixture.issueASummary,
            Ts454TargetedIssueRefreshFixture.initialStatusLabel,
          ),
          isTrue,
          reason:
              'Step 1 failed: Issue-A did not start with the visible "${Ts454TargetedIssueRefreshFixture.initialStatusLabel}" summary-row status. '
              'Visible row texts: ${_formatSnapshot(screen.issueSearchResultTextsSnapshot(Ts454TargetedIssueRefreshFixture.issueAKey, Ts454TargetedIssueRefreshFixture.issueASummary))}.',
        );

        await screen.openIssue(
          Ts454TargetedIssueRefreshFixture.issueAKey,
          Ts454TargetedIssueRefreshFixture.issueASummary,
        );
        await screen.expectIssueDetailText(
          Ts454TargetedIssueRefreshFixture.issueAKey,
          Ts454TargetedIssueRefreshFixture.issueADescription,
        );
        expect(
          await screen.tapVisibleControl('Comments'),
          isTrue,
          reason:
              'Step 1 failed: Issue-A did not expose a visible Comments tab after the detail hydrated.',
        );
        await screen.expectIssueDetailText(
          Ts454TargetedIssueRefreshFixture.issueAKey,
          Ts454TargetedIssueRefreshFixture.issueAComment,
        );

        await screen.openIssue(
          Ts454TargetedIssueRefreshFixture.issueBKey,
          Ts454TargetedIssueRefreshFixture.issueBSummary,
        );
        expect(
          await screen.tapVisibleControl('Detail'),
          isTrue,
          reason:
              'Step 1 failed: Issue-B did not expose a visible Detail tab after selection.',
        );
        await screen.expectIssueDetailText(
          Ts454TargetedIssueRefreshFixture.issueBKey,
          Ts454TargetedIssueRefreshFixture.issueBDescription,
        );
        expect(
          await screen.tapVisibleControl('Comments'),
          isTrue,
          reason:
              'Step 1 failed: Issue-B did not expose a visible Comments tab after the detail hydrated.',
        );
        await screen.expectIssueDetailText(
          Ts454TargetedIssueRefreshFixture.issueBKey,
          Ts454TargetedIssueRefreshFixture.issueBComment,
        );

        final issueBBeforeMutation = fixture.requireCachedIssue(
          Ts454TargetedIssueRefreshFixture.issueBKey,
        );
        expect(
          issueBBeforeMutation.hasDetailLoaded &&
              issueBBeforeMutation.hasCommentsLoaded,
          isTrue,
          reason:
              'Precondition failed: Issue-B should already be hydrated in the cached hosted snapshot before mutating Issue-A.',
        );

        final baselineSnapshotLoadCount = fixture.snapshotLoadCount;
        final baselineHydrationCount = fixture.hydrateCalls.length;

        await screen.openIssue(
          Ts454TargetedIssueRefreshFixture.issueAKey,
          Ts454TargetedIssueRefreshFixture.issueASummary,
        );
        expect(
          await screen.tapVisibleControl('Detail'),
          isTrue,
          reason:
              'Step 2 failed: Issue-A did not expose a visible Detail tab before the status transition.',
        );
        await screen.tapIssueDetailAction(
          Ts454TargetedIssueRefreshFixture.issueAKey,
          label: 'Transition',
        );
        await screen.expectTextVisible('Transition issue');
        await screen.selectDropdownOption(
          'Status',
          optionText: Ts454TargetedIssueRefreshFixture.updatedStatusLabel,
        );
        final saveTapped = await screen.tapVisibleControl('Save');
        expect(
          saveTapped,
          isTrue,
          reason:
              'Step 2 failed: the visible Save control in the Issue-A transition dialog could not be activated.',
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));

        expect(
          await screen.isIssueSearchResultTextVisible(
            Ts454TargetedIssueRefreshFixture.issueAKey,
            Ts454TargetedIssueRefreshFixture.issueASummary,
            Ts454TargetedIssueRefreshFixture.updatedStatusLabel,
          ),
          isTrue,
          reason:
              'Step 2 failed: the Issue-A summary row did not refresh to the visible "${Ts454TargetedIssueRefreshFixture.updatedStatusLabel}" status after the mutation. '
              'Visible row texts: ${_formatSnapshot(screen.issueSearchResultTextsSnapshot(Ts454TargetedIssueRefreshFixture.issueAKey, Ts454TargetedIssueRefreshFixture.issueASummary))}.',
        );
        await screen.expectIssueDetailText(
          Ts454TargetedIssueRefreshFixture.issueAKey,
          Ts454TargetedIssueRefreshFixture.updatedStatusLabel,
        );
        expect(
          await screen.tapVisibleControl('Comments'),
          isTrue,
          reason:
              'Step 2 failed: Issue-A did not expose a visible Comments tab after the transition.',
        );
        await screen.expectIssueDetailText(
          Ts454TargetedIssueRefreshFixture.issueAKey,
          Ts454TargetedIssueRefreshFixture.issueAComment,
        );

        final mutationHydrationCalls = fixture.hydrateCalls
            .skip(baselineHydrationCount)
            .toList(growable: false);
        final forcedIssueARefreshes = mutationHydrationCalls
            .where(
              (call) =>
                  call.issueKey == Ts454TargetedIssueRefreshFixture.issueAKey &&
                  call.force,
            )
            .toList(growable: false);
        final unrelatedIssueRefreshes = mutationHydrationCalls
            .where(
              (call) =>
                  call.issueKey == Ts454TargetedIssueRefreshFixture.issueBKey,
            )
            .toList(growable: false);

        expect(
          fixture.snapshotLoadCount,
          baselineSnapshotLoadCount,
          reason:
              'Step 3 failed: mutating Issue-A triggered loadSnapshot again (${fixture.snapshotLoadCount} total loads, baseline $baselineSnapshotLoadCount) instead of staying scoped to targeted issue refreshes.',
        );
        expect(
          forcedIssueARefreshes,
          isNotEmpty,
          reason:
              'Step 4 failed: mutating Issue-A did not trigger any forced targeted refresh for the affected hosted issue. '
              'Observed post-mutation hydration calls: ${_formatHydrationCalls(mutationHydrationCalls)}.',
        );
        expect(
          forcedIssueARefreshes.every(
            (call) => call.scopes.contains(IssueHydrationScope.detail),
          ),
          isTrue,
          reason:
              'Step 4 failed: the targeted refreshes for Issue-A did not include detail hydration. '
              'Observed post-mutation hydration calls: ${_formatHydrationCalls(mutationHydrationCalls)}.',
        );
        expect(
          unrelatedIssueRefreshes,
          isEmpty,
          reason:
              'Step 5 failed: mutating Issue-A also rehydrated Issue-B, which indicates the hosted refresh was not scoped. '
              'Observed post-mutation hydration calls: ${_formatHydrationCalls(mutationHydrationCalls)}.',
        );

        final issueBAfterMutation = fixture.requireCachedIssue(
          Ts454TargetedIssueRefreshFixture.issueBKey,
        );
        expect(
          issueBAfterMutation.hasDetailLoaded &&
              issueBAfterMutation.hasCommentsLoaded,
          isTrue,
          reason:
              'Step 5 failed: Issue-B lost its hydrated detail/comment flags after mutating Issue-A.',
        );
        expect(
          issueBAfterMutation.description,
          Ts454TargetedIssueRefreshFixture.issueBDescription,
          reason:
              'Step 5 failed: Issue-B lost its cached detail text after mutating Issue-A.',
        );
        expect(
          issueBAfterMutation.comments.map((comment) => comment.body).toList(),
          contains(Ts454TargetedIssueRefreshFixture.issueBComment),
          reason:
              'Step 5 failed: Issue-B lost its cached comment artifact after mutating Issue-A.',
        );

        expect(
          fixture.indexStatusFor(Ts454TargetedIssueRefreshFixture.issueAKey),
          'in-progress',
          reason:
              'Expected result mismatch: the hosted repository index did not persist Issue-A as in-progress after the mutation.',
        );

        await screen.openIssue(
          Ts454TargetedIssueRefreshFixture.issueBKey,
          Ts454TargetedIssueRefreshFixture.issueBSummary,
        );
        expect(
          await screen.tapVisibleControl('Comments'),
          isTrue,
          reason:
              'Human-style verification failed: reopening Issue-B did not expose the Comments tab.',
        );
        await screen.expectIssueDetailText(
          Ts454TargetedIssueRefreshFixture.issueBKey,
          Ts454TargetedIssueRefreshFixture.issueBComment,
        );
        expect(
          await screen.tapVisibleControl('Detail'),
          isTrue,
          reason:
              'Human-style verification failed: reopening Issue-B did not expose the Detail tab before editing.',
        );
        await screen.tapIssueDetailAction(
          Ts454TargetedIssueRefreshFixture.issueBKey,
          label: 'Edit',
        );
        await screen.expectIssueDescriptionEditorVisible(
          Ts454TargetedIssueRefreshFixture.issueBKey,
          label: 'Description',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          Ts454TargetedIssueRefreshFixture.issueBDescription,
          reason:
              'Human-style verification failed: reopening Issue-B after the Issue-A mutation did not keep the previously loaded description editable with the original user-facing text.',
        );
      } finally {
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

String _formatHydrationCalls(List<Ts454HydrationCall> calls) {
  if (calls.isEmpty) {
    return '<none>';
  }
  return calls
      .map(
        (call) =>
            '${call.issueKey}[force=${call.force};scopes=${call.scopes.map((scope) => scope.name).join(',')}]',
      )
      .join(' | ');
}
