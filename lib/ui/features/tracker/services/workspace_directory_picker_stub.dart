import 'package:file_selector/file_selector.dart';

Future<String?> pickWorkspaceDirectory({
  String? confirmButtonText,
  String? initialDirectory,
}) {
  return getDirectoryPath(
    confirmButtonText: confirmButtonText,
    initialDirectory: initialDirectory,
  );
}
