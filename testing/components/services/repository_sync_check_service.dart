import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/repository_sync_check_driver.dart';
import '../../frameworks/api/github/github_repository_sync_check_framework.dart';

class RepositorySyncCheckService {
  const RepositorySyncCheckService(this._driver);

  final RepositorySyncCheckDriver _driver;

  static Future<RepositorySyncCheckService> create({
    RepositorySyncCheckDriver? driver,
    String repositoryName = 'owner/current',
    String branch = 'main',
    RepositoryConnection connection = const RepositoryConnection(
      repository: 'owner/current',
      branch: 'main',
      token: 'token',
    ),
  }) async {
    return RepositorySyncCheckService(
      driver ??
          await GitHubRepositorySyncCheckFramework.create(
            repositoryName: repositoryName,
            branch: branch,
            connection: connection,
          ),
    );
  }

  Future<RepositorySyncCheck> readHostedSyncCheck({int? loadSnapshotDelta}) {
    return _driver.readHostedSyncCheck(loadSnapshotDelta: loadSnapshotDelta);
  }
}
