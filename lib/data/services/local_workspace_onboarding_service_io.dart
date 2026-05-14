import 'dart:convert';
import 'dart:io';

import '../providers/local/local_git_trackstate_provider.dart';
import '../repositories/local_trackstate_repository.dart';
import 'local_workspace_onboarding_service.dart';

LocalWorkspaceOnboardingService createLocalWorkspaceOnboardingService() =>
    const LocalGitWorkspaceOnboardingService();

class LocalGitWorkspaceOnboardingService
    implements LocalWorkspaceOnboardingService {
  const LocalGitWorkspaceOnboardingService({
    GitProcessRunner processRunner = const IoGitProcessRunner(),
  }) : _processRunner = processRunner;

  final GitProcessRunner _processRunner;

  @override
  Future<LocalWorkspaceInspection> inspectFolder(String folderPath) async {
    final normalizedPath = _normalizePath(folderPath);
    if (normalizedPath.isEmpty) {
      return const LocalWorkspaceInspection(
        folderPath: '',
        state: LocalWorkspaceInspectionState.blocked,
        message: 'Choose a folder to continue.',
        suggestedWorkspaceName: '',
        suggestedWriteBranch: _defaultBranchName,
      );
    }

    final directory = Directory(normalizedPath);
    final exists = await directory.exists();
    if (!exists) {
      return LocalWorkspaceInspection(
        folderPath: normalizedPath,
        state: LocalWorkspaceInspectionState.blocked,
        message: 'The selected folder does not exist.',
        suggestedWorkspaceName: _defaultWorkspaceName(normalizedPath),
        suggestedWriteBranch: _defaultBranchName,
      );
    }

    if (!await _canReadDirectory(directory)) {
      return LocalWorkspaceInspection(
        folderPath: normalizedPath,
        state: LocalWorkspaceInspectionState.blocked,
        message:
            'TrackState could not read this folder. Check the folder permissions and try again.',
        suggestedWorkspaceName: _defaultWorkspaceName(normalizedPath),
        suggestedWriteBranch: _defaultBranchName,
      );
    }

    final repositoryTopLevel = await _tryGitString(normalizedPath, [
      'rev-parse',
      '--show-toplevel',
    ]);
    final suggestedWorkspaceName = _defaultWorkspaceName(normalizedPath);

    if (repositoryTopLevel == null) {
      final entries = await _listDirectoryEntries(directory);
      if (entries.isEmpty) {
        return LocalWorkspaceInspection(
          folderPath: normalizedPath,
          state: LocalWorkspaceInspectionState.readyToInitialize,
          message:
              'This folder is empty. TrackState can initialize Git and create the starter workspace here.',
          suggestedWorkspaceName: suggestedWorkspaceName,
          suggestedWriteBranch: _defaultBranchName,
          needsGitInitialization: true,
        );
      }
      final hasTrackStateArtifacts = await _containsTrackStateArtifacts(
        directory,
      );
      if (hasTrackStateArtifacts) {
        return LocalWorkspaceInspection(
          folderPath: normalizedPath,
          state: LocalWorkspaceInspectionState.blocked,
          message:
              'TrackState files already exist here, but Git is not initialized for this folder yet. Clean up the partial setup or choose a different folder before onboarding.',
          suggestedWorkspaceName: suggestedWorkspaceName,
          suggestedWriteBranch: _defaultBranchName,
        );
      }
      return LocalWorkspaceInspection(
        folderPath: normalizedPath,
        state: LocalWorkspaceInspectionState.readyToInitialize,
        message:
            'This folder is not a Git repository yet. TrackState can initialize Git and create the starter workspace here.',
        suggestedWorkspaceName: suggestedWorkspaceName,
        suggestedWriteBranch: _defaultBranchName,
        needsGitInitialization: true,
      );
    }

    final normalizedTopLevel = _normalizePath(repositoryTopLevel);
    if (normalizedTopLevel != normalizedPath) {
      return LocalWorkspaceInspection(
        folderPath: normalizedPath,
        state: LocalWorkspaceInspectionState.blocked,
        message:
            'Choose the repository root folder instead of a nested directory.',
        suggestedWorkspaceName: suggestedWorkspaceName,
        suggestedWriteBranch: _defaultBranchName,
        hasGitRepository: true,
      );
    }

    final isBare = await _tryGitString(normalizedPath, [
      'rev-parse',
      '--is-bare-repository',
    ]);
    if (isBare == 'true') {
      return LocalWorkspaceInspection(
        folderPath: normalizedPath,
        state: LocalWorkspaceInspectionState.blocked,
        message:
            'Bare Git repositories are not supported for local TrackState workspaces.',
        suggestedWorkspaceName: suggestedWorkspaceName,
        suggestedWriteBranch: _defaultBranchName,
        hasGitRepository: true,
      );
    }

    final detectedWriteBranch = await _tryGitString(normalizedPath, [
      'symbolic-ref',
      '--quiet',
      '--short',
      'HEAD',
    ]);
    final hasCommit = await _hasCommit(normalizedPath);
    final suggestedWriteBranch =
        (detectedWriteBranch == null || detectedWriteBranch.isEmpty)
        ? _defaultBranchName
        : detectedWriteBranch;

    if (!hasCommit) {
      final hasTrackStateArtifacts = await _containsTrackStateArtifacts(
        directory,
      );
      if (hasTrackStateArtifacts) {
        return LocalWorkspaceInspection(
          folderPath: normalizedPath,
          state: LocalWorkspaceInspectionState.blocked,
          message:
              'TrackState files already exist here, but the repository does not have a usable committed scaffold yet. Clean up the partial setup or choose a different folder.',
          suggestedWorkspaceName: suggestedWorkspaceName,
          suggestedWriteBranch: suggestedWriteBranch,
          detectedWriteBranch: detectedWriteBranch,
          hasGitRepository: true,
        );
      }
      return LocalWorkspaceInspection(
        folderPath: normalizedPath,
        state: LocalWorkspaceInspectionState.readyToInitialize,
        message:
            'This Git repository does not have an initial commit yet. Initialize TrackState here to create the starter scaffold and first commit.',
        suggestedWorkspaceName: suggestedWorkspaceName,
        suggestedWriteBranch: suggestedWriteBranch,
        detectedWriteBranch: detectedWriteBranch,
        hasGitRepository: true,
      );
    }

    if (detectedWriteBranch == null || detectedWriteBranch.isEmpty) {
      return LocalWorkspaceInspection(
        folderPath: normalizedPath,
        state: LocalWorkspaceInspectionState.blocked,
        message:
            'This repository is not on a usable local branch. Check out the branch you want to use, then try again.',
        suggestedWorkspaceName: suggestedWorkspaceName,
        suggestedWriteBranch: suggestedWriteBranch,
        hasGitRepository: true,
      );
    }

    final hasTrackStateArtifacts = await _containsTrackStateArtifacts(
      directory,
    );
    if (!hasTrackStateArtifacts) {
      return LocalWorkspaceInspection(
        folderPath: normalizedPath,
        state: LocalWorkspaceInspectionState.readyToInitialize,
        message:
            'Git is already initialized here, but TrackState metadata is missing. Initialize TrackState here to create the project scaffold.',
        suggestedWorkspaceName: suggestedWorkspaceName,
        suggestedWriteBranch: suggestedWriteBranch,
        detectedWriteBranch: detectedWriteBranch,
        hasGitRepository: true,
      );
    }

    final validationError = await _trackStateValidationError(
      repositoryPath: normalizedPath,
      writeBranch: detectedWriteBranch,
    );
    if (validationError == null) {
      return LocalWorkspaceInspection(
        folderPath: normalizedPath,
        state: LocalWorkspaceInspectionState.readyToOpen,
        message:
            'This folder already contains a committed TrackState workspace and is ready to open.',
        suggestedWorkspaceName: suggestedWorkspaceName,
        suggestedWriteBranch: suggestedWriteBranch,
        detectedWriteBranch: detectedWriteBranch,
        hasGitRepository: true,
      );
    }

    return LocalWorkspaceInspection(
      folderPath: normalizedPath,
      state: LocalWorkspaceInspectionState.blocked,
      message:
          'TrackState files were found here, but the workspace is incomplete or invalid. Repair the existing metadata before opening this folder. $validationError',
      suggestedWorkspaceName: suggestedWorkspaceName,
      suggestedWriteBranch: suggestedWriteBranch,
      detectedWriteBranch: detectedWriteBranch,
      hasGitRepository: true,
    );
  }

  @override
  Future<LocalWorkspaceSetupResult> initializeFolder({
    required LocalWorkspaceInspection inspection,
    required String workspaceName,
    required String writeBranch,
  }) async {
    if (!inspection.canInitialize) {
      throw const LocalWorkspaceOnboardingException(
        'This folder cannot be initialized for TrackState.',
      );
    }

    final normalizedFolderPath = _normalizePath(inspection.folderPath);
    final normalizedWriteBranch = writeBranch.trim();
    final normalizedWorkspaceName = workspaceName.trim();
    if (normalizedFolderPath.isEmpty ||
        normalizedWorkspaceName.isEmpty ||
        normalizedWriteBranch.isEmpty) {
      throw const LocalWorkspaceOnboardingException(
        'Workspace name, folder, and write branch are required.',
      );
    }

    final lockedBranch = inspection.detectedWriteBranch?.trim();
    if (inspection.hasGitRepository &&
        lockedBranch != null &&
        lockedBranch.isNotEmpty &&
        lockedBranch != normalizedWriteBranch) {
      throw LocalWorkspaceOnboardingException(
        'This repository is currently on $lockedBranch. Switch the repository branch yourself before onboarding, or keep the detected write branch.',
      );
    }

    if (inspection.needsGitInitialization) {
      await _initializeGitRepository(
        repositoryPath: normalizedFolderPath,
        branch: normalizedWriteBranch,
      );
    }

    final projectKey = _deriveProjectKey(normalizedWorkspaceName);
    final projectRoot = Directory('$normalizedFolderPath/$projectKey');
    if (await projectRoot.exists()) {
      throw LocalWorkspaceOnboardingException(
        'TrackState cannot initialize here because $projectKey already exists in the selected folder.',
      );
    }

    await _writeStarterScaffold(
      repositoryPath: normalizedFolderPath,
      projectKey: projectKey,
      workspaceName: normalizedWorkspaceName,
    );
    await _ensureDefaultGitAttributes(normalizedFolderPath);
    await _commitInitialization(
      repositoryPath: normalizedFolderPath,
      projectKey: projectKey,
    );

    return LocalWorkspaceSetupResult(
      folderPath: normalizedFolderPath,
      displayName: normalizedWorkspaceName,
      defaultBranch: normalizedWriteBranch,
      writeBranch: normalizedWriteBranch,
      projectKey: projectKey,
    );
  }

  Future<void> _initializeGitRepository({
    required String repositoryPath,
    required String branch,
  }) async {
    final initResult = await _processRunner.run(repositoryPath, [
      'init',
      '--initial-branch',
      branch,
    ]);
    if (initResult.exitCode == 0) {
      return;
    }
    final fallbackResult = await _processRunner.run(repositoryPath, ['init']);
    if (fallbackResult.exitCode != 0) {
      throw LocalWorkspaceOnboardingException(
        _gitFailureMessage(
          operation: 'initialize Git',
          stderr: initResult.stderr.ifEmpty(fallbackResult.stderr),
        ),
      );
    }
    final branchResult = await _processRunner.run(repositoryPath, [
      'checkout',
      '-B',
      branch,
    ]);
    if (branchResult.exitCode != 0) {
      throw LocalWorkspaceOnboardingException(
        _gitFailureMessage(
          operation: 'create the initial branch',
          stderr: branchResult.stderr,
        ),
      );
    }
  }

  Future<void> _writeStarterScaffold({
    required String repositoryPath,
    required String projectKey,
    required String workspaceName,
  }) async {
    final files = <String, String>{
      '$projectKey/project.json':
          '${jsonEncode(_projectJson(projectKey: projectKey, workspaceName: workspaceName))}\n',
      '$projectKey/config/issue-types.json': '${jsonEncode(_issueTypesJson)}\n',
      '$projectKey/config/statuses.json': '${jsonEncode(_statusesJson)}\n',
      '$projectKey/config/fields.json': '${jsonEncode(_fieldsJson)}\n',
      '$projectKey/config/workflows.json': '${jsonEncode(_workflowsJson)}\n',
      '$projectKey/config/priorities.json': '${jsonEncode(_prioritiesJson)}\n',
      '$projectKey/config/components.json': '${jsonEncode(_componentsJson)}\n',
      '$projectKey/config/versions.json': '${jsonEncode(_versionsJson)}\n',
      '$projectKey/config/resolutions.json':
          '${jsonEncode(_resolutionsJson)}\n',
      '$projectKey/config/i18n/en.json':
          '${jsonEncode(_localizedLabelsJson)}\n',
      '$projectKey/.trackstate/index/issues.json': '[]\n',
      '$projectKey/.trackstate/index/tombstones.json': '[]\n',
    };

    for (final entry in files.entries) {
      final file = File('$repositoryPath/${entry.key}');
      await file.parent.create(recursive: true);
      await file.writeAsString(entry.value);
    }
  }

  Future<void> _ensureDefaultGitAttributes(String repositoryPath) async {
    final file = File('$repositoryPath/.gitattributes');
    final existingContent = await file.exists()
        ? await file.readAsString()
        : '';
    final normalizedExisting = LineSplitter.split(
      existingContent,
    ).map((line) => line.trim()).where((line) => line.isNotEmpty).toSet();
    final missingLines = [
      for (final line in _defaultGitAttributesLines)
        if (!normalizedExisting.contains(line)) line,
    ];
    if (missingLines.isEmpty) {
      return;
    }
    final buffer = StringBuffer();
    final trimmedExisting = existingContent.trimRight();
    if (trimmedExisting.isNotEmpty) {
      buffer
        ..write(trimmedExisting)
        ..write('\n');
    }
    buffer.writeAll(missingLines, '\n');
    buffer.write('\n');
    await file.writeAsString(buffer.toString());
  }

  Future<void> _commitInitialization({
    required String repositoryPath,
    required String projectKey,
  }) async {
    final addResult = await _processRunner.run(repositoryPath, [
      'add',
      '--',
      '.gitattributes',
      projectKey,
    ]);
    if (addResult.exitCode != 0) {
      throw LocalWorkspaceOnboardingException(
        _gitFailureMessage(
          operation: 'stage the TrackState scaffold',
          stderr: addResult.stderr,
        ),
      );
    }
    final commitResult = await _processRunner.run(repositoryPath, [
      'commit',
      '-m',
      'Initialize TrackState workspace',
    ]);
    if (commitResult.exitCode != 0) {
      throw LocalWorkspaceOnboardingException(
        _gitFailureMessage(
          operation: 'create the initial commit',
          stderr: commitResult.stderr,
        ),
      );
    }
  }

  Future<bool> _canReadDirectory(Directory directory) async {
    try {
      await directory.list(followLinks: false).take(1).toList();
      return true;
    } on FileSystemException {
      return false;
    }
  }

  Future<List<FileSystemEntity>> _listDirectoryEntries(
    Directory directory,
  ) async {
    return directory.list(followLinks: false).toList();
  }

  Future<bool> _containsTrackStateArtifacts(Directory directory) async {
    try {
      await for (final entity in directory.list(
        recursive: true,
        followLinks: false,
      )) {
        final normalizedPath = _normalizePath(entity.path);
        if (normalizedPath.endsWith('/project.json') ||
            normalizedPath.contains('/.trackstate/') ||
            normalizedPath.endsWith('/config/statuses.json') ||
            normalizedPath.endsWith('/config/issue-types.json') ||
            normalizedPath.endsWith('/config/fields.json')) {
          return true;
        }
      }
      return false;
    } on FileSystemException {
      return true;
    }
  }

  Future<bool> _hasCommit(String repositoryPath) async {
    final result = await _processRunner.run(repositoryPath, [
      'rev-parse',
      '--verify',
      'HEAD',
    ]);
    return result.exitCode == 0;
  }

  Future<String?> _tryGitString(
    String repositoryPath,
    List<String> args,
  ) async {
    final result = await _processRunner.run(repositoryPath, args);
    if (result.exitCode != 0) {
      return null;
    }
    final value = result.stdout.trim();
    return value.isEmpty ? null : value;
  }

  Future<String?> _trackStateValidationError({
    required String repositoryPath,
    required String writeBranch,
  }) async {
    try {
      final repository = LocalTrackStateRepository(
        repositoryPath: repositoryPath,
        dataRef: writeBranch,
        writeBranch: writeBranch,
      );
      await repository.loadSnapshot();
      return null;
    } on Object catch (error) {
      return '$error';
    }
  }

  String _gitFailureMessage({
    required String operation,
    required String stderr,
  }) {
    final trimmedError = stderr.trim();
    if (trimmedError.contains('Author identity unknown') ||
        trimmedError.contains('unable to auto-detect email address')) {
      return 'TrackState could not $operation because Git author details are not configured for this repository. Set user.name and user.email, then try again.';
    }
    if (trimmedError.isEmpty) {
      return 'TrackState could not $operation.';
    }
    return 'TrackState could not $operation. $trimmedError';
  }
}

