import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/providers/github/github_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'demo repository exposes richer issue schema and repository index data',
    () async {
      const repository = DemoTrackStateRepository();

      final snapshot = await repository.loadSnapshot();
      final issue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'TRACK-12',
      );

      expect(snapshot.project.key, 'TRACK');
      expect(snapshot.project.statusLabel('in-progress'), 'In Progress');
      expect(snapshot.project.fieldLabel('storyPoints'), 'Story Points');
      expect(
        snapshot.project.attachmentStorage.mode,
        AttachmentStorageMode.repositoryPath,
      );
      expect(
        snapshot.repositoryIndex.pathForKey('TRACK-12'),
        'TRACK/TRACK-1/TRACK-12/main.md',
      );
      expect(issue.issueTypeId, 'story');
      expect(issue.statusId, 'in-progress');
      expect(issue.priorityId, 'high');
      expect(issue.fixVersionIds, ['mvp']);
      expect(issue.watchers, ['ana', 'denis']);
      expect(issue.customFields['storyPoints'], 8);
      expect(issue.links.single.targetKey, 'TRACK-41');
      expect(issue.attachments.single.mediaType, 'image/svg+xml');
    },
  );

  test(
    'setup repository resolves github releases attachment storage and metadata',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'attachmentStorage': {
              'mode': 'github-releases',
              'githubReleases': {'tagPrefix': 'trackstate-attachments-'},
            },
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
            {
              'id': 'description',
              'name': 'Description',
              'type': 'markdown',
              'required': false,
            },
            {
              'id': 'acceptanceCriteria',
              'name': 'Acceptance Criteria',
              'type': 'markdown',
              'required': false,
            },
            {
              'id': 'priority',
              'name': 'Priority',
              'type': 'option',
              'required': false,
              'options': [
                {'id': 'medium', 'name': 'Medium'},
              ],
            },
            {
              'id': 'assignee',
              'name': 'Assignee',
              'type': 'user',
              'required': false,
            },
            {
              'id': 'labels',
              'name': 'Labels',
              'type': 'array',
              'required': false,
            },
            {
              'id': 'storyPoints',
              'name': 'Story Points',
              'type': 'number',
              'required': false,
            },
          ]),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'summary': 'Release-backed attachment issue',
              'issueType': 'story',
              'status': 'todo',
              'priority': 'medium',
              'labels': [],
              'updated': '2026-05-05T00:00:00Z',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: story
status: todo
priority: medium
summary: Release-backed attachment issue
updated: 2026-05-05T00:00:00Z
---

# Description

Issue with release-backed attachment metadata.
''',
          'DEMO/DEMO-1/attachments.json': jsonEncode([
            {
              'id': 'DEMO/DEMO-1/attachments/design.png',
              'name': 'design.png',
              'mediaType': 'image/png',
              'sizeBytes': 42,
              'author': 'demo-user',
              'createdAt': '2026-05-05T00:10:00Z',
              'storagePath': 'DEMO/DEMO-1/attachments/design.png',
              'revisionOrOid': 'release-asset-42',
              'storageBackend': 'github-releases',
              'githubReleaseTag': 'trackstate-attachments-DEMO-1',
              'githubReleaseAssetName': 'design.png',
            },
          ]),
        },
      );

      final snapshot = await repository.loadSnapshot();
      final issue = await repository.hydrateIssue(
        snapshot.issues.single,
        scopes: const {IssueHydrationScope.attachments},
      );

      expect(
        snapshot.project.attachmentStorage.mode,
        AttachmentStorageMode.githubReleases,
      );
      expect(
        snapshot.project.attachmentStorage.githubReleases?.releaseTagForIssue(
          issue.key,
        ),
        'trackstate-attachments-DEMO-1',
      );
      expect(
        issue.attachments.single.storageBackend,
        AttachmentStorageMode.githubReleases,
      );
      expect(
        issue.attachments.single.githubReleaseTag,
        'trackstate-attachments-DEMO-1',
      );
      expect(issue.attachments.single.githubReleaseAssetName, 'design.png');
    },
  );

  test(
    'setup repository keeps release-backed metadata authoritative over legacy blobs at the same path',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'attachmentStorage': {
              'mode': 'github-releases',
              'githubReleases': {'tagPrefix': 'trackstate-attachments-'},
            },
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
            {
              'id': 'description',
              'name': 'Description',
              'type': 'markdown',
              'required': false,
            },
          ]),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'summary': 'Release-backed attachment issue',
              'issueType': 'story',
              'status': 'todo',
              'priority': 'medium',
              'labels': [],
              'updated': '2026-05-05T00:00:00Z',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: story
status: todo
priority: medium
summary: Release-backed attachment issue
updated: 2026-05-05T00:00:00Z
---

# Description

Issue with release-backed attachment metadata.
''',
          'DEMO/DEMO-1/attachments/design.png': 'legacy-binary',
          'DEMO/DEMO-1/attachments.json': jsonEncode([
            {
              'id': 'DEMO/DEMO-1/attachments/design.png',
              'name': 'design.png',
              'mediaType': 'image/png',
              'sizeBytes': 42,
              'author': 'demo-user',
              'createdAt': '2026-05-05T00:10:00Z',
              'storagePath': 'DEMO/DEMO-1/attachments/design.png',
              'revisionOrOid': 'release-asset-42',
              'storageBackend': 'github-releases',
              'githubReleaseTag': 'trackstate-attachments-DEMO-1',
              'githubReleaseAssetName': 'design.png',
            },
          ]),
        },
      );

      final snapshot = await repository.loadSnapshot();
      final issue = await repository.hydrateIssue(
        snapshot.issues.single,
        scopes: const {IssueHydrationScope.attachments},
      );

      expect(issue.attachments, hasLength(1));
      expect(
        issue.attachments.single.storageBackend,
        AttachmentStorageMode.githubReleases,
      );
      expect(issue.attachments.single.revisionOrOid, 'release-asset-42');
      expect(
        issue.attachments.single.githubReleaseTag,
        'trackstate-attachments-DEMO-1',
      );
      expect(issue.attachments.single.githubReleaseAssetName, 'design.png');
      expect(issue.attachments.single.sizeBytes, 42);
    },
  );

  test(
    'setup repository surfaces invalid github releases attachment config',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'attachmentStorage': {
              'mode': 'github-releases',
              'githubReleases': {'tagPrefix': ''},
            },
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
            {
              'id': 'description',
              'name': 'Description',
              'type': 'markdown',
              'required': false,
            },
            {
              'id': 'acceptanceCriteria',
              'name': 'Acceptance Criteria',
              'type': 'markdown',
              'required': false,
            },
            {
              'id': 'priority',
              'name': 'Priority',
              'type': 'option',
              'required': false,
              'options': [
                {'id': 'medium', 'name': 'Medium'},
              ],
            },
            {
              'id': 'assignee',
              'name': 'Assignee',
              'type': 'user',
              'required': false,
            },
            {
              'id': 'labels',
              'name': 'Labels',
              'type': 'array',
              'required': false,
            },
            {
              'id': 'storyPoints',
              'name': 'Story Points',
              'type': 'number',
              'required': false,
            },
          ]),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'summary': 'Issue',
              'issueType': 'story',
              'status': 'todo',
              'priority': 'medium',
              'labels': [],
              'updated': '2026-05-05T00:00:00Z',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: story
status: todo
priority: medium
summary: Invalid attachment config issue
updated: 2026-05-05T00:00:00Z
---

# Description

