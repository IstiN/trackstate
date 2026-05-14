import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service_io.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../fixtures/workspace_onboarding_screen_fixture.dart';
import 'support/ts717_ready_workspace_fixture.dart';

const String _ticketKey = 'TS-717';
const String _ticketSummary =
    'Local folder inspection recognizes a usable TrackState repository as ready';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-717 local folder inspection keeps a ready repository openable without writes',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final fixture = await tester.runAsync(Ts717ReadyWorkspaceFixture.create);
      if (fixture == null) {
        semantics.dispose();
        throw StateError('TS-717 fixture creation did not complete.');
      }
      addTearDown(() async {
        await tester.runAsync(fixture.dispose);
      });

      try {
        final service = const LocalGitWorkspaceOnboardingService();
        final beforeSnapshot = await tester.runAsync(fixture.captureSnapshot);
        if (beforeSnapshot == null) {
          throw StateError(
            'TS-717 pre-open repository snapshot did not complete.',
          );
        }

        result['repository_path'] = fixture.repositoryPath;
        result['workspace_folder_name'] = fixture.workspaceFolderName;
        result['before_head_revision'] = beforeSnapshot.headRevision;
        result['before_worktree_status'] = beforeSnapshot.worktreeStatusLines;
        result['before_files'] = beforeSnapshot.files;

        final inspection = await tester.runAsync(
          () => service.inspectFolder(fixture.repositoryPath),
        );
        if (inspection == null) {
          throw StateError('TS-717 inspection did not complete.');
        }

        result['inspection'] = <String, Object?>{
          'state': inspection.state.name,
          'message': inspection.message,
          'folderPath': inspection.folderPath,
          'suggestedWorkspaceName': inspection.suggestedWorkspaceName,
          'suggestedWriteBranch': inspection.suggestedWriteBranch,
          'detectedWriteBranch': inspection.detectedWriteBranch,
          'hasGitRepository': inspection.hasGitRepository,
          'canOpen': inspection.canOpen,
        };

        if (inspection.state != LocalWorkspaceInspectionState.readyToOpen ||
            !inspection.canOpen ||
            inspection.folderPath != fixture.repositoryPath ||
            inspection.suggestedWorkspaceName != fixture.workspaceFolderName ||
            inspection.suggestedWriteBranch !=
                Ts717ReadyWorkspaceFixture.defaultBranch ||
            inspection.detectedWriteBranch !=
                Ts717ReadyWorkspaceFixture.defaultBranch ||
            !inspection.hasGitRepository) {
          throw AssertionError(
            'Step 3 failed: LocalWorkspaceInspectionService did not classify the prepared repository as a ready local workspace.\n'
            'Observed state: ${inspection.state.name}\n'
            'Observed message: ${inspection.message}\n'
            'Observed folderPath: ${inspection.folderPath}\n'
            'Observed suggestedWorkspaceName: ${inspection.suggestedWorkspaceName}\n'
            'Observed suggestedWriteBranch: ${inspection.suggestedWriteBranch}\n'
            'Observed detectedWriteBranch: ${inspection.detectedWriteBranch}\n'
            'Observed hasGitRepository: ${inspection.hasGitRepository}\n'
            'Observed canOpen: ${inspection.canOpen}',
          );
        }

        final pickerInvocations = <Map<String, String?>>[];
        final openedRepositories = <String>[];
        final workspaceProfileService =
            SharedPreferencesWorkspaceProfileService(
              now: () => DateTime.utc(2026, 5, 14, 16, 30),
            );

        final screen = await launchWorkspaceOnboardingFixture(
          tester,
          workspaceProfileService: workspaceProfileService,
          localWorkspaceOnboardingService:
              _StaticLocalWorkspaceOnboardingService(inspection),
          workspaceDirectoryPicker:
              ({String? confirmButtonText, String? initialDirectory}) async {
                pickerInvocations.add(<String, String?>{
                  'confirmButtonText': confirmButtonText,
                  'initialDirectory': initialDirectory,
                });
                return fixture.repositoryPath;
              },
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                openedRepositories.add(
                  '$repositoryPath@$defaultBranch@$writeBranch',
                );
                return const DemoTrackStateRepository();
              },
        );

        try {
          final initialVisibleTexts = _normalizedVisibleTexts(tester);
          result['initial_visible_texts'] = initialVisibleTexts;
          if (!initialVisibleTexts.contains('Add workspace') ||
              !initialVisibleTexts.contains('Open existing folder')) {
            throw AssertionError(
              'Step 1 failed: the onboarding screen did not render the expected Add workspace entry point before choosing a local folder.\n'
              'Observed visible texts: ${_formatList(initialVisibleTexts)}',
            );
          }

          await tester.tap(
            find.byKey(
              const ValueKey('local-workspace-onboarding-open-existing'),
            ),
            warnIfMissed: false,
          );
          await _pumpUntil(
            tester,
            condition: () =>
                pickerInvocations.isNotEmpty &&
                find
                    .byKey(const ValueKey('local-workspace-onboarding-submit'))
                    .evaluate()
                    .isNotEmpty,
            timeout: const Duration(seconds: 10),
            failureMessage:
                'Step 2 failed: the onboarding flow did not finish inspecting the selected folder after invoking the DirectoryPickerAdapter.',
          );

          if (pickerInvocations.length != 1) {
            throw AssertionError(
              'Step 2 failed: selecting "Open existing folder" did not invoke the DirectoryPickerAdapter exactly once.\n'
              'Observed picker invocations: ${pickerInvocations.length}\n'
              'Observed invocations: ${jsonEncode(pickerInvocations)}',
            );
          }

          final pickerInvocation = pickerInvocations.single;
          result['picker_invocation'] = pickerInvocation;
          if (pickerInvocation['confirmButtonText'] !=
              'Choose existing folder') {
            throw AssertionError(
              'Step 2 failed: the DirectoryPickerAdapter was not called with the expected open-existing confirmation label.\n'
              'Observed confirmButtonText: ${pickerInvocation['confirmButtonText'] ?? '<null>'}\n'
              'Observed initialDirectory: ${pickerInvocation['initialDirectory'] ?? '<null>'}',
            );
          }
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action:
                'Launch the app and select "Open existing folder" on the onboarding screen.',
            observed:
                'visible_texts=${_formatList(initialVisibleTexts)}; picker_invoked=true',
          );
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action:
                'Use the DirectoryPickerAdapter to select the prepared directory.',
            observed:
                'confirmButtonText=${pickerInvocation['confirmButtonText']}; selectedFolder=${fixture.repositoryPath}',
          );

          final visibleTexts = _normalizedVisibleTexts(tester);
          final interactiveLabels = _interactiveSemanticsLabels(tester);
          final nameValue = _editableTextValue(
            tester,
            const ValueKey('local-workspace-onboarding-name'),
          );
          final writeBranchValue = _editableTextValue(
            tester,
            const ValueKey('local-workspace-onboarding-write-branch'),
          );
          final submitFinder = find.byKey(
            const ValueKey('local-workspace-onboarding-submit'),
          );
          final submitButton = tester.widget<FilledButton>(submitFinder);
          final submitLabel = _filledButtonLabel(tester, submitFinder);
          result['visible_texts'] = visibleTexts;
          result['interactive_semantics_labels'] = interactiveLabels;
          result['workspace_name_value'] = nameValue;
          result['write_branch_value'] = writeBranchValue;
          result['submit_label'] = submitLabel;
          result['submit_enabled'] = submitButton.onPressed != null;

          final requiredTexts = <String>[
            'Ready to open',
            'This folder already contains a committed TrackState workspace and is ready to open.',
            'Selected folder',
            fixture.repositoryPath,
            'Workspace details',
            'Workspace name',
            'Write Branch',
            'Open workspace',
          ];
          final missingTexts = requiredTexts
              .where((text) => !visibleTexts.contains(text))
              .toList(growable: false);
          if (missingTexts.isNotEmpty ||
              nameValue != fixture.workspaceFolderName ||
              writeBranchValue != Ts717ReadyWorkspaceFixture.defaultBranch ||
              submitLabel != 'Open workspace' ||
              submitButton.onPressed == null) {
            throw AssertionError(
              'Step 3 failed: the ready repository selection did not advance to the expected Workspace details state with an enabled Open action.\n'
              'Missing visible texts: ${_formatList(missingTexts)}\n'
              'Observed visible texts: ${_formatList(visibleTexts)}\n'
              'Observed workspace name: $nameValue\n'
              'Observed write branch: $writeBranchValue\n'
              'Observed submit label: $submitLabel\n'
              'Observed submit enabled: ${submitButton.onPressed != null}',
            );
          }
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action:
                'Observe the LocalWorkspaceInspectionService output and the visible UI state.',
            observed:
                'inspection_state=${inspection.state.name}; status=Ready to open; selected_folder=${fixture.repositoryPath}; workspace_name=$nameValue; write_branch=$writeBranchValue; submit_label=$submitLabel; submit_enabled=${submitButton.onPressed != null}',
          );

          final requiredSemanticFragments = <String>[
            'Open existing folder',
            'Initialize folder',
            'Change folder',
            'Workspace name',
            'Write Branch',
            'Open workspace',
          ];
          final missingSemanticFragments = requiredSemanticFragments
              .where(
                (fragment) =>
                    !interactiveLabels.any((label) => label.contains(fragment)),
              )
              .toList(growable: false);
          if (missingSemanticFragments.isNotEmpty ||
              interactiveLabels.any((label) => label.trim().isEmpty)) {
            throw AssertionError(
              'Step 4 failed: one or more interactive onboarding elements did not expose a non-empty semantics label.\n'
              'Missing semantic fragments: ${_formatList(missingSemanticFragments)}\n'
              'Observed interactive semantics labels: ${_formatList(interactiveLabels)}',
            );
          }
          _recordStep(
            result,
            step: 4,
            status: 'passed',
            action:
                'Verify that interactive elements have non-empty Semantics labels (AC6).',
            observed:
                'interactive_semantics_labels=${_formatList(interactiveLabels)}',
          );

          await tester.tap(submitFinder, warnIfMissed: false);
          await _pumpUntil(
            tester,
            condition: () =>
                openedRepositories.isNotEmpty ||
                find.text('Dashboard').evaluate().isNotEmpty,
            timeout: const Duration(seconds: 10),
            failureMessage:
                'Step 3 failed: submitting the ready local workspace did not continue into the workspace shell.',
          );

          final afterSnapshot = await tester.runAsync(fixture.captureSnapshot);
          if (afterSnapshot == null) {
            throw StateError(
              'TS-717 post-open repository snapshot did not complete.',
            );
          }
          result['after_head_revision'] = afterSnapshot.headRevision;
          result['after_worktree_status'] = afterSnapshot.worktreeStatusLines;
          result['after_files'] = afterSnapshot.files;
          result['opened_repositories'] = openedRepositories;
          result['dashboard_visible'] = find
              .text('Dashboard')
              .evaluate()
              .isNotEmpty;

          if (_singleOrNull(openedRepositories) !=
                  '${fixture.repositoryPath}@main@main' ||
              afterSnapshot.headRevision != beforeSnapshot.headRevision ||
              !_listEquals(
                afterSnapshot.worktreeStatusLines,
                beforeSnapshot.worktreeStatusLines,
              ) ||
              !_mapEquals(afterSnapshot.files, beforeSnapshot.files)) {
            throw AssertionError(
              'Step 3 failed: opening the ready repository changed files on disk or called the local repository loader with unexpected arguments.\n'
              'Observed opened repositories: ${_formatList(openedRepositories)}\n'
              'Observed head revision before/after: ${beforeSnapshot.headRevision} -> ${afterSnapshot.headRevision}\n'
              'Observed worktree status before: ${_formatList(beforeSnapshot.worktreeStatusLines)}\n'
              'Observed worktree status after: ${_formatList(afterSnapshot.worktreeStatusLines)}\n'
              'Observed files changed: ${!_mapEquals(afterSnapshot.files, beforeSnapshot.files)}',
            );
          }

          if (find.text('Dashboard').evaluate().isEmpty) {
            throw AssertionError(
              'Human-style verification failed: after pressing "Open workspace", the visible app did not continue into the workspace shell.\n'
              'Observed visible texts: ${_formatList(_normalizedVisibleTexts(tester))}',
            );
          }

          _recordHumanVerification(
            result,
            check:
                'Observed the visible onboarding copy a user sees after choosing the folder, including the ready status, selected folder path, workspace details heading, and enabled Open workspace action.',
            observed:
                'visible_texts=${_formatList(visibleTexts)}; interactive_semantics_labels=${_formatList(interactiveLabels)}',
          );
          _recordHumanVerification(
            result,
            check:
                'Pressed "Open workspace" and verified the dashboard became visible while the selected repository stayed byte-for-byte unchanged on disk.',
            observed:
                'dashboard_visible=true; opened_repositories=${_formatList(openedRepositories)}; head_revision=${afterSnapshot.headRevision}; worktree_status=${_formatList(afterSnapshot.worktreeStatusLines)}; file_manifest_unchanged=true',
          );

          print('TS-717-OBSERVATION:${jsonEncode(result)}');
        } finally {
          screen.dispose();
        }
      } finally {
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 60)),
  );
}

