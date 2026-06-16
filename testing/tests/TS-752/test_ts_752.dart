import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/settings_screen_robot.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-732/support/ts732_removed_issue_sync_repository.dart';

const String _ticketKey = 'TS-752';
const String _ticketSummary =
    'Sync removal banner stays non-blocking and still allows selecting another issue';
const String _expectedNotificationFragment = 'no longer available';
const List<String> _requestSteps = <String>[
  'Simulate a background sync event where Issue-A is removed from the workspace.',
  "Confirm the 'issue no longer available' notification banner appears.",
  'Attempt to click on Issue-B in the search result list.',
  'Observe the selection state and the detail panel.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-752 removed-issue banner stays non-blocking for follow-up navigation',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };
      final failures = <String>[];
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts732RemovedIssueSyncRepository();

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts732RemovedIssueSyncRepository.removedIssueKey,
          Ts732RemovedIssueSyncRepository.removedIssueSummary,
        );
        await screen.expectIssueSearchResultVisible(
          Ts732RemovedIssueSyncRepository.remainingIssueKey,
          Ts732RemovedIssueSyncRepository.remainingIssueSummary,
        );
        await screen.openIssue(
          Ts732RemovedIssueSyncRepository.removedIssueKey,
          Ts732RemovedIssueSyncRepository.removedIssueSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts732RemovedIssueSyncRepository.removedIssueKey,
        );
        await screen.expectIssueDetailText(
          Ts732RemovedIssueSyncRepository.removedIssueKey,
          Ts732RemovedIssueSyncRepository.removedIssueDescription,
        );

        final initialQuery = await screen.readJqlSearchFieldValue();
        final initialVisibleRows = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final initialRemovedSelected = await screen.isIssueSearchResultSelected(
          Ts732RemovedIssueSyncRepository.removedIssueKey,
          Ts732RemovedIssueSyncRepository.removedIssueSummary,
        );
        final initialRemovedDetailVisible = await screen.isIssueDetailVisible(
          Ts732RemovedIssueSyncRepository.removedIssueKey,
        );
        result['initial_query'] = initialQuery ?? '<missing>';
        result['initial_rows'] = initialVisibleRows;

        final preconditionPassed =
            initialRemovedSelected &&
            initialRemovedDetailVisible &&
            _snapshotContains(
              initialVisibleRows,
              'Open ${Ts732RemovedIssueSyncRepository.removedIssueKey} ${Ts732RemovedIssueSyncRepository.removedIssueSummary}',
            ) &&
            _snapshotContains(
              initialVisibleRows,
              'Open ${Ts732RemovedIssueSyncRepository.remainingIssueKey} ${Ts732RemovedIssueSyncRepository.remainingIssueSummary}',
            ) &&
            initialQuery == SettingsScreenRobot.jqlPlaceholderText;
        result['precondition_passed'] = preconditionPassed;
        if (!preconditionPassed) {
          failures.add(
            'Precondition failed: TS-752 expected ${Ts732RemovedIssueSyncRepository.removedIssueKey} '
            'to start selected in JQL Search while both issues were visible.\n'
            'removed_selected=$initialRemovedSelected; '
            'removed_detail_visible=$initialRemovedDetailVisible; '
            'query=${initialQuery ?? '<missing>'}; '
            'visible_rows=${_formatSnapshot(initialVisibleRows)}',
          );
        }

        await repository.emitIssueRemovalSync();
        final settledPostRefreshStateReached = await _pumpUntil(
          tester,
          condition: () async => await _hasSettledPostRefreshState(
            screen,
            expectedSearchValue: SettingsScreenRobot.jqlPlaceholderText,
            notificationFragment: _expectedNotificationFragment,
          ),
          timeout: const Duration(seconds: 10),
        );

        final rowsAfterRefresh = screen
            .visibleIssueSearchResultLabelsSnapshot();
        final textsAfterRefresh = screen.visibleTextsSnapshot();
        final semanticsAfterRefresh = screen.visibleSemanticsLabelsSnapshot();
        final removedIssueStillVisible = _snapshotContains(
          rowsAfterRefresh,
          'Open ${Ts732RemovedIssueSyncRepository.removedIssueKey} ${Ts732RemovedIssueSyncRepository.removedIssueSummary}',
        );
        final remainingIssueVisible = _snapshotContains(
          rowsAfterRefresh,
          'Open ${Ts732RemovedIssueSyncRepository.remainingIssueKey} ${Ts732RemovedIssueSyncRepository.remainingIssueSummary}',
        );
        final bannerVisibleBeforeClick = await screen
            .isMessageBannerVisibleContaining(_expectedNotificationFragment);
        final noDetailVisibleBeforeClick =
            !(await screen.isIssueDetailVisible(
              Ts732RemovedIssueSyncRepository.removedIssueKey,
            )) &&
            !(await screen.isIssueDetailVisible(
              Ts732RemovedIssueSyncRepository.remainingIssueKey,
            ));

        result['settled_post_refresh_state_reached'] =
            settledPostRefreshStateReached;
        result['rows_after_refresh'] = rowsAfterRefresh;
        result['texts_after_refresh'] = textsAfterRefresh;
        result['semantics_after_refresh'] = semanticsAfterRefresh;

        final stepOnePassed =
            settledPostRefreshStateReached &&
            !removedIssueStillVisible &&
            remainingIssueVisible &&
            noDetailVisibleBeforeClick;
        _recordStep(
          result,
          step: 1,
          status: stepOnePassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed:
              'settled_post_refresh_state_reached=$settledPostRefreshStateReached; '
              'removed_issue_still_visible=$removedIssueStillVisible; '
              'remaining_issue_visible=$remainingIssueVisible; '
              'no_detail_visible_before_click=$noDetailVisibleBeforeClick; '
              'visible_rows=${_formatSnapshot(rowsAfterRefresh)}',
        );
        if (!stepOnePassed) {
          failures.add(
            'Step 1 failed: the background sync did not leave the search surface '
            'in the expected post-removal state before the click attempt.\n'
            'Observed rows: ${_formatSnapshot(rowsAfterRefresh)}\n'
            'Observed texts: ${_formatSnapshot(textsAfterRefresh)}',
          );
        }

        final stepTwoPassed = bannerVisibleBeforeClick;
        _recordStep(
          result,
          step: 2,
          status: stepTwoPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed:
              'banner_visible_before_click=$bannerVisibleBeforeClick; '
              'visible_texts=${_formatSnapshot(textsAfterRefresh)}; '
              'visible_semantics=${_formatSnapshot(semanticsAfterRefresh)}',
        );
        if (!stepTwoPassed) {
          failures.add(
            'Step 2 failed: the unavailable notification banner was not visible '
            'after the selected issue was removed by sync.\n'
            'Visible texts: ${_formatSnapshot(textsAfterRefresh)}\n'
            'Visible semantics: ${_formatSnapshot(semanticsAfterRefresh)}',
          );
        }

        var navigationError = '';
        try {
          await screen.openIssue(
            Ts732RemovedIssueSyncRepository.remainingIssueKey,
            Ts732RemovedIssueSyncRepository.remainingIssueSummary,
          );
        } catch (error) {
          navigationError = '$error';
        }

        final remainingDetailVisible = await screen.isIssueDetailVisible(
          Ts732RemovedIssueSyncRepository.remainingIssueKey,
        );
        final removedDetailVisibleAfterClick = await screen
            .isIssueDetailVisible(
              Ts732RemovedIssueSyncRepository.removedIssueKey,
            );
        final remainingDescriptionVisible = await screen.isTextVisible(
          Ts732RemovedIssueSyncRepository.remainingIssueDescription,
        );
        final remainingSelectedObservation = await screen
            .readIssueSearchResultSelectionObservation(
              Ts732RemovedIssueSyncRepository.remainingIssueKey,
              Ts732RemovedIssueSyncRepository.remainingIssueSummary,
              expectedSelected: true,
            );
        final textsAfterClick = screen.visibleTextsSnapshot();
        final semanticsAfterClick = screen.visibleSemanticsLabelsSnapshot();
        final bannerVisibleAfterClick = await screen
            .isMessageBannerVisibleContaining(_expectedNotificationFragment);

        result['navigation_error'] = navigationError;
        result['texts_after_click'] = textsAfterClick;
        result['semantics_after_click'] = semanticsAfterClick;
        result['remaining_selected_observation'] = remainingSelectedObservation
            .describe();
        result['remaining_detail_visible_after_click'] = remainingDetailVisible;
        result['removed_detail_visible_after_click'] =
            removedDetailVisibleAfterClick;
        result['remaining_description_visible_after_click'] =
            remainingDescriptionVisible;
        result['banner_visible_after_click'] = bannerVisibleAfterClick;

        final stepThreePassed =
            navigationError.isEmpty && remainingDetailVisible;
        _recordStep(
          result,
          step: 3,
          status: stepThreePassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed:
              'navigation_error=${navigationError.isEmpty ? '<none>' : navigationError}; '
              'remaining_detail_visible_after_click=$remainingDetailVisible; '
              'banner_visible_before_click=$bannerVisibleBeforeClick',
        );
        if (!stepThreePassed) {
          failures.add(
            'Step 3 failed: clicking ${Ts732RemovedIssueSyncRepository.remainingIssueKey} '
            'while the unavailable banner was visible did not open the issue.\n'
            'Navigation error: ${navigationError.isEmpty ? '<none>' : navigationError}\n'
            'Visible texts after click: ${_formatSnapshot(textsAfterClick)}\n'
            'Visible semantics after click: ${_formatSnapshot(semanticsAfterClick)}',
          );
        }

        final stepFourPassed =
            remainingSelectedObservation.usesExpectedTokens &&
            remainingDetailVisible &&
            !removedDetailVisibleAfterClick &&
            remainingDescriptionVisible;
        _recordStep(
          result,
          step: 4,
          status: stepFourPassed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed:
              'remaining_selected_observation=${remainingSelectedObservation.describe()}; '
              'remaining_detail_visible_after_click=$remainingDetailVisible; '
              'removed_detail_visible_after_click=$removedDetailVisibleAfterClick; '
              'remaining_description_visible_after_click=$remainingDescriptionVisible; '
              'banner_visible_after_click=$bannerVisibleAfterClick; '
              'visible_texts=${_formatSnapshot(textsAfterClick)}',
        );
        if (!stepFourPassed) {
          failures.add(
            'Step 4 failed: after clicking ${Ts732RemovedIssueSyncRepository.remainingIssueKey}, '
            'the remaining result was not visibly selected with its detail panel loaded.\n'
            'Observed selection: ${remainingSelectedObservation.describe()}\n'
            'Visible texts: ${_formatSnapshot(textsAfterClick)}\n'
            'Visible semantics: ${_formatSnapshot(semanticsAfterClick)}',
          );
        }

        final matchedExpected = failures.isEmpty;
        _recordHumanVerification(
          result,
          check:
              'Viewed the refreshed search state the way a user would: the unavailable banner appeared above the JQL Search results while the only remaining issue stayed visible and clickable.',
          observed:
              'banner_visible_before_click=$bannerVisibleBeforeClick; '
              'visible_rows=${_formatSnapshot(rowsAfterRefresh)}; '
              'visible_texts=${_formatSnapshot(textsAfterRefresh)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Clicked the remaining result while the banner was present and confirmed the row visibly highlighted and the TRACK-11 detail panel opened with its description.',
          observed:
              'selected_observation=${remainingSelectedObservation.describe()}; '
              'remaining_detail_visible_after_click=$remainingDetailVisible; '
              'remaining_description_visible_after_click=$remainingDescriptionVisible; '
              'banner_visible_after_click=$bannerVisibleAfterClick',
        );
        result['matched_expected_result'] = matchedExpected;
        if (failures.isNotEmpty) {
          result['failures'] = failures;
        }

        print('TS-752:${jsonEncode(result)}');

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