String _normalizePath(String path) {
  var normalized = path.replaceAll('\\', '/').trim();
  while (normalized.length > 1 && normalized.endsWith('/')) {
    normalized = normalized.substring(0, normalized.length - 1);
  }
  return normalized;
}

String _defaultWorkspaceName(String folderPath) {
  final normalized = _normalizePath(folderPath);
  final segments = normalized.split('/');
  for (var index = segments.length - 1; index >= 0; index -= 1) {
    final candidate = segments[index].trim();
    if (candidate.isNotEmpty) {
      return candidate;
    }
  }
  return normalized;
}

String _deriveProjectKey(String workspaceName) {
  final normalized = workspaceName
      .toUpperCase()
      .replaceAll(RegExp(r'[^A-Z0-9]+'), ' ')
      .trim();
  if (normalized.isEmpty) {
    return 'TRACK';
  }
  final parts = normalized
      .split(RegExp(r'\s+'))
      .where((part) => part.isNotEmpty)
      .toList(growable: false);
  if (parts.length > 1) {
    final acronym = parts.map((part) => part[0]).join();
    if (acronym.length >= 3) {
      final endIndex = acronym.length > 10 ? 10 : acronym.length;
      return acronym.substring(0, endIndex);
    }
  }
  final collapsed = parts.join();
  final endIndex = collapsed.length > 10 ? 10 : collapsed.length;
  return collapsed.substring(0, endIndex);
}