Invalid configuration fixture.
''',
        },
      );

      await expectLater(
        repository.loadSnapshot,
        throwsA(
          isA<TrackStateRepositoryException>().having(
            (error) => error.message,
            'message',
            contains('tagPrefix'),
          ),
        ),
      );
    },
  );

  test('JQL search filters out done issues and sorts by priority', () async {
    const repository = DemoTrackStateRepository();

    final results = await repository.searchIssues(
      'project = TRACK AND status != Done ORDER BY priority DESC',
    );

    expect(results, isNotEmpty);
    expect(results.any((issue) => issue.status == IssueStatus.done), isFalse);
    expect(results.first.priority, IssuePriority.highest);
  });

  test('JQL search supports epic relationship lookup', () async {
    const repository = DemoTrackStateRepository();

    final results = await repository.searchIssues(
      'project = TRACK AND issueType = Story AND epic = TRACK-34',
    );

    expect(results.map((issue) => issue.key), contains('TRACK-41'));
    expect(results.every((issue) => issue.epicKey == 'TRACK-34'), isTrue);
  });

  test('JQL search exposes deterministic page metadata', () async {
    const repository = DemoTrackStateRepository();

    final page = await repository.searchIssuePage(
      'project = TRACK AND status != Done ORDER BY priority DESC',
      maxResults: 2,
    );

    expect(page.issues, hasLength(2));
    expect(page.startAt, 0);
    expect(page.total, greaterThan(page.issues.length));
    expect(page.nextStartAt, 2);
    expect(page.nextPageToken, 'offset:2');
  });

  test(
    'demo repository creates the first issue under the project root path when no issue paths exist yet',
    () async {
      const repository = DemoTrackStateRepository(
        snapshot: TrackerSnapshot(
          project: ProjectConfig(
            key: 'DEMO',
            name: 'Demo Project',
            repository: 'demo/repository',
            branch: 'main',
            defaultLocale: 'en',
            issueTypeDefinitions: [
              TrackStateConfigEntry(id: 'story', name: 'Story'),
            ],
            statusDefinitions: [
              TrackStateConfigEntry(id: 'todo', name: 'To Do'),
            ],
            fieldDefinitions: [
              TrackStateFieldDefinition(
                id: 'summary',
                name: 'Summary',
                type: 'string',
                required: true,
              ),
            ],
            priorityDefinitions: [
              TrackStateConfigEntry(id: 'medium', name: 'Medium'),
            ],
          ),
          issues: [],
        ),
      );

      final created = await repository.createIssue(
        summary: 'First demo issue',
        description: 'Created in an empty project snapshot.',
      );

      expect(created.key, 'DEMO-1');
      expect(created.storagePath, 'DEMO/DEMO-1/main.md');
    },
  );

  test(
    'setup repository loads indexes, comments, links, attachments, tombstones, and localized labels',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'defaultLocale': 'en',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
            {'id': 'in-progress', 'name': 'In Progress'},
            {'id': 'done', 'name': 'Done'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'epic', 'name': 'Epic'},
            {'id': 'story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
            {
              'id': 'storyPoints',
              'name': 'Story Points',
              'type': 'number',
              'required': false,
            },
          ]),
          'DEMO/config/priorities.json': jsonEncode([
            {'id': 'high', 'name': 'High'},
          ]),
          'DEMO/config/versions.json': jsonEncode([
            {'id': 'mvp', 'name': 'MVP'},
          ]),
          'DEMO/config/components.json': jsonEncode([
            {'id': 'tracker-core', 'name': 'Tracker Core'},
          ]),
          'DEMO/config/resolutions.json': jsonEncode([
            {'id': 'done', 'name': 'Done'},
          ]),
          'DEMO/config/i18n/en.json': jsonEncode({
            'issueTypes': {'epic': 'Epic', 'story': 'Story'},
            'statuses': {
              'todo': 'To Do',
              'in-progress': 'In Progress',
              'done': 'Done',
            },
            'fields': {'storyPoints': 'Story Points'},
            'priorities': {'high': 'High'},
            'versions': {'mvp': 'MVP'},
            'components': {'tracker-core': 'Tracker Core'},
            'resolutions': {'done': 'Done'},
          }),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'parentPath': null,
              'epicPath': null,
              'summary': 'Root epic',
              'issueType': 'epic',
              'status': 'in-progress',
              'priority': 'high',
              'assignee': 'demo-admin',
              'labels': ['root'],
              'updated': '2026-05-05T00:00:00Z',
              'children': ['DEMO-2'],
              'archived': false,
            },
            {
              'key': 'DEMO-2',
              'path': 'DEMO/DEMO-1/DEMO-2/main.md',
              'parent': null,
              'epic': 'DEMO-1',
              'parentPath': null,
              'epicPath': 'DEMO/DEMO-1/main.md',
              'summary': 'Indexed markdown issue',
              'issueType': 'story',
              'status': 'in-progress',
              'priority': 'high',
              'assignee': 'demo-user',
              'labels': ['setup'],
              'updated': '2026-05-05T00:05:00Z',
              'resolution': 'done',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/.trackstate/index/tombstones.json': jsonEncode([
            {
              'key': 'DEMO-99',
              'path': 'DEMO/.trackstate/tombstones/DEMO-99.json',
            },
          ]),
          'DEMO/.trackstate/tombstones/DEMO-99.json': jsonEncode({
            'key': 'DEMO-99',
            'project': 'DEMO',
            'formerPath': 'DEMO/DEMO-99/main.md',
            'deletedAt': '2026-05-05T00:30:00Z',
            'summary': 'Retired issue',
            'issueType': 'story',
            'parent': null,
            'epic': 'DEMO-1',
          }),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: epic
status: in-progress
priority: high
summary: Root epic
assignee: demo-admin
reporter: demo-admin
labels:
  - root
components:
  - tracker-core
fixVersions:
  - mvp
watchers:
  - demo-admin
archived: false
parent: null
epic: null
updated: 2026-05-05T00:00:00Z
---

# Description

Root epic.
''',
          'DEMO/DEMO-1/DEMO-2/main.md': '''
---
key: DEMO-2
project: DEMO
issueType: story
status: in-progress
priority: high
summary: Indexed markdown issue
assignee: demo-user
reporter: demo-admin
labels:
  - setup
components:
  - tracker-core
fixVersions:
  - mvp
watchers:
  - demo-admin
resolution: done
archived: false
customFields:
  storyPoints: 5
  releaseTrain:
    - web
    - mobile
parent: null
epic: DEMO-1
updated: 2026-05-05T00:05:00Z
---

# Description

Loaded from setup data.
''',
          'DEMO/DEMO-1/DEMO-2/comments/0001.md': '''
---
author: demo-admin
created: 2026-05-05T00:10:00Z
---

This comment demonstrates markdown-backed collaboration history.
''',
          'DEMO/DEMO-1/DEMO-2/links.json': jsonEncode([
            {'type': 'blocks', 'target': 'DEMO-1', 'direction': 'outward'},
          ]),
          'DEMO/DEMO-1/DEMO-2/attachments/preview.svg': '<svg />',
        },
      );

      final snapshot = await repository.loadSnapshot();
      final summaryIssue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'DEMO-2',
      );
      final issue = await repository.hydrateIssue(
        summaryIssue,
        scopes: const {
          IssueHydrationScope.detail,
          IssueHydrationScope.comments,
          IssueHydrationScope.attachments,
        },
      );

      expect(snapshot.project.key, 'DEMO');
      expect(snapshot.project.defaultLocale, 'en');
      expect(snapshot.project.statusLabel('in-progress'), 'In Progress');
      expect(snapshot.project.fieldLabel('storyPoints'), 'Story Points');
      expect(snapshot.project.versionLabel('mvp'), 'MVP');
      expect(snapshot.project.componentLabel('tracker-core'), 'Tracker Core');
      expect(snapshot.project.resolutionLabel('done'), 'Done');
      expect(
        snapshot.repositoryIndex.pathForKey('DEMO-2'),
        'DEMO/DEMO-1/DEMO-2/main.md',
      );
      expect(snapshot.repositoryIndex.deleted.single.key, 'DEMO-99');
      expect(issue.issueTypeId, 'story');
      expect(issue.statusId, 'in-progress');
      expect(issue.priorityId, 'high');
      expect(issue.fixVersionIds, ['mvp']);
      expect(issue.watchers, ['demo-admin']);
      expect(summaryIssue.hasDetailLoaded, isFalse);
      expect(summaryIssue.hasCommentsLoaded, isFalse);
      expect(summaryIssue.hasAttachmentsLoaded, isFalse);
      expect(issue.customFields['storyPoints'], 5);
      expect(issue.customFields['releaseTrain'], ['web', 'mobile']);
      expect(issue.comments.single.id, '0001');
      expect(issue.comments.single.author, 'demo-admin');
      expect(issue.links.single.type, 'blocks');
      expect(issue.links.single.targetKey, 'DEMO-1');
      expect(issue.attachments.single.name, 'preview.svg');
      expect(issue.attachments.single.mediaType, 'image/svg+xml');
      expect(issue.epicPath, 'DEMO/DEMO-1/main.md');
      expect(issue.resolutionId, 'done');
    },
  );

  test(
    'checked-in setup template includes repository index artifacts and richer fixtures',
    () async {
      final files = _fixtureFilesFromDisk('trackstate-setup/DEMO');

      expect(
        files.keys,
        containsAll([
          'DEMO/.trackstate/index/issues.json',
          'DEMO/config/resolutions.json',
          'DEMO/DEMO-1/DEMO-2/links.json',
          'DEMO/DEMO-1/DEMO-2/attachments/board-preview.svg',
        ]),
      );
      expect(
        files.containsKey('DEMO/.trackstate/index/tombstones.json') ||
            files.containsKey('DEMO/.trackstate/index/deleted.json'),
        isTrue,
        reason:
            'The checked-in setup template must include either the current '
            'tombstone index or the legacy deleted index.',
      );
      if (files.containsKey('DEMO/.trackstate/index/tombstones.json')) {
        expect(
          files.keys,
          contains('DEMO/.trackstate/tombstones/DEMO-99.json'),
        );
      }

      final repository = _mockSetupRepository(files: files);
      final snapshot = await repository.loadSnapshot();
      final boardSummaryIssue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'DEMO-2',
      );
      final boardIssue = await repository.hydrateIssue(
        boardSummaryIssue,
        scopes: const {
          IssueHydrationScope.detail,
          IssueHydrationScope.comments,
          IssueHydrationScope.attachments,
        },
      );
      final doneIssue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'DEMO-4',
      );
      final epicSummaryIssue = snapshot.issues.firstWhere(
        (entry) => entry.key == 'DEMO-1',
      );
      final epicIssue = await repository.hydrateIssue(
        epicSummaryIssue,
        scopes: const {IssueHydrationScope.detail},
      );

      expect(snapshot.project.fieldLabel('storyPoints'), 'Story Points');
      expect(snapshot.project.resolutionLabel('done'), 'Done');
      expect(
        snapshot.repositoryIndex.pathForKey('DEMO-2'),
        'DEMO/DEMO-1/DEMO-2/main.md',
      );
      expect(snapshot.repositoryIndex.deleted.single.key, 'DEMO-99');
      expect(boardIssue.issueTypeId, 'story');
      expect(boardIssue.statusId, 'in-progress');
      expect(boardIssue.priorityId, 'high');
      expect(boardIssue.fixVersionIds, ['mvp']);
      expect(boardIssue.watchers, ['demo-admin', 'demo-user']);
      expect(boardIssue.customFields['storyPoints'], 5);
      expect(boardIssue.customFields['releaseTrain'], ['web', 'mobile']);
      expect(epicIssue.customFields['created'], '2026-05-05T00:00:00Z');
      expect(boardIssue.links.single.targetKey, 'DEMO-4');
      expect(boardIssue.attachments.single.name, 'board-preview.svg');
      expect(doneIssue.statusId, 'done');
      expect(doneIssue.resolutionId, 'done');
    },
  );

  test(
    'checked-in setup template supports TS-315 text-search terms across description and acceptance criteria only',
    () async {
      final repository = _mockSetupRepository(
        files: _fixtureFilesFromDisk('trackstate-setup/DEMO'),
      );

      final descriptionResults = await repository.searchIssues(
        'project = DEMO AND ASSIGNEES',
      );
      final implicitTextResults = await repository.searchIssues(
        'project = DEMO accessibility',
      );
      final acceptanceResults = await repository.searchIssues(
        'project = DEMO AND accessibility',
      );
      final commentOnlyResults = await repository.searchIssues(
        'project = DEMO AND markdown-backed',
      );

      expect(descriptionResults.map((issue) => issue.key), ['DEMO-2']);
      expect(implicitTextResults.map((issue) => issue.key), ['DEMO-2']);
      expect(acceptanceResults.map((issue) => issue.key), ['DEMO-2']);
      expect(commentOnlyResults, isEmpty);
    },
  );

  test(
    'setup repository recovers from hosted tombstone rate limits with summary data intact',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'defaultLocale': 'en',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
            {'id': 'in-progress', 'name': 'In Progress'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'epic', 'name': 'Epic'},
            {'id': 'story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
          ]),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'parentPath': null,
              'epicPath': null,
              'summary': 'Root epic',
              'issueType': 'epic',
              'status': 'in-progress',
              'priority': 'medium',
              'assignee': 'demo-admin',
              'labels': ['root'],
              'updated': '2026-05-05T00:00:00Z',
              'children': ['DEMO-2'],
              'archived': false,
            },
            {
              'key': 'DEMO-2',
              'path': 'DEMO/DEMO-1/DEMO-2/main.md',
              'parent': null,
              'epic': 'DEMO-1',
              'parentPath': null,
              'epicPath': 'DEMO/DEMO-1/main.md',
              'summary': 'Indexed markdown issue',
              'issueType': 'story',
              'status': 'todo',
              'priority': 'medium',
              'assignee': 'demo-user',
              'labels': ['setup'],
              'updated': '2026-05-05T00:05:00Z',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/.trackstate/index/tombstones.json': jsonEncode([
            {
              'key': 'DEMO-99',
              'path': 'DEMO/.trackstate/tombstones/DEMO-99.json',
            },
          ]),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: epic
