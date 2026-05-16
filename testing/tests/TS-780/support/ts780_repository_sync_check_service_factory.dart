import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../../components/services/repository_sync_check_service.dart';
import '../../../frameworks/api/github/github_repository_sync_check_framework.dart';

Future<RepositorySyncCheckService> createTs780RepositorySyncCheckService({
  String repositoryName = 'owner/current',
  String branch = 'main',
  RepositoryConnection connection = const RepositoryConnection(
    repository: 'owner/current',
    branch: 'main',
    token: 'token',
  ),
}) async {
  final driver = await GitHubRepositorySyncCheckFramework.create(
    repositoryName: repositoryName,
    branch: branch,
    connection: connection,
  );
  return RepositorySyncCheckService(driver);
}
