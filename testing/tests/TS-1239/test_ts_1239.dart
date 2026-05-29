import 'dart:ui' show Size;

import 'package:flutter/material.dart' show Semantics;
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts1239_repository_access_golden_fixture.dart';

const Size _requiredViewport = Size(1440, 960);

const String _disconnectedGoldenPath =
    'goldens/repository_access_unauthenticated_desktop.png';
const String _readOnlyGoldenPath =
    'goldens/repository_access_read_only_desktop.png';
const String _fullAccessGoldenPath =
    'goldens/repository_access_full_access_desktop.png';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-1239 global repository-access banner matches approved goldens and avoids overflow at 1440x960',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent app = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final fixture = Ts1239RepositoryAccessGoldenFixture();
      final failures = <String>[];

      try {
        await app.pump(fixture.createRepository());
        _expectViewport(tester, failures: failures, stepLabel: 'Step 1');

        await _waitForCondition(
          tester,
          condition: () async =>
              await app.isTopBarTextVisible(
                Ts1239RepositoryAccessGoldenFixture.disconnectedLabel,
              ) &&
              await app.isRepositoryAccessBannerVisible(
                title: Ts1239RepositoryAccessGoldenFixture.disconnectedTitle,
                message:
                    Ts1239RepositoryAccessGoldenFixture.disconnectedMessage,
              ),
          failureMessage:
              'Step 1 failed: the unauthenticated 1440x960 app did not show the expected repository-access banner. '
              'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
          failures: failures,
        );

        await _expectRepositoryAccessBannerState(
          app: app,
          failures: failures,
          topBarLabel: Ts1239RepositoryAccessGoldenFixture.disconnectedLabel,
          title: Ts1239RepositoryAccessGoldenFixture.disconnectedTitle,
          message: Ts1239RepositoryAccessGoldenFixture.disconnectedMessage,
          actionLabel: Ts1239RepositoryAccessGoldenFixture.disconnectedAction,
          stepLabel: 'Step 2',
        );
        await _compareApprovedGolden(
          target: _repositoryAccessBanner(
            Ts1239RepositoryAccessGoldenFixture.disconnectedTitle,
            message: Ts1239RepositoryAccessGoldenFixture.disconnectedMessage,
          ),
          approvedGoldenPath: _disconnectedGoldenPath,
          failureLabel:
              'Step 2 failed: the unauthenticated repository-access banner no longer matches the approved golden baseline.',
          failures: failures,
        );

        await _openRepositoryAccessDialog(
          app: app,
          failures: failures,
          stepLabel: 'Step 2',
          bannerTitle: Ts1239RepositoryAccessGoldenFixture.disconnectedTitle,
          bannerMessage:
              Ts1239RepositoryAccessGoldenFixture.disconnectedMessage,
          actionLabel: Ts1239RepositoryAccessGoldenFixture.disconnectedAction,
          expectedDialogTitle:
              Ts1239RepositoryAccessGoldenFixture.disconnectedAction,
        );
        await _submitHostedAccessToken(
          tester,
          app: app,
          token: Ts1239RepositoryAccessGoldenFixture.readOnlyToken,
          stepLabel: 'Step 3',
          failures: failures,
        );

        await _waitForCondition(
          tester,
          condition: () async =>
              await app.isTopBarTextVisible(
                Ts1239RepositoryAccessGoldenFixture.readOnlyLabel,
              ) &&
              await app.isRepositoryAccessBannerVisible(
                title: Ts1239RepositoryAccessGoldenFixture.readOnlyTitle,
                message: Ts1239RepositoryAccessGoldenFixture.readOnlyMessage,
              ),
          failureMessage:
              'Step 3 failed: submitting the read-only repository access token did not transition the production UI to the read-only banner state. '
              'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
          failures: failures,
        );

        await _expectRepositoryAccessBannerState(
          app: app,
          failures: failures,
          topBarLabel: Ts1239RepositoryAccessGoldenFixture.readOnlyLabel,
          title: Ts1239RepositoryAccessGoldenFixture.readOnlyTitle,
          message: Ts1239RepositoryAccessGoldenFixture.readOnlyMessage,
          actionLabel: Ts1239RepositoryAccessGoldenFixture.readOnlyAction,
          stepLabel: 'Step 4',
        );
        _expectReadOnlyBannerWrapsAcrossMultipleLines(
          tester,
          message: Ts1239RepositoryAccessGoldenFixture.readOnlyMessage,
          failures: failures,
        );
        _expectNoFrameworkOverflowErrors(
          tester,
          stepLabel: 'Step 4',
          failures: failures,
          visibleTexts: app.visibleTextsSnapshot(),
          visibleSemantics: app.visibleSemanticsLabelsSnapshot(),
        );
        await _compareApprovedGolden(
          target: _repositoryAccessBanner(
            Ts1239RepositoryAccessGoldenFixture.readOnlyTitle,
            message: Ts1239RepositoryAccessGoldenFixture.readOnlyMessage,
          ),
          approvedGoldenPath: _readOnlyGoldenPath,
          failureLabel:
              'Step 4 failed: the read-only repository-access banner no longer matches the approved golden baseline.',
          failures: failures,
        );

        _expectViewport(tester, failures: failures, stepLabel: 'Step 5');
        await _openRepositoryAccessDialog(
          app: app,
          failures: failures,
          stepLabel: 'Step 5',
          bannerTitle: Ts1239RepositoryAccessGoldenFixture.readOnlyTitle,
          bannerMessage: Ts1239RepositoryAccessGoldenFixture.readOnlyMessage,
          actionLabel: Ts1239RepositoryAccessGoldenFixture.readOnlyAction,
          expectedDialogTitle:
              Ts1239RepositoryAccessGoldenFixture.manageAccessDialogTitle,
        );
        await _submitHostedAccessToken(
          tester,
          app: app,
          token: Ts1239RepositoryAccessGoldenFixture.writableToken,
          stepLabel: 'Step 5',
          failures: failures,
        );

        await _waitForCondition(
          tester,
          condition: () async =>
              await app.isTopBarTextVisible(
                Ts1239RepositoryAccessGoldenFixture.writableLabel,
              ) &&
              !await app.isRepositoryAccessBannerVisible(
                title: Ts1239RepositoryAccessGoldenFixture.disconnectedTitle,
                message:
                    Ts1239RepositoryAccessGoldenFixture.disconnectedMessage,
              ) &&
              !await app.isRepositoryAccessBannerVisible(
                title: Ts1239RepositoryAccessGoldenFixture.readOnlyTitle,
                message: Ts1239RepositoryAccessGoldenFixture.readOnlyMessage,
              ),
          failureMessage:
              'Step 5 failed: reconnecting with writable permissions did not produce the expected full-access state. '
              'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
          failures: failures,
        );
        _expectNoFrameworkOverflowErrors(
          tester,
          stepLabel: 'Step 5',
          failures: failures,
          visibleTexts: app.visibleTextsSnapshot(),
          visibleSemantics: app.visibleSemanticsLabelsSnapshot(),
        );

        if (await app.isRepositoryAccessBannerVisible(
          title: Ts1239RepositoryAccessGoldenFixture.disconnectedTitle,
          message: Ts1239RepositoryAccessGoldenFixture.disconnectedMessage,
        )) {
          failures.add(
            'Step 5 failed: the unauthenticated repository-access banner still remained visible after the writable connection completed. '
            'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
          );
        }

        if (!await app.isTopBarTextVisible(
          Ts1239RepositoryAccessGoldenFixture.writableLabel,
        )) {
          failures.add(
            'Human-style verification failed: the full-access state did not show the visible "${Ts1239RepositoryAccessGoldenFixture.writableLabel}" label in the top bar after reconnecting. '
            'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}.',
          );
        }

        await app.openSection('Settings');
        await _waitForCondition(
          tester,
          condition: () async =>
              await app.isTextVisible('Project Settings') &&
              await app.isTextVisible('Repository access'),
          failureMessage:
              'Step 5 failed: the connected flow did not reach the Settings repository-access surface needed for the scoped full-access golden. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
          failures: failures,
        );
        await _compareApprovedGolden(
          target: _settingsRepositoryAccessLabel(
            Ts1239RepositoryAccessGoldenFixture.writableLabel,
          ),
          approvedGoldenPath: _fullAccessGoldenPath,
          failureLabel:
              'Step 5 failed: the Settings repository-access state label no longer matches the approved golden baseline.',
          failures: failures,
        );

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        app.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(minutes: 3)),
  );
}

