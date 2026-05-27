import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class IssueAggregateLoader {
  Future<TrackStateIssue> loadIssue(String issueKey);
}
