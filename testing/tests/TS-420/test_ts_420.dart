import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts420_section_readiness_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-420 section readiness keeps Dashboard and Settings available while Search stays partial',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      const repository = Ts420SectionReadinessRepository();
      final snapshot = await repository.loadSnapshot();
      final bootstrapIssue = snapshot.issues.firstWhere(
        (issue) => !issue.hasDetailLoaded,
        orElse: () => throw StateError(
          'TS-420 precondition failed: the bootstrap snapshot did not expose an issue with deferred detail loading.',
        ),
      );

      try {
        expect(
          snapshot.readiness.domainState(TrackerDataDomain.projectMeta),
          TrackerLoadState.ready,
          reason:
              'Step 2 failed: projectMeta was not ready in the bootstrap readiness contract.',
        );
        expect(
          snapshot.readiness.domainState(TrackerDataDomain.issueSummaries),
          TrackerLoadState.ready,
          reason:
              'Step 2 failed: issueSummaries were not ready in the bootstrap readiness contract.',
        );
        expect(
          snapshot.readiness.domainState(TrackerDataDomain.issueDetails),
          TrackerLoadState.partial,
          reason:
              'Step 2 failed: issueDetails were not partial in the bootstrap readiness contract.',
        );
        expect(
          snapshot.readiness.sectionState(TrackerSectionKey.dashboard),
          TrackerLoadState.ready,
          reason:
              'Step 3 failed: Dashboard was not marked ready in the section readiness contract.',
        );
        expect(
          snapshot.readiness.sectionState(TrackerSectionKey.settings),
          TrackerLoadState.ready,
          reason:
              'Step 3 failed: Settings was not marked ready in the section readiness contract.',
        );
        expect(
          snapshot.readiness.sectionState(TrackerSectionKey.search),
          TrackerLoadState.partial,
          reason:
              'Step 5 failed: Search was not marked partial in the section readiness contract.',
        );

        await screen.pump(repository);

        await screen.expectNavigationControlEnabled('Dashboard');
        await screen.expectNavigationControlEnabled('Settings');
        await screen.expectNavigationControlEnabled('JQL Search');

        await screen.openSection('Settings');
        expect(
          await screen.isTextVisible('Project Settings'),
          isTrue,
          reason:
              'Step 4 failed: opening Settings did not render the visible "Project Settings" heading. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );
        expect(
          await screen.tapVisibleControl('Fields'),
          isTrue,
          reason:
              'Step 4 failed: the ready Settings surface did not expose an interactive "Fields" tab. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible('Summary'),
          isTrue,
          reason:
              'Step 4 failed: the Settings Fields tab did not render the visible "Summary" field definition after navigation. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );

        await screen.openSection('Dashboard');
        expect(
          await screen.isTextVisible('Open Issues'),
          isTrue,
          reason:
              'Step 4 failed: opening Dashboard did not render the visible "Open Issues" metric card. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );

        await screen.openSection('JQL Search');
        expect(
          await screen.isTextVisible('JQL Search'),
          isTrue,
          reason:
              'Step 5 failed: opening Search did not render the visible "JQL Search" heading. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Search issues'),
          isTrue,
          reason:
              'Step 5 failed: Search did not keep the visible "Search issues" field interactive while issue details were partial.',
        );
        expect(
          screen.visibleIssueSearchResultLabelsSnapshot(),
          contains('Open ${bootstrapIssue.key} ${bootstrapIssue.summary}'),
          reason:
              'Step 5 failed: Search did not keep the bootstrap-backed row for ${bootstrapIssue.key} visible while issue details were partial. '
              'Visible issue rows: ${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        await screen.openIssue(bootstrapIssue.key, bootstrapIssue.summary);
        expect(
          await screen.isSemanticsLabelVisible('Detail Loading...'),
          isTrue,
          reason:
              'Step 5 failed: Search did not expose the user-visible partial detail state for ${bootstrapIssue.key}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible('Loading...'),
          isTrue,
          reason:
              'Expected result failed: the Search detail panel did not keep a visible loading indicator while deferred issue details were still pending. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
        );
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
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