Future<void> _expectRepositoryAccessBannerState({
  required TrackStateAppComponent app,
  required List<String> failures,
  required String topBarLabel,
  required String title,
  required String message,
  required String actionLabel,
  required String stepLabel,
}) async {
  if (!await app.isRepositoryAccessBannerVisible(
    title: title,
    message: message,
  )) {
    failures.add(
      '$stepLabel failed: the repository-access banner for "$title" was not visible. '
      'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
      'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
    );
  }

  if (!_snapshotContains(app.topBarVisibleTextsSnapshot(), topBarLabel) &&
      !_snapshotContains(app.visibleSemanticsLabelsSnapshot(), topBarLabel)) {
    failures.add(
      '$stepLabel failed: the top bar did not expose the expected "$topBarLabel" access-mode label. '
      'Top bar texts: ${_formatSnapshot(app.topBarVisibleTextsSnapshot())}. '
      'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
    );
  }

  for (final text in <String>[title, message, actionLabel]) {
    if (!await app.isRepositoryAccessBannerTextVisible(
      title: title,
      message: message,
      text: text,
    )) {
      failures.add(
        '$stepLabel failed: the repository-access banner for "$title" did not visibly render "$text". '
        'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
      );
    }
  }
}

Finder _repositoryAccessBanner(String title, {required String message}) =>
    find.byWidgetPredicate(
      (widget) =>
          widget is Semantics &&
          widget.properties.label == '$title $title $message',
      description: 'repository-access banner "$title"',
    );

