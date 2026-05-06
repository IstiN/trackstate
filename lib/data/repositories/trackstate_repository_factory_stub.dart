import 'package:http/http.dart' as http;

import 'trackstate_repository.dart';
import 'trackstate_runtime.dart';

TrackStateRepository createPlatformTrackStateRepository({
  required TrackStateRuntime runtime,
  http.Client? client,
  String? localRepositoryPath,
}) {
  if (runtime == TrackStateRuntime.localGit) {
    throw UnsupportedError(
      'The local Git runtime is not available in web builds. Use the hosted GitHub runtime.',
    );
  }
  return SetupTrackStateRepository(client: client);
}
