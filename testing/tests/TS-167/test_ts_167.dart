import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import '../../fixtures/repositories/ts135_archived_issue_fixture.dart';

void main() {
  test(
    'TS-167 archives an issue without overwriting existing frontmatter metadata',
    () async {
      final fixture = await Ts135ArchivedIssueFixture.create(
        includePreservedMetadata: true,
      );
      addTearDown(fixture.dispose);

      final beforeArchival = await fixture.observeBeforeArchivalState();
      final beforeFrontmatter = _frontmatterWithoutArchived(
        beforeArchival.mainMarkdown,
      );

      expect(
        beforeArchival.issue.priority,
        Ts135ArchivedIssueFixture.preservedPriority,
        reason:
            'Step 1 failed: TRACK-555 must start with priority ${Ts135ArchivedIssueFixture.preservedPriority.name} before archiveIssue runs.',
      );
      expect(
        beforeArchival.issue.priorityId,
        Ts135ArchivedIssueFixture.preservedPriorityId,
        reason:
            'Step 1 failed: TRACK-555 must preserve the machine priority id ${Ts135ArchivedIssueFixture.preservedPriorityId} before archiveIssue runs.',
      );
      expect(
        beforeArchival.issue.components,
        Ts135ArchivedIssueFixture.preservedComponents,
        reason:
            'Step 1 failed: TRACK-555 must start with the expected components so TS-167 can detect archive metadata corruption.',
      );
      expect(
        beforeArchival.issue.fixVersionIds,
        Ts135ArchivedIssueFixture.preservedFixVersionIds,
        reason:
            'Step 1 failed: TRACK-555 must start with the expected fixVersions so TS-167 can detect archive metadata corruption.',
      );
      expect(
        _frontmatterMetadataSummary(beforeArchival.mainMarkdown),
        _expectedFrontmatterMetadataSummary(),
        reason:
            'Step 2 failed: the seeded YAML frontmatter must contain the exact priority, components, and fixVersions values before archiveIssue runs.\nObserved frontmatter:\n$beforeFrontmatter',
      );
      expect(
        beforeArchival.standardSearchResults.single.priorityId,
        Ts135ArchivedIssueFixture.preservedPriorityId,
        reason:
            'Human-style verification failed before archiving: a standard repository search should expose the same priority clients rely on.',
      );
      expect(
        beforeArchival.standardSearchResults.single.components,
        Ts135ArchivedIssueFixture.preservedComponents,
        reason:
            'Human-style verification failed before archiving: a standard repository search should expose the same components clients rely on.',
      );
      expect(
        beforeArchival.standardSearchResults.single.fixVersionIds,
        Ts135ArchivedIssueFixture.preservedFixVersionIds,
        reason:
            'Human-style verification failed before archiving: a standard repository search should expose the same fixVersions clients rely on.',
      );

      final afterArchival = await fixture.archiveIssueViaRepositoryService();
      final afterFrontmatter = _frontmatterWithoutArchived(
        afterArchival.mainMarkdown,
      );
      final archivedSearchIssue = afterArchival.standardSearchResults.single;

      expect(
        afterArchival.issue.isArchived,
        isTrue,
        reason:
            'Step 3 failed: archiveIssue must mark TRACK-555 as archived in the repository issue model.',
      );
      expect(
        afterArchival.mainMarkdown,
        contains('archived: true'),
        reason:
            'Step 3 failed: archiveIssue must persist archived: true into the physical YAML frontmatter.',
      );
      expect(
        afterArchival.issue.priority,
        beforeArchival.issue.priority,
        reason:
            'Expected result mismatch: archiveIssue changed the parsed priority from ${beforeArchival.issue.priority.name} to ${afterArchival.issue.priority.name}.',
      );
      expect(
        afterArchival.issue.priorityId,
        beforeArchival.issue.priorityId,
        reason:
            'Expected result mismatch: archiveIssue changed the priority id from ${beforeArchival.issue.priorityId} to ${afterArchival.issue.priorityId}.',
      );
      expect(
        afterArchival.issue.components,
        beforeArchival.issue.components,
        reason:
            'Expected result mismatch: archiveIssue changed the parsed components from ${beforeArchival.issue.components} to ${afterArchival.issue.components}.',
      );
      expect(
        afterArchival.issue.fixVersionIds,
        beforeArchival.issue.fixVersionIds,
        reason:
            'Expected result mismatch: archiveIssue changed the parsed fixVersions from ${beforeArchival.issue.fixVersionIds} to ${afterArchival.issue.fixVersionIds}.',
      );
      expect(
        afterFrontmatter,
        beforeFrontmatter,
        reason:
            'Expected result mismatch: archiveIssue rewrote frontmatter metadata other than the archived flag.\nBefore:\n$beforeFrontmatter\n\nAfter:\n$afterFrontmatter',
      );
      expect(
        _frontmatterMetadataSummary(afterArchival.mainMarkdown),
        _expectedFrontmatterMetadataSummary(),
        reason:
            'Expected result mismatch: the physical YAML frontmatter no longer preserves the original priority, components, and fixVersions values after archiving.\nObserved frontmatter:\n$afterFrontmatter',
      );
      expect(
        archivedSearchIssue.isArchived,
        isTrue,
        reason:
            'Human-style verification failed after archiving: a standard repository search should expose TRACK-555 as archived to integrated clients.',
      );
      expect(
        archivedSearchIssue.priorityId,
        Ts135ArchivedIssueFixture.preservedPriorityId,
        reason:
            'Human-style verification failed after archiving: the observable search result changed priority metadata.',
      );
      expect(
        archivedSearchIssue.components,
        Ts135ArchivedIssueFixture.preservedComponents,
        reason:
            'Human-style verification failed after archiving: the observable search result changed components metadata.',
      );
      expect(
        archivedSearchIssue.fixVersionIds,
        Ts135ArchivedIssueFixture.preservedFixVersionIds,
        reason:
            'Human-style verification failed after archiving: the observable search result changed fixVersions metadata.',
      );
    },
  );
}

