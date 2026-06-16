import 'package:flutter_test/flutter_test.dart';

import '../support/reopen_issue_resolution_scenario.dart';

void main() {
  testWidgets(
    'TS-281 reopens a done issue to to-do and clears the persisted resolution',
    (tester) async =>
        runReopenIssueResolutionScenario(tester, ticketKey: 'TS-281'),
    timeout: const Timeout(Duration(seconds: 20)),
  );
}
