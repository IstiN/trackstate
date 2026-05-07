Uri currentBrowserUri() => Uri.base;

bool setBrowserCallbackUri({
  Map<String, String> queryParameters = const {},
  required String fragment,
}) => false;

void restoreBrowserUri(Uri uri) {}
