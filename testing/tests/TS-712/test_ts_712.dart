import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/services/workspace_sync_cadence_service_probe.dart';
import '../../core/interfaces/workspace_sync_cadence_probe.dart';

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

      final failures = <String>[];
      final WorkspaceSyncCadenceProbe probe =
          await WorkspaceSyncCadenceServiceProbe.create(
            initialNow: DateTime.utc(2026, 5, 14, 12, 0, 0),
          );

      try {
        await probe.requestManualSync();
        await probe.waitForSyncStarts(1);

        _recordStep(
          result,
          step: 1,
          status: probe.callCount == 1 ? 'passed' : 'failed',
          action: 'Force a manual sync check using requestCheck.',
          observed:
              'call_count=${probe.callCount}; triggers=${probe.triggerLabels.join(', ')}; started_at=${probe.startedAt.first.toIso8601String()}',
        );
        if (probe.callCount != 1) {
          failures.add(
            'Step 1 failed: the manual request should start exactly one sync check.\n'
            'Observed call count: ${probe.callCount}\n'
            'Observed triggers: ${probe.triggerLabels.join(', ')}',
          );
        }

        probe.advanceClockBy(const Duration(seconds: 10));
        await probe.simulateAppResume();

        _recordStep(
          result,
          step: 2,
          status: probe.callCount == 1 ? 'passed' : 'failed',
          action:
              "Wait 10 seconds and simulate an 'app resume' event while the first check is still running.",
          observed:
              'call_count=${probe.callCount}; pending_probe_completion=${probe.latestCheckPending}; triggers=${probe.triggerLabels.join(', ')}',
        );
        if (probe.callCount != 1) {
          failures.add(
            'Step 2 failed: overlapping app-resume triggers should be coalesced while the manual sync is in flight.\n'
            'Observed call count before the first check completed: ${probe.callCount}\n'
            'Observed triggers: ${probe.triggerLabels.join(', ')}',
          );
        }

        final firstCompletedAt = probe.now;
        probe.completeLatestSyncCheck();
        await probe.settle();

        _recordStep(
          result,
          step: 3,
          status: probe.callCount == 1 ? 'passed' : 'failed',
          action:
              "Observe the coordinator after the first check completes to confirm a second check does not start inside the 30-second floor.",
          observed:
              'call_count=${probe.callCount}; completed_at=${firstCompletedAt.toIso8601String()}; status_health=${probe.statuses.isEmpty ? 'none' : probe.statuses.last.health.name}',
        );
        if (probe.callCount != 1) {
          failures.add(
            'Step 3 failed: completing the first check should not immediately start a duplicate follow-up inside the 30-second floor.\n'
            'Observed call count right after completion: ${probe.callCount}\n'
            'Observed triggers: ${probe.triggerLabels.join(', ')}\n'
            'Started-at timestamps: ${probe.startedAt.map((value) => value.toIso8601String()).join(', ')}',
          );
        }

        probe.setClock(firstCompletedAt.add(const Duration(seconds: 10)));
        await probe.simulateAppResume();

        _recordStep(
          result,
          step: 4,
          status: probe.callCount == 1 ? 'passed' : 'failed',
          action:
              "Wait 10 seconds since the first check completed and simulate another 'app resume'.",
          observed:
              'call_count=${probe.callCount}; elapsed_since_completion=${probe.now.difference(firstCompletedAt).inSeconds}s',
        );
        if (probe.callCount != 1) {
          failures.add(
            'Step 4 failed: the 10-second app-resume trigger should be suppressed by the 30-second minimum interval.\n'
            'Observed call count: ${probe.callCount}\n'
            'Elapsed since first completion: ${probe.now.difference(firstCompletedAt).inSeconds}s\n'
            'Observed triggers: ${probe.triggerLabels.join(', ')}',
          );
        }

        probe.setClock(firstCompletedAt.add(const Duration(seconds: 35)));
        await probe.simulateAppResume();
        await probe.waitForSyncStarts(2);

        _recordStep(
          result,
          step: 5,
          status: probe.callCount == 2 ? 'passed' : 'failed',
          action:
              "Wait 35 seconds since the first check completed and simulate another 'app resume'.",
          observed:
              'call_count=${probe.callCount}; elapsed_since_completion=${probe.now.difference(firstCompletedAt).inSeconds}s; second_started_at=${probe.startedAt.length > 1 ? probe.startedAt[1].toIso8601String() : 'not-started'}',
        );
        if (probe.callCount != 2) {
          failures.add(
            'Step 5 failed: once 35 seconds have elapsed since the first completion, the next app-resume trigger should start a new sync immediately.\n'
            'Observed call count: ${probe.callCount}\n'
            'Elapsed since first completion: ${probe.now.difference(firstCompletedAt).inSeconds}s',
          );
        }

        probe.completeLatestSyncCheck();
        await probe.settle();

        final matchingExpectedResult =
            failures.isEmpty &&
            probe.callCount == 2 &&
            probe.refreshes.isEmpty &&
            probe.statuses.isNotEmpty &&
            probe.statuses.last.health == WorkspaceSyncHealth.synced;
        _recordHumanVerification(
          result,
          check:
              'Observed the production WorkspaceSyncService the same way an integrated client would observe it: by watching whether a real repository sync started when manual and app-resume triggers were fired.',
          observed:
              'trigger_sequence=${probe.triggerLabels.join(' -> ')}; started_at=${probe.startedAt.map((value) => value.toIso8601String()).join(' | ')}; final_health=${probe.statuses.isEmpty ? 'none' : probe.statuses.last.health.name}; matched_expected=$matchingExpectedResult',
        );
        result['matched_expected_result'] = matchingExpectedResult;

        if (failures.isNotEmpty) {
          result['failures'] = failures;
          throw AssertionError(failures.join('\n'));
        }

        print('TS-712:${jsonEncode(result)}');
      } finally {
        probe.dispose();
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