const String _defaultBranchName = 'main';

Map<String, Object?> _projectJson({
  required String projectKey,
  required String workspaceName,
}) => <String, Object?>{
  'key': projectKey,
  'name': workspaceName,
  'defaultLocale': 'en',
  'supportedLocales': ['en'],
  'configPath': 'config',
  'attachmentStorage': <String, Object?>{'mode': 'repository-path'},
};

const List<Map<String, Object?>> _issueTypesJson = [
  {
    'id': 'epic',
    'name': 'Epic',
    'hierarchyLevel': 1,
    'icon': 'epic',
    'workflowId': 'epic-workflow',
  },
  {
    'id': 'story',
    'name': 'Story',
    'hierarchyLevel': 0,
    'icon': 'story',
    'workflowId': 'delivery-workflow',
  },
  {
    'id': 'task',
    'name': 'Task',
    'hierarchyLevel': 0,
    'icon': 'task',
    'workflowId': 'delivery-workflow',
  },
  {
    'id': 'subtask',
    'name': 'Sub-task',
    'hierarchyLevel': -1,
    'icon': 'subtask',
    'workflowId': 'delivery-workflow',
  },
  {
    'id': 'bug',
    'name': 'Bug',
    'hierarchyLevel': 0,
    'icon': 'bug',
    'workflowId': 'delivery-workflow',
  },
];

