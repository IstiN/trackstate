import 'package:trackstate/data/providers/trackstate_provider.dart';

abstract interface class RepositorySyncCheckDriver {
  Future<RepositorySyncCheck> readHostedSyncCheck({int? loadSnapshotDelta});
}
