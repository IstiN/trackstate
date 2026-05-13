import 'package:http/http.dart' as http;

import '../providers/github/github_trackstate_provider.dart';
import '../providers/local/local_git_trackstate_provider.dart';
import 'trackstate_repository.dart';

class LocalTrackStateRepository extends ProviderBackedTrackStateRepository {
  LocalTrackStateRepository({
    required String repositoryPath,
    String dataRef = 'HEAD',
    http.Client? client,
    GitProcessRunner? processRunner,
  }) : super(
          provider: LocalGitTrackStateProvider(
            repositoryPath: repositoryPath,
            dataRef: dataRef,
            processRunner: processRunner,
            hostedProviderFactory: ({
              required String repository,
              required String branch,
              required String dataRef,
            }) => GitHubTrackStateProvider(
              client: client,
              repositoryName: repository,
              sourceRef: branch,
              dataRef: dataRef,
            ),
          ),
          usesLocalPersistence: true,
          supportsGitHubAuth: false,
          githubClient: client,
        );
}
