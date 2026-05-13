import '../providers/local/local_git_trackstate_provider.dart';
import 'trackstate_repository.dart';

class LocalTrackStateRepository extends ProviderBackedTrackStateRepository {
  LocalTrackStateRepository({
    required String repositoryPath,
    String dataRef = 'HEAD',
    super.githubClient,
    GitProcessRunner? processRunner,
  }) : super(
         provider: LocalGitTrackStateProvider(
           repositoryPath: repositoryPath,
           dataRef: dataRef,
           processRunner: processRunner,
         ),
         usesLocalPersistence: true,
         supportsGitHubAuth: false,
       );
}
