import 'package:flutter/widgets.dart';

class BrowserFocusableControl extends StatelessWidget {
  const BrowserFocusableControl({
    super.key,
    required this.child,
    required this.label,
    required this.onPressed,
    this.focusTargetId,
    this.panelId,
    this.rowId,
    this.controlsId,
    this.expanded,
    this.selectedRow = false,
    this.focusableWhenDisabled = false,
    this.tabIndex,
  });

  final Widget child;
  final String label;
  final VoidCallback? onPressed;
  final String? focusTargetId;
  final String? panelId;
  final String? rowId;
  final String? controlsId;
  final bool? expanded;
  final bool selectedRow;
  final bool focusableWhenDisabled;
  final int? tabIndex;

  @override
  Widget build(BuildContext context) => child;
}
