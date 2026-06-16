import 'dart:io';

const int _maxLines = 3000;
const String _targetDir = 'lib';

// Known legacy violations that are being addressed separately.
// Do NOT add new entries here — extract widgets/helpers instead.
const Set<String> _legacyViolationWhitelist = {};

void main() {
  final root = Directory(_targetDir);
  if (!root.existsSync()) {
    stderr.writeln('Directory $_targetDir does not exist.');
    exit(1);
  }

  final violations = <String>[];
  final legacyViolations = <String>[];

  for (final entity in root.listSync(recursive: true)) {
    if (entity is! File) continue;
    if (!entity.path.endsWith('.dart')) continue;

    final lines = entity.readAsLinesSync();
    // Skip part files because they are library fragments, not standalone units.
    if (lines.isNotEmpty && lines.first.trim().startsWith("part of '")) {
      continue;
    }

    final lineCount = lines.length;
    if (lineCount > _maxLines) {
      final relativePath = entity.path.replaceFirst('$_targetDir/', '');
      final fullPath = '$_targetDir/$relativePath';
      final message = '$fullPath: $lineCount lines (max $_maxLines)';
      if (_legacyViolationWhitelist.contains(fullPath)) {
        legacyViolations.add(message);
      } else {
        violations.add(message);
      }
    }
  }

  if (legacyViolations.isNotEmpty) {
    stdout.writeln('Legacy file line limit violations (whitelisted):');
    for (final v in legacyViolations) {
      stdout.writeln('  $v');
    }
  }

  if (violations.isNotEmpty) {
    stderr.writeln('File line limit violations found:');
    for (final v in violations) {
      stderr.writeln('  $v');
    }
    exit(1);
  }

  stdout.writeln('All Dart files in $_targetDir are within the $_maxLines line limit.');
}