status: in-progress
priority: medium
summary: Root epic
assignee: demo-admin
reporter: demo-admin
updated: 2026-05-05T00:00:00Z
---

# Description

Root epic.
''',
          'DEMO/DEMO-1/DEMO-2/main.md': '''
---
key: DEMO-2
project: DEMO
issueType: story
status: todo
priority: medium
summary: Indexed markdown issue
assignee: demo-user
reporter: demo-admin
epic: DEMO-1
updated: 2026-05-05T00:05:00Z
---

# Description

Summary data stays available.
''',
        },
        responseOverrides: {
          'DEMO/.trackstate/index/tombstones.json': http.Response(
            '{"message":"API rate limit exceeded"}',
            403,
            headers: {
              'x-ratelimit-remaining': '0',
              'x-ratelimit-reset': '1760000000',
            },
          ),
        },
      );

      final snapshot = await repository.loadSnapshot();

      expect(snapshot.issues.map((issue) => issue.key), ['DEMO-1', 'DEMO-2']);
      expect(snapshot.repositoryIndex.deleted, isEmpty);
      expect(
        snapshot.startupRecovery?.kind,
        TrackerStartupRecoveryKind.githubRateLimit,
      );
    },
  );

  test(
    'setup repository keeps startup blocked when issue summary index is rate limited',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'defaultLocale': 'en',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
          ]),
          'DEMO/.trackstate/index/issues.json': '[]',
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: story
status: todo
priority: medium
summary: Summary missing from hosted index
updated: 2026-05-05T00:00:00Z
---
''',
        },
        responseOverrides: {
          'DEMO/.trackstate/index/issues.json': http.Response(
            '{"message":"API rate limit exceeded"}',
            403,
            headers: {
              'x-ratelimit-remaining': '0',
              'x-ratelimit-reset': '1760000000',
            },
          ),
        },
      );

      await expectLater(
        repository.loadSnapshot,
        throwsA(isA<GitHubRateLimitException>()),
      );
    },
  );

  test(
    'setup repository keeps compatibility with legacy display labels',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'queued', 'name': 'To Do'},
            {'id': 'building', 'name': 'In Progress'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'feature-story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
          ]),
          'DEMO/config/priorities.json': jsonEncode([
            {'id': 'p1', 'name': 'High'},
          ]),
          'DEMO/config/versions.json': jsonEncode([]),
          'DEMO/config/components.json': jsonEncode([]),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'summary': 'Legacy markdown issue',
              'issueType': 'feature-story',
              'status': 'building',
              'priority': 'p1',
              'assignee': 'user',
              'labels': [],
              'updated': '2026-05-05T00:00:00Z',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: Legacy markdown issue
assignee: user
reporter: admin
parent: null
epic: null
---

# Description

