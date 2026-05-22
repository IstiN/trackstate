import 'workspace_directory_picker_stub.dart'
    if (dart.library.js_interop) 'workspace_directory_picker_web.dart'
    as impl;

typedef WorkspaceDirectoryPicker =
    Future<String?> Function({
      String? confirmButtonText,
      String? initialDirectory,
    });

Future<String?> pickWorkspaceDirectory({
  String? confirmButtonText,
  String? initialDirectory,
}) {
  return impl.pickWorkspaceDirectory(
    confirmButtonText: confirmButtonText,
    initialDirectory: initialDirectory,
  );
}
