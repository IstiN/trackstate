import 'package:trackstate/data/services/workspace_sync_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class WorkspaceSyncCadenceProbe {
  DateTime get now;

  int get callCount;

  bool get latestCheckPending;

  List<String> get triggerLabels;

  List<DateTime> get startedAt;

  List<WorkspaceSyncRefresh> get refreshes;

  List<WorkspaceSyncStatus> get statuses;

  void advanceClockBy(Duration offset);

  void completeLatestSyncCheck();

  Future<void> requestManualSync();

  void setClock(DateTime next);

  Future<void> settle();

  Future<void> simulateAppResume();

  Future<void> waitForSyncStarts(int expected);

  void dispose();
}