Finder _settingsRepositoryAccessLabel(String label) =>
    find.bySemanticsLabel(RegExp('^${RegExp.escape(label)}\$'));

Future<void> _openRepositoryAccessDialog({
  required TrackStateAppComponent app,
  required List<String> failures,
  required String stepLabel,
  required String bannerTitle,
  required String bannerMessage,
  required String actionLabel,
  required String expectedDialogTitle,
}) async {
  final opened = await app.tapRepositoryAccessBannerAction(
    title: bannerTitle,
    message: bannerMessage,
    actionLabel: actionLabel,
  );
  if (!opened) {
    failures.add(
      '$stepLabel failed: tapping the visible "$actionLabel" CTA did not open the repository-access dialog. '
      'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
    );
    return;
  }

  final dialogVisible =
      await app.isDialogTextVisible(expectedDialogTitle) &&
      await app.isTextFieldVisible('Fine-grained token') &&
      await app.isDialogTextVisible('Connect token');
  if (!dialogVisible) {
    failures.add(
      '$stepLabel failed: the repository-access dialog did not expose the expected token-entry controls. '
      'Visible dialog texts: ${_formatSnapshot(app.visibleDialogTextsSnapshot())}. '
      'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
    );
  }
}

Future<void> _submitHostedAccessToken(
  WidgetTester tester, {
  required TrackStateAppComponent app,
  required String token,
  required String stepLabel,
  required List<String> failures,
}) async {
  if (!await app.isTextFieldVisible('Fine-grained token')) {
    failures.add(
      '$stepLabel failed: the token field was not visible before entering "$token". '
      'Visible dialog texts: ${_formatSnapshot(app.visibleDialogTextsSnapshot())}.',
    );
    return;
  }

  await app.enterLabeledTextField('Fine-grained token', text: token);

  if (!await app.isDialogTextVisible('Connect token')) {
    failures.add(
      '$stepLabel failed: the "Connect token" action disappeared after entering the token. '
      'Visible dialog texts: ${_formatSnapshot(app.visibleDialogTextsSnapshot())}.',
    );
    return;
  }

  await app.tapDialogControlWithoutSettling('Connect token');
  await tester.pump();
}