const List<Map<String, Object?>> _statusesJson = [
  {'id': 'todo', 'name': 'To Do', 'category': 'new'},
  {'id': 'in-progress', 'name': 'In Progress', 'category': 'indeterminate'},
  {'id': 'in-review', 'name': 'In Review', 'category': 'indeterminate'},
  {'id': 'done', 'name': 'Done', 'category': 'done'},
];

const List<Map<String, Object?>> _fieldsJson = [
  {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
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
      {'id': 'highest', 'name': 'Highest'},
      {'id': 'high', 'name': 'High'},
      {'id': 'medium', 'name': 'Medium'},
      {'id': 'low', 'name': 'Low'},
    ],
  },
  {'id': 'assignee', 'name': 'Assignee', 'type': 'user', 'required': false},
  {'id': 'labels', 'name': 'Labels', 'type': 'array', 'required': false},
  {
    'id': 'storyPoints',
    'name': 'Story Points',
    'type': 'number',
    'required': false,
  },
];

const Map<String, Object?> _workflowsJson = {
  'epic-workflow': {
    'name': 'Epic Workflow',
    'statuses': ['todo', 'in-progress', 'done'],
    'transitions': [
      {
        'id': 'epic-start',
        'name': 'Start epic',
        'from': 'todo',
        'to': 'in-progress',
      },
      {
        'id': 'epic-complete',
        'name': 'Complete epic',
        'from': 'in-progress',
        'to': 'done',
      },
    ],
  },
  'delivery-workflow': {
    'name': 'Delivery Workflow',
    'statuses': ['todo', 'in-progress', 'in-review', 'done'],
    'transitions': [
      {
        'id': 'start',
        'name': 'Start work',
        'from': 'todo',
        'to': 'in-progress',
      },
      {
        'id': 'review',
        'name': 'Request review',
        'from': 'in-progress',
        'to': 'in-review',
      },
      {'id': 'complete', 'name': 'Complete', 'from': 'in-review', 'to': 'done'},
      {'id': 'reopen', 'name': 'Reopen', 'from': 'done', 'to': 'todo'},
    ],
  },
};

