import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../core/interfaces/issue_aggregate_loader.dart';
import '../../core/interfaces/issue_link_mutation_driver.dart';
import '../../core/interfaces/issue_link_mutation_port.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../frameworks/flutter/flutter_issue_link_mutation_driver.dart';
import '../screens/trackstate_app_screen.dart';
import '../services/issue_aggregate_probe.dart';
import '../services/issue_link_mutation_service.dart';
import '../services/local_git_repository_service.dart';

class DefaultTestingDependencyFactory {
  const DefaultTestingDependencyFactory();

  IssueAggregateLoader createIssueAggregateLoader(
    TrackStateRepository repository,
  ) => IssueAggregateProbe(repository);

  IssueLinkMutationDriver createIssueLinkMutationDriver(WidgetTester tester) =>
      FlutterIssueLinkMutationDriver(tester);

  IssueLinkMutationPort createIssueLinkMutationPort(WidgetTester tester) =>
      IssueLinkMutationService(
        mutationDriver: createIssueLinkMutationDriver(tester),
      );

  LocalGitRepositoryPort createLocalGitRepositoryPort(WidgetTester tester) {
    return LocalGitRepositoryService(tester);
  }

  TrackStateAppComponent createTrackStateAppScreen(WidgetTester tester) =>
      TrackStateAppScreen(
        tester,
        repositoryService: createLocalGitRepositoryPort(tester),
      );
}