Loaded from older demo data.
''',
        },
      );

      final snapshot = await repository.loadSnapshot();
      final issue = snapshot.issues.single;

      expect(issue.issueType, IssueType.story);
      expect(issue.issueTypeId, 'feature-story');
      expect(issue.status, IssueStatus.inProgress);
      expect(issue.statusId, 'building');
      expect(issue.priority, IssuePriority.high);
      expect(issue.priorityId, 'p1');
      expect(issue.storagePath, 'DEMO/DEMO-1/main.md');
    },
  );

  test(
    'setup repository preserves stored config ids while reading semantic enums',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'queued', 'name': 'To Do'},
            {'id': 'building', 'name': 'In Progress'},
            {'id': 'accepted', 'name': 'Done'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'feature-story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
          ]),
          'DEMO/config/priorities.json': jsonEncode([
            {'id': 'p1', 'name': 'High'},
          ]),
          'DEMO/config/versions.json': jsonEncode([]),
          'DEMO/config/components.json': jsonEncode([]),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'summary': 'Canonical ids stay intact',
              'issueType': 'feature-story',
              'status': 'building',
              'priority': 'p1',
              'assignee': 'user',
              'labels': [],
              'updated': 'from repo',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: feature-story
status: building
priority: p1
summary: Canonical ids stay intact
assignee: user
reporter: admin
parent: null
epic: null
---

# Description

Machine ids should survive parsing.
''',
        },
      );

      final snapshot = await repository.loadSnapshot();
      final issue = snapshot.issues.single;

      expect(issue.issueType, IssueType.story);
      expect(issue.issueTypeId, 'feature-story');
      expect(issue.status, IssueStatus.inProgress);
      expect(issue.statusId, 'building');
      expect(issue.priority, IssuePriority.high);
      expect(issue.priorityId, 'p1');
    },
  );

  test(
    'setup repository preserves inline customFields while resolving canonical ids',
    () async {
      final repository = _mockSetupRepository(
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
            {'id': 'done', 'name': 'Done'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
            {
              'id': 'field_101',
              'name': 'Custom Field 101',
              'type': 'string',
              'required': false,
            },
            {
              'id': 'priority',
              'name': 'Priority',
              'type': 'option',
              'required': false,
            },
          ]),
          'DEMO/config/priorities.json': jsonEncode([
            {'id': 'high', 'name': 'High'},
          ]),
          'DEMO/config/versions.json': jsonEncode([]),
          'DEMO/config/components.json': jsonEncode([]),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-63',
              'path': 'DEMO/DEMO-63/main.md',
              'parent': null,
              'epic': null,
              'summary': 'Inline custom fields issue',
              'issueType': 'story',
              'status': 'done',
              'priority': 'high',
              'assignee': 'qa-user',
              'labels': [],
              'updated': '2026-05-07T00:00:00Z',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/DEMO-63/main.md': '''
---
key: DEMO-63
project: DEMO
issueType: story
status: done
priority: high
summary: Inline custom fields issue
assignee: qa-user
reporter: qa-admin
customFields: { "field_101": "value" }
updated: 2026-05-07T00:00:00Z
---

# Description

Created from inline frontmatter custom fields.
''',
        },
      );

      final snapshot = await repository.loadSnapshot();
      final issue = await repository.hydrateIssue(
        snapshot.issues.single,
        scopes: const {IssueHydrationScope.detail},
      );

      expect(issue.customFields['field_101'], 'value');
      expect(issue.status, IssueStatus.done);
      expect(issue.statusId, 'done');
      expect(issue.priority, IssuePriority.high);
      expect(issue.priorityId, 'high');
    },
  );

  test(
    'setup repository writes the repository canonical status id through the provider adapter',
    () async {
      Map<String, Object?>? savedBody;
      final repository = SetupTrackStateRepository(
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/git/trees/main')) {
            return http.Response('''
{
  "tree": [
    {"path": "DEMO/project.json", "type": "blob"},
    {"path": "DEMO/config/statuses.json", "type": "blob"},
    {"path": "DEMO/config/issue-types.json", "type": "blob"},
    {"path": "DEMO/config/fields.json", "type": "blob"},
    {"path": "DEMO/config/priorities.json", "type": "blob"},
    {"path": "DEMO/config/versions.json", "type": "blob"},
    {"path": "DEMO/config/components.json", "type": "blob"},
    {"path": "DEMO/.trackstate/index/issues.json", "type": "blob"},
    {"path": "DEMO/DEMO-1/main.md", "type": "blob"}
  ]
}
''', 200);
          }
          if (path == '/repos/${SetupTrackStateRepository.repositoryName}') {
            return http.Response('''
{"full_name":"${SetupTrackStateRepository.repositoryName}","permissions":{"pull":true,"push":true,"admin":false}}
''', 200);
          }
          if (path == '/user') {
            return http.Response(
              '{"login":"demo-user","name":"Demo User"}',
              200,
            );
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/.trackstate/index/issues.json') {
            return _contentResponse(
              '[{"key":"DEMO-1","path":"DEMO/DEMO-1/main.md","parent":null,"epic":null,"summary":"Issue","issueType":"story","status":"building","priority":"high","assignee":"demo-user","labels":[],"updated":"from repo","children":[],"archived":false}]',
            );
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/project.json') {
            return _contentResponse('{"key":"DEMO","name":"Demo Project"}');
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/statuses.json') {
            return _contentResponse(
              jsonEncode([
                {'id': 'queued', 'name': 'To Do'},
                {'id': 'building', 'name': 'In Progress'},
                {'id': 'accepted', 'name': 'Done'},
              ]),
            );
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/issue-types.json') {
            return _contentResponse(
              '[{"id":"epic","name":"Epic"},{"id":"story","name":"Story"}]',
            );
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/fields.json') {
            return _contentResponse(
              '[{"id":"summary","name":"Summary","type":"string","required":true}]',
            );
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/priorities.json') {
            return _contentResponse('[{"id":"high","name":"High"}]');
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/versions.json') {
            return _contentResponse('[]');
          }
          if (path ==
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/config/components.json') {
            return _contentResponse('[]');
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/DEMO-1/main.md' &&
              request.method == 'GET') {
            return _contentResponse('''
---
key: DEMO-1
project: DEMO
issueType: story
status: building
priority: high
summary: Issue
assignee: demo-user
reporter: demo-admin
---
''');
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/DEMO-1/main.md' &&
              request.method == 'PUT') {
            savedBody = jsonDecode(request.body) as Map<String, Object?>;
            return http.Response('{"content":{"sha":"next"}}', 200);
          }
          return http.Response('', 404);
        }),
      );

      final snapshot = await repository.loadSnapshot();
      final user = await repository.connect(
        const RepositoryConnection(
          repository: SetupTrackStateRepository.repositoryName,
          branch: 'main',
          token: 'token',
        ),
      );
      final updated = await repository.updateIssueStatus(
        snapshot.issues.single,
        IssueStatus.done,
      );

      expect(user.login, 'demo-user');
      expect(updated.status, IssueStatus.done);
      expect(updated.statusId, 'accepted');
      expect(savedBody?['branch'], 'main');
      expect(savedBody?['message'], 'Move DEMO-1 to Done');
      final content = utf8.decode(
        base64Decode(savedBody?['content']! as String),
      );
      expect(content, contains('status: accepted'));
      expect(content, isNot(contains('status: done')));
    },
  );

  test('setup repository honors configPath from project.json', () async {
    final repository = _mockSetupRepository(
      files: {
        'DEMO/project.json': jsonEncode({
          'key': 'DEMO',
          'name': 'Demo Project',
          'configPath': 'tracker-config',
        }),
        'DEMO/tracker-config/statuses.json': jsonEncode([
          {'name': 'To Do'},
          {'name': 'Done'},
        ]),
        'DEMO/tracker-config/issue-types.json': jsonEncode([
          {'name': 'Epic'},
          {'name': 'Story'},
        ]),
        'DEMO/tracker-config/fields.json': jsonEncode([
          {'name': 'Summary'},
          {'name': 'Priority'},
        ]),
        'DEMO/.trackstate/index/issues.json': jsonEncode([
          {
            'key': 'DEMO-1',
            'path': 'DEMO/DEMO-1/main.md',
            'parent': null,
            'epic': null,
            'summary': 'Config-aware issue',
            'issueType': 'Story',
            'status': 'In Progress',
            'priority': 'High',
            'assignee': 'user',
            'labels': [],
            'updated': '2026-05-05T00:00:00Z',
            'children': [],
            'archived': false,
          },
        ]),
        'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: Config-aware issue
assignee: user
reporter: admin
parent: null
epic: null
updated: 2026-05-05T00:00:00Z
---

# Description

Loaded from setup data.
''',
      },
    );

    final snapshot = await repository.loadSnapshot();

    expect(snapshot.project.statuses, ['To Do', 'Done']);
    expect(snapshot.project.issueTypes, ['Epic', 'Story']);
    expect(snapshot.project.fields, ['Summary', 'Priority']);
  });

  test(
    'github provider evaluates LFS rules against the requested path',
    () async {
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          if (request.url.path.endsWith('/contents/.gitattributes')) {
            return _contentResponse('''
*.png filter=lfs diff=lfs merge=lfs -text
docs/**/*.zip filter=lfs diff=lfs merge=lfs -text
README.md -filter
''');
          }
          return http.Response('', 404);
        }),
      );

      expect(await provider.isLfsTracked('attachments/screenshot.png'), isTrue);
      expect(await provider.isLfsTracked('docs/releases/archive.zip'), isTrue);
      expect(await provider.isLfsTracked('README.md'), isFalse);
      expect(await provider.isLfsTracked('notes/todo.txt'), isFalse);
    },
  );

  test(
    'github provider reports release-backed writes for writable sessions',
    () async {
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          final path = request.url.path;
          if (path == '/repos/IstiN/trackstate' && request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path == '/user' && request.method == 'GET') {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'token',
        ),
      );
      final permission = await provider.getPermission();

      expect(permission.canWrite, isTrue);
      expect(permission.canManageAttachments, isTrue);
      expect(permission.supportsReleaseAttachmentWrites, isTrue);
    },
  );

  test(
    'github provider reads non-LFS binary attachments without UTF-8 decoding',
    () async {
      final bytes = Uint8List.fromList(const [
        0x89,
        0x50,
        0x4E,
        0x47,
        0x00,
        0xFF,
      ]);
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          if (request.url.path.endsWith(
            '/contents/attachments/screenshot.png',
          )) {
            return _binaryContentResponse(bytes);
          }
          return http.Response('', 404);
        }),
      );

      final attachment = await provider.readAttachment(
        'attachments/screenshot.png',
        ref: 'main',
      );

      expect(attachment.bytes, bytes);
      expect(attachment.lfsOid, isNull);
      expect(attachment.declaredSizeBytes, isNull);
    },
  );

  test(
    'github provider downloads LFS attachment content after pointer detection',
    () async {
      final pointer = '''
version https://git-lfs.github.com/spec/v1
oid sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
size 6
''';
      final bytes = Uint8List.fromList(const [
        0x25,
        0x50,
        0x44,
        0x46,
        0x00,
        0x01,
      ]);
      final provider = GitHubTrackStateProvider(
        client: MockClient((request) async {
          if (request.url.path.endsWith('/contents/attachments/manual.pdf')) {
            return _contentResponse(
              pointer,
              downloadUrl: 'https://example.test/lfs/manual.pdf',
            );
          }
          if (request.url.toString() == 'https://example.test/lfs/manual.pdf') {
            return http.Response.bytes(bytes, 200);
          }
          return http.Response('', 404);
        }),
      );

      final attachment = await provider.readAttachment(
        'attachments/manual.pdf',
        ref: 'main',
      );

      expect(attachment.bytes, bytes);
      expect(
        attachment.lfsOid,
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
      );
      expect(attachment.declaredSizeBytes, 6);
    },
  );

  test(
    'github provider reports LFS attachment uploads as unsupported',
    () async {
      var putAttempted = false;
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/repos/IstiN/trackstate') &&
              request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path.endsWith('/user') && request.method == 'GET') {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          if (path.endsWith('/contents/.gitattributes') &&
              request.method == 'GET') {
            return _contentResponse(
              '*.png filter=lfs diff=lfs merge=lfs -text\n',
            );
          }
          if (path.endsWith('/contents/attachments/screenshot.png') &&
              request.method == 'PUT') {
            putAttempted = true;
            return http.Response('{"content":{"sha":"uploaded-sha"}}', 201);
          }
          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'token',
        ),
      );

      await expectLater(
        () => provider.writeAttachment(
          RepositoryAttachmentWriteRequest(
            path: 'attachments/screenshot.png',
            bytes: Uint8List.fromList(const [1, 2, 3]),
            message: 'Upload screenshot',
            branch: 'main',
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains('not yet implemented'),
          ),
        ),
      );
      expect(putAttempted, isFalse);
    },
  );

  test(
    'github provider evaluates LFS upload rules against the target branch',
    () async {
      var putAttempted = false;
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/repos/IstiN/trackstate') &&
              request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path.endsWith('/user') && request.method == 'GET') {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          if (path.endsWith('/contents/.gitattributes') &&
              request.method == 'GET') {
            final ref = request.url.queryParameters['ref'];
            if (ref == 'feature/lfs') {
              return _contentResponse(
                '*.png filter=lfs diff=lfs merge=lfs -text\n',
              );
            }
            return _contentResponse('README.md -filter\n');
          }
          if (path.endsWith('/contents/attachments/screenshot.png') &&
              request.method == 'PUT') {
            putAttempted = true;
            return http.Response('{"content":{"sha":"uploaded-sha"}}', 201);
          }
          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'feature/lfs',
          token: 'token',
        ),
      );

      expect(
        await provider.isLfsTracked('attachments/screenshot.png'),
        isFalse,
      );
      await expectLater(
        () => provider.writeAttachment(
          RepositoryAttachmentWriteRequest(
            path: 'attachments/screenshot.png',
            bytes: Uint8List.fromList(const [1, 2, 3]),
            message: 'Upload screenshot',
            branch: 'feature/lfs',
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains('not yet implemented'),
          ),
        ),
      );
      expect(putAttempted, isFalse);
    },
  );

  test(
    'setup repository uploads github release attachments and persists metadata',
    () async {
      Map<String, Object?>? metadataWriteBody;
      final repository = SetupTrackStateRepository(
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/git/trees/main')) {
            final tree = _releaseAttachmentFixtureFiles().keys
                .map((filePath) => {'path': filePath, 'type': 'blob'})
                .toList(growable: false);
            return http.Response(jsonEncode({'tree': tree}), 200);
          }
          if (path == '/repos/${SetupTrackStateRepository.repositoryName}' &&
              request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path == '/user' && request.method == 'GET') {
            return http.Response(
              '{"login":"demo-user","name":"Demo User"}',
              200,
            );
          }
          final contentsPrefix =
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/';
          if (path.startsWith(contentsPrefix) && request.method == 'GET') {
            final filePath = path.substring(contentsPrefix.length);
            final content = _releaseAttachmentFixtureFiles()[filePath];
            if (content != null) {
              return _contentResponse(content);
            }
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/DEMO-1/attachments.json' &&
              request.method == 'PUT') {
            metadataWriteBody =
                jsonDecode(request.body) as Map<String, Object?>;
            return http.Response(
              '{"content":{"sha":"attachments-meta-sha"}}',
              200,
            );
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/tags/trackstate-attachments-DEMO-1' &&
              request.method == 'GET') {
            return http.Response('', 404);
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases' &&
              request.method == 'POST') {
            return http.Response(
              jsonEncode({
                'id': 21,
                'tag_name': 'trackstate-attachments-DEMO-1',
                'name': 'Attachments for DEMO-1',
                'assets': const <Object?>[],
              }),
              201,
            );
          }
          if (request.url.host == 'uploads.github.com' &&
              path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/21/assets' &&
              request.method == 'POST') {
            expect(request.url.queryParameters['name'], 'release-plan.txt');
            expect(request.headers['content-type'], 'text/plain');
            expect(
              request.bodyBytes,
              Uint8List.fromList(utf8.encode('roadmap')),
            );
            return http.Response(
              jsonEncode({
                'id': 84,
                'name': 'release-plan.txt',
                'size': 7,
                'browser_download_url': 'https://example.test/release-plan.txt',
              }),
              201,
            );
          }
          return http.Response('', 404);
        }),
      );

      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(
          repository: SetupTrackStateRepository.repositoryName,
          branch: 'main',
          token: 'token',
        ),
      );
      final updated = await repository.uploadIssueAttachment(
        issue: snapshot.issues.single,
        name: 'release plan.txt',
        bytes: Uint8List.fromList(utf8.encode('roadmap')),
      );

      final uploaded = updated.attachments.single;
      expect(uploaded.storageBackend, AttachmentStorageMode.githubReleases);
      expect(uploaded.githubReleaseTag, 'trackstate-attachments-DEMO-1');
      expect(uploaded.githubReleaseAssetName, 'release-plan.txt');
      expect(uploaded.revisionOrOid, '84');
      final encodedContent = metadataWriteBody?['content']?.toString();
      expect(encodedContent, isNotNull);
      final metadataJson =
          jsonDecode(utf8.decode(base64Decode(encodedContent!)))
              as List<Object?>;
      expect(metadataJson, [
        {
          'id': 'DEMO/DEMO-1/attachments/release-plan.txt',
          'name': 'release-plan.txt',
          'mediaType': 'text/plain',
          'sizeBytes': 7,
          'author': 'demo-user',
          'createdAt': uploaded.createdAt,
          'storagePath': 'DEMO/DEMO-1/attachments/release-plan.txt',
          'revisionOrOid': '84',
          'storageBackend': 'github-releases',
          'githubReleaseTag': 'trackstate-attachments-DEMO-1',
          'githubReleaseAssetName': 'release-plan.txt',
        },
      ]);
    },
  );

  test(
    'provider-backed repository allows release-backed uploads when release writes are available without generic attachment management',
    () async {
      final provider = _FakeReleaseAttachmentProvider(
        permission: const RepositoryPermission(
          canRead: true,
          canWrite: true,
          isAdmin: false,
          canCreateBranch: true,
          canManageAttachments: false,
          attachmentUploadMode: AttachmentUploadMode.none,
          supportsReleaseAttachmentWrites: true,
          canCheckCollaborators: false,
        ),
        files: _releaseAttachmentFixtureFiles(),
      );
      final repository = ProviderBackedTrackStateRepository(provider: provider);

      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'token',
        ),
      );
      final updated = await repository.uploadIssueAttachment(
        issue: snapshot.issues.single,
        name: 'release plan.txt',
        bytes: Uint8List.fromList(utf8.encode('roadmap')),
      );

      expect(
        updated.attachments.single.storageBackend,
        AttachmentStorageMode.githubReleases,
      );
      expect(updated.attachments.single.revisionOrOid, '84');
      final metadata =
          jsonDecode(provider.files['DEMO/DEMO-1/attachments.json']!)
              as List<Object?>;
      expect(metadata.single, {
        'id': 'DEMO/DEMO-1/attachments/release-plan.txt',
        'name': 'release-plan.txt',
        'mediaType': 'text/plain',
        'sizeBytes': 7,
        'author': 'demo-user',
        'createdAt': updated.attachments.single.createdAt,
        'storagePath': 'DEMO/DEMO-1/attachments/release-plan.txt',
        'revisionOrOid': '84',
        'storageBackend': 'github-releases',
        'githubReleaseTag': 'trackstate-attachments-DEMO-1',
        'githubReleaseAssetName': 'release-plan.txt',
      });
    },
  );

  test(
    'provider-backed repository replaces a legacy repository-path attachment with github-releases metadata',
    () async {
      final provider = _FakeReleaseAttachmentProvider(
        permission: const RepositoryPermission(
          canRead: true,
          canWrite: true,
          isAdmin: false,
          canCreateBranch: true,
          canManageAttachments: false,
          attachmentUploadMode: AttachmentUploadMode.none,
          supportsReleaseAttachmentWrites: true,
          canCheckCollaborators: false,
        ),
        enforceExistingRevisionOnWrite: true,
        files: {
          'DEMO/project.json': jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'attachmentStorage': {
              'mode': 'github-releases',
              'githubReleases': {'tagPrefix': 'trackstate-attachments-'},
            },
          }),
          'DEMO/config/statuses.json': jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
          ]),
          'DEMO/config/issue-types.json': jsonEncode([
            {'id': 'story', 'name': 'Story'},
          ]),
          'DEMO/config/fields.json': jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
          ]),
          'DEMO/.trackstate/index/issues.json': jsonEncode([
            {
              'key': 'DEMO-2',
              'path': 'DEMO/DEMO-1/DEMO-2/main.md',
              'parent': null,
              'epic': null,
              'summary': 'Nested release-backed attachment issue',
              'issueType': 'story',
              'status': 'todo',
              'labels': [],
              'updated': '2026-05-12T20:31:06Z',
              'children': [],
              'archived': false,
            },
          ]),
          'DEMO/DEMO-1/DEMO-2/main.md': '''
---
key: DEMO-2
project: DEMO
issueType: story
status: todo
summary: Nested release-backed attachment issue
updated: 2026-05-12T20:31:06Z
---

# Description

Nested release-backed attachment issue.
''',
          'DEMO/DEMO-1/DEMO-2/attachments/manual.pdf':
              '%PDF-1.4\nlegacy repository attachment\n',
          'DEMO/DEMO-1/DEMO-2/attachments.json': jsonEncode([
            {
              'id': 'DEMO/DEMO-1/DEMO-2/attachments/manual.pdf',
              'name': 'manual.pdf',
              'mediaType': 'application/pdf',
              'sizeBytes': 59,
              'author': 'legacy-user',
              'createdAt': '2026-05-12T20:31:06Z',
              'storagePath': 'DEMO/DEMO-1/DEMO-2/attachments/manual.pdf',
              'revisionOrOid': '',
              'storageBackend': 'repository-path',
              'repositoryPath': 'DEMO/DEMO-1/DEMO-2/attachments/manual.pdf',
            },
          ]),
        },
      );
      final repository = ProviderBackedTrackStateRepository(provider: provider);

      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'token',
        ),
      );
      final issue = await repository.hydrateIssue(
        snapshot.issues.single,
        scopes: const {IssueHydrationScope.attachments},
      );
      final updated = await repository.uploadIssueAttachment(
        issue: issue,
        name: 'manual.pdf',
        bytes: Uint8List.fromList(utf8.encode('replacement attachment')),
      );

      expect(updated.attachments, hasLength(1));
      expect(
        updated.attachments.single.storageBackend,
        AttachmentStorageMode.githubReleases,
      );
      expect(
        updated.attachments.single.githubReleaseTag,
        'trackstate-attachments-DEMO-2',
      );
      expect(updated.attachments.single.githubReleaseAssetName, 'manual.pdf');
      expect(updated.attachments.single.revisionOrOid, '84');
      final metadata =
          jsonDecode(provider.files['DEMO/DEMO-1/DEMO-2/attachments.json']!)
              as List<Object?>;
      expect(metadata, [
        {
          'id': 'DEMO/DEMO-1/DEMO-2/attachments/manual.pdf',
          'name': 'manual.pdf',
          'mediaType': 'application/octet-stream',
          'sizeBytes': utf8.encode('replacement attachment').length,
          'author': 'demo-user',
          'createdAt': updated.attachments.single.createdAt,
          'storagePath': 'DEMO/DEMO-1/DEMO-2/attachments/manual.pdf',
          'revisionOrOid': '84',
          'storageBackend': 'github-releases',
          'githubReleaseTag': 'trackstate-attachments-DEMO-2',
          'githubReleaseAssetName': 'manual.pdf',
        },
      ]);
    },
  );

  test(
    'setup repository downloads github release attachments from metadata',
    () async {
      final repository = SetupTrackStateRepository(
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/git/trees/main')) {
            final tree = _releaseAttachmentFixtureFiles().keys
                .map((filePath) => {'path': filePath, 'type': 'blob'})
                .toList(growable: false);
            return http.Response(jsonEncode({'tree': tree}), 200);
          }
          if (path == '/repos/${SetupTrackStateRepository.repositoryName}' &&
              request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path == '/user' && request.method == 'GET') {
            return http.Response(
              '{"login":"demo-user","name":"Demo User"}',
              200,
            );
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/assets/84' &&
              request.method == 'GET') {
            expect(request.headers['accept'], 'application/octet-stream');
            expect(request.headers['authorization'], 'Bearer token');
            return http.Response(
              '',
              302,
              headers: {'location': 'https://example.test/release-plan.txt'},
            );
          }
          if (request.url.toString() ==
              'https://example.test/release-plan.txt') {
            return http.Response.bytes(utf8.encode('roadmap'), 200);
          }
          return http.Response('', 404);
        }),
      );
      await repository.connect(
        const RepositoryConnection(
          repository: SetupTrackStateRepository.repositoryName,
          branch: 'main',
          token: 'token',
        ),
      );

      final bytes = await repository.downloadAttachment(
        const IssueAttachment(
          id: 'DEMO/DEMO-1/attachments/release-plan.txt',
          name: 'release-plan.txt',
          mediaType: 'text/plain',
          sizeBytes: 7,
          author: 'demo-user',
          createdAt: '2026-05-05T00:00:00Z',
          storagePath: 'DEMO/DEMO-1/attachments/release-plan.txt',
          revisionOrOid: '84',
          storageBackend: AttachmentStorageMode.githubReleases,
          githubReleaseTag: 'trackstate-attachments-DEMO-1',
          githubReleaseAssetName: 'release-plan.txt',
        ),
      );

      expect(utf8.decode(bytes), 'roadmap');
    },
  );

  test(
    'setup repository rolls back release asset uploads when metadata write fails',
    () async {
      var deletedAssetId = '';
      final repository = SetupTrackStateRepository(
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/git/trees/main')) {
            final tree =
                {
                      ..._releaseAttachmentFixtureFiles(),
                      'DEMO/DEMO-1/attachments.json': jsonEncode([
                        {
                          'id': 'DEMO/DEMO-1/attachments/release-plan.txt',
                          'name': 'release-plan.txt',
                          'mediaType': 'text/plain',
                          'sizeBytes': 6,
                          'author': 'demo-user',
                          'createdAt': '2026-05-05T00:00:00Z',
                          'storagePath':
                              'DEMO/DEMO-1/attachments/release-plan.txt',
                          'revisionOrOid': '1',
                          'storageBackend': 'github-releases',
                          'githubReleaseTag': 'trackstate-attachments-DEMO-1',
                          'githubReleaseAssetName': 'release-plan.txt',
                        },
                      ]),
                    }.keys
                    .map((filePath) => {'path': filePath, 'type': 'blob'})
                    .toList(growable: false);
            return http.Response(jsonEncode({'tree': tree}), 200);
          }
          if (path == '/repos/${SetupTrackStateRepository.repositoryName}' &&
              request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path == '/user' && request.method == 'GET') {
            return http.Response(
              '{"login":"demo-user","name":"Demo User"}',
              200,
            );
          }
          final contentsPrefix =
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/';
          if (path.startsWith(contentsPrefix) && request.method == 'GET') {
            final filePath = path.substring(contentsPrefix.length);
            final content = _releaseAttachmentFixtureFiles()[filePath];
            if (content != null) {
              return _contentResponse(content);
            }
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/DEMO-1/attachments.json' &&
              request.method == 'PUT') {
            return http.Response('{"message":"stale revision"}', 409);
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/tags/trackstate-attachments-DEMO-1' &&
              request.method == 'GET') {
            return http.Response('', 404);
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases' &&
              request.method == 'POST') {
            return http.Response(
              jsonEncode({
                'id': 21,
                'tag_name': 'trackstate-attachments-DEMO-1',
                'name': 'Attachments for DEMO-1',
                'assets': const <Object?>[],
              }),
              201,
            );
          }
          if (request.url.host == 'uploads.github.com' &&
              path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/21/assets' &&
              request.method == 'POST') {
            return http.Response(
              jsonEncode({'id': 84, 'name': 'release-plan.txt', 'size': 7}),
              201,
            );
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/assets/84' &&
              request.method == 'DELETE') {
            deletedAssetId = '84';
            return http.Response('', 204);
          }
          return http.Response('', 404);
        }),
      );

      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(
          repository: SetupTrackStateRepository.repositoryName,
          branch: 'main',
          token: 'token',
        ),
      );

      await expectLater(
        () => repository.uploadIssueAttachment(
          issue: snapshot.issues.single,
          name: 'release plan.txt',
          bytes: Uint8List.fromList(utf8.encode('roadmap')),
        ),
        throwsA(isA<TrackStateProviderException>()),
      );
      expect(deletedAssetId, '84');
    },
  );

  test(
    'setup repository restores the previous release asset when overwrite metadata fails',
    () async {
      var currentReleaseAssetId = '1';
      final repository = SetupTrackStateRepository(
        client: MockClient((request) async {
          final path = request.url.path;
          if (path.endsWith('/git/trees/main')) {
            final tree =
                {
                      ..._releaseAttachmentFixtureFiles(),
                      'DEMO/DEMO-1/attachments.json': jsonEncode([
                        {
                          'id': 'DEMO/DEMO-1/attachments/release-plan.txt',
                          'name': 'release-plan.txt',
                          'mediaType': 'text/plain',
                          'sizeBytes': 6,
                          'author': 'demo-user',
                          'createdAt': '2026-05-05T00:00:00Z',
                          'storagePath':
                              'DEMO/DEMO-1/attachments/release-plan.txt',
                          'revisionOrOid': '1',
                          'storageBackend': 'github-releases',
                          'githubReleaseTag': 'trackstate-attachments-DEMO-1',
                          'githubReleaseAssetName': 'release-plan.txt',
                        },
                      ]),
                    }.keys
                    .map((filePath) => {'path': filePath, 'type': 'blob'})
                    .toList(growable: false);
            return http.Response(jsonEncode({'tree': tree}), 200);
          }
          if (path == '/repos/${SetupTrackStateRepository.repositoryName}' &&
              request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path == '/user' && request.method == 'GET') {
            return http.Response(
              '{"login":"demo-user","name":"Demo User"}',
              200,
            );
          }
          final contentsPrefix =
              '/repos/${SetupTrackStateRepository.repositoryName}/contents/';
          if (path.startsWith(contentsPrefix) && request.method == 'GET') {
            final filePath = path.substring(contentsPrefix.length);
            final content = {
              ..._releaseAttachmentFixtureFiles(),
              'DEMO/DEMO-1/attachments.json': jsonEncode([
                {
                  'id': 'DEMO/DEMO-1/attachments/release-plan.txt',
                  'name': 'release-plan.txt',
                  'mediaType': 'text/plain',
                  'sizeBytes': 6,
                  'author': 'demo-user',
                  'createdAt': '2026-05-05T00:00:00Z',
                  'storagePath': 'DEMO/DEMO-1/attachments/release-plan.txt',
                  'revisionOrOid': '1',
                  'storageBackend': 'github-releases',
                  'githubReleaseTag': 'trackstate-attachments-DEMO-1',
                  'githubReleaseAssetName': 'release-plan.txt',
                },
              ]),
            }[filePath];
            if (content != null) {
              return _contentResponse(content);
            }
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/contents/DEMO/DEMO-1/attachments.json' &&
              request.method == 'PUT') {
            return http.Response('{"message":"stale revision"}', 409);
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/assets/1' &&
              request.method == 'GET') {
            expect(request.headers['accept'], 'application/octet-stream');
            expect(request.headers['authorization'], 'Bearer token');
            return http.Response.bytes(utf8.encode('legacy'), 200);
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/assets/1' &&
              request.method == 'DELETE') {
            currentReleaseAssetId = '';
            return http.Response('', 204);
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/tags/trackstate-attachments-DEMO-1' &&
              request.method == 'GET') {
            return http.Response(
              jsonEncode({
                'id': 21,
                'tag_name': 'trackstate-attachments-DEMO-1',
                'name': 'Attachments for DEMO-1',
                'assets': currentReleaseAssetId.isEmpty
                    ? const <Object?>[]
                    : [
                        {
                          'id': currentReleaseAssetId,
                          'name': 'release-plan.txt',
                          'size': 6,
                        },
                      ],
              }),
              200,
            );
          }
          if (request.url.host == 'uploads.github.com' &&
              path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/21/assets' &&
              request.method == 'POST') {
            final body = utf8.decode(request.bodyBytes);
            if (body == 'roadmap') {
              currentReleaseAssetId = '2';
              return http.Response(
                jsonEncode({'id': 2, 'name': 'release-plan.txt', 'size': 7}),
                201,
              );
            }
            if (body == 'legacy') {
              currentReleaseAssetId = '3';
              return http.Response(
                jsonEncode({'id': 3, 'name': 'release-plan.txt', 'size': 6}),
                201,
              );
            }
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/assets/2' &&
              request.method == 'DELETE') {
            currentReleaseAssetId = '';
            return http.Response('', 204);
          }
          if (path ==
                  '/repos/${SetupTrackStateRepository.repositoryName}/releases/assets/3' &&
              request.method == 'GET') {
            expect(request.headers['accept'], 'application/octet-stream');
            expect(request.headers['authorization'], 'Bearer token');
            return http.Response.bytes(utf8.encode('legacy'), 200);
          }
          return http.Response('', 404);
        }),
      );

      final snapshot = await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(
          repository: SetupTrackStateRepository.repositoryName,
          branch: 'main',
          token: 'token',
        ),
      );
      final issue = await repository.hydrateIssue(
        snapshot.issues.single,
        scopes: const {IssueHydrationScope.attachments},
      );

      await expectLater(
        () => repository.uploadIssueAttachment(
          issue: issue,
          name: 'release plan.txt',
          bytes: Uint8List.fromList(utf8.encode('roadmap')),
        ),
        throwsA(isA<TrackStateProviderException>()),
      );

      final restoredBytes = await repository.downloadAttachment(
        issue.attachments.single,
      );
      expect(utf8.decode(restoredBytes), 'legacy');
    },
  );

  test(
    'github provider replaces same-name release assets deterministically',
    () async {
      var deletedAssetId = '';
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          final path = request.url.path;
          if (path == '/repos/IstiN/trackstate' && request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path == '/user' && request.method == 'GET') {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          if (path ==
                  '/repos/IstiN/trackstate/releases/tags/trackstate-attachments-DEMO-1' &&
              request.method == 'GET') {
            return http.Response(
              jsonEncode({
                'id': 10,
                'tag_name': 'trackstate-attachments-DEMO-1',
                'name': 'Attachments for DEMO-1',
                'assets': [
                  {'id': 1, 'name': 'design.png', 'size': 3},
                ],
              }),
              200,
            );
          }
          if (path == '/repos/IstiN/trackstate/releases/assets/1' &&
              request.method == 'DELETE') {
            deletedAssetId = '1';
            return http.Response('', 204);
          }
          if (request.url.host == 'uploads.github.com' &&
              path == '/repos/IstiN/trackstate/releases/10/assets' &&
              request.method == 'POST') {
            expect(request.url.queryParameters['name'], 'design.png');
            return http.Response(
              jsonEncode({'id': 2, 'name': 'design.png', 'size': 4}),
              201,
            );
          }
          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'token',
        ),
      );
      final result = await provider.writeReleaseAttachment(
        RepositoryReleaseAttachmentWriteRequest(
          issueKey: 'DEMO-1',
          releaseTag: 'trackstate-attachments-DEMO-1',
          releaseTitle: 'Attachments for DEMO-1',
          assetName: 'design.png',
          bytes: Uint8List.fromList(const [1, 2, 3, 4]),
          mediaType: 'image/png',
          branch: 'main',
        ),
      );

      expect(deletedAssetId, '1');
      expect(result.assetId, '2');
    },
  );

  test(
    'github provider rejects release containers with unexpected assets',
    () async {
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          final path = request.url.path;
          if (path == '/repos/IstiN/trackstate' && request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path == '/user' && request.method == 'GET') {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          if (path ==
                  '/repos/IstiN/trackstate/releases/tags/trackstate-attachments-DEMO-1' &&
              request.method == 'GET') {
            return http.Response(
              jsonEncode({
                'id': 10,
                'tag_name': 'trackstate-attachments-DEMO-1',
                'name': 'Attachments for DEMO-1',
                'assets': [
                  {'id': 3, 'name': 'foreign.bin', 'size': 9},
                ],
              }),
              200,
            );
          }
          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'token',
        ),
      );

      await expectLater(
        () => provider.writeReleaseAttachment(
          RepositoryReleaseAttachmentWriteRequest(
            issueKey: 'DEMO-1',
            releaseTag: 'trackstate-attachments-DEMO-1',
            releaseTitle: 'Attachments for DEMO-1',
            assetName: 'design.png',
            bytes: Uint8List.fromList(const [1, 2, 3]),
            mediaType: 'image/png',
            branch: 'main',
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains('unexpected assets'),
          ),
        ),
      );
    },
  );

  test('github provider reports release identity conflicts explicitly', () async {
    final provider = GitHubTrackStateProvider(
      repositoryName: 'IstiN/trackstate',
      dataRef: 'main',
      client: MockClient((request) async {
        final path = request.url.path;
        if (path == '/repos/IstiN/trackstate' && request.method == 'GET') {
          return http.Response(
            '{"permissions":{"pull":true,"push":true,"admin":false}}',
            200,
          );
        }
        if (path == '/user' && request.method == 'GET') {
          return http.Response('{"login":"octocat","name":"Mona"}', 200);
        }
        if (path ==
                '/repos/IstiN/trackstate/releases/tags/trackstate-attachments-DEMO-1' &&
            request.method == 'GET') {
          return http.Response(
            jsonEncode({
              'id': 10,
              'tag_name': 'trackstate-attachments-DEMO-1',
              'name': 'Attachments for DEMO-2',
              'assets': const <Object?>[],
            }),
            200,
          );
        }
        return http.Response('', 404);
      }),
    );

    await provider.authenticate(
      const RepositoryConnection(
        repository: 'IstiN/trackstate',
        branch: 'main',
        token: 'token',
      ),
    );

    await expectLater(
      () => provider.writeReleaseAttachment(
        RepositoryReleaseAttachmentWriteRequest(
          issueKey: 'DEMO-1',
          releaseTag: 'trackstate-attachments-DEMO-1',
          releaseTitle: 'Attachments for DEMO-1',
          assetName: 'design.png',
          bytes: Uint8List.fromList(const [1, 2, 3]),
          mediaType: 'image/png',
          branch: 'main',
        ),
      ),
      throwsA(
        isA<TrackStateProviderException>().having(
          (error) => error.message,
          'message',
          contains('requires manual cleanup'),
        ),
      ),
    );
  });

  test(
    'github provider falls back to release lookup when stored asset id is stale',
    () async {
      final provider = GitHubTrackStateProvider(
        repositoryName: 'IstiN/trackstate',
        dataRef: 'main',
        client: MockClient((request) async {
          final path = request.url.path;
          if (path == '/repos/IstiN/trackstate' && request.method == 'GET') {
            return http.Response(
              '{"permissions":{"pull":true,"push":true,"admin":false}}',
              200,
            );
          }
          if (path == '/user' && request.method == 'GET') {
            return http.Response('{"login":"octocat","name":"Mona"}', 200);
          }
          if (path == '/repos/IstiN/trackstate/releases/assets/1' &&
              request.method == 'GET') {
            expect(request.headers['accept'], 'application/octet-stream');
            return http.Response('', 404);
          }
          if (path ==
                  '/repos/IstiN/trackstate/releases/tags/trackstate-attachments-DEMO-1' &&
              request.method == 'GET') {
            return http.Response(
              jsonEncode({
                'id': 10,
                'tag_name': 'trackstate-attachments-DEMO-1',
                'name': 'Attachments for DEMO-1',
                'assets': [
                  {'id': 3, 'name': 'design.png', 'size': 6},
                ],
              }),
              200,
            );
          }
          if (path == '/repos/IstiN/trackstate/releases/assets/3' &&
              request.method == 'GET') {
            expect(request.headers['accept'], 'application/octet-stream');
            expect(request.headers['authorization'], 'Bearer token');
            return http.Response.bytes(const [1, 2, 3, 4, 5, 6], 200);
          }
          return http.Response('', 404);
        }),
      );

      await provider.authenticate(
        const RepositoryConnection(
          repository: 'IstiN/trackstate',
          branch: 'main',
          token: 'token',
        ),
      );

      final asset = await provider.readReleaseAttachment(
        const RepositoryReleaseAttachmentReadRequest(
          releaseTag: 'trackstate-attachments-DEMO-1',
          assetName: 'design.png',
          assetId: '1',
        ),
      );

      expect(asset.revision, '3');
      expect(asset.bytes, Uint8List.fromList(const [1, 2, 3, 4, 5, 6]));
    },
  );

  test(
    'provider-backed repository resolves release-backed downloads through a local GitHub remote identity',
    () async {
      final provider = _FakeRemoteIdentityProvider(
        permission: const RepositoryPermission(
          canRead: true,
          canWrite: true,
          isAdmin: false,
          canCreateBranch: true,
          canManageAttachments: true,
          canCheckCollaborators: false,
        ),
        repository: 'cli/cli',
        files: _releaseAttachmentFixtureFiles(),
      );
      final repository = ProviderBackedTrackStateRepository(
        provider: provider,
        githubClient: MockClient((request) async {
          final path = request.url.path;
          if (path == '/repos/cli/cli/releases/assets/1' &&
              request.method == 'GET') {
            expect(request.headers['accept'], 'application/octet-stream');
            return http.Response('', 404);
          }
          if (path == '/repos/cli/cli/releases/tags/v2.74.0' &&
              request.method == 'GET') {
            return http.Response(
              jsonEncode({
                'id': 10,
                'tag_name': 'v2.74.0',
                'name': 'CLI 2.74.0',
                'assets': const [],
              }),
              200,
            );
          }
          return http.Response('', 404);
        }),
      );

      await expectLater(
        () => repository.downloadAttachment(
          const IssueAttachment(
            id: 'DEMO/DEMO-1/attachments/manual.pdf',
            name: 'manual.pdf',
            mediaType: 'application/pdf',
            sizeBytes: 19,
            author: 'tester',
            createdAt: '2026-05-13T00:00:00Z',
            storagePath: 'DEMO/DEMO-1/attachments/manual.pdf',
            revisionOrOid: '1',
            storageBackend: AttachmentStorageMode.githubReleases,
            githubReleaseTag: 'v2.74.0',
            githubReleaseAssetName: 'manual.pdf',
          ),
        ),
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            contains(
              'GitHub release v2.74.0 does not contain asset manual.pdf.',
            ),
          ),
        ),
      );
    },
  );
}

