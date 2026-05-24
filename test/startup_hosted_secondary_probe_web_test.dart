@TestOn('browser')
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'web hosted startup renders the shell before delayed project metadata completes',
    (tester) async {
      const workspaceId = 'hosted:stable/repo@main';
      const authStore = SharedPreferencesTrackStateAuthStore();
      final workspaceProfiles = SharedPreferencesWorkspaceProfileService(
        authStore: authStore,
      );
      await workspaceProfiles.createProfile(
        const WorkspaceProfileInput(
          targetType: WorkspaceProfileTargetType.hosted,
          target: 'stable/repo',
          defaultBranch: 'main',
          displayName: 'Hosted setup workspace',
        ),
      );
      await authStore.saveToken('github-token', workspaceId: workspaceId);

      final harness = _HostedSecondaryProbeHarness();

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });
      addTearDown(() async {
        await tester.pump(const Duration(seconds: 31));
        await tester.pump();
      });

      await tester.pumpWidget(
        TrackStateApp(
          workspaceProfileService: workspaceProfiles,
          authStore: authStore,
          openHostedRepository:
              ({
                required String repository,
                required String defaultBranch,
                required String writeBranch,
              }) async => SetupTrackStateRepository(
                client: MockClient(harness.handle),
                repositoryName: repository,
                dataRef: defaultBranch,
                sourceRef: writeBranch,
              ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(seconds: 11));
      await tester.pump();

      expect(
        find.byKey(const ValueKey('workspace-switcher-trigger')),
        findsOneWidget,
      );
      expect(find.text('Dashboard'), findsWidgets);
      expect(
        find.text('Git-native. Jira-compatible. Team-proven.'),
        findsWidgets,
      );
      expect(harness.delayedProjectJsonCompleted, isFalse);
    },
  );
}

class _HostedSecondaryProbeHarness {
  bool delayedProjectJsonCompleted = false;

  Future<http.Response> handle(http.Request request) async {
    final path = request.url.path;
    final ref = request.url.queryParameters['ref'] ?? '';
    switch (path) {
      case '/repos/stable/repo':
        return http.Response(
          jsonEncode({
            'full_name': 'stable/repo',
            'permissions': <String, Object?>{
              'pull': true,
              'push': true,
              'admin': false,
            },
          }),
          200,
        );
      case '/user':
        await Future<void>.delayed(const Duration(seconds: 1));
        return http.Response(
          jsonEncode({
            'login': 'demo-user',
            'name': 'Demo User',
            'id': 1,
            'email': 'demo@example.com',
          }),
          200,
        );
      case '/repos/stable/repo/branches/main':
        return http.Response(
          jsonEncode({
            'name': 'main',
            'commit': <String, Object?>{'sha': 'mock-revision'},
          }),
          200,
        );
      case '/repos/stable/repo/git/trees/main':
        return http.Response(
          jsonEncode({
            'tree': [
              {'path': 'DEMO/project.json', 'type': 'blob'},
              {'path': 'DEMO/config/statuses.json', 'type': 'blob'},
              {'path': 'DEMO/config/issue-types.json', 'type': 'blob'},
              {'path': 'DEMO/config/fields.json', 'type': 'blob'},
              {'path': 'DEMO/.trackstate/index/issues.json', 'type': 'blob'},
              {'path': 'DEMO/DEMO-1/main.md', 'type': 'blob'},
            ],
          }),
          200,
        );
      case '/repos/stable/repo/contents/DEMO/project.json':
        expect(ref, 'main');
        await Future<void>.delayed(const Duration(seconds: 31));
        delayedProjectJsonCompleted = true;
        return _contentResponse(
          jsonEncode({
            'key': 'DEMO',
            'name': 'Demo Project',
            'defaultLocale': 'en',
          }),
        );
      case '/repos/stable/repo/contents/DEMO/config/statuses.json':
        return _contentResponse(
          jsonEncode([
            {'id': 'todo', 'name': 'To Do'},
          ]),
        );
      case '/repos/stable/repo/contents/DEMO/config/issue-types.json':
        return _contentResponse(
          jsonEncode([
            {'id': 'story', 'name': 'Story'},
          ]),
        );
      case '/repos/stable/repo/contents/DEMO/config/fields.json':
        return _contentResponse(
          jsonEncode([
            {
              'id': 'summary',
              'name': 'Summary',
              'type': 'string',
              'required': true,
            },
          ]),
        );
      case '/repos/stable/repo/contents/DEMO/.trackstate/index/issues.json':
        return _contentResponse(
          jsonEncode([
            {
              'key': 'DEMO-1',
              'path': 'DEMO/DEMO-1/main.md',
              'parent': null,
              'epic': null,
              'summary': 'Indexed markdown issue',
              'issueType': 'story',
              'status': 'todo',
              'labels': [],
              'updated': '2026-05-05T00:05:00Z',
              'children': [],
              'archived': false,
            },
          ]),
        );
    }
    throw StateError('Unexpected request: ${request.method} ${request.url}');
  }

  http.Response _contentResponse(String content) {
    return http.Response(
      jsonEncode({
        'content': base64Encode(utf8.encode(content)),
        'encoding': 'base64',
        'sha': 'mock-revision',
      }),
      200,
    );
  }
}
