import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  group('startup workspace routing', () {
    test('web startup without saved workspaces opens Project Settings', () {
      expect(
        shouldOpenProjectSettingsForStartupWithoutSavedWorkspaces(
          isWeb: true,
          hasRepository: false,
          hasProfiles: false,
        ),
        isTrue,
      );
      expect(
        shouldShowWorkspaceOnboardingForStartup(
          isWeb: true,
          hasRepository: false,
          hasProfiles: false,
        ),
        isFalse,
      );
    });

    test('native startup without saved workspaces keeps local onboarding', () {
      expect(
        shouldOpenProjectSettingsForStartupWithoutSavedWorkspaces(
          isWeb: false,
          hasRepository: false,
          hasProfiles: false,
        ),
        isFalse,
      );
      expect(
        shouldShowWorkspaceOnboardingForStartup(
          isWeb: false,
          hasRepository: false,
          hasProfiles: false,
        ),
        isTrue,
      );
    });

    test(
      'saved workspaces or an injected repository bypass first-run routing',
      () {
        expect(
          shouldOpenProjectSettingsForStartupWithoutSavedWorkspaces(
            isWeb: true,
            hasRepository: false,
            hasProfiles: true,
          ),
          isFalse,
        );
        expect(
          shouldOpenProjectSettingsForStartupWithoutSavedWorkspaces(
            isWeb: true,
            hasRepository: true,
            hasProfiles: false,
          ),
          isFalse,
        );
        expect(
          shouldShowWorkspaceOnboardingForStartup(
            isWeb: false,
            hasRepository: false,
            hasProfiles: true,
          ),
          isFalse,
        );
        expect(
          shouldShowWorkspaceOnboardingForStartup(
            isWeb: false,
            hasRepository: true,
            hasProfiles: false,
          ),
          isFalse,
        );
      },
    );
  });
}