void _expectReadOnlyBannerWrapsAcrossMultipleLines(
  WidgetTester tester, {
  required String message,
  required List<String> failures,
}) {
  final finder = find.text(message, findRichText: true);
  if (finder.evaluate().isEmpty) {
    failures.add(
      'Step 4 failed: the read-only banner message was not present in the rendered UI, so its wrapped layout could not be inspected.',
    );
    return;
  }

  final RenderParagraph renderParagraph = tester.renderObject<RenderParagraph>(
    finder.first,
  );
  final boxes = renderParagraph.getBoxesForSelection(
    TextSelection(baseOffset: 0, extentOffset: message.length),
  );
  final distinctLineTops = boxes
      .map((box) => box.top.toStringAsFixed(1))
      .toSet()
      .length;
  if (distinctLineTops < 2) {
    failures.add(
      'Human-style verification failed: the read-only repository-access message did not wrap across multiple visible lines at the required 1440x960 viewport. '
      'Observed line count: $distinctLineTops.',
    );
  }
}

void _expectNoFrameworkOverflowErrors(
  WidgetTester tester, {
  required String stepLabel,
  required List<String> failures,
  required List<String> visibleTexts,
  required List<String> visibleSemantics,
}) {
  final errors = _drainFrameworkErrors(tester);
  if (errors.isEmpty) {
    return;
  }

  failures.add(
    '$stepLabel failed: the repository-access flow raised framework errors instead of rendering cleanly. '
    'Observed errors: ${errors.join(' || ')}. '
    'Visible texts: ${_formatSnapshot(visibleTexts)}. '
    'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
  );
}

void _expectViewport(
  WidgetTester tester, {
  required List<String> failures,
  required String stepLabel,
}) {
  final viewport = Size(
    tester.view.physicalSize.width,
    tester.view.physicalSize.height,
  );
  if (viewport != _requiredViewport) {
    failures.add(
      '$stepLabel failed: the widget test rendered at ${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)} instead of the required '
      '${_requiredViewport.width.toStringAsFixed(0)}x${_requiredViewport.height.toStringAsFixed(0)} viewport.',
    );
  }
}

Future<void> _compareApprovedGolden({
  required Finder target,
  required String approvedGoldenPath,
  required String failureLabel,
  required List<String> failures,
}) async {
  if (target.evaluate().isEmpty) {
    failures.add(
      '$failureLabel The expected production-visible golden target was not present in the rendered UI.',
    );
    return;
  }

  try {
    await expectLater(
      target,
      matchesGoldenFile(approvedGoldenPath),
      reason: failureLabel,
    );
  } on TestFailure catch (error) {
    failures.add('$failureLabel $error');
  }
}

Future<void> _waitForCondition(
  WidgetTester tester, {
  required Future<bool> Function() condition,
  required String failureMessage,
  required List<String> failures,
  Duration timeout = const Duration(seconds: 10),
  Duration step = const Duration(milliseconds: 100),
}) async {
  final deadline = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(deadline)) {
    if (await condition()) {
      return;
    }
    await tester.pump(step);
  }
  failures.add(failureMessage);
}

bool _snapshotContains(List<String> snapshot, String text) {
  return snapshot.any((entry) => entry.contains(text));
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

List<String> _drainFrameworkErrors(WidgetTester tester) {
  final errors = <String>[];
  while (true) {
    final error = tester.takeException();
    if (error == null) {
      break;
    }
    errors.add(error.toString());
  }
  return errors;
}
