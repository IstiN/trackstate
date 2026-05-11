import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-398 shows only valid workflow targets and conditionally requires resolution',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      const issueKey = 'TRACK-398';
      const issueSummary = 'Workflow transition regression coverage';
      const query = 'project = TRACK';
      const expectedTransitions = <String>['To Do', 'Done'];

      try {
        await screen.pump(const _Ts398WorkflowRepository());

        await screen.openSection('JQL Search');
        await screen.searchIssues(query);
        await screen.expectIssueSearchResultVisible(issueKey, issueSummary);
        await screen.openIssue(issueKey, issueSummary);

        await screen.expectIssueDetailVisible(issueKey);
        await screen.expectIssueDetailText(
          issueKey,
          'Only valid outgoing transitions are offered.',
        );

        await screen.tapIssueDetailAction(issueKey, label: 'Transition');
        await screen.expectTextVisible('Transition issue');
        await screen.expectTextVisible('Current status');
        await screen.expectTextVisible('Status');

        expect(
          await screen.readReadOnlyFieldValue('Current status'),
          'In Progress',
          reason:
              'Step 1 failed: opening the visible workflow transition surface '
              'did not show the current status as "In Progress".',
        );

        final transitionOptions = await screen.readDropdownOptions('Status');
        expect(
          transitionOptions,
          equals(expectedTransitions),
          reason:
              'Step 2 failed: the workflow transition target list did not show '
              'exactly the valid outgoing statuses. Observed options: '
              '${transitionOptions.join(' | ')}.',
        );

        expect(
          await screen.isDropdownFieldVisible('Resolution'),
          isFalse,
          reason:
              'Step 2 failed: the Resolution field should stay hidden before a '
              'terminal transition is selected.',
        );

        await screen.selectDropdownOption('Status', optionText: 'Done');

        expect(
          await screen.isDropdownFieldVisible('Resolution'),
          isTrue,
          reason:
              'Step 4 failed: selecting the Done transition did not reveal the '
              'visible Resolution field.',
        );
        expect(
          await screen.readDropdownOptions('Resolution'),
          equals(const <String>['Done', 'Won\'t Do']),
          reason:
              'Step 4 failed: the visible Resolution field did not expose the '
              'expected resolution choices for the terminal transition.',
        );

        final saveTappedWithoutResolution = await screen.tapVisibleControl(
          'Save',
        );
        expect(
          saveTappedWithoutResolution,
          isTrue,
          reason:
              'Step 4 failed: the visible Save action could not be activated '
              'after selecting the Done transition.',
        );
        await screen.expectTextVisible(
          'Resolution is required for this transition.',
        );

        await screen.selectDropdownOption('Status', optionText: 'To Do');

        expect(
          await screen.isDropdownFieldVisible('Resolution'),
          isFalse,
          reason:
              'Step 6 failed: selecting the To Do transition should hide the '
              'Resolution field again, but it stayed visible.',
        );
        expect(
          await screen.isTextVisible(
            'Resolution is required for this transition.',
          ),
          isFalse,
          reason:
              'Step 6 failed: the Resolution required validation stayed visible '
              'after switching back to the non-terminal To Do transition.',
        );
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

class _Ts398WorkflowRepository extends DemoTrackStateRepository {
  const _Ts398WorkflowRepository() : super(snapshot: _snapshot);

  static const TrackerSnapshot _snapshot = TrackerSnapshot(
    project: ProjectConfig(
      key: 'TRACK',
      name: 'TrackState.AI',
      repository: 'IstiN/trackstate',
      branch: 'main',
      defaultLocale: 'en',
      issueTypeDefinitions: <TrackStateConfigEntry>[
        TrackStateConfigEntry(
          id: 'story',
          name: 'Story',
          localizedLabels: {'en': 'Story'},
          workflowId: 'workflow-transition-ui',
        ),
      ],
      statusDefinitions: <TrackStateConfigEntry>[
        TrackStateConfigEntry(
          id: 'todo',
          name: 'To Do',
          category: 'new',
          localizedLabels: {'en': 'To Do'},
        ),
        TrackStateConfigEntry(
          id: 'in-progress',
          name: 'In Progress',
          category: 'indeterminate',
          localizedLabels: {'en': 'In Progress'},
        ),
        TrackStateConfigEntry(
          id: 'done',
          name: 'Done',
          category: 'done',
          localizedLabels: {'en': 'Done'},
        ),
      ],
      fieldDefinitions: <TrackStateFieldDefinition>[
        TrackStateFieldDefinition(
          id: 'summary',
          name: 'Summary',
          type: 'string',
          required: true,
          reserved: true,
          localizedLabels: {'en': 'Summary'},
        ),
        TrackStateFieldDefinition(
          id: 'description',
          name: 'Description',
          type: 'markdown',
          required: false,
          reserved: true,
          localizedLabels: {'en': 'Description'},
        ),
        TrackStateFieldDefinition(
          id: 'resolution',
          name: 'Resolution',
          type: 'option',
          required: false,
          reserved: true,
          localizedLabels: {'en': 'Resolution'},
          options: <TrackStateFieldOption>[
            TrackStateFieldOption(id: 'done', name: 'Done'),
            TrackStateFieldOption(id: 'wont-do', name: 'Won\'t Do'),
          ],
        ),
      ],
      workflowDefinitions: <TrackStateWorkflowDefinition>[
        TrackStateWorkflowDefinition(
          id: 'workflow-transition-ui',
          name: 'Workflow Transition UI',
          statusIds: <String>['todo', 'in-progress', 'done'],
          transitions: <TrackStateWorkflowTransition>[
            TrackStateWorkflowTransition(
              id: 'reopen',
              name: 'Reopen',
              fromStatusId: 'in-progress',
              toStatusId: 'todo',
            ),
            TrackStateWorkflowTransition(
              id: 'complete',
              name: 'Complete',
              fromStatusId: 'in-progress',
              toStatusId: 'done',
            ),
          ],
        ),
      ],
      priorityDefinitions: <TrackStateConfigEntry>[
        TrackStateConfigEntry(
          id: 'medium',
          name: 'Medium',
          localizedLabels: {'en': 'Medium'},
        ),
      ],
      resolutionDefinitions: <TrackStateConfigEntry>[
        TrackStateConfigEntry(
          id: 'done',
          name: 'Done',
          localizedLabels: {'en': 'Done'},
        ),
        TrackStateConfigEntry(
          id: 'wont-do',
          name: 'Won\'t Do',
          localizedLabels: {'en': 'Won\'t Do'},
        ),
      ],
    ),
    repositoryIndex: RepositoryIndex(
      entries: <RepositoryIssueIndexEntry>[
        RepositoryIssueIndexEntry(
          key: 'TRACK-398',
          path: 'TRACK/TRACK-398/main.md',
          childKeys: <String>[],
        ),
      ],
    ),
    issues: <TrackStateIssue>[
      TrackStateIssue(
        key: 'TRACK-398',
        project: 'TRACK',
        issueType: IssueType.story,
        issueTypeId: 'story',
        status: IssueStatus.inProgress,
        statusId: 'in-progress',
        priority: IssuePriority.medium,
        priorityId: 'medium',
        summary: 'Workflow transition regression coverage',
        description:
            'Verify valid workflow targets and conditional resolution handling.',
        assignee: 'automation-user',
        reporter: 'automation-user',
        labels: <String>['workflow'],
        components: <String>[],
        fixVersionIds: <String>[],
        watchers: <String>['automation-user'],
        customFields: const <String, Object?>{},
        parentKey: null,
        epicKey: null,
        parentPath: null,
        epicPath: null,
        progress: .55,
        updatedLabel: 'just now',
        acceptanceCriteria: <String>[
          'Only valid outgoing transitions are offered.',
          'Resolution is collected only for terminal transitions.',
        ],
        comments: <IssueComment>[],
        links: <IssueLink>[],
        attachments: <IssueAttachment>[],
        isArchived: false,
        storagePath: 'TRACK/TRACK-398/main.md',
      ),
    ],
  );
}
