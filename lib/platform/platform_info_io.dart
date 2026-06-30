import 'dart:io';

bool get isMacOS => Platform.isMacOS;
bool get isWindows => Platform.isWindows;
bool get isLinux => Platform.isLinux;
bool get isDesktop => isMacOS || isWindows || isLinux;
bool get isRunningInTest => Platform.environment.containsKey('FLUTTER_TEST');
