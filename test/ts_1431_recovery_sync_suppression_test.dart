import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'unauthenticated hosted startup recovery does not start background workspace sync',
    () async {
      final counts = <String, int>{};
      final repository = _buildMockRepository(
        counts,
        issuesJsonDelay: Duration.zero,
      );
      final viewModel = TrackerViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.load();
      expect(viewModel.hasStartupRecovery, isTrue);
      expect(viewModel.isConnected, isFalse);

      final baselineCount = counts['/repos/istin/trackstate-setup/branches/main'] ?? 0;
      expect(baselineCount, 0, reason: 'sync should not make branch request during recovery');

      await viewModel.handleAppResumed();
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(
        counts['/repos/istin/trackstate-setup/branches/main'] ?? 0,
        baselineCount,
        reason: 'app resume must not trigger a sync check while unauthenticated recovery is active',
      );
    },
  );

  test(
    'hosted startup fallback snapshot suppresses background workspace sync even when timeout fires before rate-limit response',
    () async {
      final counts = <String, int>{};
      final repository = _buildMockRepository(
        counts,
        probeTimeout: const Duration(milliseconds: 50),
        issuesJsonDelay: const Duration(milliseconds: 200),
      );
      final viewModel = TrackerViewModel(repository: repository);
      addTearDown(viewModel.dispose);

      await viewModel.load();
      // The snapshot is a fallback because the timeout fired before the 403.
      // Sync must still be suppressed because the snapshot is a fallback.
      expect(
        counts['/repos/istin/trackstate-setup/branches/main'] ?? 0,
        0,
        reason: 'sync should not make branch request during fallback startup',
      );

      await viewModel.handleAppResumed();
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(
        counts['/repos/istin/trackstate-setup/branches/main'] ?? 0,
        0,
        reason: 'app resume must not trigger a sync check while hosted startup fallback is active',
      );
    },
  );
}

TrackStateRepository _buildMockRepository(
  Map<String, int> counts, {
  Duration? probeTimeout,
  Duration? issuesJsonDelay,
}) {
  const repo = 'istin/trackstate-setup';
  const branch = 'main';
  const dataRoot = 'DEMO';
  const tree = {
    'tree': [
      {'path': 'DEMO/project.json', 'type': 'blob'},
      {'path': 'DEMO/config/statuses.json', 'type': 'blob'},
      {'path': 'DEMO/config/issue-types.json', 'type': 'blob'},
      {'path': 'DEMO/config/fields.json', 'type': 'blob'},
      {'path': 'DEMO/config/workflows.json', 'type': 'blob'},
      {'path': 'DEMO/config/priorities.json', 'type': 'blob'},
      {'path': 'DEMO/.trackstate/index/issues.json', 'type': 'blob'},
      {'path': 'DEMO/DEMO-1/main.md', 'type': 'blob'},
    ],
  };
  const projectJson = '{"key":"DEMO","name":"Demo","defaultLocale":"en"}';
  const statusesJson = '[{"id":"todo","name":"To Do","category":"new"}]';
  const issueTypesJson = '[{"id":"story","name":"Story","workflowId":"default","hierarchyLevel":0}]';
  const fieldsJson = '[{"id":"summary","name":"Summary","type":"string","required":true,"reserved":true}]';
  const workflowsJson = '{"default":{"name":"Default","statuses":["todo"],"transitions":[]}}';
  const prioritiesJson = '[]';

  final effectiveIssuesJsonDelay = issuesJsonDelay ?? Duration.zero;

  return SetupTrackStateRepository(
    client: MockClient((request) async {
      final path = request.url.path;
      counts[path] = (counts[path] ?? 0) + 1;

      if (path == '/repos/$repo/git/trees/$branch') {
        return http.Response(jsonEncode(tree), 200);
      }
      if (path == '/repos/$repo/contents/$dataRoot/project.json') {
        return http.Response(jsonEncode({'content': base64Encode(utf8.encode(projectJson)), 'sha': 'p'}), 200);
      }
      if (path == '/repos/$repo/contents/$dataRoot/config/statuses.json') {
        return http.Response(jsonEncode({'content': base64Encode(utf8.encode(statusesJson)), 'sha': 's'}), 200);
      }
      if (path == '/repos/$repo/contents/$dataRoot/config/issue-types.json') {
        return http.Response(jsonEncode({'content': base64Encode(utf8.encode(issueTypesJson)), 'sha': 'i'}), 200);
      }
      if (path == '/repos/$repo/contents/$dataRoot/config/fields.json') {
        return http.Response(jsonEncode({'content': base64Encode(utf8.encode(fieldsJson)), 'sha': 'f'}), 200);
      }
      if (path == '/repos/$repo/contents/$dataRoot/config/workflows.json') {
        return http.Response(jsonEncode({'content': base64Encode(utf8.encode(workflowsJson)), 'sha': 'w'}), 200);
      }
      if (path == '/repos/$repo/contents/$dataRoot/config/priorities.json') {
        return http.Response(jsonEncode({'content': base64Encode(utf8.encode(prioritiesJson)), 'sha': 'pr'}), 200);
      }
      if (path == '/repos/$repo/contents/$dataRoot/.trackstate/index/issues.json') {
        if (effectiveIssuesJsonDelay > Duration.zero) {
          await Future<void>.delayed(effectiveIssuesJsonDelay);
        }
        return http.Response(
          jsonEncode({'message': 'API rate limit exceeded'}),
          403,
        );
      }
      return http.Response('not found', 404);
    }),
    repositoryName: repo,
    sourceRef: branch,
    dataRef: branch,
    hostedStartupProbeTimeout: probeTimeout ?? const Duration(seconds: 11),
  );
}
