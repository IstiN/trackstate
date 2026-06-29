import 'dart:io';

import 'package:flutter/material.dart';
import 'package:window_manager/window_manager.dart';

export 'package:window_manager/window_manager.dart'
    show WindowListener, windowManager;

Future<void> initWindow() async {
  if (!Platform.isMacOS && !Platform.isWindows && !Platform.isLinux) {
    return;
  }
  // window_manager is a platform plugin unavailable in headless tests.
  if (Platform.environment.containsKey('FLUTTER_TEST')) return;
  await windowManager.ensureInitialized();
  final options = WindowOptions(
    size: const Size(1400, 900),
    minimumSize: const Size(900, 600),
    center: true,
    // macOS titlebar styling is handled in MainFlutterWindow.swift.
    // Windows/Linux keep using the custom WindowTitleBar widget.
    titleBarStyle: Platform.isMacOS ? null : TitleBarStyle.hidden,
    windowButtonVisibility: true,
  );
  await windowManager.waitUntilReadyToShow(options, () async {
    await windowManager.show();
    await windowManager.focus();
  });
}
