import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-704/support/ts704_hosted_workspace_runtime.dart';

const String _ticketKey = 'TS-1354';
const String _ticketSummary =
    'Desktop Authentication UI — GitHub App OAuth button is hidden';
const String _testFilePath = 'testing/tests/TS-1354/test_ts_1354_runtime.dart';
const String _runCommand =
    'flutter test testing/tests/TS-1354/test_ts_1354_runtime.dart --dart-define=TRACKSTATE_GITHUB_APP_CLIENT_ID= --dart-define=TRACKSTATE_GITHUB_AUTH_PROXY_URL= --reporter expanded';
const List<String> _requestSteps = <String>[
  'Launch the desktop authentication screen for a hosted workspace.',
  'Verify the GitHub App OAuth control is not rendered.',
  'Verify the Personal Access Token controls and accessibility labels are present.',
];

const String _githubAppClientId = String.fromEnvironment(
  'TRACKSTATE_GITHUB_APP_CLIENT_ID',
);
const String _githubAuthProxyUrl = String.fromEnvironment(
  'TRACKSTATE_GITHUB_AUTH_PROXY_URL',
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-1354 desktop auth UI hides GitHub App OAuth and exposes PAT controls',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'test_file_path': _testFilePath,
        'github_app_client_id_defined': _githubAppClientId.isNotEmpty,
        'github_auth_proxy_url_defined': _githubAuthProxyUrl.isNotEmpty,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      try {
        final snapshot = await createTs704Snapshot(
          repository: 'owner/desktop-auth-test',
          branch: 'main',
        );
        final repository = Ts704HostedWorkspaceRepository(
          snapshot: snapshot,
          provider: Ts704HostedProvider(
            repositoryName: 'owner/desktop-auth-test',
            branch: 'main',
          ),
        );

        await screen.pump(repository);

        result['initial_visible_texts'] = screen.visibleTextsSnapshot();
        result['initial_semantics_labels'] = screen.visibleSemanticsLabelsSnapshot();

        final connectGitHubTapped = await screen.tapVisibleControl('Connect GitHub');
        result['connect_github_tapped'] = connectGitHubTapped;

        result['visible_dialog_texts'] = screen.visibleDialogTextsSnapshot();
        result['dialog_contains_connect_github'] =
            screen.visibleDialogTextsSnapshot().contains('Connect GitHub');

        final failures = <String>[];

        final step1Observed =
            'repository_pumped=true; connect_github_tapped=$connectGitHubTapped; initial_texts=${_formatList(screen.visibleTextsSnapshot())}; initial_semantics=${_formatList(screen.visibleSemanticsLabelsSnapshot())}; dialog_texts=${_formatList(screen.visibleDialogTextsSnapshot())}';
        final step1Passed =
            connectGitHubTapped &&
            screen.visibleDialogTextsSnapshot().contains('Connect GitHub');
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: step1Observed,
        );
        if (!step1Passed) {
          failures.add(
            'Step 1 failed: the hosted repository access dialog did not open.\n'
            'Observed: $step1Observed',
          );
        }

        final continueWithGitHubAppVisible = await screen.isDialogTextVisible(
          'Continue with GitHub App',
        );
        final continueWithGitHubAppBySemantics = await screen
            .isSemanticsLabelVisible('Continue with GitHub App');
        result['continue_with_github_app_visible'] =
            continueWithGitHubAppVisible;
        result['continue_with_github_app_semantics_visible'] =
            continueWithGitHubAppBySemantics;

        final step2Observed =
            'continue_with_github_app_visible=$continueWithGitHubAppVisible; '
            'continue_with_github_app_semantics_visible=$continueWithGitHubAppBySemantics; '
            'github_app_client_id_defined=${_githubAppClientId.isNotEmpty}; '
            'github_auth_proxy_url_defined=${_githubAuthProxyUrl.isNotEmpty}';
        final step2Passed =
            !continueWithGitHubAppVisible && !continueWithGitHubAppBySemantics;
        _recordStep(
          result,
          step: 2,
          status: step2Passed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: step2Observed,
        );
        if (!step2Passed) {
          failures.add(
            'Step 2 failed: the GitHub App OAuth control was rendered on the desktop auth screen.\n'
            'Observed: $step2Observed',
          );
        }

        final fineGrainedTokenFieldVisible = await screen.isTextFieldVisible(
          'Fine-grained token',
        );
        final fineGrainedTokenFieldCount = await screen.countLabeledTextFields(
          'Fine-grained token',
        );
        final connectTokenVisible = await screen.isDialogTextVisible(
          'Connect token',
        );
        final connectTokenBySemantics = await screen.isSemanticsLabelVisible(
          'Connect token',
        );
        result['fine_grained_token_field_visible'] = fineGrainedTokenFieldVisible;
        result['fine_grained_token_field_count'] = fineGrainedTokenFieldCount;
        result['connect_token_visible'] = connectTokenVisible;
        result['connect_token_semantics_visible'] = connectTokenBySemantics;

        final step3Observed =
            'fine_grained_token_field_visible=$fineGrainedTokenFieldVisible; '
            'fine_grained_token_field_count=$fineGrainedTokenFieldCount; '
            'connect_token_visible=$connectTokenVisible; '
            'connect_token_semantics_visible=$connectTokenBySemantics';
        final step3Passed =
            fineGrainedTokenFieldVisible &&
            fineGrainedTokenFieldCount == 1 &&
            connectTokenVisible &&
            connectTokenBySemantics;
        _recordStep(
          result,
          step: 3,
          status: step3Passed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: step3Observed,
        );
        if (!step3Passed) {
          failures.add(
            'Step 3 failed: the desktop auth screen did not expose the PAT/token controls with accessible labels.\n'
            'Observed: $step3Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the hosted repository access dialog the way a desktop user would and confirmed the OAuth option is absent while token entry remains available.',
          observed:
              'dialog_texts=${_formatList(screen.visibleDialogTextsSnapshot())}; '
              'github_app_oauth_visible=$continueWithGitHubAppVisible; '
              'pat_field_visible=$fineGrainedTokenFieldVisible; '
              'connect_button_visible=$connectTokenVisible',
        );

        print('TS-1354-OBSERVATION:${jsonEncode(result)}');

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }
      } finally {
        semantics.dispose();
      }
    },
  );
}

void _recordStep(
  Map<String, Object?> result, {
  required int step,
  required String status,
  required String action,
  required String observed,
}) {
  final steps = result['steps'] as List<Map<String, Object?>>;
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
  final checks = result['human_verification'] as List<Map<String, Object?>>;
  checks.add(<String, Object?>{
    'check': check,
    'observed': observed,
  });
}

String _formatList(List<String> values) {
  return values.isEmpty ? '<none>' : values.join(', ');
}
