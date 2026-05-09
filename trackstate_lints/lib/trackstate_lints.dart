import 'dart:convert';

import 'package:analyzer/dart/analysis/analysis_context.dart';
import 'package:analyzer/dart/analysis/results.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:analyzer/diagnostic/diagnostic.dart';
import 'package:analyzer/error/error.dart';
import 'package:analyzer/error/listener.dart';
import 'package:analyzer_plugin/plugin/plugin.dart';
import 'package:analyzer_plugin/protocol/protocol_generated.dart';
import 'package:analyzer_plugin/utilities/analyzer_converter.dart';

const _hardcodedHexColorCode = LintCode(
  'avoid_hardcoded_hex_color',
  'Use a theme token instead of a hardcoded hex Color literal.',
);

class TrackStateLintsPlugin extends ServerPlugin {
  TrackStateLintsPlugin({required super.resourceProvider});

  final AnalyzerConverter _converter = AnalyzerConverter();

  @override
  List<String> get fileGlobsToAnalyze => const <String>['**/*.dart'];

  @override
  String get name => 'TrackState lints';

  @override
  String get version => '1.0.0';

  @override
  Future<void> analyzeFile({
    required AnalysisContext analysisContext,
    required String path,
  }) async {
    final result = await getResolvedUnitResult(path);
    final diagnostics = _collectDiagnostics(result);
    final pluginErrors = _converter.convertAnalysisErrors(
      diagnostics,
      lineInfo: result.lineInfo,
      options: result.analysisOptions,
    );

    channel.sendNotification(
      AnalysisErrorsParams(path, pluginErrors).toNotification(),
    );
  }

  List<Diagnostic> _collectDiagnostics(ResolvedUnitResult result) {
    final listener = RecordingDiagnosticListener();
    final reporter = DiagnosticReporter(listener, result.libraryFragment.source);
    result.unit.accept(_HardcodedHexColorVisitor(result: result, reporter: reporter));
    return listener.diagnostics;
  }
}

class _HardcodedHexColorVisitor extends RecursiveAstVisitor<void> {
  _HardcodedHexColorVisitor({
    required ResolvedUnitResult result,
    required DiagnosticReporter reporter,
  }) : _result = result,
       _reporter = reporter,
       _lines = const LineSplitter().convert(result.content),
       _fileIgnored = _ignoreForFilePattern.hasMatch(result.content);

  static final RegExp _ignoreForFilePattern = RegExp(
    r'//\s*ignore_for_file:\s*.*\bavoid_hardcoded_hex_color\b',
  );
  static final RegExp _ignoreNextLinePattern = RegExp(
    r'//\s*ignore:\s*.*\bavoid_hardcoded_hex_color\b',
  );

  final ResolvedUnitResult _result;
  final DiagnosticReporter _reporter;
  final List<String> _lines;
  final bool _fileIgnored;

  @override
  void visitInstanceCreationExpression(InstanceCreationExpression node) {
    if (!_fileIgnored &&
        !_isIgnoredOnPreviousLine(node) &&
        _isHardcodedHexColor(node)) {
      _reporter.atNode(node, _hardcodedHexColorCode);
    }
    super.visitInstanceCreationExpression(node);
  }

  bool _isHardcodedHexColor(InstanceCreationExpression node) {
    if (node.constructorName.type.toString() != 'Color') {
      return false;
    }
    if (node.argumentList.arguments.length != 1) {
      return false;
    }

    final argument = node.argumentList.arguments.first;
    if (argument is! IntegerLiteral) {
      return false;
    }

    return argument.literal.lexeme.toLowerCase().startsWith('0x');
  }

  bool _isIgnoredOnPreviousLine(AstNode node) {
    final location = _result.lineInfo.getLocation(node.offset);
    final lineIndex = location.lineNumber - 1;
    if (lineIndex <= 0) {
      return false;
    }
    return _ignoreNextLinePattern.hasMatch(_lines[lineIndex - 1]);
  }
}
