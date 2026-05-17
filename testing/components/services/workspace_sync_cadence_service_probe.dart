import 'dart:async';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_sync_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/workspace_sync_cadence_probe.dart';

class WorkspaceSyncCadenceServiceProbe implements WorkspaceSyncCadenceProbe {
  WorkspaceSyncCadenceServiceProbe._({
    required _MutableClock clock,
    required _WorkspaceSyncProbeRepository repository,
    required WorkspaceSyncService service,
    required List<WorkspaceSyncRefresh> refreshes,
    required List<WorkspaceSyncStatus> statuses,
  }) : _clock = clock,
       _repository = repository,
       _service = service,
       _refreshes = refreshes,
       _statuses = statuses;

  static Future<WorkspaceSyncCadenceServiceProbe> create({
    required DateTime initialNow,
  }) async {
    final baseline = await const DemoTrackStateRepository().loadSnapshot();
    final refreshes = <WorkspaceSyncRefresh>[];
    final statuses = <WorkspaceSyncStatus>[];
    final clock = _MutableClock(initialNow);
    final repository = _WorkspaceSyncProbeRepository(now: clock.call);
    final service = WorkspaceSyncService(
      repository: repository,
      loadSnapshot: () async => baseline,
      onRefresh: refreshes.add,
      onStatusChanged: statuses.add,
      now: clock.call,
    );
    return WorkspaceSyncCadenceServiceProbe._(
      clock: clock,
      repository: repository,
      service: service,
      refreshes: refreshes,
      statuses: statuses,
    );
  }

  final _MutableClock _clock;
  final _WorkspaceSyncProbeRepository _repository;
  final WorkspaceSyncService _service;
  final List<WorkspaceSyncRefresh> _refreshes;
  final List<WorkspaceSyncStatus> _statuses;
  final List<Future<void>> _pendingTriggers = <Future<void>>[];

  @override
  int get callCount => _repository.callCount;

  @override
  bool get latestCheckPending => _repository.latestCheckPending;

  @override
  DateTime get now => _clock.value;

  @override
  List<WorkspaceSyncRefresh> get refreshes => List.unmodifiable(_refreshes);

  @override
  List<DateTime> get startedAt => List.unmodifiable(_repository.startedAt);

  @override
  List<WorkspaceSyncStatus> get statuses => List.unmodifiable(_statuses);

  @override
  List<String> get triggerLabels =>
      List.unmodifiable(_repository.triggerLabels);

  @override
  void advanceClockBy(Duration offset) {
    _clock.jumpBy(offset);
  }

  @override
  void completeLatestSyncCheck() {
    _repository.completeLatest();
  }

  @override
  Future<void> requestManualSync() async {
    _trackTrigger(_service.retryNow());
    await _flushMicrotasks();
  }

  @override
  void setClock(DateTime next) {
    _clock.set(next);
  }

  @override
  Future<void> settle() async {
    while (_pendingTriggers.isNotEmpty) {
      final pending = List<Future<void>>.from(_pendingTriggers);
      await Future.wait(pending);
      await _flushMicrotasks();
    }
    await _flushMicrotasks();
  }

  @override
  Future<void> simulateAppResume() async {
    _trackTrigger(_service.handleAppResume());
    await _flushMicrotasks();
  }

  @override
  Future<void> waitForSyncStarts(int expected) {
    return _repository.waitForCallCount(expected);
  }

  @override
  void dispose() {
    _service.dispose();
    _repository.dispose();
  }

  void _trackTrigger(Future<void> trigger) {
    _pendingTriggers.add(trigger);
    trigger.whenComplete(() {
      _pendingTriggers.remove(trigger);
    });
  }

  Future<void> _flushMicrotasks() async {
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);
  }
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

  bool get latestCheckPending =>
      _pendingChecks.isNotEmpty && !_pendingChecks.last.isCompleted;

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
