import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class IssueDetailPage {
  const IssueDetailPage(this.tester);

  final WidgetTester tester;

  Finder get searchSectionButton => find.text('JQL Search').first;

  Finder get issueDetailCard =>
      find.bySemanticsLabel(RegExp(r'^Issue detail TRACK-12$'));

  Finder get issueSummary => find.text('Implement Git sync service');

  Finder get transitionButton =>
      find.widgetWithText(FilledButton, 'Transition');

  Finder get permissionRequiredMessage => find.text('Permission required');

  Future<void> open() async {
    await tester.tap(searchSectionButton);
    await tester.pumpAndSettle();
  }

  bool get transitionActionUnavailable {
    if (transitionButton.evaluate().isEmpty) {
      return true;
    }
    return tester.widget<FilledButton>(transitionButton).onPressed == null;
  }

  bool get editActionVisible => _labelVisible('Edit');

  bool get commentActionVisible => _labelVisible('Comment');

  bool get permissionMessageVisible =>
      permissionRequiredMessage.evaluate().isNotEmpty;

  bool _labelVisible(String label) {
    final textMatches = find.text(label).evaluate().isNotEmpty;
    final semanticsMatches = find
        .bySemanticsLabel(RegExp('^$label\$'))
        .evaluate()
        .isNotEmpty;
    return textMatches || semanticsMatches;
  }
}
