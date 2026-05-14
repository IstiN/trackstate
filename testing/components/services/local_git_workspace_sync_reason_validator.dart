import 'dart:io';

import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/local_git_workspace_sync_reason_probe.dart';
import '../../core/interfaces/local_git_workspace_sync_runtime_factory.dart';
import '../../core/models/local_git_workspace_sync_reason_observation.dart';
import '../../core/utils/local_git_repository_fixture.dart';

class LocalGitWorkspaceSyncReasonValidator
    implements LocalGitWorkspaceSyncReasonProbe {
  LocalGitWorkspaceSyncReasonValidator({
    required Future<LocalGitRepositoryFixture> Function() createFixture,
    required LocalGitWorkspaceSyncRuntimeFactory syncRuntimeFactory,
  }) : _createFixture = createFixture,
       _syncRuntimeFactory = syncRuntimeFactory;

  static const String issuePath = 'DEMO/DEMO-1/main.md';
  static const String headChangeCommitSubject = 'TS-713 local head change';

  final Future<LocalGitRepositoryFixture> Function() _createFixture;
  final LocalGitWorkspaceSyncRuntimeFactory _syncRuntimeFactory;

  @override
  Future<LocalGitWorkspaceSyncReasonObservation> runScenario() async {
    final fixture = await _createFixture();
    final issueFile = File('${fixture.directory.path}/$issuePath');
    final syncRuntime = await _syncRuntimeFactory.create(
      repositoryPath: fixture.directory.path,
    );

    try {
      final baselineSnapshot = await syncRuntime.loadSnapshot();
      syncRuntime.updateBaselineSnapshot(baselineSnapshot);
      await syncRuntime.checkNow(force: true);

      final initialResult = syncRuntime.status.lastResult;
      if (initialResult == null ||
          initialResult.hasChanges ||
          syncRuntime.refreshCount != 0) {
        throw StateError(
          'Precondition failed: the initial background sync check should establish a clean baseline without reporting any domains.\n'
          'Observed signals: ${_signalNames(initialResult?.signals ?? const <WorkspaceSyncSignal>{})}\n'
          'Observed domains: ${_domainNames(initialResult?.changedDomains ?? const <WorkspaceSyncDomain>{})}\n'
          'Observed refresh count: ${syncRuntime.refreshCount}',
        );
      }

      final initialHeadRevision = await _gitOutput(fixture.directory.path, [
        'rev-parse',
        'HEAD',
      ]);
      final initialIssueContent = await issueFile.readAsString();
      await issueFile.writeAsString(
        '$initialIssueContent\nCommitted local head change for TS-713.\n',
      );
      await fixture.stageAll();
      await fixture.commit(headChangeCommitSubject);

      final headChangeRevision = await _gitOutput(fixture.directory.path, [
        'rev-parse',
        'HEAD',
      ]);
      final headRefreshCount = syncRuntime.refreshCount;
      await syncRuntime.checkNow(force: true);
      final headCheck = _captureCheckObservation(
        syncRuntime.status,
        refreshesBefore: headRefreshCount,
        refreshesAfter: syncRuntime.refreshCount,
      );

      final committedIssueContent = await issueFile.readAsString();
      await issueFile.writeAsString(
        '$committedIssueContent\nDirty local worktree change for TS-713.\n',
      );
      final worktreeStatusLines = await _gitLines(fixture.directory.path, [
        'status',
        '--short',
        '--untracked-files=all',
      ]);
      final worktreeRefreshCount = syncRuntime.refreshCount;
      await syncRuntime.checkNow(force: true);
      final worktreeCheck = _captureCheckObservation(
        syncRuntime.status,
        refreshesBefore: worktreeRefreshCount,
        refreshesAfter: syncRuntime.refreshCount,
      );

      return LocalGitWorkspaceSyncReasonObservation(
        repositoryPath: fixture.directory.path,
        issuePath: issuePath,
        initialHeadRevision: initialHeadRevision,
        headChangeRevision: headChangeRevision,
        headChangeCommitSubject: headChangeCommitSubject,
        headCheck: headCheck,
        worktreeStatusLines: worktreeStatusLines,
        worktreeCheck: worktreeCheck,
      );
    } finally {
      syncRuntime.dispose();
      await fixture.dispose();
    }
  }

  LocalGitWorkspaceSyncCheckObservation _captureCheckObservation(
    WorkspaceSyncStatus status, {
    required int refreshesBefore,
    required int refreshesAfter,
  }) {
    final result = status.lastResult;
    if (result == null) {
      throw StateError(
        'Workspace sync status did not publish a lastResult after a forced sync check.',
      );
    }
    return LocalGitWorkspaceSyncCheckObservation(
      result: result,
      statusHealth: status.health,
      reasons: _reasonLabels(result.signals),
      refreshTriggered: refreshesAfter > refreshesBefore,
    );
  }

  List<String> _reasonLabels(Set<WorkspaceSyncSignal> signals) {
    final labels = <String>[];
    for (final signal in WorkspaceSyncSignal.values) {
      if (!signals.contains(signal)) {
        continue;
      }
      labels.add(switch (signal) {
        WorkspaceSyncSignal.localHead => 'local head change',
        WorkspaceSyncSignal.localWorktree => 'local worktree change',
        WorkspaceSyncSignal.hostedRepository => 'hosted repository change',
        WorkspaceSyncSignal.hostedSession => 'hosted session change',
      });
    }
    return labels;
  }

  static List<String> _signalNames(Set<WorkspaceSyncSignal> signals) =>
      signals.map((signal) => signal.name).toList(growable: false)..sort();

  static List<String> _domainNames(Set<WorkspaceSyncDomain> domains) =>
      domains.map((domain) => domain.name).toList(growable: false)..sort();

  Future<String> _gitOutput(String repositoryPath, List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }

  Future<List<String>> _gitLines(
    String repositoryPath,
    List<String> args,
  ) async {
    final output = await _gitOutput(repositoryPath, args);
    if (output.isEmpty) {
      return const <String>[];
    }
    return output
        .split('\n')
        .map((line) => line.trimRight())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }
}
