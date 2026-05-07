import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../core/interfaces/issue_aggregate_loader.dart';
import '../../core/interfaces/local_git_repository_port.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../screens/trackstate_app_screen.dart';
import '../services/issue_aggregate_probe.dart';
import '../services/local_git_repository_service.dart';

class DefaultTestingDependencyFactory {
  const DefaultTestingDependencyFactory();

  IssueAggregateLoader createIssueAggregateLoader(
    TrackStateRepository repository,
  ) => IssueAggregateProbe(repository);

  LocalGitRepositoryPort createLocalGitRepositoryPort(WidgetTester tester) =>
      LocalGitRepositoryService(tester);

  TrackStateAppComponent createTrackStateAppScreen(WidgetTester tester) =>
      TrackStateAppScreen(
        tester,
        repositoryService: createLocalGitRepositoryPort(tester),
      );
}
