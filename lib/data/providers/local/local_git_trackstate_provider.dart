import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import '../../../domain/models/trackstate_models.dart';
import '../trackstate_provider.dart';

class LocalGitTrackStateProvider implements TrackStateProviderAdapter {
  LocalGitTrackStateProvider({
    required this.repositoryPath,
    this.dataRef = 'HEAD',
    GitProcessRunner? processRunner,
  }) : _processRunner = processRunner ?? const IoGitProcessRunner();

  final String repositoryPath;
  final GitProcessRunner _processRunner;

  @override
  final String dataRef;

  @override
  ProviderType get providerType => ProviderType.local;

  @override
  String get repositoryLabel => repositoryPath;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    final branch = await getBranch(connection.branch);
    if (!branch.exists) {
      throw TrackStateProviderException(
        'Local branch ${connection.branch} was not found in $repositoryPath.',
      );
    }
    final name = await _gitConfigValue('user.name');
    final email = await _gitConfigValue('user.email');
    return RepositoryUser(
      login: email.ifEmpty('local-user'),
      displayName: name.ifEmpty(email.ifEmpty('Local User')),
    );
  }

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async {
    final result = await _runGit(['ls-tree', '-r', '--full-tree', ref]);
    return LineSplitter.split(
      result.stdout,
    ).where((line) => line.trim().isNotEmpty).map((line) {
      final metadata = line.split('\t');
      final header = metadata.first.split(' ');
      return RepositoryTreeEntry(
        path: metadata.length > 1 ? metadata[1] : '',
        type: header.length > 1 ? header[1] : 'blob',
      );
    }).toList();
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final show = await _runGit(['show', '$ref:$path']);
    final revision = await _tryGit(['rev-parse', '$ref:$path']);
    return RepositoryTextFile(
      path: path,
      content: show.stdout,
      revision: revision?.stdout.trim(),
    );
  }

  @override
  Future<String> resolveWriteBranch() async {
    final result = await _runGit(['rev-parse', '--abbrev-ref', 'HEAD']);
    return result.stdout.trim();
  }

  @override
  Future<RepositoryBranch> getBranch(String name) async {
    final branchResult = await _tryGit([
      'show-ref',
      '--verify',
      '--quiet',
      'refs/heads/$name',
    ]);
    final currentBranch = await resolveWriteBranch();
    return RepositoryBranch(
      name: name,
      exists: branchResult != null,
      isCurrent: currentBranch == name,
    );
  }

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    await _ensureOnBranch(request.branch);
    await _ensurePathClean(request.path);
    _ensureExpectedRevisionMatches(
      path: request.path,
      expectedRevision: request.expectedRevision,
      currentRevision: await _currentHeadRevision(request.path),
    );
    final file = File(_absolutePath(request.path));
    await file.parent.create(recursive: true);
    await file.writeAsString(request.content);
    await _runGit(['add', '--', request.path]);
    if (!await _hasStagedChanges(request.path)) {
      final revision = await _tryGit(['rev-parse', 'HEAD:${request.path}']);
      return RepositoryWriteResult(
        path: request.path,
        branch: request.branch,
        revision: revision?.stdout.trim() ?? request.expectedRevision,
      );
    }
    await _runGit(['commit', '-m', request.message, '--', request.path]);
    final revision = await _runGit(['rev-parse', 'HEAD:${request.path}']);
    return RepositoryWriteResult(
      path: request.path,
      branch: request.branch,
      revision: revision.stdout.trim(),
    );
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    final result = await writeTextFile(
      RepositoryWriteRequest(
        path: request.path,
        content: request.content,
        message: request.message,
        branch: request.branch,
        expectedRevision: request.expectedRevision,
      ),
    );
    return RepositoryCommitResult(
      branch: result.branch,
      message: request.message,
      revision: result.revision,
    );
  }

  @override
  Future<RepositoryPermission> getPermission() async {
    final branch = await resolveWriteBranch();
    final exists = await getBranch(branch);
    return RepositoryPermission(
      canRead: exists.exists,
      canWrite: exists.exists,
      isAdmin: false,
    );
  }

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final result = await _runGit(['show', '$ref:$path'], binaryOutput: true);
    final revision = await _tryGit(['rev-parse', '$ref:$path']);
    return RepositoryAttachment(
      path: path,
      bytes: result.stdoutBytes,
      revision: revision?.stdout.trim(),
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    await _ensureOnBranch(request.branch);
    await _ensurePathClean(request.path);
    _ensureExpectedRevisionMatches(
      path: request.path,
      expectedRevision: request.expectedRevision,
      currentRevision: await _currentHeadRevision(request.path),
    );
    final file = File(_absolutePath(request.path));
    await file.parent.create(recursive: true);
    await file.writeAsBytes(request.bytes);
    await _runGit(['add', '--', request.path]);
    if (!await _hasStagedChanges(request.path)) {
      final revision = await _tryGit(['rev-parse', 'HEAD:${request.path}']);
      return RepositoryAttachmentWriteResult(
        path: request.path,
        branch: request.branch,
        revision: revision?.stdout.trim() ?? request.expectedRevision,
      );
    }
    await _runGit(['commit', '-m', request.message, '--', request.path]);
    final revision = await _runGit(['rev-parse', 'HEAD:${request.path}']);
    return RepositoryAttachmentWriteResult(
      path: request.path,
      branch: request.branch,
      revision: revision.stdout.trim(),
    );
  }

  @override
  Future<bool> isLfsTracked(String path) async {
    final result = await _tryGit(['check-attr', 'filter', '--', path]);
    return result?.stdout.trim().endsWith(': lfs') ?? false;
  }

  Future<void> _ensureOnBranch(String branch) async {
    final currentBranch = await resolveWriteBranch();
    if (currentBranch != branch) {
      throw TrackStateProviderException(
        'Local repository is on $currentBranch, but write operations require $branch.',
      );
    }
  }

  Future<bool> _hasStagedChanges(String path) async {
    final result = await _runGit([
      'diff',
      '--cached',
      '--name-only',
      '--',
      path,
    ]);
    return result.stdout.trim().isNotEmpty;
  }

  Future<String> _gitConfigValue(String key) async =>
      (await _tryGit(['config', key]))?.stdout.trim() ?? '';

  Future<void> _ensurePathClean(String path) async {
    final result = await _runGit(['status', '--porcelain', '--', path]);
    if (result.stdout.trim().isEmpty) {
      return;
    }
    throw TrackStateProviderException(
      'Cannot save $path because it has staged or unstaged local changes.',
    );
  }

  Future<String?> _currentHeadRevision(String path) async {
    final revision = await _tryGit(['rev-parse', 'HEAD:$path']);
    return revision?.stdout.trim();
  }

  void _ensureExpectedRevisionMatches({
    required String path,
    required String? expectedRevision,
    required String? currentRevision,
  }) {
    if (expectedRevision == currentRevision) {
      return;
    }
    throw TrackStateProviderException(
      'Cannot save $path because it changed in the current branch. '
      'Expected revision ${expectedRevision ?? 'for a new file'}, '
      'found ${currentRevision ?? 'no file at HEAD'}.',
    );
  }

  Future<GitCommandResult> _runGit(
    List<String> args, {
    bool binaryOutput = false,
  }) async {
    final result = await _processRunner.run(
      repositoryPath,
      args,
      binaryOutput: binaryOutput,
    );
    if (result.exitCode != 0) {
      throw TrackStateProviderException(
        'Git command failed: git ${args.join(' ')}\n${result.stderr.trim()}',
      );
    }
    return result;
  }

  Future<GitCommandResult?> _tryGit(
    List<String> args, {
    bool binaryOutput = false,
  }) async {
    final result = await _processRunner.run(
      repositoryPath,
      args,
      binaryOutput: binaryOutput,
    );
    return result.exitCode == 0 ? result : null;
  }

  String _absolutePath(String path) =>
      '$repositoryPath/${path.replaceAll('\\', '/')}';
}

abstract interface class GitProcessRunner {
  Future<GitCommandResult> run(
    String repositoryPath,
    List<String> args, {
    bool binaryOutput = false,
  });
}

class IoGitProcessRunner implements GitProcessRunner {
  const IoGitProcessRunner();

  @override
  Future<GitCommandResult> run(
    String repositoryPath,
    List<String> args, {
    bool binaryOutput = false,
  }) async {
    final result = await Process.run(
      'git',
      ['-C', repositoryPath, ...args],
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

class GitCommandResult {
  const GitCommandResult({
    required this.exitCode,
    required this.stdout,
    required this.stdoutBytes,
    required this.stderr,
  });

  final int exitCode;
  final String stdout;
  final Uint8List stdoutBytes;
  final String stderr;
}

extension on String {
  String ifEmpty(String fallback) => isEmpty ? fallback : this;
}
