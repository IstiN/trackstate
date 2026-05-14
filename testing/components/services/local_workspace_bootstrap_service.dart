import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service_io.dart';

import '../../core/interfaces/local_workspace_bootstrap_probe.dart';
import '../../core/models/local_workspace_bootstrap_observation.dart';

class LocalWorkspaceBootstrapService implements LocalWorkspaceBootstrapProbe {
  LocalWorkspaceBootstrapService({
    GitProcessRunner? processRunner,
  }) : _processRunner = processRunner ?? const _ConfiguredGitProcessRunner();

  final GitProcessRunner _processRunner;

  @override
  Future<LocalWorkspaceBootstrapObservation> runScenario({
    required String workspaceName,
    required String writeBranch,
  }) async {
    final tempRoot = await Directory.systemTemp.createTemp('ts718-bootstrap-');
    final targetFolder = Directory('${tempRoot.path}/empty-workspace');
    await targetFolder.create(recursive: true);

    final onboardingService = LocalGitWorkspaceOnboardingService(
      processRunner: _processRunner,
    );
    final inspection = await onboardingService.inspectFolder(targetFolder.path);
    final setup = await onboardingService.initializeFolder(
      inspection: inspection,
      workspaceName: workspaceName,
      writeBranch: writeBranch,
    );

    final relativeFiles = await _listNonGitFiles(targetFolder);
    final projectJsonPath = File(
      '${targetFolder.path}/${setup.projectKey}/project.json',
    );
    final projectJson =
        jsonDecode(await projectJsonPath.readAsString()) as Map<String, Object?>;
    final issuesIndexPath = File(
      '${targetFolder.path}/${setup.projectKey}/.trackstate/index/issues.json',
    );
    final tombstonesIndexPath = File(
      '${targetFolder.path}/${setup.projectKey}/.trackstate/index/tombstones.json',
    );
    final gitAttributesPath = File('${targetFolder.path}/.gitattributes');
    final gitLogOutput = await _git(
      targetFolder.path,
      <String>['log', '--decorate', '--stat', '--oneline'],
    );
    final commitMessagesOutput = await _git(
      targetFolder.path,
      <String>['log', '--format=%s'],
    );
    final commitCount = int.parse(
      await _git(targetFolder.path, <String>['rev-list', '--count', 'HEAD']),
    );
    final headBranch = await _git(
      targetFolder.path,
      <String>['rev-parse', '--abbrev-ref', 'HEAD'],
    );

    return LocalWorkspaceBootstrapObservation(
      targetFolderPath: targetFolder.path,
      workspaceName: workspaceName,
      writeBranch: writeBranch,
      inspectionState: inspection.state.name,
      inspectionMessage: inspection.message,
      suggestedWorkspaceName: inspection.suggestedWorkspaceName,
      needsGitInitialization: inspection.needsGitInitialization,
      hasGitRepository: inspection.hasGitRepository,
      projectKey: setup.projectKey,
      projectJson: projectJson,
      nonGitFilePaths: relativeFiles,
      directoryTree: _renderDirectoryTree(relativeFiles),
      gitattributesContent: await gitAttributesPath.readAsString(),
      issuesIndexContent: await issuesIndexPath.readAsString(),
      tombstonesIndexContent: await tombstonesIndexPath.readAsString(),
      gitLogOutput: gitLogOutput,
      gitCommitMessages: LineSplitter.split(
        commitMessagesOutput,
      ).where((line) => line.trim().isNotEmpty).toList(growable: false),
      gitCommitCount: commitCount,
      gitHeadBranch: headBranch,
    );
  }

  Future<List<String>> _listNonGitFiles(Directory root) async {
    final files = <String>[];
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is! File) {
        continue;
      }
      final relativePath = entity.path.substring(root.path.length + 1).replaceAll(
        '\\',
        '/',
      );
      if (relativePath == '.git' || relativePath.startsWith('.git/')) {
        continue;
      }
      files.add(relativePath);
    }
    files.sort();
    return files;
  }

  String _renderDirectoryTree(List<String> relativeFiles) {
    final buffer = StringBuffer();
    for (final path in relativeFiles) {
      buffer.writeln(path);
    }
    return buffer.toString().trimRight();
  }

  Future<String> _git(String repositoryPath, List<String> args) async {
    final result = await _processRunner.run(repositoryPath, args);
    if (result.exitCode != 0) {
      throw StateError(
        'git ${args.join(' ')} failed for $repositoryPath.\n'
        'stdout:\n${result.stdout}\n'
        'stderr:\n${result.stderr}',
      );
    }
    return result.stdout.trim();
  }
}

class _ConfiguredGitProcessRunner implements GitProcessRunner {
  const _ConfiguredGitProcessRunner();

  static const Map<String, String> _gitIdentity = <String, String>{
    'GIT_AUTHOR_NAME': 'TrackState Test',
    'GIT_AUTHOR_EMAIL': 'trackstate-test@example.com',
    'GIT_COMMITTER_NAME': 'TrackState Test',
    'GIT_COMMITTER_EMAIL': 'trackstate-test@example.com',
  };

  @override
  Future<GitCommandResult> run(
    String repositoryPath,
    List<String> args, {
    bool binaryOutput = false,
  }) async {
    final result = await Process.run(
      'git',
      <String>['-C', repositoryPath, ...args],
      environment: <String, String>{...Platform.environment, ..._gitIdentity},
      stdoutEncoding: binaryOutput ? null : utf8,
      stderrEncoding: utf8,
    );
    final stdoutBytes = switch (result.stdout) {
      final List<int> bytes => Uint8List.fromList(bytes),
      final String text => Uint8List.fromList(utf8.encode(text)),
      _ => Uint8List(0),
    };
    final stdout = switch (result.stdout) {
      final String text => text,
      final List<int> bytes => utf8.decode(bytes, allowMalformed: true),
      _ => '',
    };
    return GitCommandResult(
      exitCode: result.exitCode,
      stdout: stdout,
      stdoutBytes: stdoutBytes,
      stderr: result.stderr.toString(),
    );
  }
}