SetupTrackStateRepository _mockSetupRepository({
  required Map<String, String> files,
  Map<String, http.Response> responseOverrides = const {},
}) {
  return SetupTrackStateRepository(
    client: MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/git/trees/main')) {
        final tree = files.keys
            .map((filePath) => {'path': filePath, 'type': 'blob'})
            .toList(growable: false);
        return http.Response(jsonEncode({'tree': tree}), 200);
      }
      final contentsPrefix =
          '/repos/${SetupTrackStateRepository.repositoryName}/contents/';
      if (path.startsWith(contentsPrefix)) {
        final filePath = path.substring(contentsPrefix.length);
        final override = responseOverrides[filePath];
        if (override != null) {
          return override;
        }
        final content = files[filePath];
        if (content != null) {
          return _contentResponse(content);
        }
      }
      return http.Response('', 404);
    }),
  );
}

http.Response _contentResponse(String content, {String? downloadUrl}) {
  final encoded = base64Encode(utf8.encode(content));
  return http.Response(
    jsonEncode({
      'content': encoded,
      'sha': 'abc123',
      if (downloadUrl != null) 'download_url': downloadUrl,
    }),
    200,
  );
}

http.Response _binaryContentResponse(Uint8List content, {String? downloadUrl}) {
  final encoded = base64Encode(content);
  return http.Response(
    jsonEncode({
      'content': encoded,
      'sha': 'abc123',
      if (downloadUrl != null) 'download_url': downloadUrl,
    }),
    200,
  );
}

