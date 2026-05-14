import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/settings_screen_robot.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts732_removed_issue_sync_repository.dart';

const String _ticketKey = 'TS-732';
const String _ticketSummary =
    'Sync refresh removes current issue and clears the invalid selection with a notification';
const String _expectedNotificationFragment = 'no longer available';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-732 sync refresh removes the current issue and leaves the user in search with a notification',
    (tester) async {
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
      final robot = SettingsScreenRobot(tester);
      final TrackStateAppComponent app = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      await robot.pumpApp(
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
      await app.expectIssueDetailText(
        Ts732RemovedIssueSyncRepository.removedIssueKey,
        Ts732RemovedIssueSyncRepository.removedIssueDescription,
      );

      final initialSearchValue = await app.readJqlSearchFieldValue();
      final initialConnected = await app.isTopBarTextVisible('Connected');
      final initialIssueDetailVisible = _issueDetailVisible(
        app,
        Ts732RemovedIssueSyncRepository.removedIssueKey,
      );
      final initialVisibleResults = app
          .visibleIssueSearchResultLabelsSnapshot();
      final expectedSearchValue = SettingsScreenRobot.jqlPlaceholderText;

      final step1Passed =
          initialConnected &&
          initialIssueDetailVisible &&
          initialSearchValue == expectedSearchValue;
      _recordStep(
        result,
        step: 1,
        status: step1Passed ? 'passed' : 'failed',
        action:
            'Start in JQL Search with Issue-A selected in the Search and Detail surface.',
        observed:
            'connected=$initialConnected; issue_detail_visible=$initialIssueDetailVisible; '
            'jql_value=${initialSearchValue ?? '<missing>'}; '
            'visible_results=${_formatSnapshot(initialVisibleResults)}',
      );
      if (!step1Passed) {
        failures.add(
          'Precondition failed: the hosted search session did not start with ${Ts732RemovedIssueSyncRepository.removedIssueKey} selected in the Search and Detail surface. '
          'Connected=$initialConnected; issue_detail_visible=$initialIssueDetailVisible; '
          'jql_value=${initialSearchValue ?? '<missing>'}; '
          'expected_jql_value=$expectedSearchValue; '
          'visible_results=${_formatSnapshot(initialVisibleResults)}.',
        );
      }

      await repository.emitIssueRemovalSync();
      final settledPostRefreshStateReached = await _pumpUntil(
        tester,
        condition: () async => await _hasSettledPostRefreshState(
          app,
          expectedSearchValue: expectedSearchValue,
          notificationFragment: _expectedNotificationFragment,
        ),
        timeout: const Duration(seconds: 10),
      );

      final visibleTexts = app.visibleTextsSnapshot();
      final visibleSemantics = app.visibleSemanticsLabelsSnapshot();
      final visibleResults = app.visibleIssueSearchResultLabelsSnapshot();
      final jqlValueAfterRefresh = await app.readJqlSearchFieldValue();
      final anyIssueDetailVisible = _anyIssueDetailVisible(app);
      final removedIssueSearchResultVisible = _snapshotContains(
        visibleResults,
        'Open ${Ts732RemovedIssueSyncRepository.removedIssueKey} ${Ts732RemovedIssueSyncRepository.removedIssueSummary}',
      );
      final remainingIssueSearchResultVisible = _snapshotContains(
        visibleResults,
        'Open ${Ts732RemovedIssueSyncRepository.remainingIssueKey} ${Ts732RemovedIssueSyncRepository.remainingIssueSummary}',
      );
      final notificationVisible = await app.isMessageBannerVisibleContaining(
        _expectedNotificationFragment,
      );

      result['settled_post_refresh_state_reached'] =
          settledPostRefreshStateReached;
      result['visible_texts_after_refresh'] = visibleTexts;
      result['visible_semantics_after_refresh'] = visibleSemantics;
      result['visible_search_results_after_refresh'] = visibleResults;

      final step2Passed = !anyIssueDetailVisible;
      _recordStep(
        result,
        step: 2,
        status: step2Passed ? 'passed' : 'failed',
        action:
            'Simulate a background sync where Issue-A no longer exists in issueSummaries/repositoryIndex, then observe the issue detail surface.',
        observed:
            'settled_post_refresh_state_reached=$settledPostRefreshStateReached; '
            'any_issue_detail_visible=$anyIssueDetailVisible; '
            'visible_semantics=${_formatSnapshot(visibleSemantics)}',
      );
      if (!step2Passed) {
        failures.add(
          'Step 2 failed: after the background sync removed ${Ts732RemovedIssueSyncRepository.removedIssueKey} from the workspace, the app still showed an issue detail surface instead of clearing the invalid selection. '
          'Visible semantics: ${_formatSnapshot(visibleSemantics)}. '
          'Visible texts: ${_formatSnapshot(visibleTexts)}.',
        );
      }

      final step3Passed =
          jqlValueAfterRefresh == expectedSearchValue &&
          !removedIssueSearchResultVisible &&
          remainingIssueSearchResultVisible &&
          notificationVisible;
      _recordStep(
        result,
        step: 3,
        status: step3Passed ? 'passed' : 'failed',
        action:
            'Observe the Search section navigation state and the non-blocking notification area after the refresh applies.',
        observed:
            'settled_post_refresh_state_reached=$settledPostRefreshStateReached; '
            'jql_value=${jqlValueAfterRefresh ?? '<missing>'}; '
            'removed_issue_search_result_visible=$removedIssueSearchResultVisible; '
            'remaining_issue_search_result_visible=$remainingIssueSearchResultVisible; '
            'notification_visible=$notificationVisible; '
            'visible_results=${_formatSnapshot(visibleResults)}; '
            'visible_texts=${_formatSnapshot(visibleTexts)}',
      );
      if (jqlValueAfterRefresh != expectedSearchValue) {
        failures.add(
          'Step 3 failed: the app did not keep the user in the current JQL Search section after the invalid selection was cleared. '
          'Expected the search field to keep "$expectedSearchValue", but observed "${jqlValueAfterRefresh ?? '<missing>'}".',
        );
      }
      if (removedIssueSearchResultVisible) {
        failures.add(
          'Step 3 failed: ${Ts732RemovedIssueSyncRepository.removedIssueKey} still appeared in the visible search results after the background sync removed it from the workspace. '
          'Visible search results: ${_formatSnapshot(visibleResults)}.',
        );
      }
      if (!remainingIssueSearchResultVisible) {
        failures.add(
          'Step 3 failed: the Search section did not keep the remaining issue list visible after clearing the invalid selection. '
          'Visible search results: ${_formatSnapshot(visibleResults)}.',
        );
      }
      if (!notificationVisible) {
        failures.add(
          'Step 3 failed: the app did not show a visible non-blocking notification explaining that the previous issue was no longer available. '
          'Visible texts: ${_formatSnapshot(visibleTexts)}. '
          'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
        );
      }

      final matchedExpected = failures.isEmpty;
      _recordHumanVerification(
        result,
        check:
            'Verified the refreshed search screen the way a user would see it: the detail panel closed, the JQL Search panel stayed on screen, the removed issue disappeared from the result list, and the notification banner communicated that the previous issue was no longer available.',
        observed:
            'matched_expected=$matchedExpected; '
            'visible_results=${_formatSnapshot(visibleResults)}; '
            'visible_texts=${_formatSnapshot(visibleTexts)}',
      );
      result['matched_expected_result'] = matchedExpected;
      if (failures.isNotEmpty) {
        result['failures'] = failures;
      }

      print('TS-732:${jsonEncode(result)}');

      if (failures.isNotEmpty) {
        fail(failures.join('\n'));
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
  TrackStateAppComponent app, {
  required String expectedSearchValue,
  required String notificationFragment,
}) async {
  final visibleResults = app.visibleIssueSearchResultLabelsSnapshot();
  final jqlSearchValue = await app.readJqlSearchFieldValue();
  return !_anyIssueDetailVisible(app) &&
      await app.isMessageBannerVisibleContaining(notificationFragment) &&
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
