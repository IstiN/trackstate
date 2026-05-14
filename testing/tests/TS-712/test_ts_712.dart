import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_sync_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

const String _ticketKey = 'TS-712';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
    'TS-712 workspace sync enforces the 30-second floor and suppresses duplicate resume triggers',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'environment': 'flutter service test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final refreshes = <WorkspaceSyncRefresh>[];
      final statuses = <WorkspaceSyncStatus>[];
      final failures = <String>[];
      final clock = _MutableClock(DateTime.utc(2026, 5, 14, 12, 0, 0));
      final repository = _WorkspaceSyncProbeRepository(now: clock.call);
      final service = WorkspaceSyncService(
        repository: repository,
        loadSnapshot: () async => baseline,
        onRefresh: refreshes.add,
        onStatusChanged: statuses.add,
        now: clock.call,
      );

      try {
        final manualCheckFuture = service.retryNow();
        await repository.waitForCallCount(1);

        _recordStep(
          result,
          step: 1,
          status: repository.callCount == 1 ? 'passed' : 'failed',
          action: 'Force a manual sync check using requestCheck.',
          observed:
              'call_count=${repository.callCount}; triggers=${repository.triggerLabels.join(', ')}; started_at=${repository.startedAt.first.toIso8601String()}',
        );
        if (repository.callCount != 1) {
          failures.add(
            'Step 1 failed: the manual request should start exactly one sync check.\n'
            'Observed call count: ${repository.callCount}\n'
            'Observed triggers: ${repository.triggerLabels.join(', ')}',
          );
        }

        clock.jumpBy(const Duration(seconds: 10));
        final overlapResumeFuture = service.handleAppResume();
        await Future<void>.delayed(Duration.zero);
        await Future<void>.delayed(Duration.zero);

        _recordStep(
          result,
          step: 2,
          status: repository.callCount == 1 ? 'passed' : 'failed',
          action:
              "Wait 10 seconds and simulate an 'app resume' event while the first check is still running.",
          observed:
              'call_count=${repository.callCount}; pending_probe_completion=${!repository.latestCompleter.isCompleted}; triggers=${repository.triggerLabels.join(', ')}',
        );
        if (repository.callCount != 1) {
          failures.add(
            'Step 2 failed: overlapping app-resume triggers should be coalesced while the manual sync is in flight.\n'
            'Observed call count before the first check completed: ${repository.callCount}\n'
            'Observed triggers: ${repository.triggerLabels.join(', ')}',
          );
        }

        final firstCompletedAt = clock.value;
        repository.completeLatest();
        await manualCheckFuture;
        await overlapResumeFuture;
        await Future<void>.delayed(Duration.zero);
        await Future<void>.delayed(Duration.zero);

        _recordStep(
          result,
          step: 3,
          status: repository.callCount == 1 ? 'passed' : 'failed',
          action:
              "Observe the coordinator after the first check completes to confirm a second check does not start inside the 30-second floor.",
          observed:
              'call_count=${repository.callCount}; completed_at=${firstCompletedAt.toIso8601String()}; status_health=${statuses.isEmpty ? 'none' : statuses.last.health.name}',
        );
        if (repository.callCount != 1) {
          failures.add(
            'Step 3 failed: completing the first check should not immediately start a duplicate follow-up inside the 30-second floor.\n'
            'Observed call count right after completion: ${repository.callCount}\n'
            'Observed triggers: ${repository.triggerLabels.join(', ')}\n'
            'Started-at timestamps: ${repository.startedAt.map((value) => value.toIso8601String()).join(', ')}',
          );
        }

        clock.set(firstCompletedAt.add(const Duration(seconds: 10)));
        await service.handleAppResume();
        await Future<void>.delayed(Duration.zero);
        await Future<void>.delayed(Duration.zero);

        _recordStep(
          result,
          step: 4,
          status: repository.callCount == 1 ? 'passed' : 'failed',
          action:
              "Wait 10 seconds since the first check completed and simulate another 'app resume'.",
          observed:
              'call_count=${repository.callCount}; elapsed_since_completion=${clock.value.difference(firstCompletedAt).inSeconds}s',
        );
        if (repository.callCount != 1) {
          failures.add(
            'Step 4 failed: the 10-second app-resume trigger should be suppressed by the 30-second minimum interval.\n'
            'Observed call count: ${repository.callCount}\n'
            'Elapsed since first completion: ${clock.value.difference(firstCompletedAt).inSeconds}s\n'
            'Observed triggers: ${repository.triggerLabels.join(', ')}',
          );
        }

        clock.set(firstCompletedAt.add(const Duration(seconds: 35)));
        final postFloorResumeFuture = service.handleAppResume();
        await repository.waitForCallCount(2);

        _recordStep(
          result,
          step: 5,
          status: repository.callCount == 2 ? 'passed' : 'failed',
          action:
              "Wait 35 seconds since the first check completed and simulate another 'app resume'.",
          observed:
              'call_count=${repository.callCount}; elapsed_since_completion=${clock.value.difference(firstCompletedAt).inSeconds}s; second_started_at=${repository.startedAt.length > 1 ? repository.startedAt[1].toIso8601String() : 'not-started'}',
        );
        if (repository.callCount != 2) {
          failures.add(
            'Step 5 failed: once 35 seconds have elapsed since the first completion, the next app-resume trigger should start a new sync immediately.\n'
            'Observed call count: ${repository.callCount}\n'
            'Elapsed since first completion: ${clock.value.difference(firstCompletedAt).inSeconds}s',
          );
        }

        repository.completeLatest();
        await postFloorResumeFuture;
        await Future<void>.delayed(Duration.zero);

        final matchingExpectedResult =
            failures.isEmpty &&
            repository.callCount == 2 &&
            refreshes.isEmpty &&
            statuses.isNotEmpty &&
            statuses.last.health == WorkspaceSyncHealth.synced;
        _recordHumanVerification(
          result,
          check:
              'Observed the production WorkspaceSyncService the same way an integrated client would observe it: by watching whether a real repository sync started when manual and app-resume triggers were fired.',
          observed:
              'trigger_sequence=${repository.triggerLabels.join(' -> ')}; started_at=${repository.startedAt.map((value) => value.toIso8601String()).join(' | ')}; final_health=${statuses.isEmpty ? 'none' : statuses.last.health.name}; matched_expected=$matchingExpectedResult',
        );
        result['matched_expected_result'] = matchingExpectedResult;

        if (failures.isNotEmpty) {
          result['failures'] = failures;
          throw AssertionError(failures.join('\n'));
        }

        print('TS-712:${jsonEncode(result)}');
      } finally {
        service.dispose();
        repository.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

void _recordStep(
  Map<String, Object?> result, {
  required int step,
  required String status,
  required String action,
  required String observed,
}) {
  final steps = result['steps']! as List<Map<String, Object?>>;
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
  final verifications =
      result['human_verification']! as List<Map<String, Object?>>;
  verifications.add(<String, Object?>{'check': check, 'observed': observed});
}

class _MutableClock {
  _MutableClock(this.value);

  DateTime value;

  DateTime call() => value;

  void jumpBy(Duration offset) {
    value = value.add(offset);
  }

  void set(DateTime next) {
    value = next;
  }
}

class _WorkspaceSyncProbeRepository implements WorkspaceSyncRepository {
  _WorkspaceSyncProbeRepository({required DateTime Function() now})
    : _now = now;

  final DateTime Function() _now;
  final List<String> triggerLabels = <String>[];
  final List<DateTime> startedAt = <DateTime>[];
  final List<Completer<RepositorySyncCheck>> _pendingChecks =
      <Completer<RepositorySyncCheck>>[];
  final List<Timer> _timers = <Timer>[];

  int get callCount => startedAt.length;

  Completer<RepositorySyncCheck> get latestCompleter => _pendingChecks.last;

  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositorySyncCheck> checkSync({RepositorySyncState? previousState}) {
    startedAt.add(_now());
    triggerLabels.add(
      previousState == null ? 'manual-request' : 'resume-follow-up',
    );
    final completer = Completer<RepositorySyncCheck>();
    _pendingChecks.add(completer);
    return completer.future;
  }

  Future<void> waitForCallCount(int expected) {
    if (callCount >= expected) {
      return Future<void>.value();
    }
    final completer = Completer<void>();
    late Timer timer;
    timer = Timer.periodic(const Duration(milliseconds: 1), (_) {
      if (callCount >= expected && !completer.isCompleted) {
        timer.cancel();
        completer.complete();
      }
    });
    _timers.add(timer);
    return completer.future;
  }

  void completeLatest() {
    if (_pendingChecks.isEmpty) {
      throw StateError('No pending sync check exists.');
    }
    final completer = _pendingChecks.removeLast();
    if (!completer.isCompleted) {
      completer.complete(
        const RepositorySyncCheck(
          state: RepositorySyncState(
            providerType: ProviderType.github,
            repositoryRevision: 'ts712-rev',
            sessionRevision: 'ts712-session',
            connectionState: ProviderConnectionState.connected,
          ),
        ),
      );
    }
  }

  void dispose() {
    for (final timer in _timers) {
      timer.cancel();
    }
    for (final completer in _pendingChecks) {
      if (!completer.isCompleted) {
        completer.complete(
          const RepositorySyncCheck(
            state: RepositorySyncState(
              providerType: ProviderType.github,
              repositoryRevision: 'ts712-disposed',
              sessionRevision: 'ts712-disposed',
              connectionState: ProviderConnectionState.connected,
            ),
          ),
        );
      }
    }
  }
}
