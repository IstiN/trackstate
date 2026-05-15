import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/settings_screen_robot.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-732/support/ts732_removed_issue_sync_repository.dart';

const String _ticketKey = 'TS-753';
const String _ticketSummary =
    'Sync removal of selected issue leaves a dismissible notification banner';
const String _expectedNotificationFragment = 'no longer available';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-753 lets the user dismiss the issue unavailable notification banner after sync removal',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final repository = Ts732RemovedIssueSyncRepository();
      final TrackStateAppComponent app = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final expectedSearchValue = SettingsScreenRobot.jqlPlaceholderText;
      final expectedNotificationMessage =
          '${Ts732RemovedIssueSyncRepository.removedIssueKey} is no longer available in this workspace.';

      try {
        await SettingsScreenRobot(tester).pumpApp(
          repository: repository,
          sharedPreferences: const <String, Object>{
            Ts732RemovedIssueSyncRepository.hostedTokenKey:
                Ts732RemovedIssueSyncRepository.hostedTokenValue,
          },
        );

        await app.openSection('JQL Search');
        await app.expectIssueSearchResultVisible(
          Ts732RemovedIssueSyncRepository.removedIssueKey,
          Ts732RemovedIssueSyncRepository.removedIssueSummary,
        );
        await app.openIssue(
          Ts732RemovedIssueSyncRepository.removedIssueKey,
          Ts732RemovedIssueSyncRepository.removedIssueSummary,
        );
        await app.expectIssueDetailVisible(
          Ts732RemovedIssueSyncRepository.removedIssueKey,
        );

        final initialSearchValue = await app.readJqlSearchFieldValue();
        final initialDetailVisible = _issueDetailVisible(
          app,
          Ts732RemovedIssueSyncRepository.removedIssueKey,
        );
        final initialVisibleResults = app
            .visibleIssueSearchResultLabelsSnapshot();
        final preconditionPassed =
            initialSearchValue == expectedSearchValue && initialDetailVisible;
        result['initial_search_value'] = initialSearchValue ?? '<missing>';
        result['initial_visible_results'] = initialVisibleResults;
        result['initial_issue_detail_visible'] = initialDetailVisible;
        if (!preconditionPassed) {
          failures.add(
            'Precondition failed: expected ${Ts732RemovedIssueSyncRepository.removedIssueKey} to be selected in JQL Search before the sync update. '
            'Observed search_value=${initialSearchValue ?? '<missing>'}; '
            'issue_detail_visible=$initialDetailVisible; '
            'visible_results=${_formatSnapshot(initialVisibleResults)}.',
          );
        }

        await repository.emitIssueRemovalSync();
        final notificationReady = await _pumpUntil(
          tester,
          condition: () async => await _hasVisibleUnavailableBanner(
            app,
            expectedSearchValue: expectedSearchValue,
            notificationFragment: _expectedNotificationFragment,
          ),
          timeout: const Duration(seconds: 10),
        );

        final visibleTextsBeforeDismiss = app.visibleTextsSnapshot();
        final visibleSemanticsBeforeDismiss = app
            .visibleSemanticsLabelsSnapshot();
        final visibleResultsBeforeDismiss = app
            .visibleIssueSearchResultLabelsSnapshot();
        final notificationVisible = await app.isMessageBannerVisibleContaining(
          _expectedNotificationFragment,
        );
        final notificationTextVisible = await app.isTextVisible(
          expectedNotificationMessage,
        );
        final anyIssueDetailVisible = _anyIssueDetailVisible(app);
        final remainingIssueVisible = _snapshotContains(
          visibleResultsBeforeDismiss,
          'Open ${Ts732RemovedIssueSyncRepository.remainingIssueKey} ${Ts732RemovedIssueSyncRepository.remainingIssueSummary}',
        );

        result['notification_ready'] = notificationReady;
        result['visible_texts_before_dismiss'] = visibleTextsBeforeDismiss;
        result['visible_semantics_before_dismiss'] =
            visibleSemanticsBeforeDismiss;
        result['visible_results_before_dismiss'] = visibleResultsBeforeDismiss;

        final step1Passed = notificationReady && !anyIssueDetailVisible;
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action: 'Simulate a background sync event where Issue-A is removed.',
          observed:
              'notification_ready=$notificationReady; any_issue_detail_visible=$anyIssueDetailVisible; '
              'visible_results=${_formatSnapshot(visibleResultsBeforeDismiss)}; '
              'visible_semantics=${_formatSnapshot(visibleSemanticsBeforeDismiss)}',
        );
        if (!step1Passed) {
          failures.add(
            'Step 1 failed: after the background sync removed ${Ts732RemovedIssueSyncRepository.removedIssueKey}, the refreshed UI did not settle into the expected state with the detail panel cleared and the unavailable banner ready. '
            'notification_ready=$notificationReady; any_issue_detail_visible=$anyIssueDetailVisible; '
            'visible_results=${_formatSnapshot(visibleResultsBeforeDismiss)}; '
            'visible_texts=${_formatSnapshot(visibleTextsBeforeDismiss)}.',
          );
        }

        final step2Passed =
            notificationVisible &&
            notificationTextVisible &&
            remainingIssueVisible;
        _recordStep(
          result,
          step: 2,
          status: step2Passed ? 'passed' : 'failed',
          action:
              "Confirm the notification banner containing 'no longer available' is visible.",
          observed:
              'notification_visible=$notificationVisible; notification_text_visible=$notificationTextVisible; '
              'remaining_issue_visible=$remainingIssueVisible; '
              'visible_texts=${_formatSnapshot(visibleTextsBeforeDismiss)}',
        );
        if (!notificationVisible) {
          failures.add(
            'Step 2 failed: no visible message banner containing "$_expectedNotificationFragment" appeared after the sync removal. '
            'Visible texts: ${_formatSnapshot(visibleTextsBeforeDismiss)}. '
            'Visible semantics: ${_formatSnapshot(visibleSemanticsBeforeDismiss)}.',
          );
        }
        if (!notificationTextVisible) {
          failures.add(
            'Step 2 failed: the exact user-facing unavailable message was not visible after the sync removal. '
            'Expected text: "$expectedNotificationMessage". '
            'Visible texts: ${_formatSnapshot(visibleTextsBeforeDismiss)}.',
          );
        }
        if (!remainingIssueVisible) {
          failures.add(
            'Step 2 failed: the refreshed JQL Search results did not leave the remaining issue visible while the unavailable banner was shown. '
            'Visible results: ${_formatSnapshot(visibleResultsBeforeDismiss)}.',
          );
        }

        final dismissed = await app.dismissMessageBannerContaining(
          _expectedNotificationFragment,
        );
        final bannerVisibleAfterDismiss = await app
            .isMessageBannerVisibleContaining(_expectedNotificationFragment);
        final notificationTextVisibleAfterDismiss = await app.isTextVisible(
          expectedNotificationMessage,
        );
        final visibleTextsAfterDismiss = app.visibleTextsSnapshot();
        final visibleSemanticsAfterDismiss = app
            .visibleSemanticsLabelsSnapshot();
        final visibleResultsAfterDismiss = app
            .visibleIssueSearchResultLabelsSnapshot();

        result['dismissed'] = dismissed;
        result['banner_visible_after_dismiss'] = bannerVisibleAfterDismiss;
        result['notification_text_visible_after_dismiss'] =
            notificationTextVisibleAfterDismiss;
        result['visible_texts_after_dismiss'] = visibleTextsAfterDismiss;
        result['visible_semantics_after_dismiss'] =
            visibleSemanticsAfterDismiss;
        result['visible_results_after_dismiss'] = visibleResultsAfterDismiss;

        final step3Passed =
            dismissed &&
            !bannerVisibleAfterDismiss &&
            !notificationTextVisibleAfterDismiss;
        _recordStep(
          result,
          step: 3,
          status: step3Passed ? 'passed' : 'failed',
          action:
              "Click the dismissal action (e.g., 'X' or 'Close') on the banner.",
          observed:
              'dismissed=$dismissed; banner_visible_after_dismiss=$bannerVisibleAfterDismiss; '
              'notification_text_visible_after_dismiss=$notificationTextVisibleAfterDismiss; '
              'visible_texts_after_dismiss=${_formatSnapshot(visibleTextsAfterDismiss)}',
        );
        if (!dismissed) {
          failures.add(
            'Step 3 failed: the visible unavailable banner did not expose a working dismiss/close action. '
            'Visible texts before dismiss: ${_formatSnapshot(visibleTextsBeforeDismiss)}. '
            'Visible semantics before dismiss: ${_formatSnapshot(visibleSemanticsBeforeDismiss)}.',
          );
        }
        if (bannerVisibleAfterDismiss || notificationTextVisibleAfterDismiss) {
          failures.add(
            'Expected result failed: after dismissing the unavailable banner, it remained visible or its text still occupied the UI. '
            'banner_visible_after_dismiss=$bannerVisibleAfterDismiss; '
            'notification_text_visible_after_dismiss=$notificationTextVisibleAfterDismiss; '
            'visible_texts_after_dismiss=${_formatSnapshot(visibleTextsAfterDismiss)}; '
            'visible_semantics_after_dismiss=${_formatSnapshot(visibleSemanticsAfterDismiss)}.',
          );
        }

        final matchedExpected = failures.isEmpty;
        _recordHumanVerification(
          result,
          check:
              'Reviewed the refreshed JQL Search screen the way a user would: the unavailable banner appeared after the sync update, then disappeared completely after tapping its visible Close action while the rest of the search surface stayed usable.',
          observed:
              'matched_expected=$matchedExpected; '
              'before_dismiss=${_formatSnapshot(visibleTextsBeforeDismiss)}; '
              'after_dismiss=${_formatSnapshot(visibleTextsAfterDismiss)}; '
              'remaining_results=${_formatSnapshot(visibleResultsAfterDismiss)}',
        );
        result['matched_expected_result'] = matchedExpected;
        if (failures.isNotEmpty) {
          result['failures'] = failures;
        }

        print('TS-753:${jsonEncode(result)}');

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        app.resetView();
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

bool _issueDetailVisible(TrackStateAppComponent app, String issueKey) {
  return _snapshotContains(
    app.visibleSemanticsLabelsSnapshot(),
    'Issue detail $issueKey',
  );
}

bool _anyIssueDetailVisible(TrackStateAppComponent app) {
  for (final label in app.visibleSemanticsLabelsSnapshot()) {
    if (label.contains('Issue detail ')) {
      return true;
    }
  }
  return false;
}

Future<bool> _hasVisibleUnavailableBanner(
  TrackStateAppComponent app, {
  required String expectedSearchValue,
  required String notificationFragment,
}) async {
  final visibleResults = app.visibleIssueSearchResultLabelsSnapshot();
  final jqlSearchValue = await app.readJqlSearchFieldValue();
  return !_anyIssueDetailVisible(app) &&
      await app.isMessageBannerVisibleContaining(notificationFragment) &&
      jqlSearchValue == expectedSearchValue &&
      _snapshotContains(
        visibleResults,
        'Open ${Ts732RemovedIssueSyncRepository.remainingIssueKey} ${Ts732RemovedIssueSyncRepository.remainingIssueSummary}',
      );
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
