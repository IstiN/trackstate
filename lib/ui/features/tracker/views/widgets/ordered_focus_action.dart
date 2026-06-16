import 'package:flutter/material.dart';

class OrderedFocusAction extends StatelessWidget {
  const OrderedFocusAction({super.key, required this.child, this.order});

  final Widget child;
  final double? order;

  @override
  Widget build(BuildContext context) {
    if (order == null) {
      return child;
    }
    return FocusTraversalOrder(order: NumericFocusOrder(order!), child: child);
  }
}
