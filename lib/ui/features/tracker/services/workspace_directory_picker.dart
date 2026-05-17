import 'package:file_selector/file_selector.dart';

typedef WorkspaceDirectoryPicker =
    Future<String?> Function({
      String? confirmButtonText,
      String? initialDirectory,
    });

Future<String?> pickWorkspaceDirectory({
  String? confirmButtonText,
  String? initialDirectory,
}) {
  return getDirectoryPath(
    confirmButtonText: confirmButtonText,
    initialDirectory: initialDirectory,
  );
}
