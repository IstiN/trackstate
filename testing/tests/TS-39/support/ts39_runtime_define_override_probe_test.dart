import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';

void main() {
  test('explicit runtime define switches startup to Local Git on VM', () {
    final repository = createTrackStateRepository();
    expect(configuredTrackStateRuntimeName, 'local-git');
    expect(configuredTrackStateRuntime, TrackStateRuntime.localGit);
    expect(repository.runtimeType.toString(), 'LocalTrackStateRepository');
    expect(repository.usesLocalPersistence, isTrue);
    expect(repository.supportsGitHubAuth, isFalse);

    // ignore: avoid_print
    print(
      'TS39_OVERRIDE_RESULT:${jsonEncode({
        'configuredRuntimeName': configuredTrackStateRuntimeName,
        'repositoryType': repository.runtimeType.toString(),
        'usesLocalPersistence': repository.usesLocalPersistence,
        'supportsGitHubAuth': repository.supportsGitHubAuth,
      })}',
    );
  });
}
