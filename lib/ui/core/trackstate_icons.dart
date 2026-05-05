import 'package:flutter/material.dart';

enum TrackStateIconGlyph {
  logo,
  dashboard,
  board,
  search,
  hierarchy,
  settings,
  issue,
  epic,
  story,
  subtask,
  sync,
  gitBranch,
  comment,
  attachment,
  link,
  user,
  plus,
  moon,
  sun,
}

class TrackStateIcon extends StatelessWidget {
  const TrackStateIcon(
    this.glyph, {
    super.key,
    this.size = 20,
    this.color,
    this.filled = false,
    this.semanticLabel,
  });

  final TrackStateIconGlyph glyph;
  final double size;
  final Color? color;
  final bool filled;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final icon = CustomPaint(
      size: Size.square(size),
      painter: _TrackStateIconPainter(
        glyph: glyph,
        color: color ?? Theme.of(context).colorScheme.onSurface,
        filled: filled,
      ),
    );
    if (semanticLabel == null) return icon;
    return Semantics(label: semanticLabel, image: true, child: icon);
  }
}

class _TrackStateIconPainter extends CustomPainter {
  const _TrackStateIconPainter({
    required this.glyph,
    required this.color,
    required this.filled,
  });

  final TrackStateIconGlyph glyph;
  final Color color;
  final bool filled;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width;
    final paint = Paint()
      ..color = color
      ..strokeWidth = s * .08
      ..style = filled ? PaintingStyle.fill : PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final fillPaint = Paint()..color = color;