class _FakeReleaseAttachmentProvider
    implements TrackStateProviderAdapter, RepositoryReleaseAttachmentStore {
  _FakeReleaseAttachmentProvider({
    required this.permission,
    required Map<String, String> files,
    this.enforceExistingRevisionOnWrite = false,
  }) : files = {...files};

  final RepositoryPermission permission;
  final Map<String, String> files;
  final bool enforceExistingRevisionOnWrite;
  RepositoryConnection? _connection;

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => _connection?.repository ?? 'IstiN/trackstate';

  @override
  String get dataRef => 'main';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    _connection = connection;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async {
    return [
      for (final path in files.keys)
        RepositoryTreeEntry(path: path, type: 'blob'),
    ];
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = files[path];
    if (content == null) {
      throw TrackStateProviderException('File not found: $path');
    }
    return RepositoryTextFile(path: path, content: content, revision: 'abc123');
  }

  @override
  Future<String> resolveWriteBranch() async => _connection?.branch ?? dataRef;

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: name == dataRef);

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    if (enforceExistingRevisionOnWrite &&
        files.containsKey(request.path) &&
        (request.expectedRevision?.isNotEmpty != true)) {
      throw TrackStateProviderException(
        'Cannot save ${request.path} because it changed in the current branch. '
        'Expected revision for existing file was not provided.',
      );
    }
    files[request.path] = request.content;
    return RepositoryWriteResult(
      path: request.path,
      branch: request.branch,
      revision: 'metadata-sha',
    );
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => RepositoryCommitResult(
    branch: request.branch,
    message: request.message,
    revision: 'commit-sha',
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryPermission> getPermission() async => permission;

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final content = files[path];
    if (content == null) {
      throw TrackStateProviderException('Attachment not found: $path');
    }
    return RepositoryAttachment(
      path: path,
      bytes: Uint8List.fromList(utf8.encode(content)),
      revision: 'attachment-sha',
      declaredSizeBytes: utf8.encode(content).length,
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<RepositoryAttachment> readReleaseAttachment(
    RepositoryReleaseAttachmentReadRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<RepositoryReleaseAttachmentWriteResult> writeReleaseAttachment(
    RepositoryReleaseAttachmentWriteRequest request,
  ) async {
    return RepositoryReleaseAttachmentWriteResult(
      releaseTag: request.releaseTag,
      assetName: request.assetName,
      assetId: '84',
    );
  }

  @override
  Future<void> deleteReleaseAttachment(
    RepositoryReleaseAttachmentDeleteRequest request,
  ) async {}
}

class _FakeRemoteIdentityProvider
    implements TrackStateProviderAdapter, RepositoryGitHubIdentityResolver {
  _FakeRemoteIdentityProvider({
    required this.permission,
    required this.repository,
    required Map<String, String> files,
  }) : files = {...files};

  final RepositoryPermission permission;
  final String repository;
  final Map<String, String> files;
  RepositoryConnection? _connection;

  @override
  ProviderType get providerType => ProviderType.local;

  @override
  String get repositoryLabel => _connection?.repository ?? '.';

  @override
  String get dataRef => 'HEAD';

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    _connection = connection;
    return const RepositoryUser(login: 'demo-user', displayName: 'Demo User');
  }

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async {
    return [
      for (final path in files.keys)
        RepositoryTreeEntry(path: path, type: 'blob'),
    ];
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final content = files[path];
    if (content == null) {
      throw TrackStateProviderException('File not found: $path');
    }
    return RepositoryTextFile(path: path, content: content, revision: 'abc123');
  }

  @override
  Future<String> resolveWriteBranch() async => _connection?.branch ?? dataRef;

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: true);

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    files[request.path] = request.content;
    return RepositoryWriteResult(
      path: request.path,
      branch: request.branch,
      revision: 'metadata-sha',
    );
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => RepositoryCommitResult(
    branch: request.branch,
    message: request.message,
    revision: 'commit-sha',
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryPermission> getPermission() async => permission;

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final content = files[path];
    if (content == null) {
      throw TrackStateProviderException('Attachment not found: $path');
    }
    return RepositoryAttachment(
      path: path,
      bytes: Uint8List.fromList(utf8.encode(content)),
      revision: 'attachment-sha',
      declaredSizeBytes: utf8.encode(content).length,
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    throw UnimplementedError();
  }

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<String?> resolveGitHubRepositoryIdentity() async => repository;

  @override
  Future<String?> releaseAttachmentIdentityFailureReason() async => null;
}

Map<String, String> _fixtureFilesFromDisk(String rootPath) {
  final root = Directory(rootPath);
  final normalizedRoot = root.path.replaceAll('\\', '/');
  final files = <String, String>{};

  for (final entity in root.listSync(recursive: true, followLinks: false)) {
    if (entity is! File) continue;
    final normalizedPath = entity.path.replaceAll('\\', '/');
    final relativePath = normalizedPath.substring(normalizedRoot.length + 1);
    files['DEMO/$relativePath'] = entity.readAsStringSync();
  }

  return files;
}

Map<String, String> _releaseAttachmentFixtureFiles() => {
  'DEMO/project.json': jsonEncode({
    'key': 'DEMO',
    'name': 'Demo Project',
    'attachmentStorage': {
      'mode': 'github-releases',
      'githubReleases': {'tagPrefix': 'trackstate-attachments-'},
    },
  }),
  'DEMO/config/statuses.json': jsonEncode([
    {'id': 'todo', 'name': 'To Do'},
  ]),
  'DEMO/config/issue-types.json': jsonEncode([
    {'id': 'story', 'name': 'Story'},
  ]),
  'DEMO/config/fields.json': jsonEncode([
    {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
  ]),
  'DEMO/.trackstate/index/issues.json': jsonEncode([
    {
      'key': 'DEMO-1',
      'path': 'DEMO/DEMO-1/main.md',
      'parent': null,
      'epic': null,
      'summary': 'Release-backed attachment issue',
      'issueType': 'story',
      'status': 'todo',
      'labels': [],
      'updated': '2026-05-05T00:00:00Z',
      'children': [],
      'archived': false,
    },
  ]),
  'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: story
status: todo
summary: Release-backed attachment issue
updated: 2026-05-05T00:00:00Z
---

# Description

Release-backed attachment issue.
''',
  'DEMO/DEMO-1/attachments.json': '[]\n',
};
