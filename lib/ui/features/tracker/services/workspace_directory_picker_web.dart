@JS()
library;

import 'dart:async';
import 'dart:js_interop';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/foundation.dart';

import '../../../../data/repositories/browser_local_workspace_repository.dart';
import 'workspace_directory_picker.dart';

typedef BrowserDirectoryAccessRequester =
    Future<Object?> Function({
      String? confirmButtonText,
      String? initialDirectory,
    });
typedef BrowserWorkspaceSelectionPersister =
    Future<void> Function({
      required String workspacePath,
      required Object selection,
    });

extension type _DirectoryHandle(JSObject _value) implements JSObject {
  external String get name;
}

@JS('window.showDirectoryPicker')
external JSPromise<JSAny?> _showDirectoryPicker();

@visibleForTesting
BrowserDirectoryAccessRequester browserDirectoryAccessRequester =
    _requestBrowserDirectoryAccess;

@visibleForTesting
BrowserWorkspaceSelectionPersister browserWorkspaceSelectionPersister =
    rememberBrowserLocalWorkspaceSelection;

Future<String?> pickWorkspaceDirectory({
  String? confirmButtonText,
  String? initialDirectory,
}) async {
  final normalizedInitialDirectory = _normalizeDirectoryPath(initialDirectory);
  try {
    final selection = await browserDirectoryAccessRequester(
      confirmButtonText: confirmButtonText,
      initialDirectory: normalizedInitialDirectory,
    );
    final normalizedSelection = _normalizeSelection(
      selection,
      initialDirectory: normalizedInitialDirectory,
    );
    if (normalizedSelection != null &&
        selection != null &&
        selection is! String) {
      _rememberBrowserWorkspaceSelection(
        workspacePath: normalizedSelection,
        selection: selection,
      );
    }
    return normalizedSelection;
  } on Object catch (error) {
    if (_looksLikePickerCancellation(error)) {
      return null;
    }
    rethrow;
  }
}

void _rememberBrowserWorkspaceSelection({
  required String workspacePath,
  required Object selection,
}) {
  unawaited(
    browserWorkspaceSelectionPersister(
      workspacePath: workspacePath,
      selection: selection,
    ).catchError((Object error, StackTrace stackTrace) {
      FlutterError.reportError(
        FlutterErrorDetails(
          exception: error,
          stack: stackTrace,
          library: 'workspace_directory_picker_web',
          context: ErrorDescription(
            'while persisting browser local workspace access',
          ),
        ),
      );
    }),
  );
}

Future<Object?> _requestBrowserDirectoryAccess({
  String? confirmButtonText,
  String? initialDirectory,
}) async {
  try {
    return await _showDirectoryPicker().toDart;
  } on Object catch (error) {
    if (_looksLikeMissingBrowserPicker(error)) {
      return getDirectoryPath(
        confirmButtonText: confirmButtonText,
        initialDirectory: initialDirectory,
      );
    }
    rethrow;
  }
}

String? _normalizeSelection(
  Object? selection, {
  required String? initialDirectory,
}) {
  if (selection == null) {
    return null;
  }
  if (selection case final String path) {
    return _normalizeDirectoryPath(path);
  }
  final handleName = _directoryHandleName(selection);
  if (initialDirectory != null) {
    final expectedDirectoryName = _directoryName(initialDirectory);
    if (handleName != null &&
        expectedDirectoryName != null &&
        handleName != expectedDirectoryName) {
      throw const WorkspaceDirectorySelectionMismatchException(
        'Selected directory does not match the saved workspace configuration.',
      );
    }
    return initialDirectory;
  }
  if (handleName != null) {
    return handleName;
  }
  return null;
}

String? _directoryHandleName(Object selection) {
  if (selection case {'name': final Object? rawName}) {
    final name = rawName?.toString().trim();
    if (name == null || name.isEmpty) {
      return null;
    }
    return name;
  }
  try {
    final name = _DirectoryHandle(selection as JSObject).name.trim();
    if (name.isEmpty) {
      return null;
    }
    return name;
  } on Object {
    return null;
  }
}

String? _normalizeDirectoryPath(String? path) {
  final trimmed = path?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}

String? _directoryName(String? path) {
  final normalized = _normalizeDirectoryPath(path);
  if (normalized == null) {
    return null;
  }
  final withoutTrailingSeparators = normalized.replaceAll(
    RegExp(r'[\\/]+$'),
    '',
  );
  final slashIndex = withoutTrailingSeparators.lastIndexOf('/');
  final backslashIndex = withoutTrailingSeparators.lastIndexOf('\\');
  final lastSeparator = slashIndex > backslashIndex
      ? slashIndex
      : backslashIndex;
  return lastSeparator >= 0
      ? withoutTrailingSeparators.substring(lastSeparator + 1)
      : withoutTrailingSeparators;
}

bool _looksLikePickerCancellation(Object error) {
  final message = '$error'.toLowerCase();
  return message.contains('aborterror') ||
      message.contains('the user aborted a request');
}

bool _looksLikeMissingBrowserPicker(Object error) {
  final message = '$error'.toLowerCase();
  return message.contains('showdirectorypicker') &&
      (message.contains('not a function') ||
          message.contains('is not defined') ||
          message.contains('undefined'));
}
