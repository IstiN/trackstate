import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/repository_sync_check_public_payload_probe.dart';

class RepositorySyncCheckPublicPayloadService
    implements RepositorySyncCheckPublicPayloadProbe {
  @override
  Map<String, Object?> serialize(RepositorySyncCheck syncCheck) {
    final payload = <String, Object?>{
      'signals': _signalNames(syncCheck.signals),
      'changed_paths': _sortedPaths(syncCheck.changedPaths),
    };

    final loadSnapshotDelta = switch (syncCheck.hostedSnapshotReloadDirective) {
      HostedSnapshotReloadDirective.enabled => 1,
      HostedSnapshotReloadDirective.disabled => 0,
      null => null,
    };
    if (loadSnapshotDelta != null) {
      payload['load_snapshot_delta'] = loadSnapshotDelta;
    }

    return payload;
  }

  List<String> _signalNames(Set<WorkspaceSyncSignal> signals) =>
      signals.map((signal) => signal.name).toList(growable: false)..sort();

  List<String> _sortedPaths(Set<String> changedPaths) =>
      changedPaths.toList(growable: false)..sort();
}
