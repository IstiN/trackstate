import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../fixtures/workspace_onboarding_screen_fixture.dart';
import '../TS-704/support/ts704_hosted_workspace_runtime.dart';

const String _ticketKey = 'TS-702';
const String _ticketSummary =
    'Returning user entry point keeps Add workspace visible in the active shell';
const String _testFilePath = 'testing/tests/TS-702/test_ts_702.dart';
const String _runCommand =
    'flutter test testing/tests/TS-702/test_ts_702.dart --reporter expanded';
const String _currentWorkspaceRepository = 'owner/current';
const String _currentWorkspaceBranch = 'main';
const String _currentWorkspaceDisplayName = 'Current workspace';

const List<String> _requestSteps = <String>[
  'Launch the application.',
  'Inspect the top app bar or the area adjacent to the workspace switcher.',
  "Click the 'Add workspace' action.",
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-702 returning users can open onboarding from the persistent Add workspace action',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'test_file_path': _testFilePath,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      SharedPreferences.setMockInitialValues(const <String, Object>{});
      final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 14, 19, 45),
      );
      final openedRepositories = <String>[];

      Future<TrackStateRepository> openHostedRepository({
        required String repository,
        required String defaultBranch,
        required String writeBranch,
      }) async {
        openedRepositories.add('$repository@$defaultBranch@$writeBranch');
        return Ts704HostedWorkspaceRepository(
          snapshot: await createTs704Snapshot(
            repository: repository,
            branch: defaultBranch,
          ),
          provider: Ts704HostedProvider(
            repositoryName: repository,
            branch: defaultBranch,
          ),
        );
      }

      await workspaceProfileService.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: _currentWorkspaceRepository,
          defaultBranch: _currentWorkspaceBranch,
          displayName: _currentWorkspaceDisplayName,
        ),
      );

      final bootstrapSnapshot = await createTs704Snapshot(
        repository: 'bootstrap/bootstrap',
        branch: 'main',
      );

      final screen = await launchWorkspaceOnboardingFixture(
        tester,
        repositoryFactory: () => Ts704HostedWorkspaceRepository(
          snapshot: bootstrapSnapshot,
          provider: Ts704HostedProvider(
            repositoryName: 'bootstrap/bootstrap',
            branch: 'main',
          ),
        ),
        workspaceProfileService: workspaceProfileService,
        openHostedRepository: openHostedRepository,
      );

      try {
        final initialState = screen.captureState();
        result['initial_visible_texts'] = initialState.visibleTexts;
        result['initial_interactive_semantics_labels'] =
            initialState.interactiveSemanticsLabels;
        result['initial_repository_access_label'] =
            initialState.repositoryAccessTopBarLabel;
        result['opened_repositories'] = openedRepositories;

        if (openedRepositories.isEmpty ||
            openedRepositories.first !=
                '$_currentWorkspaceRepository@$_currentWorkspaceBranch@$_currentWorkspaceBranch' ||
            !initialState.isDashboardVisible) {
          throw AssertionError(
            'Precondition failed: the returning-user app shell did not open the stored active workspace before verifying the persistent Add workspace action.\n'
            'Observed opened repositories: ${_formatList(openedRepositories)}\n'
            'Observed dashboard visible: ${initialState.isDashboardVisible}\n'
            'Observed visible texts: ${_formatList(initialState.visibleTexts)}',
          );
        }

        final addWorkspaceFinder = _addWorkspaceControl();
        final workspaceSwitcherFinder = find.byKey(
          const ValueKey<String>('workspace-switcher-trigger'),
        );
        result['has_add_workspace_visible_text'] = initialState.visibleTexts
            .contains('Add workspace');

        if (addWorkspaceFinder.evaluate().isEmpty ||
            workspaceSwitcherFinder.evaluate().isEmpty ||
            !_containsSemanticLabel(
              initialState.interactiveSemanticsLabels,
              'Add workspace',
            ) ||
            !_containsSemanticLabel(
              initialState.interactiveSemanticsLabels,
              'Workspace switcher:',
            ) ||
            !_containsSemanticLabel(
              initialState.interactiveSemanticsLabels,
              _currentWorkspaceDisplayName,
            )) {
          throw AssertionError(
            'Step 1 failed: launching the application as a returning user did not render the expected active shell with both Add workspace and the workspace switcher available.\n'
            'Observed opened repositories: ${_formatList(openedRepositories)}\n'
            'Observed dashboard visible: ${initialState.isDashboardVisible}\n'
            "Observed Add workspace visible text: ${result['has_add_workspace_visible_text']}\n"
            'Observed visible texts: ${_formatList(initialState.visibleTexts)}\n'
            'Observed interactive semantics labels: ${_formatList(initialState.interactiveSemanticsLabels)}',
          );
        }
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action: _requestSteps[0],
          observed:
              'dashboard_visible=${initialState.isDashboardVisible}; opened_repositories=${_formatList(openedRepositories)}; visible_texts=${_formatList(initialState.visibleTexts)}',
        );

        final addWorkspaceRect = tester.getRect(addWorkspaceFinder.first);
        final workspaceSwitcherRect = tester.getRect(workspaceSwitcherFinder);
        final sharedTopBarRow = _sharesTopBarRow(
          addWorkspaceFinder.first,
          workspaceSwitcherFinder,
        );
        final verticalDelta =
            (addWorkspaceRect.center.dy - workspaceSwitcherRect.center.dy)
                .abs();
        final horizontalGap =
            workspaceSwitcherRect.left - addWorkspaceRect.right;
        final addWorkspaceBeforeSwitcher =
            addWorkspaceRect.center.dx < workspaceSwitcherRect.center.dx;

        result['shell_layout'] = <String, Object?>{
          'shared_top_bar_row': sharedTopBarRow,
          'vertical_center_delta': verticalDelta,
          'horizontal_gap': horizontalGap,
          'add_workspace_before_switcher': addWorkspaceBeforeSwitcher,
          'add_workspace_rect': _rectAsMap(addWorkspaceRect),
          'workspace_switcher_rect': _rectAsMap(workspaceSwitcherRect),
        };

        if (!sharedTopBarRow ||
            verticalDelta > 4 ||
            horizontalGap < 0 ||
            horizontalGap > 24 ||
            !addWorkspaceBeforeSwitcher) {
          throw AssertionError(
            'Step 2 failed: the persistent Add workspace action was not rendered beside the workspace switcher in the primary shell controls.\n'
            'Observed shared top-bar row: $sharedTopBarRow\n'
            'Observed vertical center delta: $verticalDelta\n'
            'Observed horizontal gap: $horizontalGap\n'
            'Observed add-workspace-before-switcher: $addWorkspaceBeforeSwitcher\n'
            'Observed add workspace rect: ${_rectAsMap(addWorkspaceRect)}\n'
            'Observed workspace switcher rect: ${_rectAsMap(workspaceSwitcherRect)}',
          );
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action: _requestSteps[1],
          observed:
              'shared_top_bar_row=$sharedTopBarRow; vertical_center_delta=$verticalDelta; horizontal_gap=$horizontalGap; add_workspace_before_switcher=$addWorkspaceBeforeSwitcher',
        );

        await screen.openAddWorkspace();

        final onboardingState = screen.captureState();
        result['post_click_visible_texts'] = onboardingState.visibleTexts;
        result['post_click_interactive_semantics_labels'] =
            onboardingState.interactiveSemanticsLabels;
        result['post_click_primary_action_label'] =
            onboardingState.primaryActionLabel;
        final onboardingChoices = _observedOnboardingChoices(
          onboardingState.visibleTexts,
        );
        result['post_click_onboarding_choices'] = onboardingChoices;

        if (!onboardingState.isOnboardingVisible ||
            !onboardingState.visibleTexts.contains('Add workspace') ||
            onboardingChoices.isEmpty) {
          throw AssertionError(
            "Step 3 failed: clicking the 'Add workspace' action did not route the returning user to the onboarding screen.\n"
            'Observed onboarding visible: ${onboardingState.isOnboardingVisible}\n'
            'Observed onboarding choices: ${_formatList(onboardingChoices)}\n'
            'Observed visible texts: ${_formatList(onboardingState.visibleTexts)}\n'
            'Observed interactive semantics labels: ${_formatList(onboardingState.interactiveSemanticsLabels)}',
          );
        }
        _recordStep(
          result,
          step: 3,
          status: 'passed',
          action: _requestSteps[2],
          observed:
              'onboarding_visible=${onboardingState.isOnboardingVisible}; onboarding_choices=${_formatList(onboardingChoices)}; visible_texts=${_formatList(onboardingState.visibleTexts)}',
        );

        _recordHumanVerification(
          result,
          check:
              'Viewed the returning-user shell exactly as a user would see it after launch and checked the top app bar controls.',
          observed:
              'visible_texts=${_formatList(initialState.visibleTexts)}; interactive_semantics_labels=${_formatList(initialState.interactiveSemanticsLabels)}; shell_layout=${jsonEncode(result['shell_layout'])}',
        );
        _recordHumanVerification(
          result,
          check:
              "Clicked 'Add workspace' from the shell and verified the onboarding heading and entry actions a user would see next.",
          observed:
              'visible_texts=${_formatList(onboardingState.visibleTexts)}; interactive_semantics_labels=${_formatList(onboardingState.interactiveSemanticsLabels)}',
        );

        print('TS-702-OBSERVATION:${jsonEncode(result)}');
      } finally {
        screen.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Finder _addWorkspaceControl() {
  final button = find.ancestor(
    of: find.text('Add workspace'),
    matching: find.bySubtype<ButtonStyleButton>(),
  );
  if (button.evaluate().isNotEmpty) {
    return button.first;
  }
  return find.bySemanticsLabel(RegExp('^Add workspace\$')).first;
}

bool _containsSemanticLabel(List<String> labels, String fragment) {
  return labels.any((label) => label.contains(fragment));
}

bool _sharesTopBarRow(Finder left, Finder right) {
  final leftRows = find
      .ancestor(of: left, matching: find.byType(Row))
      .evaluate();
  final rightRows = find
      .ancestor(of: right, matching: find.byType(Row))
      .evaluate();
  for (final leftRow in leftRows) {
    for (final rightRow in rightRows) {
      if (identical(leftRow, rightRow)) {
        return true;
      }
    }
  }
  return false;
}

Map<String, double> _rectAsMap(Rect rect) => <String, double>{
  'left': rect.left,
  'top': rect.top,
  'right': rect.right,
  'bottom': rect.bottom,
  'width': rect.width,
  'height': rect.height,
};

void _recordStep(
  Map<String, Object?> result, {
  required int step,
  required String status,
  required String action,
  required String observed,
}) {
  final steps =
      result.putIfAbsent('steps', () => <Map<String, Object?>>[])
          as List<Map<String, Object?>>;
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
  final checks =
      result.putIfAbsent('human_verification', () => <Map<String, Object?>>[])
          as List<Map<String, Object?>>;
  checks.add(<String, Object?>{'check': check, 'observed': observed});
}

String _formatList(List<Object?> values) {
  if (values.isEmpty) {
    return '<empty>';
  }
  return values.map((value) => value.toString()).join(' | ');
}

List<String> _observedOnboardingChoices(List<String> visibleTexts) {
  const knownChoices = <String>[
    'Local folder',
    'Hosted repository',
    'Open existing folder',
    'Initialize folder',
  ];
  return knownChoices
      .where((choice) => visibleTexts.contains(choice))
      .toList(growable: false);
}
