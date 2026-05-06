import 'package:http/http.dart' as http;

import 'trackstate_repository.dart';
import 'trackstate_runtime.dart';
import 'trackstate_repository_factory_stub.dart'
    if (dart.library.io) 'trackstate_repository_factory_io.dart'
    as platform;

TrackStateRepository createTrackStateRepository({
  TrackStateRuntime? runtime,
  http.Client? client,
  String? localRepositoryPath,
}) {
  return platform.createPlatformTrackStateRepository(
    runtime: runtime ?? configuredTrackStateRuntime,
    client: client,
    localRepositoryPath: localRepositoryPath,
  );
}
