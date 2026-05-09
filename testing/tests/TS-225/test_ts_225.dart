import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts225_local_git_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-225 keeps Local Git UI state and provider semantics after malformed fields config',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      Ts225LocalGitFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts225LocalGitFixture.create);
        if (fixture == null) {
          throw StateError('TS-225 fixture creation did not complete.');
        }

        final initialStatus =
            await tester.runAsync(fixture.worktreeStatusLines) ?? <String>[];
        expect(
          initialStatus,
          isEmpty,
          reason:
              'TS-225 requires a clean Local Git repository before launching '
              'the malformed fields.json scenario, but `git status --short` '
              'returned ${initialStatus.join(' | ')}.',
        );

        final malformedFieldsContents =
            await tester.runAsync(
              () => fixture!.readRepositoryFile('DEMO/config/fields.json'),
            ) ??
            '';
        expect(
          malformedFieldsContents,
          contains(
            '{"id":"summary","name":"Summary","type":"string","required":true}',
          ),
          reason:
              'TS-225 must exercise a malformed DEMO/config/fields.json fixture.',
        );
        expect(
          malformedFieldsContents,
          isNot(contains(',\n  {"id":"description"')),
          reason:
              'TS-225 must keep DEMO/config/fields.json syntactically invalid '
              'by omitting the comma between the Summary and Description '
              'entries.',
        );

        await screen.pump(
          createTrackStateRepository(
            runtime: TrackStateRuntime.localGit,
            localRepositoryPath: fixture.repositoryPath,
          ),
        );
        await screen.waitWithoutInteraction(const Duration(seconds: 2));

        final parseErrorLogged = await _waitForLoggedParseError(screen, tester);
        final frameworkException = tester.takeException();
        final localGitVisible =
            await screen.isSemanticsLabelVisible('Local Git') ||
            await screen.isTextVisible('Local Git');
        final localGitTopBarVisible =
            await screen.isTopBarSemanticsLabelVisible('Local Git') ||
            await screen.isTopBarTextVisible('Local Git');
        final connectGitHubVisible =
            await screen.isSemanticsLabelVisible('Connect GitHub') ||
            await screen.isTextVisible('Connect GitHub');
        final topBarTrackStateAiVisible =
            await screen.isTopBarSemanticsLabelVisible('TrackState.AI') ||
            await screen.isTopBarTextVisible('TrackState.AI');
        final topBarSnapshot = screen.topBarVisibleTextsSnapshot();

        if (!parseErrorLogged ||
            frameworkException != null ||
            !localGitVisible ||
            !localGitTopBarVisible ||
            connectGitHubVisible ||
            topBarTrackStateAiVisible) {
          fail(
            'Step 2 failed: launching the app with malformed '
            'DEMO/config/fields.json did not preserve the required Local Git '
            'runtime context. Parse error reported=${parseErrorLogged ? 'yes' : 'no'}, '
            'framework exception=${frameworkException ?? '<none>'}, '
            'Local Git visible=${localGitVisible ? 'yes' : 'no'}, '
            'top-bar Local Git visible=${localGitTopBarVisible ? 'yes' : 'no'}, '
            'Connect GitHub visible=${connectGitHubVisible ? 'yes' : 'no'}, '
            'top-bar TrackState.AI visible='
            '${topBarTrackStateAiVisible ? 'yes' : 'no'}. '
            'Top-bar texts: ${_formatSnapshot(topBarSnapshot)}. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: '
            '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.openRepositoryAccess();
        screen.expectLocalRuntimeDialog(
          repositoryPath: fixture.repositoryPath,
          branch: fixture.branch,
        );

        expect(
          tester.takeException(),
          isNull,
          reason:
              'Step 4 failed: opening the visible Local Git runtime dialog '
              'after the malformed configuration loaded surfaced a framework '
              'exception. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

Future<bool> _waitForLoggedParseError(
  TrackStateAppComponent screen,
  WidgetTester tester,
) async {
  final deadline = DateTime.now().add(const Duration(seconds: 8));
  while (DateTime.now().isBefore(deadline)) {
    if (await screen.isMessageBannerVisibleContaining('FormatException') ||
        await screen.isMessageBannerVisibleContaining('Unexpected character') ||
        _snapshotContainsParseError(screen.visibleTextsSnapshot()) ||
        _snapshotContainsParseError(screen.visibleSemanticsLabelsSnapshot())) {
      return true;
    }
    await tester.pump(const Duration(milliseconds: 200));
  }
  return await screen.isMessageBannerVisibleContaining('FormatException') ||
      await screen.isMessageBannerVisibleContaining('Unexpected character') ||
      _snapshotContainsParseError(screen.visibleTextsSnapshot()) ||
      _snapshotContainsParseError(screen.visibleSemanticsLabelsSnapshot());
}

bool _snapshotContainsParseError(List<String> values) {
  return values.any(
    (value) =>
        value.contains('FormatException') ||
        value.contains('Unexpected character'),
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
