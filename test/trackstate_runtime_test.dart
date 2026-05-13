import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

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

  test(
    'repository factory threads the shared client into local release downloads',
    () async {
      final repositoryDir = await Directory.systemTemp.createTemp(
        'trackstate-runtime-',
      );
      addTearDown(() => repositoryDir.delete(recursive: true));

      Future<void> runGit(List<String> arguments) async {
        final result = await Process.run(
          'git',
          arguments,
          workingDirectory: repositoryDir.path,
        );
        if (result.exitCode != 0) {
          throw StateError(
            'git ${arguments.join(' ')} failed: ${result.stderr}',
          );
        }
      }

      await runGit(const <String>['init']);
      await runGit(const <String>[
        'remote',
        'add',
        'origin',
        'https://github.com/trackstate-test-owner/trackstate-test-repo.git',
      ]);

      final repository = createTrackStateRepository(
        runtime: TrackStateRuntime.localGit,
        client: MockClient((request) async {
          expect(
            request.url.path,
            '/repos/trackstate-test-owner/trackstate-test-repo/releases/assets/asset-1',
          );
          expect(request.headers['accept'], 'application/octet-stream');
          return http.Response.bytes(const <int>[1, 2, 3, 4], 200);
        }),
        localRepositoryPath: repositoryDir.path,
      );

      final bytes = await repository.downloadAttachment(
        const IssueAttachment(
          id: 'TRACK/TRACK-1/attachments/manual.pdf',
          name: 'manual.pdf',
          mediaType: 'application/pdf',
          sizeBytes: 4,
          author: 'tester',
          createdAt: '2026-05-13T00:00:00Z',
          storagePath: 'TRACK/TRACK-1/attachments/manual.pdf',
          revisionOrOid: 'asset-1',
          storageBackend: AttachmentStorageMode.githubReleases,
          githubReleaseTag: 'v1.0.0',
          githubReleaseAssetName: 'manual.pdf',
        ),
      );

      expect(bytes, Uint8List.fromList(const <int>[1, 2, 3, 4]));
    },
  );
}
