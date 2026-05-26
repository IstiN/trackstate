import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts447_post_auth_resume_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-447 post-auth startup recovery resumes exactly once and requires explicit retry after a second 403',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final fixture = Ts447PostAuthResumeFixture();

      try {
        await screen.pump(fixture.repository);

        final failures = <String>[];

        if (fixture.repository.loadSnapshotCalls != 1) {
          failures.add(
            'Precondition failed: initial startup should load exactly one bootstrap snapshot before authentication, '
            'but observed ${fixture.repository.loadSnapshotCalls} loadSnapshot() calls.',
          );
        }
        if (fixture.repository.searchIssuePageCalls != 1) {
          failures.add(
            'Precondition failed: initial startup should issue exactly one search bootstrap request before authentication, '
            'but observed ${fixture.repository.searchIssuePageCalls} searchIssuePage() calls.',
          );
        }

        for (final requiredText in const [
          'Project Settings',
          Ts447PostAuthResumeFixture.startupRecoveryTitle,
          Ts447PostAuthResumeFixture.startupRecoveryMessage,
          'Retry',
          'Connect GitHub',
        ]) {
          if (!await screen.isTextVisible(requiredText)) {
            failures.add(
              'Step 1 failed: the hosted startup recovery state did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
            );
          }
        }

        if (!await screen.isTopBarSemanticsLabelVisible('Connect GitHub') &&
            !await screen.isTopBarTextVisible('Connect GitHub')) {
          failures.add(
            'Step 1 failed: the top bar did not expose the Connect GitHub access control while the app was still in startup recovery. '
            'Visible top-bar texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}.',
          );
        }

        for (final requiredText in const [
          'Fine-grained token',
          'Needs Contents: read/write. Stored only on this device if remembered.',
          'Remember on this browser',
          'Connect token',
        ]) {
          if (!await screen.isTextVisible(requiredText)) {
            failures.add(
              'Step 1 failed: the Settings repository access form did not render the visible "$requiredText" text. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
            );
          }
        }

        await screen.enterLabeledTextField(
          'Fine-grained token',
          text: 'ghp_ts447_first',
        );
        final firstTokenValue = await screen.readLabeledTextFieldValue(
          'Fine-grained token',
        );
        if (firstTokenValue != 'ghp_ts447_first') {
          failures.add(
            'Step 1 failed: typing the authentication token did not update the visible token field before submission. '
            'Observed value: "${firstTokenValue ?? '<missing>'}".',
          );
        }
        await screen.tapVisibleControl('Connect token');

        await _waitForCondition(
          tester,
          () async =>
              fixture.repository.connectCalls == 1 &&
              fixture.repository.loadSnapshotCalls == 2,
          failureMessage:
              'Timed out waiting for the first successful authentication to trigger one automatic startup resume. '
              'Observed connect calls: ${fixture.repository.connectCalls}. '
              'Observed loadSnapshot() calls: ${fixture.repository.loadSnapshotCalls}. '
              'Observed searchIssuePage() calls: ${fixture.repository.searchIssuePageCalls}.',
        );

        if (fixture.repository.loadSnapshotCalls != 2) {
          failures.add(
            'Step 2 failed: successful authentication should trigger exactly one automatic bootstrap resume, '
            'but observed ${fixture.repository.loadSnapshotCalls - 1} post-auth loadSnapshot() attempts '
            '(total loadSnapshot() calls: ${fixture.repository.loadSnapshotCalls}).',
          );
        }
        if (fixture.repository.searchIssuePageCalls != 1) {
          failures.add(
            'Step 3 failed: the failed automatic resume should stop after the second 403 before issuing another search bootstrap request, '
            'but observed ${fixture.repository.searchIssuePageCalls} total searchIssuePage() calls.',
          );
        }

        if (!await screen.isTextVisible(
          Ts447PostAuthResumeFixture.connectedBanner,
        )) {
          failures.add(
            'Step 1 failed: after authentication, the user-facing connected banner did not remain visible. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }

        if (!await screen.isTopBarSemanticsLabelVisible('Connected') &&
            !await screen.isTopBarTextVisible('Connected')) {
          failures.add(
            'Step 1 failed: after authentication, the top bar did not switch the repository access control to the visible Connected state. '
            'Visible top-bar texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}.',
          );
        }

        if (!await screen.isTextVisible(
          Ts447PostAuthResumeFixture.startupRecoveryTitle,
        )) {
          failures.add(
            'Step 3 failed: after the resumed bootstrap hit another 403, the startup recovery callout disappeared instead of keeping the user in the recovery state. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }

        final loadCallsBeforeSecondAuthentication =
            fixture.repository.loadSnapshotCalls;
        final searchCallsBeforeSecondAuthentication =
            fixture.repository.searchIssuePageCalls;

        final connectGitHubVisible =
            await screen.isTextVisible('Connect GitHub') ||
            await screen.isSemanticsLabelVisible('Connect GitHub');
        if (!connectGitHubVisible) {
          failures.add(
            'Step 3 failed: the recovery callout did not keep a visible Connect GitHub action after the automatic resume failed.',
          );
        } else {
          await screen.enterLabeledTextField(
            'Fine-grained token',
            text: 'ghp_ts447_second',
          );
          await screen.tapVisibleControl('Connect token');

          await _waitForCondition(
            tester,
            () async => fixture.repository.connectCalls == 2,
            failureMessage:
                'Timed out waiting for the second authentication attempt to finish. '
                'Observed connect calls: ${fixture.repository.connectCalls}.',
          );
        }

        await tester.pump(const Duration(milliseconds: 300));

        if (fixture.repository.loadSnapshotCalls !=
            loadCallsBeforeSecondAuthentication) {
          failures.add(
            'Step 3 failed: a second authentication event triggered another automatic bootstrap resume even though the first resumed load had already failed. '
            'Expected loadSnapshot() calls to stay at $loadCallsBeforeSecondAuthentication, '
            'but observed ${fixture.repository.loadSnapshotCalls}.',
          );
        }
        if (fixture.repository.searchIssuePageCalls !=
            searchCallsBeforeSecondAuthentication) {
          failures.add(
            'Step 3 failed: a second authentication event triggered another automatic search bootstrap call. '
            'Expected searchIssuePage() calls to stay at $searchCallsBeforeSecondAuthentication, '
            'but observed ${fixture.repository.searchIssuePageCalls}.',
          );
        }

        await screen.tapVisibleControl('Retry');

        await _waitForCondition(
          tester,
          () async =>
              fixture.repository.loadSnapshotCalls ==
                  loadCallsBeforeSecondAuthentication + 1 &&
              fixture.repository.searchIssuePageCalls ==
                  searchCallsBeforeSecondAuthentication + 1 &&
              !await screen.isTextVisible(
                Ts447PostAuthResumeFixture.startupRecoveryTitle,
              ),
          failureMessage:
              'Timed out waiting for the explicit Retry action to resume startup after the failed automatic attempt. '
              'Observed loadSnapshot() calls: ${fixture.repository.loadSnapshotCalls}. '
              'Observed searchIssuePage() calls: ${fixture.repository.searchIssuePageCalls}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );

        await screen.openSection('JQL Search');
        await screen.expectIssueSearchResultVisible(
          Ts447PostAuthResumeFixture.issueKey,
          Ts447PostAuthResumeFixture.issueSummary,
        );

        final searchRowTexts = screen.issueSearchResultTextsSnapshot(
          Ts447PostAuthResumeFixture.issueKey,
          Ts447PostAuthResumeFixture.issueSummary,
        );
        for (final requiredText in const [
          Ts447PostAuthResumeFixture.issueKey,
          Ts447PostAuthResumeFixture.issueSummary,
          'In Progress',
        ]) {
          if (!searchRowTexts.contains(requiredText)) {
            failures.add(
              'Expected Result failed: after the explicit Retry action resumed startup, the visible JQL Search result did not contain "$requiredText". '
              'Visible row texts: ${_formatSnapshot(searchRowTexts)}.',
            );
          }
        }

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

Future<void> _waitForCondition(
  WidgetTester tester,
  Future<bool> Function() condition, {
  required String failureMessage,
  Duration timeout = const Duration(seconds: 5),
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(step);
    if (await condition()) {
      return;
    }
  }
  fail(failureMessage);
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  if (snapshot.length <= limit) {
    return snapshot.join(' | ');
  }
  return snapshot.take(limit).join(' | ');
}
