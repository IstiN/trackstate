import 'package:flutter/widgets.dart';

class BrowserHeaderControlsFlexContainer extends StatelessWidget {
  const BrowserHeaderControlsFlexContainer({
    super.key,
    required this.semanticsIdentifier,
    required this.child,
  });

  final String semanticsIdentifier;
  final Widget child;

  @override
  Widget build(BuildContext context) => child;
}

void syncBrowserHeaderControlsFlexContainer({
  required String semanticsIdentifier,
}) {}

void restoreBrowserHeaderControlsFlexContainer({
  required String semanticsIdentifier,
}) {}
