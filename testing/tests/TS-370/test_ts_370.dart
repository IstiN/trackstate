import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts370_repository_access_banner_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-370 global repository-access banner keeps disconnected and read-only recovery states consistent',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent app = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final fixture = Ts370RepositoryAccessBannerFixture();
      final failures = <String>[];

      try {
        await app.pump(fixture.createRepository());

        await _verifyBannerAcrossIssueFlows(
          tester,
          app: app,
          failures: failures,
          topBarLabel: Ts370RepositoryAccessBannerFixture.disconnectedAction,
          title: Ts370RepositoryAccessBannerFixture.disconnectedTitle,
          message: Ts370RepositoryAccessBannerFixture.disconnectedMessage,
          actionLabel: Ts370RepositoryAccessBannerFixture.disconnectedAction,
          phaseLabel: 'disconnected',
        );

        final disconnectedBanner = _globalBanner(
          Ts370RepositoryAccessBannerFixture.disconnectedTitle,
          Ts370RepositoryAccessBannerFixture.disconnectedMessage,
        );
        final connectAction = _calloutAction(
          disconnectedBanner,
          Ts370RepositoryAccessBannerFixture.disconnectedAction,
        );
        if (connectAction.evaluate().isEmpty) {
          failures.add(
            'Step 2 failed: the disconnected global banner did not expose a visible '
            '"${Ts370RepositoryAccessBannerFixture.disconnectedAction}" recovery CTA. '
            'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
            'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
          );
        } else {
          await tester.tap(connectAction.first, warnIfMissed: false);
          await tester.pumpAndSettle();
        }

        final connectDialogVisible =
            await app.isDialogTextVisible('Connect GitHub') &&
            await app.isTextFieldVisible('Fine-grained token') &&
            await app.isTextVisible('Connect token');
        if (!connectDialogVisible) {
          failures.add(
            'Step 3 failed: activating the disconnected global banner CTA did not '
            'open the PAT recovery dialog. Visible dialog texts: '
            '${_formatSnapshot(app.visibleDialogTextsSnapshot())}. Visible texts: '
            '${_formatSnapshot(app.visibleTextsSnapshot())}.',
          );
        } else {
          await app.enterLabeledTextField(
            'Fine-grained token',
            text: Ts370RepositoryAccessBannerFixture.readOnlyToken,
          );
          await app.tapVisibleControl('Connect token');

          await _waitForCondition(
            tester,
            condition: () async =>
                await _isTopBarLabelVisible(
                  app,
                  Ts370RepositoryAccessBannerFixture.readOnlyLabel,
                ) &&
                _globalBanner(
                  Ts370RepositoryAccessBannerFixture.readOnlyTitle,
                  Ts370RepositoryAccessBannerFixture.readOnlyMessage,
                ).evaluate().isNotEmpty,
            failureMessage:
                'Step 4 failed: submitting a read-only PAT did not update the global repository-access banner to the read-only state. '
                'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}. '
                'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
                'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await _verifyBannerAcrossIssueFlows(
          tester,
          app: app,
          failures: failures,
          topBarLabel: Ts370RepositoryAccessBannerFixture.readOnlyLabel,
          title: Ts370RepositoryAccessBannerFixture.readOnlyTitle,
          message: Ts370RepositoryAccessBannerFixture.readOnlyMessage,
          actionLabel: Ts370RepositoryAccessBannerFixture.readOnlyAction,
          phaseLabel: 'read-only',
        );

        final readOnlyBanner = _globalBanner(
          Ts370RepositoryAccessBannerFixture.readOnlyTitle,
          Ts370RepositoryAccessBannerFixture.readOnlyMessage,
        );
        final reconnectAction = _calloutAction(
          readOnlyBanner,
          Ts370RepositoryAccessBannerFixture.readOnlyAction,
        );
        if (reconnectAction.evaluate().isEmpty) {
          failures.add(
            'Step 5 failed: the read-only global banner did not expose the '
            '"${Ts370RepositoryAccessBannerFixture.readOnlyAction}" recovery CTA. '
            'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
          );
        } else {
          await tester.tap(reconnectAction.first, warnIfMissed: false);
          await tester.pumpAndSettle();

          final authDialogVisible =
              await app.isDialogTextVisible('Manage GitHub access') &&
              await app.isTextFieldVisible('Fine-grained token');
          final settingsVisible =
              await app.isTextVisible('Project Settings') &&
              await app.isTextVisible('Repository access');

          if (!authDialogVisible && !settingsVisible) {
            failures.add(
              'Step 6 failed: activating the read-only recovery CTA did not route the user '
              'to the canonical recovery surface (Manage GitHub access dialog or Settings). '
              'Visible dialog texts: ${_formatSnapshot(app.visibleDialogTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
            );
          } else if (authDialogVisible) {
            await app.closeDialog('Cancel');
          }
        }

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

Future<void> _verifyBannerAcrossIssueFlows(
  WidgetTester tester, {
  required TrackStateAppComponent app,
  required List<String> failures,
  required String topBarLabel,
  required String title,
  required String message,
  required String actionLabel,
  required String phaseLabel,
}) async {
  const sections = <String>['Dashboard', 'Board', 'JQL Search', 'Hierarchy'];

  for (final section in sections) {
    await app.openSection(section);
    await tester.pumpAndSettle();
    _verifyVisibleBannerState(
      app: app,
      failures: failures,
      location: section,
      phaseLabel: phaseLabel,
      topBarLabel: topBarLabel,
      title: title,
      message: message,
      actionLabel: actionLabel,
    );
  }

  await app.openSection('JQL Search');
  await app.expectIssueSearchResultVisible(
    Ts370RepositoryAccessBannerFixture.issueKey,
    Ts370RepositoryAccessBannerFixture.issueSummary,
  );
  await app.openIssue(
    Ts370RepositoryAccessBannerFixture.issueKey,
    Ts370RepositoryAccessBannerFixture.issueSummary,
  );

  _verifyVisibleBannerState(
    app: app,
    failures: failures,
    location: 'issue detail for ${Ts370RepositoryAccessBannerFixture.issueKey}',
    phaseLabel: phaseLabel,
    topBarLabel: topBarLabel,
    title: title,
    message: message,
    actionLabel: actionLabel,
  );
}

void _verifyVisibleBannerState({
  required TrackStateAppComponent app,
  required List<String> failures,
  required String location,
  required String phaseLabel,
  required String topBarLabel,
  required String title,
  required String message,
  required String actionLabel,
}) {
  final banner = _globalBanner(title, message);
  if (banner.evaluate().isEmpty) {
    failures.add(
      'Expected Result failed: the $phaseLabel global repository-access banner was not visible in $location. '
      'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
      'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
    );
    return;
  }

  if (!_snapshotContains(app.topBarVisibleTextsSnapshot(), topBarLabel) &&
      !_snapshotContains(app.visibleSemanticsLabelsSnapshot(), topBarLabel)) {
    failures.add(
      'Expected Result failed: the top bar did not reflect the $phaseLabel repository-access mode in $location. '
      'Expected "$topBarLabel". Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}. '
      'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
    );
  }

  for (final requiredText in <String>[title, message, actionLabel]) {
    final visibleMatch = find.descendant(
      of: banner,
      matching: find.text(requiredText, findRichText: true),
    );
    if (visibleMatch.evaluate().isEmpty) {
      failures.add(
        'Expected Result failed: the $phaseLabel global repository-access banner in $location '
        'did not render "$requiredText" in the visible banner surface. '
        'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
      );
    }
  }
}

Finder _globalBanner(String title, String message) => find.byWidgetPredicate(
  (widget) =>
      widget is Semantics &&
      widget.properties.label == '$title $title $message',
  description: 'global repository-access banner for "$title"',
);

Finder _calloutAction(Finder callout, String label) {
  final outlinedButton = find.descendant(
    of: callout,
    matching: find.widgetWithText(OutlinedButton, label),
  );
  if (outlinedButton.evaluate().isNotEmpty) {
    return outlinedButton.first;
  }
  return find.descendant(of: callout, matching: find.text(label));
}

Future<bool> _isTopBarLabelVisible(
  TrackStateAppComponent app,
  String label,
) async {
  return await app.isTopBarSemanticsLabelVisible(label) ||
      await app.isTopBarTextVisible(label);
}

Future<void> _waitForCondition(
  WidgetTester tester, {
  required Future<bool> Function() condition,
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

bool _snapshotContains(List<String> values, String expected) {
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed == expected ||
        trimmed.startsWith(expected) ||
        trimmed.contains(expected)) {
      return true;
    }
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
