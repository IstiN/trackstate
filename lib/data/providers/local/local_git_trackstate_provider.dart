import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import '../../../domain/models/trackstate_models.dart';
import '../github/github_trackstate_provider.dart';
import '../trackstate_provider.dart';

typedef LocalGitHostedProviderFactory =
    TrackStateProviderAdapter Function({
      required String repository,
      required String branch,
      required String dataRef,
    });

class LocalGitTrackStateProvider
    implements
        TrackStateProviderAdapter,
        RepositoryReleaseAttachmentStore,
        RepositoryFileMutator,
        RepositoryHistoryReader {
  LocalGitTrackStateProvider({
    required this.repositoryPath,
    this.dataRef = 'HEAD',
    GitProcessRunner? processRunner,
    LocalGitHostedProviderFactory? hostedProviderFactory,
  }) : _processRunner = processRunner ?? const IoGitProcessRunner(),
       _hostedProviderFactory =
           hostedProviderFactory ?? _defaultLocalGitHostedProviderFactory;

  final String repositoryPath;
  final GitProcessRunner _processRunner;
  final LocalGitHostedProviderFactory _hostedProviderFactory;
  RepositoryConnection? _connection;

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
    _connection = connection;
    final name = await _gitConfigValue('user.name');
    final email = await _gitConfigValue('user.email');
    return RepositoryUser(
      login: email,
      displayName: name.ifEmpty(email),
      accountId: email.ifEmpty(name),
      emailAddress: email.isEmpty ? null : email,
      active: true,
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
    await _writeTextToWorktree(path: request.path, content: request.content);
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
  Future<RepositoryCommitResult> applyFileChanges(
    RepositoryFileChangeRequest request,
  ) async {
    await _ensureOnBranch(request.branch);
    final paths = {
      for (final change in request.changes) change.path,
    }.toList(growable: false);
    for (final change in request.changes) {
      await _ensurePathClean(change.path);
      switch (change) {
        case RepositoryTextFileChange():
          _ensureExpectedRevisionMatches(
            path: change.path,
            expectedRevision: change.expectedRevision,
            currentRevision: await _currentHeadRevision(change.path),
          );
          await _writeTextToWorktree(
            path: change.path,
            content: change.content,
          );
          await _runGit(['add', '--', change.path]);
        case RepositoryBinaryFileChange():
          _ensureExpectedRevisionMatches(
            path: change.path,
            expectedRevision: change.expectedRevision,
            currentRevision: await _currentHeadRevision(change.path),
          );
          await _writeBytesToWorktree(path: change.path, bytes: change.bytes);
          await _runGit(['add', '--', change.path]);
        case RepositoryDeleteFileChange():
          if (change.expectedRevision != null) {
            _ensureExpectedRevisionMatches(
              path: change.path,
              expectedRevision: change.expectedRevision,
              currentRevision: await _currentHeadRevision(change.path),
            );
          }
          final currentRevision = await _currentHeadRevision(change.path);
          if (currentRevision == null) {
            await _deleteWorktreeFileIfExists(change.path);
            continue;
          }
          await _runGit(['rm', '-f', '--', change.path]);
      }
    }
    if (!await _hasStagedChangesForPaths(paths)) {
      final revision = await _tryGit(['rev-parse', 'HEAD']);
      return RepositoryCommitResult(
        branch: request.branch,
        message: request.message,
        revision: revision?.stdout.trim(),
      );
    }
    await _runGit(['commit', '-m', request.message, '--', ...paths]);
    final revision = await _runGit(['rev-parse', 'HEAD']);
    return RepositoryCommitResult(
      branch: request.branch,
      message: request.message,
      revision: revision.stdout.trim(),
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {
    final result = await _runGit(['status', '--porcelain']);
    if (result.stdout.trim().isEmpty) {
      return;
    }
    throw const TrackStateProviderException(
      'Cannot create an issue because this repository has staged or unstaged local changes. '
      'commit, stash, or clean those local changes before trying again.',
    );
  }

  @override
  Future<RepositoryPermission> getPermission() async {
    final branch = await resolveWriteBranch();
    final exists = await getBranch(branch);
    final releaseAttachmentCapability = await _releaseAttachmentCapability(
      branch: branch,
    );
    return RepositoryPermission(
      canRead: exists.exists,
      canWrite: exists.exists,
      isAdmin: false,
      supportsReleaseAttachmentWrites:
          releaseAttachmentCapability.supportsReleaseAttachmentWrites,
      releaseAttachmentWriteFailureReason:
          releaseAttachmentCapability.failureReason,
    );
  }

  @override
  Future<RepositoryAttachment> readReleaseAttachment(
    RepositoryReleaseAttachmentReadRequest request,
  ) async {
    final store = await _resolveReleaseAttachmentStore(branch: dataRef);
    return store.readReleaseAttachment(request);
  }

  @override
  Future<RepositoryReleaseAttachmentWriteResult> writeReleaseAttachment(
    RepositoryReleaseAttachmentWriteRequest request,
  ) async {
    final store = await _resolveReleaseAttachmentStore(branch: request.branch);
    return store.writeReleaseAttachment(request);
  }

  @override
  Future<void> deleteReleaseAttachment(
    RepositoryReleaseAttachmentDeleteRequest request,
  ) async {
    final store = await _resolveReleaseAttachmentStore(branch: dataRef);
    await store.deleteReleaseAttachment(request);
  }

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final result = await _runGit(['show', '$ref:$path'], binaryOutput: true);
    final revision = await _tryGit(['rev-parse', '$ref:$path']);
    final pointerInfo = _parseLfsPointer(result.stdout);
    final currentBranch = await resolveWriteBranch();
    final useWorktreeBytes =
        pointerInfo != null && (ref == 'HEAD' || ref == currentBranch);
    return RepositoryAttachment(
      path: path,
      bytes: useWorktreeBytes
          ? await File(_absolutePath(path)).readAsBytes()
          : result.stdoutBytes,
      revision: revision?.stdout.trim(),
      lfsOid: pointerInfo?.oid,
      declaredSizeBytes: pointerInfo?.sizeBytes,
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
    await _writeBytesToWorktree(path: request.path, bytes: request.bytes);
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

  @override
  Future<List<RepositoryHistoryCommit>> listHistory({
    required String ref,
    required String path,
    int limit = 50,
  }) async {
    final result = await _runGit([
      'log',
      '--format=%x1e%H%x1f%P%x1f%aI%x1f%an%x1f%s',
      '--name-status',
      '--find-renames',
      '-n',
      '$limit',
      ref,
      '--',
      path,
    ]);
    return _parseGitHistory(result.stdout);
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

  Future<bool> _hasStagedChangesForPaths(List<String> paths) async {
    final result = await _runGit([
      'diff',
      '--cached',
      '--name-only',
      '--',
      ...paths,
    ]);
    return result.stdout.trim().isNotEmpty;
  }

  Future<String> _gitConfigValue(String key) async =>
      (await _tryGit(['config', '--local', key]))?.stdout.trim() ?? '';

  Future<_LocalReleaseAttachmentCapability> _releaseAttachmentCapability({
    required String branch,
  }) async {
    final remoteIdentity = await _resolveGitHubRepositoryIdentity();
    if (remoteIdentity == null) {
      return _LocalReleaseAttachmentCapability.unsupported(
        await _gitRemoteFailureReason(),
      );
    }
    final connection = _connection;
    if (connection == null || connection.token.trim().isEmpty) {
      return const _LocalReleaseAttachmentCapability.unsupported(
        'GitHub Releases attachment storage requires GitHub authentication. '
        'Set TRACKSTATE_TOKEN or authenticate with gh before using '
        'release-backed attachments from a local repository.',
      );
    }
    try {
      final provider = await _createHostedReleaseProvider(
        repository: remoteIdentity,
        branch: branch,
      );
      final permission = await provider.getPermission();
      if (permission.supportsReleaseAttachmentWrites) {
        return const _LocalReleaseAttachmentCapability.supported();
      }
      return _LocalReleaseAttachmentCapability.unsupported(
        permission.releaseAttachmentWriteFailureReason?.trim().isNotEmpty == true
            ? permission.releaseAttachmentWriteFailureReason!.trim()
            : 'GitHub authentication for $remoteIdentity does not permit '
                  'GitHub Release uploads.',
      );
    } on TrackStateProviderException catch (error) {
      return _LocalReleaseAttachmentCapability.unsupported(error.message);
    }
  }

  Future<RepositoryReleaseAttachmentStore> _resolveReleaseAttachmentStore({
    required String branch,
  }) async {
    final remoteIdentity = await _resolveGitHubRepositoryIdentity();
    if (remoteIdentity == null) {
      throw TrackStateProviderException(await _gitRemoteFailureReason());
    }
    final connection = _connection;
    if (connection == null || connection.token.trim().isEmpty) {
      throw const TrackStateProviderException(
        'GitHub Releases attachment storage requires GitHub authentication. '
        'Set TRACKSTATE_TOKEN or authenticate with gh before using '
        'release-backed attachments from a local repository.',
      );
    }
    final provider = await _createHostedReleaseProvider(
      repository: remoteIdentity,
      branch: branch,
    );
    if (provider case final RepositoryReleaseAttachmentStore store) {
      return store;
    }
    throw TrackStateProviderException(
      'GitHub release uploads are not supported for $remoteIdentity.',
    );
  }

  Future<TrackStateProviderAdapter> _createHostedReleaseProvider({
    required String repository,
    required String branch,
  }) async {
    final connection = _connection;
    if (connection == null) {
      throw const TrackStateProviderException(
        'GitHub Releases attachment storage requires a connected repository session.',
      );
    }
    final provider = _hostedProviderFactory(
      repository: repository,
      branch: branch,
      dataRef: branch,
    );
    await provider.authenticate(
      RepositoryConnection(
        repository: repository,
        branch: branch,
        token: connection.token,
      ),
    );
    return provider;
  }

  Future<String?> _resolveGitHubRepositoryIdentity() async {
    final remoteNamesResult = await _tryGit(['remote']);
    final remoteNames = remoteNamesResult == null
        ? const <String>[]
        : LineSplitter.split(remoteNamesResult.stdout)
              .map((line) => line.trim())
              .where((line) => line.isNotEmpty)
              .toList(growable: false);
    for (final remoteName in remoteNames) {
      final remoteUrl = (await _tryGit(['remote', 'get-url', remoteName]))
              ?.stdout
              .trim() ??
          '';
      final identity = _githubRepositoryIdentityFromRemoteUrl(remoteUrl);
      if (identity != null) {
        return identity;
      }
    }
    return null;
  }

  Future<String> _gitRemoteFailureReason() async {
    final remoteNamesResult = await _tryGit(['remote']);
    final remoteNames = remoteNamesResult == null
        ? const <String>[]
        : LineSplitter.split(remoteNamesResult.stdout)
              .map((line) => line.trim())
              .where((line) => line.isNotEmpty)
              .toList(growable: false);
    if (remoteNames.isEmpty) {
      return 'GitHub repository identity cannot be resolved from the local Git '
          'configuration because no remote is configured.';
    }
    return 'GitHub repository identity cannot be resolved from the local Git '
        'configuration because no GitHub remote is configured.';
  }

  String? _githubRepositoryIdentityFromRemoteUrl(String remoteUrl) {
    final normalized = remoteUrl.trim();
    if (normalized.isEmpty) {
      return null;
    }
    final match = RegExp(
      r'^(?:https://|ssh://git@|git@)github\.com[:/](?<owner>[^/]+)/(?<repo>[^/]+?)(?:\.git)?/?$',
      caseSensitive: false,
    ).firstMatch(normalized);
    if (match == null) {
      return null;
    }
    final owner = match.namedGroup('owner')?.trim() ?? '';
    final repo = match.namedGroup('repo')?.trim() ?? '';
    if (owner.isEmpty || repo.isEmpty) {
      return null;
    }
    return '$owner/$repo';
  }

  Future<void> _ensurePathClean(String path) async {
    final result = await _runGit(['status', '--porcelain', '--', path]);
    if (result.stdout.trim().isEmpty) {
      return;
    }
    throw TrackStateProviderException(
      'Cannot save $path because it has staged or unstaged local changes. '
      'commit, stash, or clean those local changes before trying again.',
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

  Future<void> _writeTextToWorktree({
    required String path,
    required String content,
  }) async {
    final file = File(_absolutePath(path));
    await _withFileSystemErrorMapping(
      path: path,
      operation: 'write text file',
      action: () async {
        await file.parent.create(recursive: true);
        await file.writeAsString(content);
      },
    );
  }

  Future<void> _writeBytesToWorktree({
    required String path,
    required List<int> bytes,
  }) async {
    final file = File(_absolutePath(path));
    await _withFileSystemErrorMapping(
      path: path,
      operation: 'write binary file',
      action: () async {
        await file.parent.create(recursive: true);
        await file.writeAsBytes(bytes);
      },
    );
  }

  Future<void> _deleteWorktreeFileIfExists(String path) async {
    final file = File(_absolutePath(path));
    await _withFileSystemErrorMapping(
      path: path,
      operation: 'delete file',
      action: () async {
        if (await file.exists()) {
          await file.delete();
        }
      },
    );
  }

  Future<void> _withFileSystemErrorMapping({
    required String path,
    required String operation,
    required Future<void> Function() action,
  }) async {
    try {
      await action();
    } on FileSystemException {
      throw TrackStateProviderException(
        'Local repository could not $operation at $path because the filesystem rejected the change.',
      );
    }
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

  List<RepositoryHistoryCommit> _parseGitHistory(String output) {
    final commits = <RepositoryHistoryCommit>[];
    for (final block in output.split('\x1e')) {
      final trimmed = block.trim();
      if (trimmed.isEmpty) {
        continue;
      }
      final lines = LineSplitter.split(trimmed).toList(growable: false);
      if (lines.isEmpty) {
        continue;
      }
      final metadata = lines.first.split('\x1f');
      if (metadata.length < 5) {
        continue;
      }
      final changes = <RepositoryHistoryFileChange>[];
      for (final line in lines.skip(1)) {
        if (line.trim().isEmpty) {
          continue;
        }
        final columns = line.split('\t');
        final status = columns.first.trim();
        if (status.startsWith('R') && columns.length >= 3) {
          changes.add(
            RepositoryHistoryFileChange(
              path: columns[2],
              previousPath: columns[1],
              changeType: RepositoryHistoryChangeType.renamed,
            ),
          );
          continue;
        }
        if (columns.length < 2) {
          continue;
        }
        changes.add(
          RepositoryHistoryFileChange(
            path: columns[1],
            changeType: switch (status) {
              'A' => RepositoryHistoryChangeType.added,
              'D' => RepositoryHistoryChangeType.removed,
              _ => RepositoryHistoryChangeType.modified,
            },
          ),
        );
      }
      commits.add(
        RepositoryHistoryCommit(
          sha: metadata[0],
          parentSha: metadata[1].trim().isEmpty
              ? null
              : metadata[1].trim().split(' ').first,
          timestamp: metadata[2],
          author: metadata[3],
          message: metadata[4],
          changes: changes,
        ),
      );
    }
    return commits;
  }
}

TrackStateProviderAdapter _defaultLocalGitHostedProviderFactory({
  required String repository,
  required String branch,
  required String dataRef,
}) => GitHubTrackStateProvider(
  repositoryName: repository,
  sourceRef: branch,
  dataRef: dataRef,
);

class _LocalReleaseAttachmentCapability {
  const _LocalReleaseAttachmentCapability.supported()
    : supportsReleaseAttachmentWrites = true,
      failureReason = null;

  const _LocalReleaseAttachmentCapability.unsupported(this.failureReason)
    : supportsReleaseAttachmentWrites = false;

  final bool supportsReleaseAttachmentWrites;
  final String? failureReason;
}

_LfsPointerInfo? _parseLfsPointer(String content) {
  if (!content.contains('version https://git-lfs.github.com/spec/v1')) {
    return null;
  }
  final oidMatch = RegExp(
    r'^oid sha256:([a-f0-9]+)$',
    multiLine: true,
  ).firstMatch(content);
  final sizeMatch = RegExp(
    r'^size (\d+)$',
    multiLine: true,
  ).firstMatch(content);
  return _LfsPointerInfo(
    oid: oidMatch?.group(1),
    sizeBytes: int.tryParse(sizeMatch?.group(1) ?? ''),
  );
}

class _LfsPointerInfo {
  const _LfsPointerInfo({this.oid, this.sizeBytes});

  final String? oid;
  final int? sizeBytes;
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
