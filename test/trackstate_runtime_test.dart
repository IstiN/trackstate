import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';

void main() {
  test('runtime parser accepts explicit runtime names', () {
    expect(parseTrackStateRuntime('github'), TrackStateRuntime.github);
    expect(parseTrackStateRuntime('local-git'), TrackStateRuntime.localGit);
    expect(parseTrackStateRuntime('git'), TrackStateRuntime.localGit);
  });

  test('runtime parser rejects unsupported values', () {
    expect(() => parseTrackStateRuntime('svn'), throwsArgumentError);
  });

  test('repository factory builds the requested adapter-backed repository', () {
    final hosted = createTrackStateRepository(
      runtime: TrackStateRuntime.github,
    );
    final local = createTrackStateRepository(
      runtime: TrackStateRuntime.localGit,
      localRepositoryPath: '.',
    );

    expect(hosted, isA<SetupTrackStateRepository>());
    expect(local, isA<LocalTrackStateRepository>());
  });
}
