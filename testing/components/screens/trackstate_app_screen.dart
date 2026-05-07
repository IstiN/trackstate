import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../frameworks/flutter/trackstate_test_runtime.dart';

class TrackStateAppScreen {
  TrackStateAppScreen(this.tester);

  final WidgetTester tester;

  Finder get localGitAccessButton =>
      find.bySemanticsLabel(RegExp('Local Git')).first;

  Finder get topBar => find.ancestor(
    of: localGitAccessButton,
    matching: find.byType(Row),
  ).first;

  Finder initialsBadge(String initials) => find.descendant(
    of: find.byType(CircleAvatar),
    matching: find.text(initials),
  );

  Finder profileInitialsBadge(String initials) => find.descendant(
    of: topBar,
    matching: find.descendant(
      of: find.byType(CircleAvatar),
      matching: find.text(initials),
    ),
  );

  Future<void> pumpApp(TrackStateRepository repository) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    await tester.pumpWidget(TrackStateApp(repository: repository));
    await _waitForAppToLoad();
  }

  Future<void> pumpLocalGitApp({required String repositoryPath}) async {
    await pumpApp(
      await createLocalGitTestRepository(
        tester: tester,
        repositoryPath: repositoryPath,
      ),
    );
  }

  void resetView() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }

  Future<void> openRepositoryAccess() async {
    await tester.tap(localGitAccessButton);
    await tester.pumpAndSettle();
  }

  TrackerViewModel currentViewModel() {
    final dynamic state = tester.state(find.byType(TrackStateApp));
    return state.viewModel as TrackerViewModel;
  }

  RepositoryUser resolvedUser() {
    final user = currentViewModel().connectedUser;
    if (user == null) {
      throw StateError('Expected a resolved repository user.');
    }
    return user;
  }

  void expectLocalRuntimeChrome() {
    expect(localGitAccessButton, findsOneWidget);
    expect(find.text('Local Git'), findsOneWidget);
    expect(find.text('Connect GitHub'), findsNothing);
  }

  void expectResolvedLocalAuthorIdentity({
    required String userName,
    required String userEmail,
    required String initials,
  }) {
    final user = resolvedUser();
    expect(user.displayName, userName);
    expect(user.login, userEmail);
    expect(profileInitialsBadge(initials), findsOneWidget);
  }

  void expectLocalRuntimeDialog({
    required String repositoryPath,
    required String branch,
  }) {
    expect(find.text('Local Git runtime'), findsOneWidget);
    expect(find.text('Repository: $repositoryPath'), findsOneWidget);
    expect(find.text('Branch: $branch'), findsOneWidget);
    expect(
      find.textContaining('GitHub tokens are not used in this runtime'),
      findsOneWidget,
    );
  }

  Future<void> _waitForAppToLoad() async {
    for (var i = 0; i < 100; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      if (!currentViewModel().isLoading) {
        await tester.pump(const Duration(milliseconds: 100));
        return;
      }
    }
    throw TimeoutException('TrackState app did not finish loading in time.');
  }
}