String? _singleOrNull(List<String> values) {
  if (values.length != 1) {
    return null;
  }
  return values.single;
}

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

List<String> _normalizedVisibleTexts(WidgetTester tester) {
  final texts = <String>[];
  for (final widget in tester.widgetList(find.byType(Text))) {
    if (widget is! Text) {
      continue;
    }
    final data = widget.data?.trim();
    if (data == null || data.isEmpty || texts.contains(data)) {
      continue;
    }
    texts.add(data);
  }
  for (final widget in tester.widgetList<SelectableText>(
    find.byType(SelectableText),
  )) {
    final data = widget.data?.trim();
    if (data == null || data.isEmpty || texts.contains(data)) {
      continue;
    }
    texts.add(data);
  }
  return texts;
}

List<String> _interactiveSemanticsLabels(WidgetTester tester) {
  final scaffoldFinder = find.byType(Scaffold);
  if (scaffoldFinder.evaluate().isEmpty) {
    return const <String>[];
  }
  final rootNode = tester.getSemantics(scaffoldFinder.first);
  final labels = <String>[];

  void visit(SemanticsNode node) {
    final children = node.debugListChildrenInOrder(
      DebugSemanticsDumpOrder.traversalOrder,
    );
    final label = node.label.replaceAll('\n', ' ').trim();
    final flags = node.getSemanticsData().flagsCollection;
    if (label.isNotEmpty &&
        !node.isInvisible &&
        !node.isMergedIntoParent &&
        (flags.isButton || flags.isTextField)) {
      labels.add(label);
    }
    for (final child in children) {
      visit(child);
    }
  }

  visit(rootNode);
  return _dedupeConsecutive(labels);
}

