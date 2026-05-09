import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/trackstate_app_screen.dart';
import '../../core/utils/local_git_repository_fixture.dart';

void main() {
  testWidgets(
    'TS-107 local git mode without configured identity stays in a guest/login-only state',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen =
          defaultTestingDependencies.createTrackStateAppScreen(tester)
              as TrackStateAppScreen;
      LocalGitRepositoryFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalGitRepositoryFixture.create);
        if (fixture == null) {
          throw StateError('TS-107 fixture creation did not complete.');
        }

        await tester.runAsync(
          () => fixture!.configureAuthor(userName: null, userEmail: null),
        );

        await screen.pumpLocalGitApp(repositoryPath: fixture.directory.path);
        screen.expectLocalRuntimeChrome();

        await screen.openRepositoryAccess();
        screen.expectLocalRuntimeDialog(
          repositoryPath: fixture.directory.path,
          branch: fixture.branch,
        );
        await screen.closeDialog('Close');

        final failures = <String>[];
        final visibleTexts = _formatSnapshot(screen.visibleTextsSnapshot());
        final visibleSemantics = _formatSnapshot(
          screen.visibleSemanticsLabelsSnapshot(),
        );

        if (_profileFallbackIdentityVisible(screen, 'Local User') ||
            _profileFallbackIdentityVisible(screen, 'local-user')) {
          failures.add(
            'Step 2 failed: the top-bar profile surface rendered fallback '
            'identity metadata (`Local User` / `local-user`) instead of a '
            'login-only or guest state. Visible texts: $visibleTexts. '
            'Visible semantics: $visibleSemantics.',
          );
        }

        if (!_hasGuestOrLoginOnlyIndicator(screen)) {
          failures.add(
            'Step 2 failed: the top-bar profile surface did not expose any '
            'user-facing guest/login-only indicator after Git identity metadata '
            'was removed. Expected guest initials such as LG/G/GU or explicit '
            'guest/login-only copy. Visible texts: $visibleTexts. Visible '
            'semantics: $visibleSemantics.',
          );
        }

        if (_containsUnexpectedErrorText(
          screen.visibleTextsSnapshot(),
          screen.visibleSemanticsLabelsSnapshot(),
        )) {
          failures.add(
            'Step 1 failed: launching Local Git mode surfaced an error-shaped '
            'message instead of a stable login-only state. Visible texts: '
            '$visibleTexts. Visible semantics: $visibleSemantics.',
          );
        }

        if (failures.isNotEmpty) {
          fail(
            'Expected missing Local Git identity metadata to keep the top-bar '
            'session/profile surface in an unauthenticated, login-only guest '
            'state without placeholder identity strings or runtime errors. '
            '${failures.join(' ')}',
          );
        }
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

bool _profileFallbackIdentityVisible(TrackStateAppScreen screen, String text) {
  return screen.profileSurfaceText(text).evaluate().isNotEmpty ||
      screen.profileSurfaceSemantics(text).evaluate().isNotEmpty;
}

bool _hasGuestOrLoginOnlyIndicator(TrackStateAppScreen screen) {
  const guestInitials = ['LG', 'GU', 'G'];
  for (final initials in guestInitials) {
    if (screen.profileInitialsBadge(initials).evaluate().isNotEmpty) {
      return true;
    }
  }

  const loginOnlyLabels = [
    'Guest',
    'guest',
    'Login only',
    'login only',
    'login-only',
    'Not signed in',
    'not signed in',
  ];
  for (final label in loginOnlyLabels) {
    if (screen.profileSurfaceText(label).evaluate().isNotEmpty ||
        screen.profileSurfaceSemantics(label).evaluate().isNotEmpty) {
      return true;
    }
  }

  return false;
}

bool _containsUnexpectedErrorText(
  List<String> visibleTexts,
  List<String> visibleSemantics,
) {
  const errorNeedles = [
    'Git command failed',
    'Exception',
    'Traceback',
    'Unhandled',
    'error',
    'Error',
  ];

  for (final value in [...visibleTexts, ...visibleSemantics]) {
    for (final needle in errorNeedles) {
      if (value.contains(needle)) {
        return true;
      }
    }
  }
  return false;
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }

  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
