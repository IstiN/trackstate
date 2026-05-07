import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

class IssueDetailAccessibilityRobot {
  IssueDetailAccessibilityRobot(this.tester);

  final WidgetTester tester;

  Future<void> openSearch() async {
    await tester.tap(find.text('JQL Search').first);
    await tester.pumpAndSettle();
  }

  Future<void> openIssue(String issueKey, String issueSummary) async {
    final issueLink = find.bySemanticsLabel(
      RegExp('Open ${RegExp.escape(issueKey)} ${RegExp.escape(issueSummary)}'),
    );
    await tester.ensureVisible(issueLink.first);
    await tester.tap(issueLink.first);
    await tester.pumpAndSettle();
  }

  Finder issueDetail(String issueKey) {
    final label = 'Issue detail $issueKey';
    return find.byWidgetPredicate((widget) {
      if (widget is! Semantics) {
        return false;
      }
      return widget.properties.label == label;
    }, description: 'Semantics widget labeled $label');
  }

  List<String> visibleTextsWithinIssueDetail(String issueKey) {
    return tester
        .widgetList<Text>(
          find.descendant(
            of: issueDetail(issueKey),
            matching: find.byType(Text),
          ),
        )
        .map((widget) => widget.data?.trim())
        .whereType<String>()
        .where((value) => value.isNotEmpty)
        .toList();
  }

  List<String> semanticsLabelsInIssueDetailTraversal(String issueKey) {
    final labels = <String>[];
    final root = tester.getSemantics(issueDetail(issueKey));

    void visit(SemanticsNode node) {
      final label = node.label.replaceAll(RegExp(r'\s+'), ' ').trim();
      if (label.isNotEmpty) {
        labels.add(label);
      }
      for (final child in node.debugListChildrenInOrder(
        DebugSemanticsDumpOrder.traversalOrder,
      )) {
        visit(child);
      }
    }

    visit(root);
    return labels;
  }

  int semanticsLabelCountInIssueDetail(String issueKey, Pattern label) {
    final semanticsRoot = _semanticsFinderFor(issueDetail(issueKey));
    final matches = find.semantics.descendant(
      of: semanticsRoot,
      matching: find.semantics.byPredicate((node) {
        final nodeLabel = node.label;
        if (nodeLabel.isEmpty) {
          return false;
        }
        return switch (label) {
          RegExp regExp => regExp.hasMatch(nodeLabel),
          _ => nodeLabel.contains(label.toString()),
        };
      }, describeMatch: (_) => 'semantics node matching $label'),
      matchRoot: true,
    );
    return matches.evaluate().length;
  }

  List<String> commentActionLabels(String issueKey) {
    final heading = find.descendant(
      of: issueDetail(issueKey),
      matching: find.text('Comments'),
    );
    if (heading.evaluate().isEmpty) {
      return const [];
    }

    final commentsTop = tester.getRect(heading.first).top;
    final buttonFinders = find.descendant(
      of: issueDetail(issueKey),
      matching: find.byWidgetPredicate(
        (widget) => widget is Semantics && widget.properties.button == true,
        description: 'button semantics',
      ),
    );
    final labels = <String>[];
    final count = buttonFinders.evaluate().length;
    for (var index = 0; index < count; index++) {
      final candidate = buttonFinders.at(index);
      if (tester.getRect(candidate).top <= commentsTop) {
        continue;
      }
      final label = tester.getSemantics(candidate).label.trim();
      if (label.isNotEmpty) {
        labels.add(label);
      }
    }
    return labels;
  }

  TrackStateColors colors() {
    final context = tester.element(find.byType(Scaffold).first);
    return context.ts;
  }

  FinderBase<SemanticsNode> _semanticsFinderFor(Finder finder) {
    final semanticsId = tester.getSemantics(finder).id;
    return find.semantics.byPredicate(
      (node) => node.id == semanticsId,
      describeMatch: (_) => 'semantics node for $finder',
    );
  }
}
