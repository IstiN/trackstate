import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../core/interfaces/issue_aggregate_loader.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../core/interfaces/testing_dependency_factory.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../screens/trackstate_app_screen.dart';
import '../services/issue_aggregate_probe.dart';
import '../services/local_git_repository_service.dart';

class DefaultTestingDependencyFactory implements TestingDependencyFactory {
  const DefaultTestingDependencyFactory();

  @override
  IssueAggregateLoader createIssueAggregateLoader(
    TrackStateRepository repository,
  ) => IssueAggregateProbe(repository);

  @override
  LocalGitRepositoryPort createLocalGitRepositoryPort(WidgetTester tester) =>
      LocalGitRepositoryService(tester);

  @override
  TrackStateAppComponent createTrackStateAppScreen(WidgetTester tester) =>
      TrackStateAppScreen(
        tester,
        repositoryService: createLocalGitRepositoryPort(tester),
      );
}