List<String> _dedupeConsecutive(List<String> labels) {
  final deduped = <String>[];
  for (final label in labels) {
    if (deduped.isEmpty || deduped.last != label) {
      deduped.add(label);
    }
  }
  return deduped;
}

String _editableTextValue(WidgetTester tester, Key key) {
  final field = find.descendant(
    of: find.byKey(key),
    matching: find.byType(EditableText),
  );
  return tester.widget<EditableText>(field.first).controller.text;
}

String _filledButtonLabel(WidgetTester tester, Finder finder) {
  final richTexts = find.descendant(
    of: finder,
    matching: find.byType(RichText),
  );
  for (final element in richTexts.evaluate()) {
    final widget = element.widget;
    if (widget is RichText) {
      final text = widget.text.toPlainText().trim();
      if (text.isNotEmpty) {
        return text;
      }
    }
  }
  return '';
}

String _formatList(List<Object?> values) {
  if (values.isEmpty) {
    return '<empty>';
  }
  return values.map((value) => value.toString()).join(' | ');
}

bool _listEquals(List<String> left, List<String> right) {
  if (left.length != right.length) {
    return false;
  }
  for (var index = 0; index < left.length; index += 1) {
    if (left[index] != right[index]) {
      return false;
    }
  }
  return true;
}

bool _mapEquals(Map<String, String> left, Map<String, String> right) {
  if (left.length != right.length) {
    return false;
  }
  for (final entry in left.entries) {
    if (right[entry.key] != entry.value) {
      return false;
    }
  }
  return true;
}

class _StaticLocalWorkspaceOnboardingService
    implements LocalWorkspaceOnboardingService {
  const _StaticLocalWorkspaceOnboardingService(this.inspection);

  final LocalWorkspaceInspection inspection;

  @override
  Future<LocalWorkspaceInspection> inspectFolder(String folderPath) async {
    return inspection;
  }

  @override
  Future<LocalWorkspaceSetupResult> initializeFolder({
    required LocalWorkspaceInspection inspection,
    required String workspaceName,
    required String writeBranch,
  }) {
    throw UnimplementedError(
      'TS-717 only exercises the ready-to-open onboarding path.',
    );
  }
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required bool Function() condition,
  required Duration timeout,
  required String failureMessage,
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (condition()) {
      await tester.pump();
      return;
    }
    await tester.pump(step);
  }
  if (!condition()) {
    fail(failureMessage);
  }
}
