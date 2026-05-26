import 'package:trackstate/data/providers/trackstate_provider.dart';

import '../../core/interfaces/repository_sync_check_driver.dart';

class RepositorySyncCheckService {
  const RepositorySyncCheckService(this._driver);

  final RepositorySyncCheckDriver _driver;

  Future<RepositorySyncCheck> readHostedSyncCheck({int? loadSnapshotDelta}) {
    return _driver.readHostedSyncCheck(loadSnapshotDelta: loadSnapshotDelta);
  }
}
