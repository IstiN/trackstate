import 'package:flutter/material.dart';

Future<void> initWindow() async {}

mixin class WindowListener {
  void onWindowEvent(String eventName) {}
  void onWindowResize() {}
  void onWindowMove() {}
  void onWindowMoved() {}
  void onWindowMinimize() {}
  void onWindowMaximize() {}
  void onWindowUnmaximize() {}
  void onWindowFullScreen() {}
  void onWindowLeaveFullScreen() {}
  void onWindowFocus() {}
  void onWindowBlur() {}
  void onWindowClose() {}
  void onWindowDocked() {}
  void onWindowUndocked() {}
}

final WindowManager windowManager = WindowManager.instance;

abstract class WindowManager {
  static WindowManager? _instance;
  static WindowManager get instance => _instance ??= _WindowManagerStub();

  Future<void> ensureInitialized();
  Future<void> waitUntilReadyToShow(
    WindowOptions options,
    VoidCallback callback,
  );
  Future<void> show();
  Future<void> focus();
  Future<void> startDragging();
  Future<void> minimize();
  Future<void> maximize();
  Future<void> unmaximize();
  Future<bool> isMaximized();
  Future<void> close();
  Future<Size> getSize();
  Future<void> setSize(Size size);
  Future<Offset> getPosition();
  Future<void> center();
  Future<void> setTitle(String title);
  void addListener(WindowListener listener);
  void removeListener(WindowListener listener);
}

class _WindowManagerStub implements WindowManager {
  @override
  Future<void> ensureInitialized() async {}
  @override
  Future<void> waitUntilReadyToShow(
    WindowOptions options,
    VoidCallback callback,
  ) async {}
  @override
  Future<void> show() async {}
  @override
  Future<void> focus() async {}
  @override
  Future<void> startDragging() async {}
  @override
  Future<void> minimize() async {}
  @override
  Future<void> maximize() async {}
  @override
  Future<void> unmaximize() async {}
  @override
  Future<bool> isMaximized() async => false;
  @override
  Future<void> close() async {}
  @override
  Future<Size> getSize() async => Size.zero;
  @override
  Future<void> setSize(Size size) async {}
  @override
  Future<Offset> getPosition() async => Offset.zero;
  @override
  Future<void> center() async {}
  @override
  Future<void> setTitle(String title) async {}
  @override
  void addListener(WindowListener listener) {}
  @override
  void removeListener(WindowListener listener) {}
}

class WindowOptions {
  const WindowOptions({
    this.size,
    this.minimumSize,
    this.center,
    this.title,
    this.titleBarStyle,
    this.windowButtonVisibility,
  });

  final Size? size;
  final Size? minimumSize;
  final bool? center;
  final String? title;
  final TitleBarStyle? titleBarStyle;
  final bool? windowButtonVisibility;
}

enum TitleBarStyle { hidden, normal }
