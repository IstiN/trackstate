import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service_io.dart';

void main() {
  test('inspectFolder recognizes a committed TrackState repository', () async {
    final repository = await _createTrackStateRepository();
    addTearDown(() => repository.delete(recursive: true));

    final service = const LocalGitWorkspaceOnboardingService();
    final inspection = await service.inspectFolder(repository.path);

    expect(inspection.state, LocalWorkspaceInspectionState.readyToOpen);
    expect(
      inspection.suggestedWorkspaceName,
      repository.path.split(Platform.pathSeparator).last,
    );
    expect(inspection.suggestedWriteBranch, 'main');
    expect(inspection.detectedWriteBranch, 'main');
  });

  test('inspectFolder blocks a non-empty non-git folder', () async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-non-git-',
    );
    addTearDown(() => directory.delete(recursive: true));
    await File('${directory.path}/notes.txt').writeAsString('hello');

    final service = const LocalGitWorkspaceOnboardingService();
    final inspection = await service.inspectFolder(directory.path);

    expect(inspection.state, LocalWorkspaceInspectionState.blocked);
    expect(inspection.message, contains('Non-empty folders'));
  });

  test('inspectFolder allows initialization for an empty folder', () async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-empty-',
    );
    addTearDown(() => directory.delete(recursive: true));

    final service = const LocalGitWorkspaceOnboardingService();
    final inspection = await service.inspectFolder(directory.path);

    expect(inspection.state, LocalWorkspaceInspectionState.readyToInitialize);
    expect(inspection.needsGitInitialization, isTrue);
    expect(inspection.suggestedWriteBranch, 'main');
  });

  test(
    'initializeFolder writes the starter scaffold and extends gitattributes',
    () async {
      final directory = await Directory.systemTemp.createTemp(
        'trackstate-init-',
      );
      addTearDown(() => directory.delete(recursive: true));
      await File(
        '${directory.path}/.gitattributes',
      ).writeAsString('docs/**/*.zip filter=lfs diff=lfs merge=lfs -text\n');

      final runner = _RecordingGitProcessRunner();
      final service = LocalGitWorkspaceOnboardingService(processRunner: runner);
      final result = await service.initializeFolder(
        inspection: LocalWorkspaceInspection(
          folderPath: directory.path,
          state: LocalWorkspaceInspectionState.readyToInitialize,
          message: 'Initialize here.',
          suggestedWorkspaceName: 'starter',
          suggestedWriteBranch: 'main',
          detectedWriteBranch: 'main',
          hasGitRepository: true,
        ),
        workspaceName: 'Starter Workspace',
        writeBranch: 'main',
      );

      expect(result.projectKey, 'STARTERWOR');
      expect(
        File('${directory.path}/STARTERWOR/project.json').existsSync(),
        isTrue,
      );
      expect(
        File(
          '${directory.path}/STARTERWOR/.trackstate/index/issues.json',
        ).readAsStringSync(),
        '[]\n',
      );
      final gitattributes = File(
        '${directory.path}/.gitattributes',
      ).readAsStringSync();
      expect(
        gitattributes,
        contains('docs/**/*.zip filter=lfs diff=lfs merge=lfs -text'),
      );
      expect(
        gitattributes,
        contains('*.png filter=lfs diff=lfs merge=lfs -text'),
      );
      expect(
        runner.commands,
        containsAll(<String>[
          'add -- .gitattributes STARTERWOR',
          'commit -m Initialize TrackState workspace',
        ]),
      );
    },
  );

  test(
    'initializeFolder records git init when the folder is not a repository',
    () async {
      final directory = await Directory.systemTemp.createTemp(
        'trackstate-init-empty-',
      );
      addTearDown(() => directory.delete(recursive: true));

      final runner = _RecordingGitProcessRunner();
      final service = LocalGitWorkspaceOnboardingService(processRunner: runner);
      final inspection = LocalWorkspaceInspection(
        folderPath: directory.path,
        state: LocalWorkspaceInspectionState.readyToInitialize,
        message: 'Initialize here.',
        suggestedWorkspaceName: 'fresh',
        suggestedWriteBranch: 'main',
        needsGitInitialization: true,
      );

      await service.initializeFolder(
        inspection: inspection,
        workspaceName: 'Fresh Workspace',
        writeBranch: 'main',
      );

      expect(runner.commands.first, 'init --initial-branch main');
    },
  );
}

class _RecordingGitProcessRunner implements GitProcessRunner {
  final List<String> commands = <String>[];

  @override
  Future<GitCommandResult> run(
    String repositoryPath,
    List<String> args, {
    bool binaryOutput = false,
  }) async {
    commands.add(args.join(' '));
    return GitCommandResult(
      exitCode: 0,
      stdout: '',
      stdoutBytes: Uint8List(0),
      stderr: '',
    );
  }
}

Future<Directory> _createTrackStateRepository() async {
  final directory = await Directory.systemTemp.createTemp('ready-workspace-');
  await _writeFile(
    directory,
    '.gitattributes',
    '*.png filter=lfs diff=lfs merge=lfs -text\n',
  );
  await _writeFile(
    directory,
    'READY/project.json',
    '{"key":"READY","name":"Ready Workspace","defaultLocale":"en","configPath":"config","attachmentStorage":{"mode":"repository-path"}}\n',
  );
  await _writeFile(
    directory,
    'READY/config/statuses.json',
    '[{"id":"todo","name":"To Do"}]\n',
  );
  await _writeFile(
    directory,
    'READY/config/issue-types.json',
    '[{"id":"story","name":"Story"}]\n',
  );
  await _writeFile(
    directory,
    'READY/config/fields.json',
    '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
  );
  await _writeFile(
    directory,
    'READY/.trackstate/index/issues.json',
    '[{"key":"READY-1","path":"READY/READY-1/main.md","summary":"Ready issue","issueType":"story","status":"todo","updated":"2026-05-05T00:00:00Z","children":[],"archived":false}]\n',
  );
  await _writeFile(
    directory,
    'READY/.trackstate/index/tombstones.json',
    '[]\n',
  );
  await _writeFile(directory, 'READY/READY-1/main.md', '''---
key: READY-1
project: READY
issueType: story
status: todo
summary: Ready issue
updated: 2026-05-05T00:00:00Z
---

# Description

Ready issue.
''');
  await _git(directory.path, ['init', '-b', 'main']);
  await _git(directory.path, [
    'config',
    '--local',
    'user.name',
    'Local Tester',
  ]);
  await _git(directory.path, [
    'config',
    '--local',
    'user.email',
    'local@example.com',
  ]);
  await _git(directory.path, ['add', '.']);
  await _git(directory.path, ['commit', '-m', 'Initial import']);
  return directory;
}

Future<void> _writeFile(
  Directory root,
  String relativePath,
  String content,
) async {
  final file = File('${root.path}/$relativePath');
  await file.parent.create(recursive: true);
  await file.writeAsString(content);
}

Future<void> _git(String repositoryPath, List<String> args) async {
  final result = await Process.run('git', ['-C', repositoryPath, ...args]);
  if (result.exitCode != 0) {
    throw StateError(result.stderr.toString());
  }
}
