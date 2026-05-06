import 'package:http/http.dart' as http;

import 'local_trackstate_repository.dart';
import 'trackstate_repository.dart';
import 'trackstate_runtime.dart';

TrackStateRepository createPlatformTrackStateRepository({
  required TrackStateRuntime runtime,
  http.Client? client,
  String? localRepositoryPath,
}) {
  return switch (runtime) {
    TrackStateRuntime.github => SetupTrackStateRepository(client: client),
    TrackStateRuntime.localGit => LocalTrackStateRepository(
      repositoryPath:
          (localRepositoryPath ?? configuredLocalRepositoryPath).trim().isEmpty
          ? '.'
          : (localRepositoryPath ?? configuredLocalRepositoryPath).trim(),
    ),
  };
}