void _recordStep(
  Map<String, Object?> result, {
  required int step,
  required String status,
  required String action,
  required String observed,
}) {
  final steps = result['steps']! as List<Map<String, Object?>>;
  steps.add(<String, Object?>{
    'step': step,
    'status': status,
    'action': action,
    'observed': observed,
  });
}

void _recordHumanVerification(
  Map<String, Object?> result, {
  required String check,
  required String observed,
}) {
  final verifications =
      result['human_verification']! as List<Map<String, Object?>>;
  verifications.add(<String, Object?>{'check': check, 'observed': observed});
}

bool _snapshotContains(List<String> values, String expected) {
  for (final value in values) {
    if (value.contains(expected)) {
      return true;
    }
  }
  return false;
}

Future<bool> _pumpUntil(
  WidgetTester tester, {
  required Future<bool> Function() condition,
  required Duration timeout,
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (await condition()) {
      return true;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
  return false;
}

Future<bool> _hasSettledPostRefreshState(
  TrackStateAppComponent screen, {
  required String expectedSearchValue,
  required String notificationFragment,
}) async {
  final visibleResults = screen.visibleIssueSearchResultLabelsSnapshot();
  final jqlSearchValue = await screen.readJqlSearchFieldValue();
  return !(await screen.isIssueDetailVisible(
        Ts732RemovedIssueSyncRepository.removedIssueKey,
      )) &&
      !(await screen.isIssueDetailVisible(
        Ts732RemovedIssueSyncRepository.remainingIssueKey,
      )) &&
      await screen.isMessageBannerVisibleContaining(notificationFragment) &&
      jqlSearchValue == expectedSearchValue &&
      !_snapshotContains(
        visibleResults,
        'Open ${Ts732RemovedIssueSyncRepository.removedIssueKey} ${Ts732RemovedIssueSyncRepository.removedIssueSummary}',
      ) &&
      _snapshotContains(
        visibleResults,
        'Open ${Ts732RemovedIssueSyncRepository.remainingIssueKey} ${Ts732RemovedIssueSyncRepository.remainingIssueSummary}',
      );
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
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
