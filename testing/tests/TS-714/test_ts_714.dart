import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/settings_screen_robot.dart';
import '../../components/screens/trackstate_app_screen.dart';
import 'support/ts714_background_sync_deferred_repository.dart';

const String _pendingLabel = 'Updates pending';
const String _pendingMessage =
    'Background updates were detected while edits were open. TrackState will apply the latest refresh after you finish the current draft or save.';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-714 background sync defers same-issue refresh while unsaved edits stay visible',
    (tester) async {
      final failures = <String>[];
      final repository = Ts714BackgroundSyncDeferredRepository();
      final robot = SettingsScreenRobot(tester);
      final app =
          defaultTestingDependencies.createTrackStateAppScreen(tester)
              as TrackStateAppScreen;

      await robot.pumpApp(
        repository: repository,
        sharedPreferences: const <String, Object>{
          Ts714BackgroundSyncDeferredRepository.hostedTokenKey:
              Ts714BackgroundSyncDeferredRepository.hostedTokenValue,
        },
      );

      await app.openSection('JQL Search');
      await app.expectIssueSearchResultVisible(
        Ts714BackgroundSyncDeferredRepository.issueKey,
        Ts714BackgroundSyncDeferredRepository.issueSummary,
      );
      await app.openIssue(
        Ts714BackgroundSyncDeferredRepository.issueKey,
        Ts714BackgroundSyncDeferredRepository.issueSummary,
      );

      if (!(await app.isTopBarTextVisible('Connected'))) {
        failures.add(
          'Precondition failed: the hosted shell did not restore a connected write-enabled session before opening the issue. '
          'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}.',
        );
      }

      await app.expectIssueDetailText(
        Ts714BackgroundSyncDeferredRepository.issueKey,
        Ts714BackgroundSyncDeferredRepository.initialDescription,
      );
      await app.tapIssueDetailAction(
        Ts714BackgroundSyncDeferredRepository.issueKey,
        label: 'Edit',
      );

      final initialEditorValue = await app.readLabeledTextFieldValue(
        'Description',
      );
      if (initialEditorValue !=
          Ts714BackgroundSyncDeferredRepository.initialDescription) {
        failures.add(
          'Precondition failed: the edit dialog did not load the existing issue description before the deferred-sync scenario started. '
          'Observed Description value: ${initialEditorValue ?? '<missing>'}.',
        );
      }

      await app.enterLabeledTextFieldWithoutSettling(
        'Description',
        text: Ts714BackgroundSyncDeferredRepository.localDraftDescription,
      );

      final draftValueBeforeSync = await app.readLabeledTextFieldValue(
        'Description',
      );
      if (draftValueBeforeSync !=
          Ts714BackgroundSyncDeferredRepository.localDraftDescription) {
        failures.add(
          'Step 1 failed: typing an unsaved local draft into the Description field did not keep the user-entered text in the visible editor. '
          'Observed Description value: ${draftValueBeforeSync ?? '<missing>'}.',
        );
      }

      await repository.emitExternalIssueDescriptionChange();
      await _pumpUntil(
        tester,
        condition: () async =>
            await app.isTopBarTextVisible(_pendingLabel) &&
            await app.isTextVisible(_pendingMessage),
        timeout: const Duration(seconds: 5),
      );

      if (!(await app.isTopBarTextVisible(_pendingLabel))) {
        failures.add(
          'Step 2 failed: after the external Git change arrived during the unsaved edit session, the top bar did not expose the visible "$_pendingLabel" sync state. '
          'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}.',
        );
      }

      if (!(await app.isTextVisible(_pendingMessage))) {
        failures.add(
          'Step 3 failed: the edit dialog did not show the deferred-sync helper message after background updates were detected. '
          'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
        );
      }

      final draftValueAfterSync = await app.readLabeledTextFieldValue(
        'Description',
      );
      if (draftValueAfterSync !=
          Ts714BackgroundSyncDeferredRepository.localDraftDescription) {
        failures.add(
          'Step 3 failed: the external refresh replaced the unsaved Description draft while the edit dialog was still open. '
          'Expected "${Ts714BackgroundSyncDeferredRepository.localDraftDescription}", but observed "${draftValueAfterSync ?? '<missing>'}".',
        );
      }

      await app.tapIssueDetailAction(
        Ts714BackgroundSyncDeferredRepository.issueKey,
        label: 'Save',
      );

      await _pumpUntil(
        tester,
        condition: () async =>
            !(await app.isTopBarTextVisible(_pendingLabel)) &&
            await app.isTextVisible(
              Ts714BackgroundSyncDeferredRepository.issueKey,
            ),
        timeout: const Duration(seconds: 5),
      );

      if (await app.isTopBarTextVisible(_pendingLabel)) {
        failures.add(
          'Step 5 failed: the top bar still showed "$_pendingLabel" after saving the issue, so the queued refresh never cleared. '
          'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}.',
        );
      }

      if (!(await app.isTextVisible(
        Ts714BackgroundSyncDeferredRepository.localDraftDescription,
      ))) {
        failures.add(
          'Step 5 failed: after saving, the issue detail did not show the user-visible saved draft description. '
          'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
        );
      }

      if (await app.isTextVisible(
        Ts714BackgroundSyncDeferredRepository.remoteDescription,
      )) {
        failures.add(
          'Human-style verification failed: after the save completed and the queued refresh applied, the issue detail showed the remote background-update description instead of the draft the user just saved. '
          'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
        );
      }

      if (failures.isNotEmpty) {
        fail(failures.join('\n'));
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
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
