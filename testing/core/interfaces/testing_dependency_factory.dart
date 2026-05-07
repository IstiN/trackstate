import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import 'issue_aggregate_loader.dart';
import 'local_git_repository_port.dart';
import 'trackstate_app_component.dart';

abstract interface class TestingDependencyFactory {
  LocalGitRepositoryPort createLocalGitRepositoryPort(WidgetTester tester);

  IssueAggregateLoader createIssueAggregateLoader(
    TrackStateRepository repository,
  );

  TrackStateAppComponent createTrackStateAppScreen(WidgetTester tester);
}
