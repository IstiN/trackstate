import '../../../../../data/repositories/trackstate_repository.dart';
import '../../../../../domain/models/workspace_profile_models.dart';

typedef LocalRepositoryLoader =
    Future<TrackStateRepository> Function({
      required String repositoryPath,
      required String defaultBranch,
      required String writeBranch,
    });

typedef BrowserLocalRepositoryLoader =
    Future<TrackStateRepository?> Function({
      required String repositoryPath,
      required String defaultBranch,
      required String writeBranch,
    });

typedef BrowserLocalRepositoryAccessRequester =
    Future<TrackStateRepository?> Function({
      required String repositoryPath,
      required String defaultBranch,
      required String writeBranch,
    });

typedef HostedRepositoryLoader =
    Future<TrackStateRepository> Function({
      required String repository,
      required String defaultBranch,
      required String writeBranch,
    });

typedef WorkspaceProfileCreator =
    Future<void> Function(WorkspaceProfileInput input);

typedef LocalRepositoryConfigurationApplier =
    Future<void> Function({
      required String repositoryPath,
      required String defaultBranch,
      required String writeBranch,
    });