    switch (glyph) {
      case TrackStateIconGlyph.logo:
        final path = Path()
          ..moveTo(s * .5, s * .08)
          ..lineTo(s * .86, s * .28)
          ..lineTo(s * .86, s * .72)
          ..lineTo(s * .5, s * .92)
          ..lineTo(s * .14, s * .72)
          ..lineTo(s * .14, s * .28)
          ..close();
        canvas.drawPath(path, paint);
        canvas.drawLine(
          Offset(s * .5, s * .28),
          Offset(s * .5, s * .68),
          paint,
        );
        canvas.drawLine(
          Offset(s * .32, s * .38),
          Offset(s * .5, s * .48),
          paint,
        );
        canvas.drawLine(
          Offset(s * .68, s * .38),
          Offset(s * .5, s * .48),
          paint,
        );
      case TrackStateIconGlyph.dashboard:
        for (final rect in [
          Rect.fromLTWH(s * .12, s * .14, s * .28, s * .28),
          Rect.fromLTWH(s * .6, s * .14, s * .28, s * .2),
          Rect.fromLTWH(s * .12, s * .6, s * .28, s * .26),
          Rect.fromLTWH(s * .6, s * .52, s * .28, s * .34),
        ]) {
          canvas.drawRRect(
            RRect.fromRectAndRadius(rect, Radius.circular(s * .06)),
            paint,
          );
        }
      case TrackStateIconGlyph.board:
        for (final x in [.16, .42, .68]) {
          canvas.drawRRect(
            RRect.fromRectAndRadius(
              Rect.fromLTWH(s * x, s * .14, s * .18, s * .72),
              Radius.circular(s * .05),
            ),
            paint,
          );
        }
      case TrackStateIconGlyph.search:
        canvas.drawCircle(Offset(s * .43, s * .43), s * .24, paint);
        canvas.drawLine(
          Offset(s * .62, s * .62),
          Offset(s * .84, s * .84),
          paint,
        );
      case TrackStateIconGlyph.hierarchy:
        canvas.drawCircle(Offset(s * .28, s * .2), s * .08, paint);
        canvas.drawCircle(Offset(s * .7, s * .5), s * .08, paint);
        canvas.drawCircle(Offset(s * .7, s * .82), s * .08, paint);
        canvas.drawLine(
          Offset(s * .28, s * .28),
          Offset(s * .28, s * .82),
          paint,
        );
        canvas.drawLine(
          Offset(s * .28, s * .5),
          Offset(s * .62, s * .5),
          paint,
        );
        canvas.drawLine(
          Offset(s * .28, s * .82),
          Offset(s * .62, s * .82),
          paint,
        );
      case TrackStateIconGlyph.settings:
        canvas.drawCircle(Offset(s * .5, s * .5), s * .16, paint);
        for (var i = 0; i < 6; i++) {
          final a = i * 1.047;
          canvas.drawLine(
            Offset(s * (.5 + .27 * cos(a)), s * (.5 + .27 * sin(a))),
            Offset(s * (.5 + .38 * cos(a)), s * (.5 + .38 * sin(a))),
            paint,
          );
        }
      case TrackStateIconGlyph.epic:
        final path = Path()
          ..moveTo(s * .56, s * .08)
          ..lineTo(s * .28, s * .56)
          ..lineTo(s * .5, s * .56)
          ..lineTo(s * .44, s * .92)
          ..lineTo(s * .74, s * .42)
          ..lineTo(s * .52, s * .42)
          ..close();
        canvas.drawPath(path, paint);
      case TrackStateIconGlyph.story:
        canvas.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromLTWH(s * .22, s * .12, s * .56, s * .76),
            Radius.circular(s * .08),
          ),
          paint,
        );
        canvas.drawLine(
          Offset(s * .34, s * .32),
          Offset(s * .66, s * .32),
          paint,
        );
        canvas.drawLine(
          Offset(s * .34, s * .5),
          Offset(s * .62, s * .5),
          paint,
        );
      case TrackStateIconGlyph.subtask:
        canvas.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromLTWH(s * .18, s * .18, s * .24, s * .24),
            Radius.circular(s * .04),
          ),
          paint,
        );
        canvas.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromLTWH(s * .58, s * .58, s * .24, s * .24),
            Radius.circular(s * .04),
          ),
          paint,
        );
        canvas.drawLine(Offset(s * .42, s * .3), Offset(s * .7, s * .3), paint);
        canvas.drawLine(Offset(s * .7, s * .3), Offset(s * .7, s * .58), paint);
      case TrackStateIconGlyph.sync:
        canvas.drawArc(
          Rect.fromLTWH(s * .18, s * .18, s * .64, s * .64),
          -.3,
          4.6,
          false,
          paint,
        );
        canvas.drawLine(
          Offset(s * .78, s * .25),
          Offset(s * .82, s * .48),
          paint,
        );
        canvas.drawLine(
          Offset(s * .78, s * .25),
          Offset(s * .56, s * .28),
          paint,
        );
      case TrackStateIconGlyph.gitBranch:
        canvas.drawCircle(Offset(s * .3, s * .22), s * .09, paint);
        canvas.drawCircle(Offset(s * .3, s * .78), s * .09, paint);
        canvas.drawCircle(Offset(s * .72, s * .5), s * .09, paint);
        canvas.drawLine(
          Offset(s * .3, s * .31),
          Offset(s * .3, s * .69),
          paint,
        );
        canvas.drawLine(Offset(s * .3, s * .5), Offset(s * .63, s * .5), paint);
      case TrackStateIconGlyph.comment:
        canvas.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromLTWH(s * .14, s * .18, s * .72, s * .52),
            Radius.circular(s * .08),
          ),
          paint,
        );
        canvas.drawLine(
          Offset(s * .34, s * .7),
          Offset(s * .24, s * .88),
          paint,
        );
      case TrackStateIconGlyph.attachment:
        canvas.drawArc(
          Rect.fromLTWH(s * .22, s * .18, s * .5, s * .66),
          .7,
          4.9,
          false,
          paint,
        );
        canvas.drawLine(
          Offset(s * .5, s * .32),
          Offset(s * .34, s * .62),
          paint,
        );
      case TrackStateIconGlyph.link:
        canvas.drawArc(
          Rect.fromLTWH(s * .12, s * .28, s * .38, s * .3),
          1.2,
          4,
          false,
          paint,
        );
        canvas.drawArc(
          Rect.fromLTWH(s * .5, s * .42, s * .38, s * .3),
          -2,
          4,
          false,
          paint,
        );
      case TrackStateIconGlyph.user:
        canvas.drawCircle(Offset(s * .5, s * .34), s * .16, paint);
        canvas.drawArc(
          Rect.fromLTWH(s * .22, s * .54, s * .56, s * .36),
          3.3,
          3.1,
          false,
          paint,
        );
      case TrackStateIconGlyph.plus:
        canvas.drawLine(
          Offset(s * .5, s * .18),
          Offset(s * .5, s * .82),
          paint,
        );
        canvas.drawLine(
          Offset(s * .18, s * .5),
          Offset(s * .82, s * .5),
          paint,
        );
      case TrackStateIconGlyph.moon:
        canvas.drawCircle(Offset(s * .5, s * .5), s * .34, fillPaint);
        canvas.drawCircle(
          Offset(s * .62, s * .38),
          s * .32,
          Paint()
            ..color = const Color(0x00000000)
            ..blendMode = BlendMode.clear,
        );
      case TrackStateIconGlyph.sun:
        canvas.drawCircle(Offset(s * .5, s * .5), s * .18, paint);
        for (var i = 0; i < 8; i++) {
          final a = i * .785;
          canvas.drawLine(
            Offset(s * (.5 + .28 * cos(a)), s * (.5 + .28 * sin(a))),
            Offset(s * (.5 + .42 * cos(a)), s * (.5 + .42 * sin(a))),
            paint,
          );
        }
      case TrackStateIconGlyph.issue:
        canvas.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromLTWH(s * .18, s * .18, s * .64, s * .64),
            Radius.circular(s * .1),
          ),
          paint,
        );
        canvas.drawCircle(Offset(s * .36, s * .4), s * .03, paint);
        canvas.drawLine(
          Offset(s * .48, s * .4),
          Offset(s * .66, s * .4),
          paint,
        );
        canvas.drawLine(
          Offset(s * .34, s * .6),
          Offset(s * .66, s * .6),
          paint,
        );
    }
  }

  @override
  bool shouldRepaint(covariant _TrackStateIconPainter oldDelegate) =>
      oldDelegate.glyph != glyph ||
      oldDelegate.color != color ||
      oldDelegate.filled != filled;
}

double cos(double radians) => _cos(radians);
double sin(double radians) => _sin(radians);

double _cos(double x) {
  const pi2 = 6.283185307179586;
  x = x % pi2;
  var term = 1.0;
  var sum = 1.0;
  for (var i = 1; i < 8; i++) {
    term *= -x * x / ((2 * i - 1) * (2 * i));
    sum += term;
  }
  return sum;
}

double _sin(double x) {
  const pi2 = 6.283185307179586;
  x = x % pi2;
  var term = x;
  var sum = x;
  for (var i = 1; i < 8; i++) {
    term *= -x * x / ((2 * i) * (2 * i + 1));
    sum += term;
  }
  return sum;
}
