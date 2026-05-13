import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-605 Tab navigation from the fine-grained token field reaches Remember and Connect in order',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final failures = <String>[];

      try {
        for (final scenario in _scenarios) {
          await robot.pumpApp(
            repository: ReactiveIssueDetailTrackStateRepository(
              permission: scenario.permission,
            ),
            sharedPreferences: <String, Object>{
              _hostedTokenKey: 'ts605-${scenario.id}-token',
            },
          );
          await robot.openSettings();

          final visibleTexts = _formatSnapshot(robot.visibleTexts());
          for (final requiredText in <String>[
            'Project Settings',
            'Repository access',
            scenario.statusTitle,
            'Fine-grained token',
            'Remember on this browser',
            'Connect token',
          ]) {
            if (!robot.isVisibleText(requiredText)) {
              failures.add(
                'Step 1 failed for ${scenario.name}: the hosted repository-access surface did not keep the visible "$requiredText" text on screen. '
                'Visible texts: $visibleTexts.',
              );
            }
          }

          final focusCandidates = <String, Finder>{
            'Fine-grained token': robot.labeledTextField('Fine-grained token'),
            'Remember on this browser': robot.checkboxTile(
              'Remember on this browser',
            ),
            'Connect token': robot.actionButton('Connect token'),
          };

          for (final entry in focusCandidates.entries) {
            if (entry.value.evaluate().isEmpty) {
              failures.add(
                'Precondition failed for ${scenario.name}: the visible "${entry.key}" control was not rendered, so keyboard traversal could not be verified. '
                'Visible texts: $visibleTexts.',
              );
            }
          }
          if (failures.any((failure) => failure.contains(scenario.name))) {
            continue;
          }

          await robot.clearFocus();
          await robot.focusTextField('Fine-grained token');
          final initialFocus = robot.focusedLabel(focusCandidates);
          if (initialFocus != 'Fine-grained token') {
            failures.add(
              'Step 2 failed for ${scenario.name}: focusing the visible Fine-grained token field did not leave keyboard focus in that field. '
              'Observed focus: ${_focusedLabelOrOutside(initialFocus)}.',
            );
            continue;
          }

          final observedFocusSequence = <String>[initialFocus];
          await tester.sendKeyEvent(LogicalKeyboardKey.tab);
          await tester.pump();
          final firstTabFocus = robot.focusedLabel(focusCandidates);
          observedFocusSequence.add(_focusedLabelOrOutside(firstTabFocus));
          if (firstTabFocus != 'Remember on this browser') {
            failures.add(
              'Step 4 failed for ${scenario.name}: after pressing Tab from the Fine-grained token field, focus did not move to the visible Remember on this browser checkbox. '
              'Observed focus sequence: ${observedFocusSequence.join(' -> ')}.',
            );
            continue;
          }

          await tester.sendKeyEvent(LogicalKeyboardKey.tab);
          await tester.pump();
          final secondTabFocus = robot.focusedLabel(focusCandidates);
          observedFocusSequence.add(_focusedLabelOrOutside(secondTabFocus));
          if (secondTabFocus != 'Connect token') {
            await tester.sendKeyEvent(LogicalKeyboardKey.tab);
            await tester.pump();
            observedFocusSequence.add(
              _focusedLabelOrOutside(robot.focusedLabel(focusCandidates)),
            );
            failures.add(
              'Step 6 failed for ${scenario.name}: after pressing Tab again, focus did not move to the visible Connect token button. '
              'Observed focus sequence: ${observedFocusSequence.join(' -> ')}.',
            );
            continue;
          }

          if (!robot.isVisibleText('Remember on this browser') ||
              !robot.isVisibleText('Connect token')) {
            failures.add(
              'Human-style verification failed for ${scenario.name}: the Remember on this browser and Connect token controls were not both visibly present while tabbing through Repository access. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}.',
            );
          }
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

const String _hostedTokenKey = 'trackstate.githubToken.trackstate.trackstate';

const List<_Ts605Scenario> _scenarios = <_Ts605Scenario>[
  _Ts605Scenario(
    id: 'fully-available',
    name: 'fully available hosted uploads',
    statusTitle: 'Connected',
    permission: RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: true,
      attachmentUploadMode: AttachmentUploadMode.full,
      canCheckCollaborators: false,
    ),
  ),
  _Ts605Scenario(
    id: 'limited',
    name: 'limited hosted uploads',
    statusTitle: 'Some attachment uploads still require local Git',
    permission: RepositoryPermission(
      canRead: true,
      canWrite: true,
      isAdmin: false,
      canCreateBranch: true,
      canManageAttachments: true,
      attachmentUploadMode: AttachmentUploadMode.noLfs,
      canCheckCollaborators: false,
    ),
  ),
];

class _Ts605Scenario {
  const _Ts605Scenario({
    required this.id,
    required this.name,
    required this.statusTitle,
    required this.permission,
  });

  final String id;
  final String name;
  final String statusTitle;
  final RepositoryPermission permission;
}

String _focusedLabelOrOutside(String? label) => label ?? '<outside candidates>';

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