const List<Map<String, Object?>> _prioritiesJson = [
  {'id': 'highest', 'name': 'Highest'},
  {'id': 'high', 'name': 'High'},
  {'id': 'medium', 'name': 'Medium'},
  {'id': 'low', 'name': 'Low'},
];

const List<Map<String, Object?>> _componentsJson = [
  {'id': 'tracker-core', 'name': 'Tracker Core'},
  {'id': 'flutter-ui', 'name': 'Flutter UI'},
  {'id': 'automation', 'name': 'Automation'},
];

const List<Map<String, Object?>> _versionsJson = [
  {'id': 'mvp', 'name': 'MVP'},
];

const List<Map<String, Object?>> _resolutionsJson = [
  {'id': 'done', 'name': 'Done'},
];

const Map<String, Object?> _localizedLabelsJson = {
  'issueTypes': {
    'epic': 'Epic',
    'story': 'Story',
    'task': 'Task',
    'subtask': 'Sub-task',
    'bug': 'Bug',
  },
  'statuses': {
    'todo': 'To Do',
    'in-progress': 'In Progress',
    'in-review': 'In Review',
    'done': 'Done',
  },
  'fields': {
    'summary': 'Summary',
    'description': 'Description',
    'acceptanceCriteria': 'Acceptance Criteria',
    'priority': 'Priority',
    'assignee': 'Assignee',
    'labels': 'Labels',
    'storyPoints': 'Story Points',
  },
  'priorities': {
    'highest': 'Highest',
    'high': 'High',
    'medium': 'Medium',
    'low': 'Low',
  },
  'components': {
    'tracker-core': 'Tracker Core',
    'flutter-ui': 'Flutter UI',
    'automation': 'Automation',
  },
  'versions': {'mvp': 'MVP'},
  'resolutions': {'done': 'Done'},
};

const List<String> _defaultGitAttributesLines = [
  '*.png filter=lfs diff=lfs merge=lfs -text',
  '*.jpg filter=lfs diff=lfs merge=lfs -text',
  '*.jpeg filter=lfs diff=lfs merge=lfs -text',
  '*.gif filter=lfs diff=lfs merge=lfs -text',
  '*.webp filter=lfs diff=lfs merge=lfs -text',
  '*.pdf filter=lfs diff=lfs merge=lfs -text',
  '*.zip filter=lfs diff=lfs merge=lfs -text',
];

extension on String {
  String ifEmpty(String fallback) => isEmpty ? fallback : this;
}