String _frontmatterWithoutArchived(String markdown) {
  final frontmatter = _frontmatter(markdown);
  return frontmatter
      .replaceAll(RegExp(r'^archived:\s*true\s*$\n?', multiLine: true), '')
      .trim();
}

String _frontmatter(String markdown) {
  final lines = const LineSplitter().convert(markdown);
  if (lines.length < 3 || lines.first.trim() != '---') {
    throw StateError('Expected issue markdown with YAML frontmatter.');
  }
  final closingIndex = lines.indexWhere((line) => line.trim() == '---', 1);
  if (closingIndex == -1) {
    throw StateError('Expected closing YAML frontmatter delimiter.');
  }
  return lines.sublist(1, closingIndex).join('\n');
}

String _frontmatterMetadataSummary(String markdown) {
  final lines = const LineSplitter().convert(
    _frontmatterWithoutArchived(markdown),
  );
  final metadataLines = <String>[];
  var includeIndentedLines = false;
  for (final line in lines) {
    final isMetadataKey =
        line == 'priority: ${Ts135ArchivedIssueFixture.preservedPriorityId}' ||
        line == 'components:' ||
        line == 'fixVersions:';
    if (isMetadataKey) {
      metadataLines.add(line);
      includeIndentedLines = line == 'components:' || line == 'fixVersions:';
      continue;
    }
    if (includeIndentedLines && line.startsWith('  - ')) {
      metadataLines.add(line);
      continue;
    }
    includeIndentedLines = false;
  }
  return metadataLines.join('\n');
}

String _expectedFrontmatterMetadataSummary() =>
    '''
priority: ${Ts135ArchivedIssueFixture.preservedPriorityId}
components:
  - ${Ts135ArchivedIssueFixture.preservedComponents[0]}
  - ${Ts135ArchivedIssueFixture.preservedComponents[1]}
fixVersions:
  - ${Ts135ArchivedIssueFixture.preservedFixVersionIds[0]}
  - ${Ts135ArchivedIssueFixture.preservedFixVersionIds[1]}''';
