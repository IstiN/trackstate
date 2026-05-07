// ignore_for_file: avoid_web_libraries_in_flutter

import 'dart:html' as html;

Uri currentBrowserUri() => Uri.parse(html.window.location.href);

bool setBrowserCallbackUri({
  Map<String, String> queryParameters = const {},
  required String fragment,
}) {
  final uri = currentBrowserUri().replace(
    queryParameters: queryParameters,
    fragment: fragment,
  );
  html.window.history.replaceState(null, '', uri.toString());
  return true;
}

void restoreBrowserUri(Uri uri) {
  html.window.history.replaceState(null, '', uri.toString());
}
