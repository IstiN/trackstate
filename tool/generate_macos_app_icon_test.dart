import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('generate macOS app icon source', (tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(1024, 1024);

    await tester.pumpWidget(
      const Directionality(
        textDirection: TextDirection.ltr,
        child: Center(
          child: SizedBox(
            width: 1024,
            height: 1024,
            child: CustomPaint(
              size: Size(1024, 1024),
              painter: _AppIconPainter(),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(CustomPaint).first,
      matchesGoldenFile('app_icon_source.png'),
    );
  });
}

class _AppIconPainter extends CustomPainter {
  const _AppIconPainter();

  static const _background = Color(0xFF1C1C1E);
  static const _coral = Color(0xFFE8A085);
  static const _offWhite = Color(0xFFFAF8F4);

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width;

    // Fill the full square; macOS will apply the rounded-rect icon mask.
    canvas.drawRect(
      Offset.zero & size,
      Paint()..color = _background,
    );

    final strokeWidth = s * 0.06;
    final hexPaint = Paint()
      ..color = _coral
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final hexPath = Path()
      ..moveTo(s * 0.5, s * 0.08)
      ..lineTo(s * 0.86, s * 0.28)
      ..lineTo(s * 0.86, s * 0.72)
      ..lineTo(s * 0.5, s * 0.92)
      ..lineTo(s * 0.14, s * 0.72)
      ..lineTo(s * 0.14, s * 0.28)
      ..close();
    canvas.drawPath(hexPath, hexPaint);

    final tPaint = Paint()
      ..color = _offWhite
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    canvas.drawLine(
      Offset(s * 0.5, s * 0.28),
      Offset(s * 0.5, s * 0.68),
      tPaint,
    );
    canvas.drawLine(
      Offset(s * 0.32, s * 0.38),
      Offset(s * 0.5, s * 0.48),
      tPaint,
    );
    canvas.drawLine(
      Offset(s * 0.68, s * 0.38),
      Offset(s * 0.5, s * 0.48),
      tPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _AppIconPainter oldDelegate) => false;
}
