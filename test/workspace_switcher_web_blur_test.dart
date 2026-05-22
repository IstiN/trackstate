import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'desktop web workspace switcher tabs into the open panel and Escape restores trigger focus',
    (tester) async {
      if (!kIsWeb) {
        return;
      }

      final semantics = tester.ensureSemantics();
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:alpha/repo@main',
              displayName: 'alpha/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alpha/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:beta/repo@main',
              displayName: 'beta/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'beta/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'hosted:alpha/repo@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
        await tester.pumpWidget(
          TrackStateApp(
            workspaceProfileService: service,
            openHostedRepository:
                ({
                  required String repository,
                  required String defaultBranch,
                  required String writeBranch,
                }) async => const DemoTrackStateRepository(),
          ),
        );
        await _pumpUntilVisible(tester, find.byType(TextField));

        final desktopCandidates = <String, Finder>{
          'Workspace switcher': find.byKey(
            const ValueKey('workspace-switcher-trigger'),
          ),
          'Active workspace': find.byKey(
            const ValueKey('workspace-hosted:alpha/repo@main'),
          ),
          'Search issues': find.byType(TextField),
          'Repository': find.widgetWithText(TextFormField, 'Repository'),
        };

        await tester.tap(desktopCandidates['Workspace switcher']!);
        await tester.pumpAndSettle();

        await _pumpUntilVisible(
          tester,
          find.widgetWithText(TextFormField, 'Repository'),
        );
        expect(_focusedLabel(tester, desktopCandidates), 'Workspace switcher');

        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.pump();
        await tester.pumpAndSettle();

        expect(_focusedLabel(tester, desktopCandidates), 'Active workspace');

        await tester.sendKeyEvent(LogicalKeyboardKey.escape);
        await tester.pump();
        await tester.pumpAndSettle();

        await _pumpUntilGone(tester, find.text('Saved workspaces'));

        await tester.sendKeyEvent(LogicalKeyboardKey.enter);
        await tester.pump();
        await _pumpUntilVisible(
          tester,
          find.widgetWithText(TextFormField, 'Repository'),
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'desktop web workspace row activation keeps focus on the browser-owned control',
    (tester) async {
      if (!kIsWeb) {
        return;
      }

      final semantics = tester.ensureSemantics();
      final service = _MemoryWorkspaceProfileService(
        WorkspaceProfilesState(
          profiles: const [
            WorkspaceProfile(
              id: 'hosted:alpha/repo@main',
              displayName: 'alpha/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'alpha/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
            WorkspaceProfile(
              id: 'hosted:beta/repo@main',
              displayName: 'beta/repo',
              targetType: WorkspaceProfileTargetType.hosted,
              target: 'beta/repo',
              defaultBranch: 'main',
              writeBranch: 'main',
            ),
          ],
          activeWorkspaceId: 'hosted:alpha/repo@main',
          migrationComplete: true,
        ),
      );

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
        await tester.pumpWidget(
          TrackStateApp(
            workspaceProfileService: service,
            openHostedRepository:
                ({
                  required String repository,
                  required String defaultBranch,
                  required String writeBranch,
                }) async => const DemoTrackStateRepository(),
          ),
        );
        await _pumpUntilVisible(tester, find.byType(TextField));

        await tester.tap(
          find.byKey(const ValueKey('workspace-switcher-trigger')),
          warnIfMissed: false,
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const ValueKey('workspace-switcher-sheet')),
          findsOneWidget,
        );

        await tester.tap(
          find.byKey(const ValueKey('workspace-hosted:beta/repo@main')),
          warnIfMissed: false,
        );
        await tester.pump();
        await tester.pumpAndSettle();

        expect(service.state.activeWorkspaceId, 'hosted:beta/repo@main');
        expect(
          FocusManager.instance.primaryFocus,
          isNull,
          reason:
              'Selecting a saved workspace on web should keep focus in the '
              'browser-owned path instead of re-entering Flutter focus nodes.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}

class _MemoryWorkspaceProfileService implements WorkspaceProfileService {
  _MemoryWorkspaceProfileService(this.state);

  WorkspaceProfilesState state;

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) {
    throw UnimplementedError();
  }

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async => null;

  @override
  Future<WorkspaceProfilesState> loadState() async => state;

  @override
  Future<WorkspaceProfilesState> saveHostedAccessMode(
    String workspaceId,
    HostedWorkspaceAccessMode? accessMode,
  ) async => state;

  @override
  Future<WorkspaceProfilesState> saveLocalWorkspaceAvailability(
    String workspaceId, {
    required bool isAvailable,
  }) async => state;

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async {
    state = state.copyWith(activeWorkspaceId: workspaceId);
    return state;
  }

  @override
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  }) {
    throw UnimplementedError();
  }
}

Future<void> _pumpUntilVisible(
  WidgetTester tester,
  Finder finder, {
  int maxPumps = 60,
  Duration step = const Duration(milliseconds: 100),
}) async {
  for (var index = 0; index < maxPumps; index += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  throw TestFailure('Expected $finder to become visible.');
}

Future<void> _pumpUntilGone(
  WidgetTester tester,
  Finder finder, {
  int maxPumps = 60,
  Duration step = const Duration(milliseconds: 100),
}) async {
  for (var index = 0; index < maxPumps; index += 1) {
    await tester.pump(step);
    if (finder.evaluate().isEmpty) {
      return;
    }
  }
  throw TestFailure('Expected $finder to disappear.');
}

String? _focusedLabel(WidgetTester tester, Map<String, Finder> candidates) {
  final focusedSemantics = find.semantics.byPredicate(
    (node) => node.getSemanticsData().flagsCollection.isFocused,
    describeMatch: (_) => 'focused semantics node',
  );
  if (focusedSemantics.evaluate().isEmpty) {
    return null;
  }

  for (final entry in candidates.entries) {
    final matches = entry.value.evaluate().length;
    if (matches == 0) {
      continue;
    }
    for (var index = 0; index < matches; index += 1) {
      final candidateFinder = entry.value.at(index);
      if (_focusWithinFinder(candidateFinder)) {
        return entry.key;
      }
      final candidateSemantics = _semanticsFinderFor(
        tester: tester,
        finder: candidateFinder,
      );
      final ownsFocusedNode = find.semantics.descendant(
        of: candidateSemantics,
        matching: focusedSemantics,
        matchRoot: true,
      );
      if (ownsFocusedNode.evaluate().isNotEmpty) {
        return entry.key;
      }
    }
  }

  return null;
}

bool _focusWithinFinder(Finder ancestorFinder) {
  final focusContext = FocusManager.instance.primaryFocus?.context;
  if (focusContext == null) {
    return false;
  }
  final targetElements = ancestorFinder.evaluate().toSet();
  if (targetElements.contains(focusContext)) {
    return true;
  }
  var found = false;
  focusContext.visitAncestorElements((element) {
    if (targetElements.contains(element)) {
      found = true;
      return false;
    }
    return true;
  });
  return found;
}

FinderBase<SemanticsNode> _semanticsFinderFor({
  required WidgetTester tester,
  required Finder finder,
}) {
  final semanticsId = tester.getSemantics(finder).id;
  return find.semantics.byPredicate(
    (node) => node.id == semanticsId,
    describeMatch: (_) => 'semantics node for $finder',
  );
}
