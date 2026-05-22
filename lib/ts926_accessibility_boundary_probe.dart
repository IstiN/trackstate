import 'package:flutter/material.dart';

class Ts926ProbeSurface extends StatelessWidget {
  const Ts926ProbeSurface({super.key});

  static const Color _textColor = Color.fromRGBO(50, 50, 50, 1);
  static const Color _backgroundColor = Color.fromRGBO(153, 153, 153, 1);

  @override
  Widget build(BuildContext context) {
    final textStyle = Theme.of(context).textTheme.bodyMedium;
    return Container(
      width: 360,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: _backgroundColor,
        border: Border.all(color: const Color(0xFFD0D7E2)),
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(15, 23, 42, 0.08),
            blurRadius: 24,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Boundary contrast sample',
            style: textStyle?.copyWith(
                  color: _textColor,
                  fontSize: 16,
                  height: 1.5,
                ) ??
                const TextStyle(
                  color: _textColor,
                  fontSize: 16,
                  height: 1.5,
                ),
          ),
          const SizedBox(height: 16),
          OutlinedButton(
            onPressed: () {},
            child: const Text('Open tracker settings'),
          ),
        ],
      ),
    );
  }
}
