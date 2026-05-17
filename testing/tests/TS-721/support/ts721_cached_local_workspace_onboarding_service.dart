import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';

class Ts721CachedLocalWorkspaceOnboardingService
    implements LocalWorkspaceOnboardingService {
  Ts721CachedLocalWorkspaceOnboardingService({
    required LocalWorkspaceInspection inspection,
  }) : _inspection = inspection;

  final LocalWorkspaceInspection _inspection;

  @override
  Future<LocalWorkspaceInspection> inspectFolder(String folderPath) async {
    final normalizedPath = _normalizePath(folderPath);
    final expectedPath = _normalizePath(_inspection.folderPath);
    if (normalizedPath != expectedPath) {
      throw StateError(
        'TS-721 expected onboarding to inspect "$expectedPath", but received "$normalizedPath".',
      );
    }
    return _inspection;
  }

  @override
  Future<LocalWorkspaceSetupResult> initializeFolder({
    required LocalWorkspaceInspection inspection,
    required String workspaceName,
    required String writeBranch,
  }) {
    throw StateError(
      'TS-721 should open an existing local workspace and must not initialize a new one.',
    );
  }
}

String _normalizePath(String path) {
  var normalized = path.replaceAll('\\', '/').trim();
  while (normalized.length > 1 && normalized.endsWith('/')) {
    normalized = normalized.substring(0, normalized.length - 1);
  }
  return normalized;
}
