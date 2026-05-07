// ignore_for_file: depend_on_referenced_packages

import 'package:url_launcher_platform_interface/link.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

class RecordingUrlLauncherPlatform extends UrlLauncherPlatform {
  Uri? lastLaunchedUri;
  String? lastWebOnlyWindowName;
  Map<String, String>? lastHeaders;
  bool? lastUseSafariVc;
  bool? lastUseWebView;
  bool? lastEnableJavaScript;
  bool? lastEnableDomStorage;
  bool? lastUniversalLinksOnly;

  @override
  LinkDelegate? get linkDelegate => null;

  @override
  Future<bool> canLaunch(String url) async => true;

  @override
  Future<bool> launch(
    String url, {
    required bool useSafariVC,
    required bool useWebView,
    required bool enableJavaScript,
    required bool enableDomStorage,
    required bool universalLinksOnly,
    required Map<String, String> headers,
    String? webOnlyWindowName,
  }) async {
    lastLaunchedUri = Uri.parse(url);
    lastWebOnlyWindowName = webOnlyWindowName;
    lastHeaders = headers;
    lastUseSafariVc = useSafariVC;
    lastUseWebView = useWebView;
    lastEnableJavaScript = enableJavaScript;
    lastEnableDomStorage = enableDomStorage;
    lastUniversalLinksOnly = universalLinksOnly;
    return true;
  }

  @override
  Future<void> closeWebView() async {}
}
