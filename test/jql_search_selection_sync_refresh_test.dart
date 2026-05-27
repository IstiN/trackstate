import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/core/interfaces/trackstate_app_component.dart';
import '../testing/tests/TS-742/support/ts742_matching_issue_sync_repository.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'selected JQL search result stays visibly selected across matching sync refreshes',
    (tester) async {
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts742MatchingIssueSyncRepository();

      await screen.pump(repository);
      await screen.openSection('JQL Search');
      await screen.searchIssues(Ts742MatchingIssueSyncRepository.query);
      await screen.openIssue(
        Ts742MatchingIssueSyncRepository.issueBKey,
        Ts742MatchingIssueSyncRepository.issueBSummary,
      );

      expect(
        await screen.isIssueSearchResultSelected(
          Ts742MatchingIssueSyncRepository.issueBKey,
          Ts742MatchingIssueSyncRepository.issueBSummary,
        ),
        isTrue,
      );

      repository.scheduleSelectedIssueDescriptionRefresh();
      await _resumeApp(tester);
      await _pumpUntil(
        tester,
        condition: () async =>
            await screen.isIssueDetailVisible(
              Ts742MatchingIssueSyncRepository.issueBKey,
            ) &&
            await screen.isTextVisible(
              Ts742MatchingIssueSyncRepository.updatedIssueBDescription,
            ),
        timeout: const Duration(seconds: 10),
      );

      expect(
        await screen.isIssueSearchResultSelected(
          Ts742MatchingIssueSyncRepository.issueAKey,
          Ts742MatchingIssueSyncRepository.issueASummary,
        ),
        isFalse,
      );
      expect(
        await screen.isIssueSearchResultSelected(
          Ts742MatchingIssueSyncRepository.issueBKey,
          Ts742MatchingIssueSyncRepository.issueBSummary,
        ),
        isTrue,
      );

      screen.resetView();
    },
  );
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required Future<bool> Function() condition,
  required Duration timeout,
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (await condition()) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
}

Future<void> _resumeApp(WidgetTester tester) async {
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
  await tester.pumpAndSettle();
}
