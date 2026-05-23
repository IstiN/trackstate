import 'workspace_directory_picker_stub.dart'
    if (dart.library.js_interop) 'workspace_directory_picker_web.dart'
    as impl;

typedef WorkspaceDirectoryPicker =
    Future<String?> Function({
      String? confirmButtonText,
      String? initialDirectory,
    });

class WorkspaceDirectorySelectionMismatchException implements Exception {
  const WorkspaceDirectorySelectionMismatchException(this.message);

  final String message;

  @override
  String toString() => message;
}

Future<String?> pickWorkspaceDirectory({
  String? confirmButtonText,
  String? initialDirectory,
}) {
  return impl.pickWorkspaceDirectory(
    confirmButtonText: confirmButtonText,
    initialDirectory: initialDirectory,
  );
}
