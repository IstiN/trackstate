import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class LocalGitWorkspaceSyncRuntime {
  Future<TrackerSnapshot> loadSnapshot();

  void updateBaselineSnapshot(TrackerSnapshot snapshot);

  Future<void> checkNow({bool force = false});

  WorkspaceSyncStatus get status;

  int get refreshCount;

  void dispose();
}
