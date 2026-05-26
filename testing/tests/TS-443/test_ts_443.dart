import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-448/support/ts448_mandatory_bootstrap_rate_limit_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-443 GitHub rate-limit during mandatory bootstrap creates startup recovery metadata and recovery actions',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];

      try {
        for (final artifact in Ts448MandatoryBootstrapArtifact.values) {
          final scenario = switch (artifact) {
            Ts448MandatoryBootstrapArtifact.projectJson =>
              'TRACK/project.json mandatory bootstrap',
            Ts448MandatoryBootstrapArtifact.issuesIndex =>
              'TRACK/.trackstate/index/issues.json mandatory bootstrap',
          };

          final metadataFixture =
              await Ts448MandatoryBootstrapRateLimitFixture.create(
                artifact: artifact,
              );
          final loadStartedAt = DateTime.now().toUtc();
          final viewModel = TrackerViewModel(
            repository: metadataFixture.repository,
          );
          await viewModel.load();
          final loadFinishedAt = DateTime.now().toUtc();

          if (metadataFixture.requestCount(
                metadataFixture.failingRequestPath,
              ) !=
              1) {
            failures.add(
              'Step 1 failed for $scenario: the mocked hosted bootstrap did not exercise exactly one 403 rate-limit response for ${metadataFixture.failingContentPath}. '
              'Observed requests: ${_formatSnapshot(metadataFixture.requestedPaths)}.',
            );
          }

          final recovery = viewModel.startupRecovery;
          if (recovery == null) {
            failures.add(
              'Step 3 failed for $scenario: TrackerViewModel.load() did not publish startupRecovery metadata after the mandatory bootstrap GitHub rate-limit response. '
              'Message=${viewModel.message}, snapshot=${viewModel.snapshot == null ? 'null' : 'present'}.',
            );
          } else {
            if (recovery.kind != TrackerStartupRecoveryKind.githubRateLimit) {
              failures.add(
                'Expected Result failed for $scenario: startupRecovery.kind was ${recovery.kind} instead of TrackerStartupRecoveryKind.githubRateLimit.',
              );
            }
            if (recovery.failedPath != metadataFixture.failingRequestPath) {
              failures.add(
                'Step 3 failed for $scenario: startupRecovery.failedPath was "${recovery.failedPath ?? '<missing>'}" instead of the blocked bootstrap request "${metadataFixture.failingRequestPath}".',
              );
            }

            final retryAfter = recovery.retryAfter;
            final earliestExpected = loadStartedAt.add(
              const Duration(seconds: 55),
            );
            final latestExpected = loadFinishedAt.add(
              const Duration(seconds: 65),
            );
            if (retryAfter == null) {
              failures.add(
                'Step 3 failed for $scenario: startupRecovery.retryAfter was missing, so the blocking rate-limit recovery did not expose a valid reset time.',
              );
            } else if (retryAfter.isBefore(earliestExpected) ||
                retryAfter.isAfter(latestExpected)) {
              failures.add(
                'Step 3 failed for $scenario: startupRecovery.retryAfter was $retryAfter, outside the expected retry window ${earliestExpected.toIso8601String()} - ${latestExpected.toIso8601String()} derived from the mocked retry-after: 60 header.',
              );
            }
          }

          if (viewModel.message != null) {
            failures.add(
              'Expected Result failed for $scenario: TrackerViewModel reported a generic load message instead of relying on startupRecovery metadata. '
              'Observed message kind=${viewModel.message!.kind}, error=${viewModel.message!.error ?? '<none>'}.',
            );
          }

          if (viewModel.snapshot != null) {
            failures.add(
              'Step 3 failed for $scenario: mandatory bootstrap recovery should remain in the blocking bootstrap phase, but TrackerViewModel published a bootstrap snapshot instead of keeping snapshot null.',
            );
          }

          if (viewModel.hasLoadedInitialSearchResults) {
            failures.add(
              'Precondition failed for $scenario: the initial search completed even though mandatory bootstrap failed before search hydration should start.',
            );
          }
          if (viewModel.hasPublishedBootstrapSnapshot) {
            failures.add(
              'Step 3 failed for $scenario: mandatory bootstrap should remain blocked before publishing a bootstrap snapshot, but hasPublishedBootstrapSnapshot was true.',
            );
          }
          if (viewModel.showsInitialBootstrapPlaceholders) {
            failures.add(
              'Step 3 failed for $scenario: blocking mandatory bootstrap should not expose partial placeholder content, but showsInitialBootstrapPlaceholders was true.',
            );
          }
          if (viewModel.shouldUseBootstrapSearchFallback) {
            failures.add(
              'Step 3 failed for $scenario: blocking mandatory bootstrap should not publish fallback bootstrap search data, but shouldUseBootstrapSearchFallback was true.',
            );
          }
          if (!viewModel.supportsGitHubAuth) {
            failures.add(
              'Expected Result failed for $scenario: the hosted recovery model did not advertise GitHub auth support, so the Connect GitHub recovery action was unavailable on the model surface.',
            );
          }
          if (viewModel.repositoryAccessState !=
              RepositoryAccessState.connectGitHub) {
            failures.add(
              'Expected Result failed for $scenario: repositoryAccessState was ${viewModel.repositoryAccessState} instead of RepositoryAccessState.connectGitHub while startup recovery was active.',
            );
          }

          final blockingDomainStates = {
            for (final domain in TrackerDataDomain.values)
              domain: viewModel.loadStateForDomain(domain),
          };
          final blockingSectionStates = {
            for (final section in TrackerSection.values)
              section: viewModel.loadStateForSection(section),
          };
          for (final entry in blockingDomainStates.entries) {
            if (entry.value != TrackerLoadState.loading) {
              failures.add(
                'Step 3 failed for $scenario: mandatory bootstrap recovery should keep ${entry.key} in TrackerLoadState.loading, but observed ${entry.value}. '
                'Observed readiness: ${_formatReadiness(blockingDomainStates, blockingSectionStates)}.',
              );
            }
          }
          for (final entry in blockingSectionStates.entries) {
            if (entry.value != TrackerLoadState.loading) {
              failures.add(
                'Step 3 failed for $scenario: mandatory bootstrap recovery should keep ${entry.key} in TrackerLoadState.loading, but observed ${entry.value}. '
                'Observed readiness: ${_formatReadiness(blockingDomainStates, blockingSectionStates)}.',
              );
            }
          }

          await viewModel.retryStartupRecovery();

          if (metadataFixture.requestCount(
                metadataFixture.failingRequestPath,
              ) !=
              2) {
            failures.add(
              'Expected Result failed for $scenario: invoking the model-level Retry recovery action did not re-run the blocked bootstrap request exactly once. '
              'Observed requests: ${_formatSnapshot(metadataFixture.requestedPaths)}.',
            );
          }
          if (viewModel.startupRecovery != null) {
            failures.add(
              'Expected Result failed for $scenario: retryStartupRecovery() should clear startupRecovery after the second bootstrap attempt succeeded, but recovery remained ${viewModel.startupRecovery}.',
            );
          }
          if (viewModel.snapshot == null ||
              !viewModel.hasPublishedBootstrapSnapshot) {
            failures.add(
              'Expected Result failed for $scenario: retryStartupRecovery() did not publish a bootstrap snapshot after the hosted rate-limit fixture recovered.',
            );
          }

          final uiFixture =
              await Ts448MandatoryBootstrapRateLimitFixture.create(
                artifact: artifact,
              );
          final TrackStateAppComponent app = defaultTestingDependencies
              .createTrackStateAppScreen(tester);
          await app.pump(uiFixture.repository);

          const expectedTitle = 'GitHub startup limit reached';
          const expectedMessage =
              'Hosted startup hit GitHub\'s rate limit before TrackState finished loading the required repository data. Retry later or connect GitHub for a higher limit. TrackState will retry once after GitHub authentication succeeds.';

          if (!await app.isTextVisible('TrackState.AI')) {
            failures.add(
              'Human-style verification failed for $scenario: the recovery screen did not keep the product title visible. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
            );
          }
          if (!await app.isTextVisible(expectedTitle)) {
            failures.add(
              'Human-style verification failed for $scenario: the blocking recovery title "$expectedTitle" was not visible to the user. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
            );
          }
          if (!await app.isTextVisible(expectedMessage)) {
            failures.add(
              'Human-style verification failed for $scenario: the blocking recovery body text did not match the expected mandatory-bootstrap rate-limit wording. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
            );
          }
          for (final requiredAction in const ['Retry', 'Connect GitHub']) {
            if (!await app.isTextVisible(requiredAction) &&
                !await app.isSemanticsLabelVisible(requiredAction)) {
              failures.add(
                'Human-style verification failed for $scenario: the recovery surface did not expose the "$requiredAction" action to the user. '
                'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
              );
            }
          }
          if (await app.isTextVisible('TrackState data was not found.')) {
            failures.add(
              'Expected Result failed for $scenario: the UI surfaced the generic data-load-failed banner instead of the dedicated startup recovery state.',
            );
          }

          final openedDialog = await app.tapVisibleControl('Connect GitHub');
          if (!openedDialog) {
            failures.add(
              'Human-style verification failed for $scenario: the visible Connect GitHub action was not tappable.',
            );
          } else {
            await tester.pumpAndSettle();
            final dialogVisible =
                await app.isTextVisible('Fine-grained token') &&
                await app.isTextVisible('Connect token');
            if (!dialogVisible) {
              failures.add(
                'Human-style verification failed for $scenario: tapping Connect GitHub did not open the expected repository access dialog. '
                'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
              );
            } else {
              await app.tapVisibleControl('Cancel');
              await tester.pumpAndSettle();
            }
          }

          final retried = await app.tapVisibleControl('Retry');
          if (!retried) {
            failures.add(
              'Human-style verification failed for $scenario: the visible Retry action was not tappable.',
            );
          } else {
            await _waitForCondition(
              tester,
              condition: () async =>
                  !await app.isTextVisible(expectedTitle) &&
                  await app.isTextVisible('Dashboard'),
              failureMessage:
                  'Human-style verification failed for $scenario: Retry did not recover from the blocking startup recovery state. '
                  'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
            );
          }

          app.resetView();
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
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

String _formatReadiness(
  Map<TrackerDataDomain, TrackerLoadState> domainStates,
  Map<TrackerSection, TrackerLoadState> sectionStates,
) {
  final domains = domainStates.entries
      .map((entry) => '${entry.key.name}=${entry.value.name}')
      .join(', ');
  final sections = sectionStates.entries
      .map((entry) => '${entry.key.name}=${entry.value.name}')
      .join(', ');
  return 'domains[$domains]; sections[$sections]';
}
